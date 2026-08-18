# OctoMesh PowerShell Cmdlet Reference

Complete catalog of cmdlets available after loading `octo-tools/modules/profile.ps1`.

## Build & Compilation

### `Invoke-BuildAll`
Build repositories in dependency order with automatic NuGet package propagation between repos. **This is the default build command** — use it whenever changes might affect NuGet packages or when building after pull/branch switch.
- `-configuration` (string): Build configuration — `DebugL` (local dev), `Debug`, `Release`. **Always use `DebugL` for local development.**
- `-branch` (string): Branch name for NuGet package resolution
- `-excludeAdditional` (bool): Skip additional/optional repos — builds only the core dependency chain. **Must pass `$true` explicitly** (e.g., `-excludeAdditional $true`), not bare flag. **Not a time-saving shortcut:** it skips the service repos, so a changed contract package reaches `nuget/` while the services still consume the previous one and fail later at startup or runtime. Use it only when you deliberately want the libraries alone.
- `-excludeFrontend` (bool): Skip Angular frontend builds — significant time savings for backend-only work. **Must pass `$true` explicitly** (e.g., `-excludeFrontend $true`), not bare flag.
- **Safety:** Mutating (local) — modifies build outputs and NuGet cache
- **Common patterns:**
  - Full build: `Invoke-BuildAll -configuration DebugL`
  - Backend only (the only sanctioned way to shorten a build): `Invoke-BuildAll -configuration DebugL -excludeFrontend $true`

### `Invoke-Build`
Build a single repository. **Does NOT handle NuGet package propagation between repos** — unlike `Invoke-BuildAll`, which does. Anything this repo publishes stays invisible to its consumers, which keep building and running against the previous package version. Only use for isolated changes within a single service repo where no NuGet packages are affected. If changes affect NuGet packages or touch library repos, use `Invoke-BuildAll` with exclusion flags instead.
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
- **Safety:** Interactive — calls `Invoke-BuildAll` then `Start-Octo`. It does NOT expose `-nonInteractive`, so it always chains into the interactive `Start-Octo` and blocks the session until a keypress.
- **CRITICAL:** Do NOT use from an agent/CI session. Run `Invoke-BuildAll -configuration DebugL` then `Start-Octo -nonInteractive $true -configuration DebugL` instead.

### `Invoke-BuildZenonPlug`
Build the Zenon plug-in project.
- `-repositoryPath` (string): Path to the Zenon plug-in repo
- `-configuration` (string): Build configuration
- **Safety:** Mutating (local)

## Service Management

### `Start-Octo`
Start OctoMesh services. Each service is controlled by its own **Boolean** parameter (there are NO `-noX` switches). Services run as background jobs. The .NET services need to be built first; the AI/MCP services only start if their repo directories exist locally.

**Service Boolean parameters** (default `$true` unless noted) — pass `$false` to skip a service:
- `-identityService` (Boolean, default `$true`): Identity Service (ports 5002/5003)
- `-assetRepoService` (Boolean, default `$true`): Asset Repo Service (ports 5000/5001)
- `-meshAdapter` (Boolean, default `$true`): Mesh Adapter (ports 5020/5021)
- `-communicationControllerService` (Boolean, default `$true`): Communication Controller (ports 5014/5015)
- `-botService` (Boolean, default `$true`): Bot Service (ports 5008/5009)
- `-adminPanel` (Boolean, default `$true`): Admin Panel (ports 5004/5005)
- `-dataRefineryStudio` (Boolean, default `$true`): Data Refinery Studio dev server
- `-frontendLibraries` (Boolean, default `$true`): Frontend Libraries dev server
- `-mcpService` (Boolean, default `$true`): MCP Service (ports 5016/5017), only if `octo-mcp-service` exists
- `-aiService` (Boolean, default `$true`): AI Service (ports 5018/5019), only if `octo-ai-services` exists
- `-aiWorker` (Boolean, default `$false`): standalone AI Worker (ports 5022/5023); off by default because the AI service's Subprocess mode does not need it
- `-reportingService` (Boolean, **default `$false`**): Reporting Service (ports 5006/5007) — opt in explicitly
- `-simulationAdapter` (Boolean, default `$false`): Simulation Adapter

**Scope shortcuts** (Boolean, default `$false`):
- `-identityOnly` (Boolean): start ONLY the Identity Service (forces all other services off)
- `-identityAssetRepoOnly` (Boolean): start ONLY Identity + Asset Repo

