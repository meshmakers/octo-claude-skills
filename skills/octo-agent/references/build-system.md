# OctoMesh Build System Deep Reference

## DebugL Configuration

`DebugL` is the mandatory local development configuration. It:
- Sets `OctoVersion` to `999.0.0` for all NuGet packages (the public release suffix is `3.3.*`; private is `0.1.*`)
- Resolves NuGet packages from the local `../nuget/` folder instead of remote feeds
- Enables peer-repo dependency resolution without publishing to any feed

All services target **`net10.0`** (build output lands in `bin/DebugL/net10.0/`).

**Never use `Debug` or `Release` for local development** — those configurations resolve packages from remote NuGet feeds and will fail if the latest packages haven't been published.

## Build Dependency Chain

The `Invoke-BuildAll` script enforces this strict order. Each repo's NuGet packages are copied to `./nuget/` after building, making them available to downstream repos:

```
1. mm-common                          → Meshmakers.Common.* packages
2. octo-distributedEventHub           → Meshmakers.Octo.Common.DistributionEventHub(.MongoDB)
3. octo-construction-kit-engine       → Meshmakers.Octo.ConstructionKit.*, Runtime.*, Models.System, Models.StreamData
4. octo-sdk                           → Meshmakers.Octo.Sdk.*, Communication.Contracts
5. octo-construction-kit-engine-mongodb → Meshmakers.Octo.Runtime.*.MongoDb, Runtime.Engine.CrateDb
6. octo-common-services               → Meshmakers.Octo.Services.*
7. octo-mesh-adapter                  → Meshmakers.Octo.MeshAdapter.*, Sdk.MeshAdapter
8. octo-bot-services                  → Meshmakers.Octo.ConstructionKit.Models.System.Bot
9. octo-communication-controller-services → Meshmakers.Octo.ConstructionKit.Models.System.Communication
10. All remaining repos (services, tools, frontends) — alphabetical
```

**Step 9 matters:** `octo-communication-controller-services` produces `System.Communication`, which `octo-ai-services` consumes. It has an explicit slot before the alphabetical fallback because `a < c` would otherwise build `octo-ai-services` first and break its restore. When selectively building anything in the AI services chain, build comm-controller first.

### Key Packages Per Repo

| Repo | Key NuGet Packages |
|------|-------------------|
| `mm-common` | `Meshmakers.Common.Shared`, `.Configuration`, `.Metrics`, `.CommandLineParser` |
| `octo-distributedEventHub` | `Meshmakers.Octo.Common.DistributionEventHub`, `.DistributionEventHub.MongoDB` |
| `octo-construction-kit-engine` | `Meshmakers.Octo.ConstructionKit.Contracts`, `.Engine`, `.Compiler`, `.SourceGeneration`, `.MsBuildTasks`, `Runtime.Contracts`, `Runtime.Engine`, `ConstructionKit.Models.System`, `ConstructionKit.Models.StreamData` |
| `octo-sdk` | `Meshmakers.Octo.Sdk.Common`, `.ServiceClient`, `.SourceGeneration`, `Communication.Contracts` |
| `octo-construction-kit-engine-mongodb` | `Meshmakers.Octo.Runtime.Contracts.MongoDb`, `Runtime.Engine.MongoDb`, `Runtime.Engine.CrateDb` (StreamData/CrateDB stack — see CK internals) |
| `octo-common-services` | `Meshmakers.Octo.Services.Infrastructure`, `.Contracts`, `.Notifications`, `.Observability`, `.Swagger` (there is **no** `Services.StreamData` package — StreamData runtime lives in `Runtime.Engine.CrateDb`) |
| `octo-bot-services` | `Meshmakers.Octo.ConstructionKit.Models.System.Bot` |
| `octo-communication-controller-services` | `Meshmakers.Octo.ConstructionKit.Models.System.Communication` |
| `octo-construction-kit` | `Meshmakers.Octo.Sdk.Packages.Basic`, `.Industry.Basic`, `.Environment`, `.EnergyCommunity`, etc. |

## Selective Build Strategy

For bug isolation, build only what is needed rather than the full chain:

### Change in a library repo (e.g., octo-construction-kit-engine)
Use `Invoke-BuildAll` — it walks the dependency order and propagates the NuGet packages between repos for you:
```powershell
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

**Do NOT hand-chain `Invoke-Build` + `Copy-NuGetPackages` down the dependency chain.** `Invoke-Build` does not propagate packages, so every repo you skip keeps consuming the previous version — and skipping one is easy, because the chain between an engine change and the service under test runs through `octo-sdk` and `octo-construction-kit-engine-mongodb`. The result is a service that builds cleanly against stale contracts and then fails at startup or at runtime, far from the change that caused it. The frontend exclusion is the only sanctioned way to shorten this build.

### Change in a service repo (e.g., octo-asset-repo-services)
Only that service needs building:
```powershell
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

