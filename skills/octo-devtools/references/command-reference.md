# OctoMesh PowerShell Cmdlet Reference

Complete catalog of cmdlets available after loading `octo-tools/modules/profile.ps1`.

## Build & Compilation

### `Invoke-BuildAll`
Build repositories in dependency order with automatic NuGet package propagation between repos. **This is the default build command** — use it whenever changes might affect NuGet packages or when building after pull/branch switch.
- `-configuration` (string): Build configuration — `DebugL` (local dev), `Debug`, `Release`. **Always use `DebugL` for local development.**
- `-branch` (string): Branch name for NuGet package resolution
- `-excludeAdditional` (bool): Skip additional/optional repos — builds only the core dependency chain. **Must pass `$true` explicitly** (e.g., `-excludeAdditional $true`), not bare flag.
- `-excludeFrontend` (bool): Skip Angular frontend builds — significant time savings for backend-only work. **Must pass `$true` explicitly** (e.g., `-excludeFrontend $true`), not bare flag.
- **Safety:** Mutating (local) — modifies build outputs and NuGet cache
- **Common patterns:**
  - Full build: `Invoke-BuildAll -configuration DebugL`
  - Backend only: `Invoke-BuildAll -configuration DebugL -excludeFrontend $true`
  - Core libraries only: `Invoke-BuildAll -configuration DebugL -excludeFrontend $true -excludeAdditional $true`

### `Invoke-Build`
Build a single repository. **Does NOT handle NuGet package propagation between repos.** Only use for isolated changes within a single service repo where no NuGet packages are affected. If changes affect NuGet packages or touch library repos, use `Invoke-BuildAll` with exclusion flags instead.
- `-configuration` (string): Build configuration (`DebugL`, `Debug`, `Release`)
- `-repositoryPath` (string): Path to the repository to build (e.g., `./octo-asset-repo-services`)
- **Safety:** Mutating (local)
- **WARNING:** Never manually chain `Invoke-Build` + `Copy-NuGetPackages` — use `Invoke-BuildAll` for multi-repo builds

### `Invoke-BuildFrontend`
Build Angular frontend applications.
- `-configuration` (string): Build configuration
- **Safety:** Mutating (local)

### `Invoke-Publish`
Publish a .NET project for deployment.
- `-configuration` (string): Build configuration
- `-repositoryPath` (string): Path to the repository
- `-publishParameters` (string): Additional dotnet publish parameters
- **Safety:** Mutating (local)

### `Invoke-BuildAndStartOcto`
Build all repos and start all services in one step.
- `-configuration` (string): Build configuration
- `-SystemDatabase` (string): MongoDB system database name
- **Safety:** Interactive — blocks the session until stopped via keypress

### `Invoke-BuildZenonPlug`
Build the Zenon plug-in project.
- `-repositoryPath` (string): Path to the Zenon plug-in repo
- `-configuration` (string): Build configuration
- **Safety:** Mutating (local)

## Service Management

### `Start-Octo`
Start all OctoMesh services (identity, asset repo, bot, comm controller, etc.).
- `-identityOnly` (switch): Start only identity services
- `-identityAssetRepoOnly` (switch): Start only identity + asset repo
- `-noIdentity` (switch): Start everything except identity
- `-noAssetRepo` (switch): Start everything except asset repo
- `-noCommunicationController` (switch): Skip communication controller
- `-noBot` (switch): Skip bot services
- `-noReporting` (switch): Skip reporting services
- `-noAi` (switch): Skip AI services
- `-noMeshAdapter` (switch): Skip mesh adapter
- **Safety:** Interactive — blocks the session until stopped via keypress. Always warn the user.

### `Start-OctoInfrastructure`
Start Docker infrastructure containers (MongoDB, RabbitMQ, CrateDB).
- No parameters
- **Safety:** Mutating

### `Stop-OctoInfrastructure`
Stop Docker infrastructure containers.
- No parameters
- **Safety:** Mutating

## Infrastructure

### `Install-OctoInfrastructure`
Install/set up Docker infrastructure for the first time.
- No parameters
- **Safety:** Mutating

### `Uninstall-OctoInfrastructure`
Remove Docker infrastructure containers and volumes.
- No parameters
- **Safety:** Destructive — removes containers and data

### `Get-OctoInfrastructureStatus`
Show status of Docker infrastructure containers.
- No parameters
- **Safety:** Read-only

### `Invoke-CleanupInfraContainerDisks`
Clean up unused Docker container disk space.
- No parameters
- **Safety:** Destructive — removes unused Docker data

## Git Repository Management

### `Sync-AllGitRepos`
Pull latest changes for all repos (git pull with rebase).
- `-branch` (string): Branch to sync
- `-resetPackageLock` (switch): Reset package-lock.json files after sync
- **Safety:** Mutating

### `Sync-GitRepo`
Pull latest changes for a single repo.
- `-repositoryPath` (string): Path to the repository
- **Safety:** Mutating

