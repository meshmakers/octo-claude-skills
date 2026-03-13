# OctoMesh Build System Deep Reference

## DebugL Configuration

`DebugL` is the mandatory local development configuration. It:
- Sets package version to `999.0.0` for all NuGet packages
- Resolves NuGet packages from the local `../nuget/` folder instead of remote feeds
- Enables peer-repo dependency resolution without publishing to any feed

**Never use `Debug` or `Release` for local development** — those configurations resolve packages from remote NuGet feeds and will fail if the latest packages haven't been published.

## Build Dependency Chain

The `Invoke-BuildAll` script enforces this strict order. Each repo's NuGet packages are copied to `./nuget/` after building, making them available to downstream repos:

```
1. mm-common                          → Meshmakers.Common.* packages
2. octo-distributedEventHub           → Meshmakers.Octo.Common.DistributionEventHub.*
3. octo-construction-kit-engine       → Meshmakers.Octo.ConstructionKit.*, Runtime.*, SystemCkModel
4. octo-sdk                           → Meshmakers.Octo.Sdk.*, Communication.Contracts
5. octo-construction-kit-engine-mongodb → Meshmakers.Octo.Runtime.*.MongoDb
6. octo-common-services               → Meshmakers.Octo.Services.*
7. octo-mesh-adapter                  → Meshmakers.Octo.MeshAdapter.*, Sdk.MeshAdapter
8. octo-bot-services                  → Meshmakers.Octo.ConstructionKit.Models.System.Bot
9. All remaining repos (services, tools, frontends)
```

### Key Packages Per Repo

| Repo | Key NuGet Packages |
|------|-------------------|
| `mm-common` | `Meshmakers.Common.Shared`, `.Configuration`, `.Metrics`, `.CommandLineParser` |
| `octo-construction-kit-engine` | `Meshmakers.Octo.ConstructionKit.Contracts`, `.Engine`, `.Compiler`, `.SourceGeneration`, `.MsBuildTasks`, `Runtime.Contracts`, `Runtime.Engine`, `ConstructionKit.Models.System` |
| `octo-sdk` | `Meshmakers.Octo.Sdk.Common`, `.ServiceClient`, `.SourceGeneration`, `Communication.Contracts` |
| `octo-construction-kit-engine-mongodb` | `Meshmakers.Octo.Runtime.Contracts.MongoDb`, `Runtime.Engine.MongoDb` |
| `octo-common-services` | `Meshmakers.Octo.Services.Infrastructure`, `.Contracts`, `.Notifications`, `.StreamData`, `.Observability`, `.Swagger` |
| `octo-bot-services` | `Meshmakers.Octo.ConstructionKit.Models.System.Bot` |
| `octo-construction-kit` | `Meshmakers.Octo.Sdk.Packages.Basic`, `.Industry.Basic`, `.Environment`, `.EnergyCommunity`, etc. |

## Selective Build Strategy

For bug isolation, build only what is needed rather than the full chain:

### Change in a library repo (e.g., octo-construction-kit-engine)
Build from the changed repo through all downstream dependents:
```powershell
# Build the changed repo
Invoke-Build -repositoryPath ./octo-construction-kit-engine -configuration DebugL
# Copy its NuGet packages
Copy-NuGetPackages -directory ./octo-construction-kit-engine
# Build downstream consumers
Invoke-Build -repositoryPath ./octo-sdk -configuration DebugL
Copy-NuGetPackages -directory ./octo-sdk
# ... continue down the chain until the service under test
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

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

### Full rebuild excluding non-core repos
```powershell
Invoke-BuildAll -configuration DebugL -excludeAdditional $true -excludeFrontend $true
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

For targeted debugging, start only the services needed:
```powershell
Start-Octo -identityOnly $true              # Just identity service (port 5003/5002)
Start-Octo -identityAssetRepoOnly $true     # Identity + asset repo (5003/5001)
Start-Octo -noBot $true -noReporting $true  # Everything except bot and reporting
Start-Octo -nonInteractive $true            # Background mode (no keypress to stop)
```

Non-interactive mode is useful for automated testing — stop with `Stop-Octo`.