### Change in octo-construction-kit (CK model packages only)
CK model packages are independent of the engine/runtime build chain. Restore old packages without rebuilding:
```powershell
Copy-NuGetPackages -directory ./octo-construction-kit
# Then build the consuming service
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

### Full rebuild excluding frontend (faster)
```powershell
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

## NuGet Package Flow

1. Each repo builds with `dotnet build -c DebugL`
2. Build outputs `.nupkg` files to `bin/DebugL/` directories
3. `Copy-NuGetPackages` copies `.nupkg` files from a repo's output to `./nuget/`
4. Downstream repos' `NuGet.Config` resolves from `../nuget/` (relative to the repo)
5. The global NuGet cache at `~/.nuget/packages/` caches resolved packages

### Stale NuGet Cache Issues
If builds behave unexpectedly after changes, the global NuGet cache may be stale:
```powershell
Remove-GlobalNuGetPackages  # Clears Meshmakers packages from global cache
```
`Invoke-BuildAll` does this automatically at the start.

## Building with dotnet Directly

For quick iteration within a single repo:
```bash
dotnet build -c DebugL                                    # Build all projects in solution
dotnet build -c DebugL src/SpecificProject/               # Build one project
dotnet test -c DebugL                                     # Run all tests
dotnet test -c DebugL --filter "FullyQualifiedName~MyTest" # Run specific test
```

## Service Startup Options

For targeted debugging, start only the services needed. `Start-Octo` exposes one **Boolean** parameter per service (default `$true` for most, `$false` for reporting / aiWorker), plus two `*Only` shortcuts:
```powershell
Start-Octo -identityOnly $true                       # Just identity (5003/5002); zeroes all other flags
Start-Octo -identityAssetRepoOnly $true              # Identity + asset repo (5003/5001)
Start-Octo -botService $false -reportingService $false  # Everything except bot and reporting
Start-Octo -mcpService $false -aiService $false       # Skip MCP + AI services
Start-Octo -nonInteractive $true                     # Background mode (no keypress to stop)
```

**CRITICAL:** there is **no** `-noBot` / `-noReporting` parameter — passing them is silently ignored. Disable a service with its real Boolean flag set to `$false` (`-botService $false`, `-reportingService $false`, `-meshAdapter $false`, etc.).

Service flags and defaults: `botService`, `identityService`, `assetRepoService`, `meshAdapter`, `communicationControllerService`, `adminPanel`, `dataRefineryStudio`, `frontendLibraries`, `mcpService`, `aiService` all default `$true`; `reportingService`, `simulationAdapter`, `aiWorker` default `$false`. `Start-Octo` also auto-sets `OCTO_STREAMDATA__ENABLED=true`.

Non-interactive mode is useful for automated testing — stop with `Stop-Octo` (a standalone module).

## DistributionEventHub (Inter-Service Messaging)

`Meshmakers.Octo.Common.DistributionEventHub` (repo `octo-distributedEventHub`, position 2 in the build chain) is the MassTransit + RabbitMQ messaging layer shared by all services. Multi-targets `net10.0` and `netstandard2.0`; consumed by identity, asset-repo, comm-controller, and the operator. When debugging message-routing failures (events not delivered, RPC timeouts, cross-environment crosstalk), this is the library to understand.

### Four Messaging Patterns

| Pattern | API | Notes |
|---------|-----|-------|
| Broadcast (fanout) | `IDistributionEventHubService.PublishAsync<T>()` | Fans out to all services; queue `octo::service::{ServiceName}` |
| Routed fire-and-forget | `IDistributionEventHubService.SendAsync<T>(uri, msg)` | Targets a specific queue; round-robin load balancing |
| Request/response RPC | `ICommandClient<TRequest>` / `IRoutedCommandClient<TRequest>` | Typed and dynamic-target clients |
| Distributed file cache | `IDistributedCacheService` | MongoDB **GridFS** file caching with TTL (in `.DistributionEventHub.MongoDB`) |

Consumers implement `IDistributedConsumer<TMessage>`.

### Registration

```csharp
services.AddDistributionEventHub(config =>
{
    config.UniqueServiceAddress = "my-service";  // required
    config.InstancePrefix = "prod";              // required — isolates environments on a shared broker

    config.AddBroadcastEventConsumer<TConsumer, TMessage>();
    config.AddRoutedEventConsumer<TConsumer, TMessage>("queue-name");
    config.AddCommandConsumer<TConsumer, TMessage>("command-name");
    config.AddCommandClient<TRequest>("target-service");
});
```

**Debugging note:** all queue/exchange names are prefixed with `InstancePrefix` (default `default`, settable in `appsettings.json` `DistributionEventHubOptions.InstancePrefix` or in code). A missing or mismatched prefix is a common cause of "events published but never consumed" — two services on the same RabbitMQ with different prefixes never see each other's messages. A missing prefix throws at startup (`DistributedOperationFailedException.NoInstancePrefix`). Blueprint lifecycle events (`BlueprintApplied`, `BlueprintUpdated`, `BlueprintRolledBack`, `BlueprintUninstalled`, `BlueprintOperationFailed`) flow over this hub.