**Adapter targeting** (string):
- `-meshAdapterTenantId` (default `meshtest`), `-meshAdapterId` (default `66004fda527ac79a03ecedd7`)
- `-simulationAdapterTenantId` (default `meshtest`), `-simulationAdapterId` (default `65d5c447b420da3fb12381bc`)

**Run control:**
- `-nonInteractive` (Boolean, default `$false`): when `$true`, do NOT wait for a keypress. Block until a job fails or a `.octo-stop` file appears (created by `Stop-Octo`). **Agents and CI MUST set this to `$true`.**
- `-configuration` (string, default `Release`): build configuration to launch from — use `DebugL` for local dev
- `-branch` (string): branch sub-folder under the workspace root
- `-SystemDatabase` (string, default `OctoSystem`): MongoDB system database name

`Start-Octo` automatically sets `OCTO_STREAMDATA__ENABLED=true` (per-tenant stream-data gate) and a deterministic dev AI encryption key, so those no longer need to be set manually.

- **Safety:** Mutating. Interactive ONLY when `-nonInteractive` is not set (then it blocks until a keypress). With `-nonInteractive $true` it blocks until a service fails or `Stop-Octo` is run — the required mode for agents.
- **Examples:**
  - Agent/CI default: `Start-Octo -nonInteractive $true -configuration DebugL`
  - Identity + asset repo only, non-interactive: `Start-Octo -nonInteractive $true -configuration DebugL -identityAssetRepoOnly $true`
  - Without the bot service: `Start-Octo -nonInteractive $true -configuration DebugL -botService $false`

### `Stop-Octo`
Stop services started with `Start-Octo -nonInteractive $true`. Standalone module (`Stop-Octo.psm1`) — writes a `.octo-stop` signal file that the running `Start-Octo` monitors, triggering a graceful shutdown of all jobs.
- `-branch` (string): branch sub-folder; must match the `-branch` used for `Start-Octo`
- **Safety:** Mutating

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

## Infrastructure Backup (Docker volumes)

Backups operate on the infra Docker volumes (Mongo + CrateDB) and are stored under `infrastructure/backups/`. Stop the infrastructure first (`Stop-OctoInfrastructure`).

### `Backup-OctoInfrastructure`
Back up all infrastructure volumes.
- `-Name` (string, optional): backup name; defaults to a timestamp
- **Safety:** Mutating (local)

### `Restore-OctoInfrastructure`
Restore infrastructure volumes from a named backup.
- `-Name` (string): backup name to restore; omit to list available backups
- **Safety:** Destructive — overwrites current volume data

### `Get-OctoInfrastructureBackup`
List available infrastructure backups.
- No parameters
- **Safety:** Read-only

### `Remove-OctoInfrastructureBackup`
Delete a named infrastructure backup.
- `-Name` (string): backup name to delete
- `-Force` (switch): skip the confirmation prompt
- **Safety:** Destructive

## Local Kubernetes (kind) dev environment

Alternative to the docker-compose infrastructure: MongoDB / RabbitMQ / CrateDB, the CRDs, and the Communication Operator run inside a local kind cluster (.NET services still run as host processes via `Start-Octo`). **Mutually exclusive with docker-compose infra — both bind the same host ports; `Install-OctoKubernetes` refuses to run while compose infra containers are up.** Requires `kind`, `helm`, `kubectl`, and `docker` on PATH. Full runbook: `C:\dev\meshmakers\octo-tools\kubernetes\README.md`; from-scratch: `C:\dev\meshmakers\octo-tools\kubernetes\QUICKSTART.md`.

### `Install-OctoKubernetes`
Create the kind cluster + CRDs Helm chart + namespaces + in-cluster infra + ingress-nginx/cert-manager + the `mm-cloud-issuer` CA, then deploy the Communication Operator. Idempotent.
- `-branch` (string, default `""`): branch sub-folder containing the checkouts (reads CRDs from `octo-helm-core/src/octo-mesh-crds`)
- `-ClusterName` (string, default `kind`)
- `-CrdReleaseName` (string, default `octo-mesh-crds`)
- `-CrdNamespace` (string, default `octo-operator-system`)
- `-SkipInfra` (switch): skip the in-cluster MongoDB/RabbitMQ/CrateDB
- `-SkipIngress` (switch): skip ingress-nginx + cert-manager + the CA ClusterIssuer
- `-ExposeLan` (switch): bind host ports on `0.0.0.0` instead of loopback (exposes dev infra to the LAN — trusted networks only; takes effect only when the cluster is created)
- `-SkipTrustCa` (switch): do not add the exported local root CA to the OS trust store (for unattended/CI runs)
- `-SkipOperator` (switch): skip deploying the operator
- `-SkipRegistryCheck` (switch): skip the dev-registry reachability pre-check (use when images are pre-loaded via `kind load`)
- `-DevRegistry` (string, default `docker.mm.cloud`): internal registry the node pulls images from; pass `""` to skip configuring it
- **Safety:** Mutating — creates a cluster and deploys workloads

