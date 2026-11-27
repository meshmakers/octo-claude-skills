# OctoMesh Build System Deep Reference

## DebugL Configuration

`DebugL` is the mandatory local development configuration. It:
- Sets `OctoVersion` to `999.0.0` for all NuGet packages (the public release suffix is `3.3.*`; private is `0.1.*`)
- Resolves NuGet packages from the local `../nuget/` folder instead of remote feeds
- Enables peer-repo dependency resolution without publishing to any feed

All services target **`net10.0`** (build output lands in `bin/DebugL/net10.0/`).

**Never use `Debug` or `Release` for local development** — those configurations resolve packages from remote NuGet feeds and will fail if the latest packages haven't been published.

## Build Dependency Chain

`Invoke-BuildAll` (full chain) and `Invoke-BuildRange` (partial chain) build the repositories of a lane in one dependency order. Each repo's NuGet packages are copied to the lane's `nuget/` folder after building, making them available to downstream repos. **The order is defined only in `octo-tools/modules/OctoBuildOrder.psm1`** — the skill copies no list, because a copied list goes stale (it already missed `octo-communication-sdk` once). Read the current order of a lane instead of guessing:

```powershell
Get-OctoBuildOrder -branchRootPath (Join-Path $rootPath 'branches/main') | Format-Table Name, Group   # the whole lane, in build order
Get-OctoPinnedBuildOrder                                                                               # only the pinned core chain
Invoke-BuildRange -branch branches/main -from <first> -to <last> -WhatIf                               # what a range would build
```

The phases, in order (`Group` column): `common` (every `mm-*` repo), `ordered` (the pinned core chain — NuGet producers that the alphabetical fallback would build after their consumers), `additional-ordered` (additional repos that other additional repos consume), `additional` (every remaining `octo-*` repo, alphabetical), and in a feature environment only `app` (consumer apps of its manifest). The comments on each entry in `OctoBuildOrder.psm1` say why a repo has its slot. Two slots that matter in diagnosis:

- **`octo-communication-sdk`** holds the adapter/pipeline framework and builds after `octo-sdk` but before `octo-mesh-adapter` and the other adapter consumers. A range that starts after it leaves the mesh adapter restoring a stale `999.0.0` package.
- **`octo-communication-controller-services`** produces `System.Communication`, which `octo-ai-services` consumes. Without its pinned slot the alphabetical fallback would build `octo-ai-services` first (`a < c`) and break its restore. When selectively building anything in the AI services chain, build comm-controller first.

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
Use `Invoke-BuildRange` over the library and everything up to the service under test — it walks the build order and propagates the changed packages (`Copy-NuGetPackages -onlyChanged`, then a purge of exactly those `999.0.0` cache folders):
```powershell
Invoke-BuildRange -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -WhatIf       # plan
Invoke-BuildRange -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -verifyTests  # build + compile tests
```
The full reset `Invoke-BuildAll -configuration DebugL -excludeFrontend $true` is for NU1101/NU1102 on a `999.0.0` package (chain out of sync) and after a pull or branch switch.

**Do NOT hand-chain `Invoke-Build` + `Copy-NuGetPackages` down the dependency chain.** `Invoke-Build` does not propagate packages, so every repo you skip keeps consuming the previous version — and skipping one is easy, because the chain between an engine change and the service under test runs through `octo-sdk` and `octo-construction-kit-engine-mongodb`. The result is a service that builds cleanly against stale contracts and then fails at startup or at runtime, far from the change that caused it.

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
3. `Copy-NuGetPackages` copies `.nupkg` files from a repo's output to the lane feed `<lane>/nuget/`
4. In DebugL each repo's `Directory.Build.props` adds `$(OctoRepoRootPath)../nuget` - the lane feed next to the repo in the plain `<lane>/<repo>` layout that lanes and feature environments use - to `<RestoreSources>`; repos that declare their own `RestoreSources` keep their other feeds too (e.g. Telerik in octo-report-services). Requirement: no `Directory.Build.props` in any folder above the lane (`branches/main`, `wt-<env>`, the workspace root or higher). Each repo looks for one in every ancestor (`GetPathOfFileAbove`); if it finds one, `OctoRepoRootPath` becomes that folder, `../nuget` points next to it and the lane's `Octo.User.props` is not imported
5. Packages are extracted into the lane's package cache. A lane is isolated when `<lane>/Octo.User.props` declares `RestorePackagesPath` with the standard value `$(MSBuildThisFileDirectory).nuget-packages` - the cache is then `<lane>/.nuget-packages`, also for Rider and plain `dotnet build`. A lane without it (main before the switch below) still uses the shared `~/.nuget/packages`. A custom `RestorePackagesPath` value is kept by `Initialize-OctoLaneUserProps` (reported as `custom-restore-packages-path`), but the octo-tools builds set and clean only `<lane>/.nuget-packages`, so a custom cache is never cleaned

Every lane builds the same `999.0.0` packages, so a shared cache lets one lane pick up another lane's build. Give main its own cache once:
```powershell
Initialize-OctoLaneUserProps -branch branches/main -AddRestorePackagesPath   # adds the line, keeps the rest, writes a .bak
```
The first restore afterwards extracts every package into `branches/main/.nuget-packages`. Feature environments (`New-OctoEnvironment`) always have the line.

### Stale NuGet Cache Issues
If builds behave unexpectedly after changes, the lane's package cache may be stale. `Invoke-BuildAll` (DebugL) clears the `meshmakers.*/999.0.0` folders of every cache the lane restores into at the start: an isolated lane only `<lane>/.nuget-packages`, a legacy lane the global cache. `Invoke-BuildRange` purges only the packages it rebuilt. By hand:
```powershell
Remove-GlobalNuGetPackages -path <lane>/.nuget-packages   # default path: ~/.nuget/packages
```

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

Service flags and defaults (octo-tools `modules/Start-Octo.psm1`): `botService`, `identityService`, `assetRepoService`, `meshAdapter`, `communicationControllerService`, `platformServices`, `dataRefineryStudio`, `frontendLibraries`, `mcpService`, `aiService`, `s3Store` default `$true`; `reportingService`, `simulationAdapter`, `aiWorker`, `httpActivator` default `$false`. `Start-Octo` also auto-sets `OCTO_STREAMDATA__ENABLED=true`.

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