### `Push-AllGitRepos`
Push all repos to remote.
- `-branch` (string): Branch to push
- **Safety:** Mutating (remote) — pushes to upstream

### `Push-GitRepo`
Push a single repo to remote.
- `-repositoryPath` (string): Path to the repository
- **Safety:** Mutating (remote) — pushes to upstream

### `Get-AllGitRepStatus`
Show git status across all repos.
- `-branch` (string): Branch to check status for
- **Safety:** Read-only

### `Find-AllGitRepos`
Discover all git repositories in the workspace.
- `-branch` (string): Branch name filter
- `-IncludeSubmodules` (switch): Include git submodules
- **Safety:** Read-only

### `Invoke-CloneMainRepos`
Clone all main OctoMesh repos.
- `-branch` (string): Branch to clone
- **Safety:** Mutating

### `Sync-AllSubmodules`
Sync all git submodules.
- No parameters
- **Safety:** Mutating

### `Invoke-CleanAllGitRepos`
Clean all git repos (removes untracked files).
- No parameters
- **Safety:** Destructive — removes untracked files from all repos

## Branch Management

### `New-TestBranch`
Create a new test branch across all repos.
- `-MinorVersion` (string): Version number for the branch
- `-Description` (string): Branch description
- `-branch` (string): Base branch to branch from
- `-NoPush` (switch): Don't push to remote after creation
- **Safety:** Mutating

### `Remove-TestBranch`
Remove a test branch from all repos.
- `-MinorVersion` (string): Version number of the branch to remove
- `-Description` (string): Branch description
- **Safety:** Destructive — deletes branches

### `Sync-TestBranch`
Sync a test branch with its base branch (merge from base).
- `-MinorVersion` (string): Version number
- `-Description` (string): Branch description
- `-branch` (string): Base branch
- `-NoPush` (switch): Don't push after sync
- **Safety:** Mutating

### `Invoke-SwitchAllBranches`
Switch all repos to a different branch.
- `-Name` (string): Branch name to switch to
- `-branch` (string): Expected current branch
- `-Push` (switch): Push after switching
- `-IncludeSubmodules` (switch): Include submodules
- **Safety:** Mutating

### `Compare-BranchStatus`
Compare branch status across repos.
- **Safety:** Read-only

## NuGet Package Management

### `Copy-AllNuGetPackages`
Copy built NuGet packages from all repos to the shared `nuget/` folder.
- No parameters
- **Safety:** Mutating (local)

### `Copy-NuGetPackages`
Copy NuGet packages from a specific directory.
- `-directory` (string): Source directory
- `-branch` (string): Branch name
- **Safety:** Mutating (local)

### `Sync-NuGetPackages`
Synchronize NuGet package cache.
- No parameters
- **Safety:** Mutating (local)

### `Remove-GlobalNuGetPackages`
Remove NuGet packages from the global cache.
- `-branch` (string): Branch name filter
- **Safety:** Destructive — clears global NuGet cache

## Cleanup & Maintenance

### `Invoke-KillDotnet`
Kill all running dotnet processes.
- No parameters
- **Safety:** Mutating — Windows only, kills running processes

### `Remove-BinAndObjFolders`
Delete all `bin/` and `obj/` folders recursively.
- `-path` (string): Root path to clean (defaults to workspace root)
- **Safety:** Destructive — removes all build output folders

## Authentication / Environment

### `Invoke-OctoCliLoginLocal`
Configure octo-cli for local environment and log in.
- No parameters
- **Safety:** Mutating

### `Invoke-OctoCliLoginTest2`
Configure octo-cli for test-2 environment and log in.
- No parameters
- **Safety:** Mutating

### `Invoke-OctoCliLoginStaging`
Configure octo-cli for staging environment and log in.
- No parameters
- **Safety:** Mutating

### `Invoke-OctoCliLoginProduction`
Configure octo-cli for production environment and log in.
- No parameters
- **Safety:** Mutating

### `Invoke-OctoCliReconfigureLogLevel`
Reconfigure service log levels via octo-cli.
- **Safety:** Mutating

## Certificates

### `New-RootCertificate`
Generate a new root CA certificate.
- No parameters
- **Safety:** Mutating

### `New-ServerCertificate`
Generate a new server certificate signed by the root CA.
- No parameters
- **Safety:** Mutating

### `AspNetDeveloperCertificate`
Set up ASP.NET developer HTTPS certificate.
- No parameters
- **Safety:** Mutating

## Kubernetes

### `Join-KubeConfigs`
Merge multiple kubeconfig files.
- No parameters
- **Safety:** Mutating

### `Invoke-MongoPortForward`
Forward MongoDB port from a Kubernetes cluster.
- No parameters
- **Safety:** Mutating

## Versioning & Templates

### `Sync-YamlTemplates`
Synchronize YAML pipeline templates across repos.
- No parameters
- **Safety:** Mutating

### `Update-MeshmakerVersion`
Update the Meshmaker version number across repos.
- No parameters
- **Safety:** Mutating