### `Deploy-OctoOperator`
(Re)deploy the Communication Operator standalone into the kind cluster from the dev registry. Generates webhook serving certs and forces a rollout.
- `-branch` (string, default `""`)
- `-ClusterName` (string, default `kind`)
- `-Namespace` (string, default `octo-operator-system`)
- `-ReleaseName` (string, default `octo-operator`)
- `-ImageTag` (string, default `main-latest`): rolling tag CI publishes on every main build
- `-ControllerHost` (string): host/IP of the host-side Communication Controller; auto-resolved from the Docker host gateway / host LAN IP when empty
- `-SkipRegistryCheck` (switch): skip the node-level registry-resolution pre-check
- **Safety:** Mutating

### `Get-OctoKubernetesStatus`
Show pods (namespaces `octo-infra`, `octo-operator-system`, `octo`), Helm releases, and host-port reachability (Mongo 27017, RabbitMQ 5672/15672, CrateDB 5432/4301).
- `-ClusterName` (string, default `kind`)
- **Safety:** Read-only

### `Uninstall-OctoKubernetes`
Delete the kind cluster and ALL its data (Mongo + CrateDB PVCs are destroyed). By default also removes the local CA from the OS trust store.
- `-ClusterName` (string, default `kind`)
- `-Force` (switch): skip the `yes` confirmation prompt
- `-KeepCaTrust` (switch): leave the local root CA trusted in the OS store
- **Safety:** Destructive — destroys the cluster and its data

### `Import-OctoImageToKind`
Load a locally-present Docker image into the kind node (for `imagePullPolicy: IfNotPresent`, no registry needed).
- `-Image` (string, Mandatory): full image reference, e.g. `meshmakers/octo-communication-operator:dev`
- `-ClusterName` (string, default `kind`)
- **Safety:** Mutating

### `Add-OctoLocalCaTrust` / `Remove-OctoLocalCaTrust`
Trust / untrust the local root CA (`OctoMesh Local Dev Root CA`) in the OS trust store so browsers/tools accept the `mm-cloud-issuer` certificates. `Add` is idempotent. On Windows uses `Cert:\LocalMachine\Root` (run elevated); on macOS/Linux prompts for sudo.
- `Add-OctoLocalCaTrust -CaPath` (string, optional): defaults to `infrastructure/local-root-ca.crt`
- **Safety:** Mutating (`Remove` is Destructive)

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
Show git status across all `octo-*` and `mm-*` repos, recursing into submodules. Output is color-coded by urgency (red = dirty, yellow = out of sync, green = clean and in sync) and shows upstream sync tags: `⇣N` commits to pull, `⇡N` commits to push, `main+N` (how far `origin/main` moved on for a feature branch), or `(no upstream)`. Fetches from origin in parallel first.
- `-branch` (string): branch sub-folder to check status under
- `-NoFetch` (switch): skip the network fetch and compare against last-known refs only (instant, offline)
- **Safety:** Read-only

### `Find-AllGitRepos`
Discover all git repositories in the workspace.
- `-branch` (string): Branch name filter
- `-IncludeSubmodules` (switch): Include git submodules
- **Safety:** Read-only

### `Invoke-CloneMainRepos`
Clone all main OctoMesh repos (mm-common, the construction-kit/engine/sdk repos, the service repos, frontends, and `octo-helm-core`). `octo-helm-core` ships the CRDs + Communication Operator Helm charts and is required by the local kind dev env (`Install-OctoKubernetes` / `Deploy-OctoOperator`).
- `-branch` (string): branch sub-folder to clone into
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
Remove the locally-built `999.0.0` OctoMesh packages (`meshmakers.*`) from the global NuGet cache (`~/.nuget/packages/`). Forces a clean restore of local packages on the next build.
- No parameters — operates on the fixed global cache path; there is no branch filter
- **Safety:** Destructive — clears local `999.0.0` packages from the global NuGet cache

## Cleanup & Maintenance

### `Invoke-KillDotnet`
Kill all running dotnet processes.
- No parameters
- **Safety:** Mutating — Windows only, kills running processes

### `Remove-BinAndObjFolders`
Delete all `bin/` and `obj/` folders recursively.
- `-path` (string): Root path to clean (defaults to workspace root)
- **Safety:** Destructive — removes all build output folders

## Authentication / Context (octo-cli)

The login cmdlets create a named octo-cli context (via `octo-cli -c AddContext`), activate it (`UseContext`), then run an interactive `Login -i`. Context names follow `{installation}_{tenantId}` (e.g. `local_meshtest`), so each environment+tenant keeps its tokens independently.

> **Parallel safety:** the `UseContext` step mutates the single global active context, so a concurrent session (or a `_train`/CI job) inherits the switch. For agent/scripted work, register with `-NoSwitch` and target the context per-command with `octo-cli ... --context <ctx>` (or `export OCTO_CLI_CONTEXT=<ctx>` for the shell) — this runs against `<ctx>` without changing the active context.

### `Register-OctoCliContext` (recommended)
Unified replacement for the per-environment `Invoke-OctoCliLogin*` cmdlets. Builds the service URIs for the chosen installation, registers the context, optionally switches to it and triggers an interactive login.
- `-Installation` (string, **Mandatory**): one of `local`, `test-2`, `staging-1`, `prod-1`, `prod-2`. Domain mapping: `local` → localhost; `test-2` → `*.test-2.mm.cloud`; `staging-1` → `*.staging.octo-mesh.com`; `prod-1` → `*.prod-1.octo-mesh.com`; `prod-2` → `*.prod-2.octo-mesh.com`
- `-TenantId` (string, **Mandatory**): tenant id to bind the context to
- `-UriSuffix` (string, optional): for test-2 PR sub-environments (e.g. `pr123` → `assets-pr123.test-2.mm.cloud`); also appended to the context name
- `-IncludeReporting` (switch): also register the reporting service URI (`-rsu`)
- `-IncludeAi` (switch): also register the AI service URI (`-aisu`)
- `-NoSwitch` (switch): skip `UseContext` (leave the active context unchanged) — recommended for parallel-safe agent use; then pass `--context <ctx>` on octo-cli commands
- `-NoLogin` (switch): skip the interactive `Login -i` (for CI / client-credentials flow)
- **Safety:** Mutating
- **Examples:**
  - `Register-OctoCliContext -Installation staging-1 -TenantId meshtest`
  - `Register-OctoCliContext -Installation local -TenantId meshtest -IncludeAi`

### `Invoke-OctoCliLoginLocal`
Register + log in to the local environment.
- `-tenantId` (string, default `meshtest`): controls the context name (`local_<tenantId>`)
- `-includeReporting` (bool, default `$false`): also register the reporting service URI
- **Safety:** Mutating

### `Invoke-OctoCliLoginTest2`
Register + log in to the test-2 environment.
- **Safety:** Mutating

### `Invoke-OctoCliLoginStaging` (legacy)
Register + log in to staging. **Legacy** — points at the old `*.meshmakers.cloud` domains. Prefer `Register-OctoCliContext -Installation staging-1`.
- **Safety:** Mutating

### `Invoke-OctoCliLoginProduction` (legacy)
Register + log in to production. **Legacy** — points at the old `*.meshmakers.cloud` domains. Prefer `Register-OctoCliContext -Installation prod-1` or `prod-2`.
- **Safety:** Mutating

### `Invoke-OctoCliReconfigureLogLevel`
Reconfigure log levels for all services (Identity, AssetRepository, Bot, CommunicationController, AdminPanel) via octo-cli. All three parameters are **Mandatory** — calling without them fails.
- `-loggerName` (string, **Mandatory**)
- `-minLogLevel` (string, **Mandatory**)
- `-maxLogLevel` (string, **Mandatory**)
- **Safety:** Mutating
- **Example:** `Invoke-OctoCliReconfigureLogLevel -loggerName "*" -minLogLevel Debug -maxLogLevel Fatal`

### `Invoke-SetDebugConfiguration`
Register the Admin Panel debug OAuth client (`octo-admin-panel-debug`) and its scopes via octo-cli. Run after logging in to local identity services (`Invoke-OctoCliLoginLocal`).
- No parameters
- **Safety:** Mutating

### `Register-AiBastion`
Register an Anthropic subscription token on an OctoMesh tenant. Drives the Anthropic device-code OAuth flow on the terminal, then POSTs the access/refresh token pair to the AI Adapter's `POST /{tenantId}/v1/credentials/register`. Plaintext token material is held in memory only and zeroed in a `finally` block.
- `-Tenant` (string, **Mandatory**): tenant slug to (re)write the lease for
- `-AdapterUrl` (string, **Mandatory**): AI Adapter base URL (no trailing slash)
- `-BearerToken` (string, optional): bearer used to authorise the POST; falls back to `$env:OCTO_BASTION_TOKEN`
- `-Ticket` (string, optional): accepted but unused in phase 1
- **Safety:** Mutating (remote) — never echo or log the bearer token or device-code output

### `Get-AiBastionStatus`
Read the current AI Bastion lease metadata for a tenant (`GET /{tenantId}/v1/credentials/status`).
- `-Tenant` (string, **Mandatory**), `-AdapterUrl` (string, **Mandatory**), `-BearerToken` (optional, falls back to `$env:OCTO_BASTION_TOKEN`)
- **Safety:** Read-only

## Certificates

### `New-RootCertificate`
Generate a new root CA certificate.
- No parameters
- **Safety:** Mutating

### `New-ServerCertificate`
Generate a new server certificate signed by the root CA.
- No parameters
- **Safety:** Mutating

### `New-AspNetDeveloperCertificate`
Set up the ASP.NET Core developer HTTPS certificate. (The module `AspNetDeveloperCertificate.psm1` exports three functions — there is no cmdlet called `AspNetDeveloperCertificate`.)
- **Safety:** Mutating

### `Test-AspNetDeveloperCertificate`
Check the ASP.NET developer certificate status.
- **Safety:** Read-only

### `Remove-AspNetDeveloperCertificate`
Remove the ASP.NET developer certificate.
- **Safety:** Destructive

## Kubernetes helpers / DB access

(For the kind cluster lifecycle see **Local Kubernetes (kind) dev environment** above.)

### `Join-KubeConfigs`
Merge multiple kubeconfig files.
- No parameters
- **Safety:** Mutating

### `Remove-KubeConfig`
Delete a named context, cluster, and user from `~/.kube/config`. Backs up the file first and waits for an interactive Enter before applying.
- `-name` (string, required): the context/cluster/user name to remove
- **Safety:** Destructive

### `Invoke-MongoPortForward`
Forward the MongoDB port from a Kubernetes cluster for direct DB access.
- No parameters
- **Safety:** Mutating

## Diagnostics & Comparison

### `Compare-CkVersions`
Diff Construction Kit model (`ckModel.yaml`) versions between two branch checkouts. Scans both folders under `$Global:ROOTPATH`, groups System CKs first, and color-codes (green = equal, yellow = minor/patch differs, red = major differs, cyan = present in only one). Sets `$LASTEXITCODE` to the count of non-equal models.
- `-OtherBranch` (string, **Mandatory**, positional): branch checkout to compare against, resolved relative to `$Global:ROOTPATH` (e.g. `../main`, `branches/test`, or an absolute path)
- `-Branch` (string, optional): the subject branch checkout; defaults to the current checkout
- `-Details` (switch): also print each model's source `ckModel.yaml` path
- **Safety:** Read-only

### `Compare-Pipelines`
Compare local pipeline YAML files against their deployed versions in a remote OctoMesh tenant (exports via octo-cli, normalizes, and `git diff`s). Requires PowerShell 7+.
- `-TenantId` (string), `-LocalPipelineDir` (string), `-ExportDir` (string), `-PipelineFile` (string, single file), `-KeepExports` (switch)
- **Safety:** Read-only (read-only against the tenant; writes only temp export files)

### `Get-BranchAvailability`
List all `octo-*` and `mm-*` repos where a given branch exists on the remote (origin).
- `-targetBranch` (string, **Mandatory**): branch to search for
- `-Fetch` (switch): fetch from origin before checking
- **Safety:** Read-only

## Versioning & Templates

### `Sync-YamlTemplates`
Synchronize YAML pipeline templates across repos.
- No parameters
- **Safety:** Mutating

### `Update-MeshmakerVersion`
Update the Meshmaker version number across repos.
- No parameters
- **Safety:** Mutating
