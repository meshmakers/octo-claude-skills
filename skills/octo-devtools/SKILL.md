---
name: octo-devtools
description: "Drives OctoMesh local development through the octo-tools PowerShell cmdlets — building repos in dependency order, starting and stopping services (always non-interactively for agents via Start-Octo -nonInteractive $true / Stop-Octo), managing Docker or local kind Kubernetes infrastructure, syncing and branching git repos, NuGet package propagation, certificates, and octo-cli context/auth setup. Use it for any OctoMesh dev-environment or DevOps task. Trigger on build, compile, feature environment, New-OctoEnvironment, Invoke-BuildEnvironment, lane isolation, dotnet build, start services, stop services, Start-Octo, Stop-Octo, Invoke-BuildAll, Invoke-Build, infrastructure, docker compose, kind, Kubernetes, Install-OctoKubernetes, Deploy-OctoOperator, git sync, pull repos, push repos, Get-AllGitRepStatus, branch management, test branch, NuGet packages, clean build, kill dotnet, certificates, clone repos, register context, login local/staging/production, infrastructure backup, or any OctoMesh PowerShell cmdlet name."
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/octo-devtools/references/*)"
  - "Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/octo-devtools/scripts/run_pwsh.sh:*)"
---

# OctoMesh Development Tools — Natural Language Interface

## Overview

Single entry point for OctoMesh development operations: `/octo-devtools <natural language>`

Claude translates the user's intent into the appropriate PowerShell cmdlet from `octo-tools/modules/profile.ps1` — with safety checks for destructive operations and warnings for interactive/session-blocking commands.

## Prerequisites

- **PowerShell** (`pwsh`) must be installed and on PATH
- The monorepo workspace must contain `octo-tools/` with `modules/profile.ps1`
- For build commands: .NET SDK must be installed
- For infrastructure commands: Docker must be running

## Invocation Pattern

All commands are executed through the wrapper script, which loads the OctoMesh profile automatically:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-devtools/scripts/run_pwsh.sh" '<PowerShell command>'
```

**CRITICAL — quoting and path examples:**
- CORRECT: `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-devtools/scripts/run_pwsh.sh" 'Get-AllGitRepStatus'`
- CORRECT: `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-devtools/scripts/run_pwsh.sh" 'Invoke-BuildAll -configuration DebugL -excludeFrontend $true'`
- WRONG: `bash "..." "Invoke-BuildAll -excludeFrontend $true"` (double quotes — bash eats `$true`!)
- WRONG: `pwsh -Command "Get-AllGitRepStatus"` (profile not loaded!)
- WRONG: `cd ... && bash scripts/run_pwsh.sh '...'` (causes permission prompts!)

**Always use single quotes** around the PowerShell command argument so that PowerShell variables like `$true` and `$false` are not consumed by bash.

## Build Strategy — CRITICAL

OctoMesh is a monorepo where repos produce NuGet packages (`999.0.0` in DebugL) consumed by downstream repos. Three cmdlets build; they differ in what they do with those packages:

| Cmdlet | What it does | Use it for |
|---|---|---|
| `Invoke-BuildRange -from <repo> [-to <repo>]` | Rebuilds only the slice of the build order between `-from` and `-to` (`src/` projects only), copies the changed packages into `<lane>/nuget` and purges exactly those from the lane's package cache | **The everyday inner loop** after a change in a library or service of the chain |
| `Invoke-BuildAll` | Full reset: wipes `<lane>/nuget` and the `meshmakers.*/999.0.0` cache folders, forces a restore, builds every repo's whole solution in build order (test projects compiled, not run) | After a fresh clone, a pull or a branch switch; restores failing with NU1101/NU1102 on a `999.0.0` package (chain out of sync) |
| `Invoke-Build -repositoryPath <repo>` | One repository, no package propagation | A change inside one service repo that produces no package another repo consumes |

**The build order** is defined in one place only: octo-tools `modules/OctoBuildOrder.psm1` (`Get-OctoBuildOrder -branchRootPath <lane>` prints it). `Invoke-BuildAll` and `Invoke-BuildRange` share it — never chain `Invoke-Build` calls by hand or copy packages manually.

**Which lane:** `-branch` is a lane folder relative to `$rootPath`. With the profile loaded from the `octo-tools` checkout at the workspace root (`$rootPath` = the workspace root - the setup feature environments need), pass `-branch branches/main` to build main; without `-branch` the cmdlets build `$rootPath` itself. With a profile loaded from inside the main checkout (`$rootPath` = `branches/main`) omit `-branch` and use `-path $rootPath` for `Remove-BinAndObjFolders` - `branches/main` would point at a nested folder there.

### Inner loop: `Invoke-BuildRange`

```
# 1. See the plan: repositories, src/ projects, cache folders to purge, running services, stale cache
Invoke-BuildRange -branch branches/main -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -WhatIf

# 2. Build. It refuses while services of the range run; -ignoreRunningServices builds anyway, -stopServices stops them first
Invoke-BuildRange -branch branches/main -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -stopServices

# 3. Before handing the change on: also compile the test projects (they are not run)
Invoke-BuildRange -branch branches/main -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -verifyTests
```

| Parameter | Meaning |
|---|---|
| `-from` / `-to` | First / last repository of the range (inclusive; `-to` defaults to `-from`). Exact name, name without `octo-`, or a unique part |
| `-include` / `-exclude` | Add repositories outside the range / skip repositories inside it (the build order is kept) |
| `-verifyTests` | After each repo's `src/` build, compile its projects outside `src/` without running them. A plain run does **not** compile test projects - use this (or `-includeTests`, whole solutions) before every hand-off |
| `-stopServices` / `-ignoreRunningServices` | Stop the services running from the range first / build anyway (it never kills dotnet processes itself) |
| `-purgeStaleCache` | Delete cache `999.0.0` folders whose hash differs from `<lane>/nuget` before the first build (otherwise they are only reported) |
| `-excludeFrontend` | Default `$true` (frontends produce no packages) |
| `-WhatIf` / `-Json` | Print the plan only / emit one JSON document |

It stops at the first failing repository and prints its error lines. Repositories outside the range are not rebuilt; they pick up a rebuilt package on their next build. More parameters: `references/command-reference.md`.

### Full reset: `Invoke-BuildAll`

```
Invoke-BuildAll -branch branches/main -configuration DebugL -excludeFrontend $true   # backend only
Invoke-BuildAll -branch branches/main -configuration DebugL                          # with the Angular frontends
```

Always pass `-configuration DebugL` (the cmdlet's own default is `Release`). `-DryRun` prints the plan without killing, deleting or building. **Do not use `-excludeAdditional $true`** to save time: it stops after the core library chain, so the service repos keep consuming the previous package and fail later at startup. Use `Invoke-BuildRange` for a narrower build.

### Single repo: `Invoke-Build`

```
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

Only when the change produces no package another repo consumes and all upstream packages in `<lane>/nuget` are current. A relative `-repositoryPath` follows the PowerShell location (`$PWD`).

### Tests: `Invoke-OctoTestRun`

The build cmdlets never run tests. `Invoke-OctoTestRun (-env <env> | -branch <lane>) -repo <name> [-project <names>] [-filter <filter>] [-rerunFailed] [-WhatIf] [-Json]` runs the test projects of one repository (no full rebuild; Docker-heavy projects run under a machine-wide test lock, `Get-OctoTestLock` shows its holder).

## Command Quick Reference

For full parameter details, read `references/command-reference.md` in this skill directory.
For common multi-step workflows, read `references/workflows.md` in this skill directory.

### Build & Compilation

| Cmdlet | Description | Safety |
|---|---|---|
| `Invoke-BuildRange` | Rebuild a slice of the build order with package propagation — **the inner loop** | Mutating (local) |
| `Invoke-BuildAll` | Full reset build of all repos in build order (frontends included unless `-excludeFrontend $true`) | Mutating (local) |
| `Invoke-Build` | Build a single repo WITHOUT package propagation | Mutating (local) |
| `Get-OctoBuildOrder` | Print the build order (`OctoBuildOrder.psm1`) | Read-only |
| `Invoke-OctoTestRun` | Run the test projects of one repository in a lane or feature environment | Mutating (local) |
| `Get-OctoTestLock` / `Remove-OctoTestLock` | Show the machine-wide test lock / remove it when its owner is gone | Read-only / Mutating |
| `Invoke-Publish` | Publish a .NET project | Mutating (local) |
| `Invoke-BuildAndStartOcto` | Build all + start services — chains into **interactive** `Start-Octo`. **Do NOT use from an agent session** (see safety rules) | **Interactive** |
| `Invoke-BuildZenonPlug` | Build Zenon plug-in | Mutating (local) |

### Feature environments (one work item, isolated lane)

A feature environment is the lane folder `<rootPath>/wt-<env>` of the octo-claude-pm lane `<env>`: worktrees of the changed repos, its own `nuget/` feed, `.nuget-packages/` cache, CK/blueprint catalogs and `.octo/environment.json`. **Do feature work here, never publish it into the base lane's `nuget/`.** Through octo-devstack the same is `lane_create` / `lane_build` (see "When the octo-devstack MCP server is available"). Details: octo-tools `readme.md`, "Feature environments".

**Base lane** (the folder holding the repositories, `nuget/` and `.octo/`): without `-base`, `New-OctoEnvironment` takes `$env:OCTO_ENVIRONMENT_BASE` if set, else `<rootPath>/branches/main` (lanes layout, profile loaded from the `octo-tools` next to `branches/`), else `$rootPath` itself (flat layout: repositories directly below `$rootPath`, profile loaded from `$rootPath/octo-tools`; the manifest records `base: "."` and `wt-<env>` lies next to the repositories). Neither fits: the error names both layouts, `-base` and `OCTO_ENVIRONMENT_BASE`. Claims live in the base lane's `.octo/claims/`.

| Cmdlet | Description | Safety |
|---|---|---|
| `New-OctoEnvironment -env <slug> [-repos <names>] [-workItem AB#..] [-base <lane>]` | Create `wt-<env>` with feature worktrees, feed and catalogs copied from the base lane; without `-repos` an empty environment (to adopt worktrees) | Mutating (local) |
| `Get-OctoEnvironment [-env <slug>]` | List environments; with `-env` the worktree state (dirty, unpushed) | Read-only |
| `Add-OctoEnvironmentRepo -env <slug> -repo <name> [-role feature\|consumer] [-addAffected]` | Add a worktree; `consumer` = detached at main's commit, `-addAffected` adds the repos between library and service | Mutating (local) |
| `Add-OctoEnvironmentRepo -env <slug> -path <worktree> [-inPlace]` | Adopt an existing linked worktree (`wt-<lane>-<repo>`, `wt-<lane>/<repo>` of a hand-made environment, or `<repo>/.claude/worktrees/<name>`): moved into `wt-<env>/<repo>`; with `-inPlace` only recorded | Mutating (local) |
| `Get-OctoAffectedRepos -env <slug> [-target <repos>]` | Repos a library change reaches (must be rebuilt, else `MissingMethodException` at runtime) | Read-only |
| `Invoke-BuildEnvironment -env <slug> [-syncMain] [-verifyTests\|-includeTests] [-DryRun]` | Incremental build of the environment's repos into its own feed and cache | Mutating (local) |
| `Sync-OctoEnvironment -env <slug>` | Take main's new packages and catalog entries (packages built in the environment keep winning) | Mutating (local) |
| `Remove-OctoEnvironment -env <slug>` | Remove the environment; refuses dirty or unpushed worktrees, keeps branches, no `-force` | **Destructive** |

**Before a build:** `Invoke-BuildEnvironment` clears the environment's kill scope (`wt-<env>` and every in-place worktree) - on Windows it stops the matching dotnet processes, e.g. a running service of the environment; `-skipKill` opts out. **Before removal:** stop the environment's services first; `Remove-OctoEnvironment` does not. For a lane made with octo-devstack use its `lane_remove` (it refuses while a process it did not start holds files in the lane).

**In-place caveat:** an `-inPlace` worktree stays where it is. `Invoke-BuildEnvironment` builds it with the environment's feed, cache and catalog, but a plain `dotnet build` or Rider there is **not** isolated, and `Remove-OctoEnvironment` only unregisters it - it is never deleted.

### Service Management

| Cmdlet | Description | Safety |
|---|---|---|
| `Start-Octo` | Start OctoMesh services. **From an agent always pass `-nonInteractive $true`** | Mutating (interactive only when `-nonInteractive` is not set) |
| `Stop-Octo` | Stop services started in non-interactive mode (writes a `.octo-stop` signal file) | Mutating |
| `Start-OctoInfrastructure` | Start the docker-compose containers (MongoDB, RabbitMQ, CrateDB) — deprecated, see below | Mutating |
| `Stop-OctoInfrastructure` | Stop the docker-compose containers | Mutating |

### Infrastructure (docker-compose — deprecated)

The local kind cluster (`Install-OctoKubernetes`, next section) is the supported local infrastructure; octo-tools deprecates the docker-compose setup and these cmdlets (removal planned for 2026-12-31). Use them only on a machine that still runs it.

| Cmdlet | Description | Safety |
|---|---|---|
| `Install-OctoInfrastructure` | First-time Docker setup | Mutating |
| `Uninstall-OctoInfrastructure` | Remove Docker containers + volumes | **Destructive** |
| `Get-OctoInfrastructureStatus` | Show container status | Read-only |
| `Invoke-CleanupInfraContainerDisks` | Clean unused Docker disk space | **Destructive** |
| `Backup-OctoInfrastructure` | Back up infra Docker volumes (Mongo + CrateDB) | Mutating (local) |
| `Restore-OctoInfrastructure` | Restore infra volumes from a named backup | **Destructive** |
| `Get-OctoInfrastructureBackup` | List available infra backups | Read-only |
| `Remove-OctoInfrastructureBackup` | Delete a named infra backup | **Destructive** |

### Local Kubernetes (kind) dev environment

An alternative to the docker-compose infra: MongoDB / RabbitMQ / CrateDB, the CRDs, and the Communication Operator run inside a local [kind](https://kind.sigs.k8s.io/) cluster (the .NET services still run as host processes via `Start-Octo`). **The two infra modes share the same host ports and CANNOT run at the same time** — `Install-OctoKubernetes` refuses to start while docker-compose infra containers are up. Full runbook: `C:\dev\meshmakers\octo-tools\kubernetes\README.md`; from-scratch setup: `C:\dev\meshmakers\octo-tools\kubernetes\QUICKSTART.md`.

| Cmdlet | Description | Safety |
|---|---|---|
| `Install-OctoKubernetes` | Create kind cluster + CRDs + in-cluster infra + ingress-nginx/cert-manager, then deploy the operator | Mutating |
| `Deploy-OctoOperator` | (Re)deploy the Communication Operator from the dev registry (`:main-latest`) | Mutating |
| `Get-OctoKubernetesStatus` | Show pods, Helm releases, and host-port reachability | Read-only |
| `Uninstall-OctoKubernetes` | Delete the kind cluster and ALL its data (Mongo + CrateDB PVCs) | **Destructive** |
| `Import-OctoImageToKind` | Load a locally-built image into the kind node | Mutating |
| `Add-OctoLocalCaTrust` / `Remove-OctoLocalCaTrust` | Trust / untrust the local root CA in the OS store | Mutating (Destructive for Remove) |

### Git Repository Management

| Cmdlet | Description | Safety |
|---|---|---|
| `Sync-AllGitRepos` | Pull all repos (rebase) | Mutating |
| `Sync-GitRepo` | Pull a single repo | Mutating |
| `Push-AllGitRepos` | Push the local commits of every `octo-*`/`mm-*` repo of the lane to origin — not the default way to publish work (see "Publishing work" below) | Mutating (remote) |
| `Push-GitRepo` | Push one repo to origin | Mutating (remote) |
| `Sync-Submodule [-repositoryPath <repo>]` | `git submodule update --init --remote --merge --recursive` in one repo | Mutating |
| `Get-AllGitRepStatus` | Git status across all repos | Read-only |
| `Find-AllGitRepos` | Discover all repos in workspace | Read-only |
| `Invoke-CloneMainRepos` | Clone all main repos | Mutating |
| `Sync-AllSubmodules` | Sync git submodules | Mutating |
| `Invoke-CleanAllGitRepos` | Clean all repos (remove untracked) | **Destructive** |

**Publishing work.** Changes reach `main` through pull requests from work branches, so a blanket `Push-AllGitRepos` is never the answer to "publish my work". When the `octo-claude-pm` plugin is installed, its `agent-operating-rules` decide how and when work is pushed; otherwise follow the repository's own contribution rules.

### Branch Management

| Cmdlet | Description | Safety |
|---|---|---|
| `New-TestBranch -MinorVersion <n> -Description <word> [-branch <lane>] [-NoPush]` | Create (or switch to) `test/0.<n>-<word>` in every repo of `Invoke-CloneMainRepos`, from a freshly fetched `origin/main`; dirty repos are listed, not branched; pushes unless `-NoPush` | Mutating (remote) |
| `Sync-TestBranch -MinorVersion <n> -Description <word> [-branch <lane>] [-NoPush]` | Fetch and merge `origin/main` into the test branch of every repo of `Invoke-CloneMainRepos`; conflicts are aborted and listed | Mutating (remote) |
| `Remove-TestBranch -MinorVersion <n> -Description <word> [-branch <lane>] [-LocalOnly]` | Delete the test branch locally and on origin (`-LocalOnly` keeps origin) | **Destructive** |
| `Invoke-SwitchAllBranches -Name <branch> [-branch <lane>] [-Push] [-IncludeSubmodules]` | Switch all repos of the lane to a branch (creates it when origin has none) | Mutating (remote with `-Push`) |
| `Compare-BranchStatus [-branch <lane>] [-targetBranch main] [-Details]` | Commits of each `octo-*`/`mm-*` repo ahead of `origin/<targetBranch>` | Read-only |

**Pre-release 0.x lines.** Work that is not ready for `main` can run on a pre-release line: a branch `test/0.<n>-<word>` (e.g. `test/0.2-dev`, `test/0.3-demo`; `<n>` 2-999, `<word>` letters, digits and `_` only, no hyphen) in all repositories of `Invoke-CloneMainRepos` (`mm-common` included), branched from a freshly fetched `origin/main`. Each line has its own checkout directory: without `-branch` the cmdlets use `<parent of rootPath>/0.<n>-<word>` (e.g. `meshmakers/0.3-demo` next to `meshmakers/main`; create it with `Invoke-CloneMainRepos -branch ../0.3-demo`); an explicit `-branch` (relative to `$rootPath`) names the folder, which is how existing lines such as `../dev` and `../demo` keep working. `New-TestBranch` does not branch a repository with uncommitted changes: it lists it with the reason and exits non-zero. Check which lines exist (`git ls-remote --heads origin test/0.<n>-<word>`; `Get-BranchAvailability` reads possibly stale remote-tracking refs of `$rootPath` only) and what a line holds (`Compare-BranchStatus -branch <line dir>`) before you judge where a change lives. Procedure: [workflows.md](references/workflows.md) section 5.

### NuGet Package Management

| Cmdlet | Description | Safety |
|---|---|---|
| `Copy-AllNuGetPackages` | Copy NuGet packages to shared folder | Mutating (local) |
| `Copy-NuGetPackages` | Copy packages from specific directory | Mutating (local) |
| `Sync-NuGetPackages` | Synchronize NuGet cache | Mutating (local) |
| `Remove-GlobalNuGetPackages [-path <cache>]` | Clear the `meshmakers.*/999.0.0` packages from a package cache (default `~/.nuget/packages`; a lane's own cache is `<lane>/.nuget-packages`) | **Destructive** |
| `Initialize-OctoLaneUserProps -branch <lane> [-AddRestorePackagesPath]` | Create or check `<lane>/Octo.User.props`; `-AddRestorePackagesPath` gives an existing lane its own package cache (once for main: `-branch branches/main`) | Mutating (local) |

### Cleanup & Maintenance

| Cmdlet | Description | Safety |
|---|---|---|
| `Invoke-KillDotnet [-branchRootPath <lane>]` | With `-branchRootPath`: only the lane's dotnet processes (Windows stops them, macOS/Linux lists them). Without it: every dotnet process (Windows only) - also feature environments' services and builds, so always pass the lane | Mutating |
| `Remove-BinAndObjFolders [-path <folder>]` | Delete all bin/ and obj/ folders below `-path` (default: the current folder) - pass the lane | **Destructive** |

### Authentication / Context (octo-cli)

| Cmdlet | Description | Safety |
|---|---|---|
| `Register-OctoCliContext -Installation <name> -TenantId <tenant>[,<tenant>...]` | **The** login cmdlet: registers the octo-cli context `<installation>[_<suffix>]_<tenant>` for an installation of your octo-tools config (`installations.json`, e.g. `local`), switches to it (one tenant only; with several it never switches) and logs in; `-NoSwitch`, `-NoLogin`, `-IncludeReporting`, `-IncludeAi`, `-UriSuffix`, `-Json`. It replaced the removed per-environment login helpers | Mutating |
| `Invoke-OctoTenantSweep -CliArguments '-c','<Command>',... (-Installation <i> \| -ContextTemplate <t> \| -Context <c>) (-Tenant a,b \| -AllTenants)` | Run one octo-cli command across many tenants (one context per tenant); never reads or prints a token; `-WhatIf` | Mutating (remote, as the command) |
| `Get-OctoToolsConfig` / `Get-OctoInstallation -Name <name>` | Read your octo-tools config (installations, registry, Rancher/Vault/Semaphore addresses) — never print it into a shared log | Read-only |
| `Invoke-IdentityOverlay [-OverlayFile <yaml>] [-DryRun]` | Add the local-dev redirect URIs of an overlay file to the blueprint-managed identity clients (`octo-cli -c ApplyClientOverlay`, idempotent); uses the active context | Mutating |
| `Invoke-OctoCliReconfigureLogLevel` | Reconfigure service log levels (3 mandatory params) | Mutating |
| `Register-AiBastion` | Register an Anthropic subscription token on a tenant (device-code OAuth) | Mutating (remote) |
| `Get-AiBastionStatus` | Read current AI Bastion lease metadata for a tenant | Read-only |

### Certificates

| Cmdlet | Description | Safety |
|---|---|---|
| `New-RootCertificate` | Generate root CA certificate | Mutating |
| `New-ServerCertificate` | Generate server certificate | Mutating |
| `New-AspNetDeveloperCertificate` | Set up ASP.NET dev HTTPS cert | Mutating |
| `Test-AspNetDeveloperCertificate` | Check the ASP.NET dev cert status | Read-only |
| `Remove-AspNetDeveloperCertificate` | Remove the ASP.NET dev cert | **Destructive** |

### Kubernetes helpers / DB access

| Cmdlet | Description | Safety |
|---|---|---|
| `Join-KubeConfigs` | Merge kubeconfig files | Mutating |
| `Remove-KubeConfig` | Delete a named context/cluster/user from `~/.kube/config` (interactive prompt) | **Destructive** |
| `Invoke-MongoPortForward` | Port-forward MongoDB from K8s | Mutating |
| `Get-RancherKubeConfig -Cluster <name>` | Routine read-only cluster access: fetches a kubeconfig through the Rancher API with your personal token and merges it into `~/.kube/config` | Mutating (local) |
| `Request-BreakGlassKubeConfig -Cluster <name> -Reason "<why>" -DurationHours <1-4>` | Incident write access: triggers the audited break-glass playbook that issues a short-lived cluster-admin token | Mutating (remote, audited) |

Both cluster-access cmdlets read their addresses from your octo-tools config and their tokens from your private profile; under `-Json` they emit only metadata (cluster, context, expiry). Never print the resulting kubeconfig, the profile or the token. Break-glass is for incidents only.

### Diagnostics & Comparison

| Cmdlet | Description | Safety |
|---|---|---|
| `Compare-CkVersions` | Diff CK model (`ckModel.yaml`) versions between two branch checkouts | Read-only |
| `Compare-Pipelines` | Diff local pipeline YAML against the deployed versions in a tenant | Read-only |
| `Get-BranchAvailability` | List repos where a given branch exists on remote | Read-only |
| `Test-OctoEncryption` | Smoke test that the encryption environment variables the local services need are set and agree (instance key, SECRET key ring); reports set/equal, not the values | Read-only |
| `Get-CiWasteReport [-Hours 24]` | Report duplicate CI work in Azure DevOps (GET requests only) | Read-only |

### Versioning & Templates

| Cmdlet | Description | Safety |
|---|---|---|
| `Sync-YamlTemplates` | Sync CI/CD YAML templates | Mutating |
| `Update-MeshmakerVersion` | Bump version numbers | Mutating |

### Not covered here

The profile loads further octo-tools modules this skill does not drive: the AGENTS.md tooling (`Initialize-OctoAgentDocs`, `Test-OctoAgentDocs`), the octo-devstack daemon management (`Start-OctoDevStackDaemon`, `Stop-OctoDevStackDaemon`, `Install-OctoDevStackDaemonService`, `Uninstall-OctoDevStackDaemonService`), `Invoke-StarOrgRepos` (GitHub stars), and cmdlets the build and install cmdlets call themselves (`Sync-OctoCkIntermediateVersions`, `Update-OctoCrateDb`, the local S3 store cmdlets of `Install-OctoKubernetes`). The remaining module files are internal helpers (JSON output, build stamps, catalog refresh, lane settings). The full, current list with parameters is octo-tools `CLAUDE.md` ("Common Development Commands") and `readme.md`.

## When the octo-devstack MCP server is available

octo-devstack is a local MCP daemon (it lives in octo-tools `devstack/`) that runs builds, test runs and the local stack for several Claude Code sessions on one machine. When its tools are available (`mcp__…octo-devstack__*`), they are an optional route that replaces the shell cmdlets below; without them the cmdlets of this skill stay the way, with `Start-Octo -nonInteractive $true` as the fallback for services.

| Shell cmdlet | octo-devstack tool |
|---|---|
| `New-OctoEnvironment`, `Add-OctoEnvironmentRepo`, `Remove-OctoEnvironment` | `lane_create`, `lane_add_repo`, `lane_remove` (`lane_list` shows the lane's worktrees) |
| `Invoke-BuildEnvironment`, `Invoke-BuildRange` in a lane | `lane_build` (returns a job; wait with `job_status`) |
| `Invoke-OctoTestRun` | `lane_test` (`test_lock` shows the machine-wide test lock) |
| `Sync-OctoEnvironment`, `Get-OctoAffectedRepos` | `lane_sync`, `lane_affected` |
| `Invoke-BuildRange` / `Invoke-BuildAll` in the base lane | `base_build`, `base_test`; `build_plan` predicts what would be built |
| `Start-Octo` / `Stop-Octo` | `stack_start` / `stack_stop` (a lane gets its own stack), `service_start`, `service_stop`, `service_restart` |
| Checking services and logs | `stack_status`, `stack_verify`, `stack_attention`, `service_logs` |

Rules of the route: a lane holds its own stack; any change to the **shared** stack (start, stop, restart of its services, builds that stop services) needs its lease first (`lease_status`, `lease_acquire`, `lease_release`). Pass the same `owner` and `session` in every changing call. Base-lane builds that publish into the shared `nuget/` and the `admin_*` tools change the machine for every session - leave them to the person who runs the machine.

## Safety Rules

### Read-only (execute directly, no confirmation)
`Get-AllGitRepStatus`, `Get-OctoInfrastructureStatus`, `Get-OctoKubernetesStatus`, `Get-OctoInfrastructureBackup`, `Find-AllGitRepos`, `Compare-BranchStatus`, `Compare-CkVersions`, `Compare-Pipelines`, `Get-BranchAvailability`, `Test-AspNetDeveloperCertificate`, `Get-AiBastionStatus`, `Get-OctoBuildOrder`, `Get-OctoTestLock`, `Get-OctoEnvironment`, `Get-OctoAffectedRepos`, `Test-OctoEncryption`, `Get-CiWasteReport`, `Get-OctoToolsConfig`, `Get-OctoInstallation`, `Invoke-BuildRange -WhatIf`, `Invoke-BuildAll -DryRun`

### Mutating — local (execute with brief confirmation)
`Invoke-BuildRange`, `Invoke-BuildAll`, `Invoke-Build`, `Invoke-OctoTestRun`, `Invoke-BuildEnvironment`, `Invoke-Publish`, `Invoke-BuildZenonPlug`, `Start-OctoInfrastructure`, `Stop-OctoInfrastructure`, `Install-OctoInfrastructure`, `Backup-OctoInfrastructure`, `Install-OctoKubernetes`, `Deploy-OctoOperator`, `Import-OctoImageToKind`, `Add-OctoLocalCaTrust`, `Sync-AllGitRepos`, `Sync-GitRepo`, `Invoke-CloneMainRepos`, `Sync-AllSubmodules`, `Sync-Submodule`, `New-TestBranch -NoPush`, `Sync-TestBranch -NoPush`, `Invoke-SwitchAllBranches` (without `-Push`), `Copy-AllNuGetPackages`, `Copy-NuGetPackages`, `Sync-NuGetPackages`, `Register-OctoCliContext`, `Invoke-IdentityOverlay`, `Get-RancherKubeConfig`, `Invoke-OctoCliReconfigureLogLevel`, `New-RootCertificate`, `New-ServerCertificate`, `New-AspNetDeveloperCertificate`, `Join-KubeConfigs`, `Invoke-MongoPortForward`, `Sync-YamlTemplates`, `Update-MeshmakerVersion`, `Invoke-KillDotnet`, `Stop-Octo`

### Mutating — remote (confirm with emphasis)
`Push-AllGitRepos`, `Push-GitRepo`, `New-TestBranch` and `Sync-TestBranch` without `-NoPush` (push to origin), `Invoke-SwitchAllBranches -Push`, `Invoke-OctoTenantSweep` (runs its command on every listed tenant — `-WhatIf` first), `Request-BreakGlassKubeConfig` (audited cluster-admin access, incidents only), `Register-AiBastion` (writes a token to a remote tenant — see note below)

### Destructive (explicit confirmation + warning)
`Remove-BinAndObjFolders`, `Remove-GlobalNuGetPackages`, `Invoke-CleanAllGitRepos`, `Uninstall-OctoInfrastructure`, `Restore-OctoInfrastructure`, `Remove-OctoInfrastructureBackup`, `Uninstall-OctoKubernetes`, `Remove-KubeConfig`, `Remove-TestBranch`, `Invoke-CleanupInfraContainerDisks`, `Remove-AspNetDeveloperCertificate`, `Remove-OctoLocalCaTrust`

### Service startup — non-interactive is the agent default — CRITICAL

`Start-Octo` blocks the session waiting for a keypress **only when `-nonInteractive` is not set**. When Claude (or any agent / CI job) starts services it MUST ALWAYS run:

```
Start-Octo -nonInteractive $true -configuration DebugL
```

In this mode `Start-Octo` blocks until a service fails or a `.octo-stop` signal file appears — it never waits for a keypress. Stop the services from another invocation with:

```
Stop-Octo
```

`Stop-Octo` is a standalone cmdlet that writes the `.octo-stop` signal file (it has a `-branch` parameter mirroring `Start-Octo`/`Install-OctoKubernetes`). This non-interactive start + `Stop-Octo` pair is a firm repo convention — never start services interactively from an agent session.

**NEVER use `Invoke-BuildAndStartOcto` from an agent session** — it chains into the interactive `Start-Octo` (no `-nonInteractive` pass-through) and will block the session indefinitely. Build with `Invoke-BuildRange` or `Invoke-BuildAll`, then start with `Start-Octo -nonInteractive $true` instead.

### Interactive (only when a human runs it directly)
Interactive blocking applies to `Start-Octo` (without `-nonInteractive $true`) and `Invoke-BuildAndStartOcto`. If a human explicitly asks for an interactive foreground run, warn first:

> **Warning:** This command will block the current session until you press a key to stop the services. The session will not be available for other commands while services are running.

### AI Bastion secret handling
`Register-AiBastion` drives the Anthropic device-code OAuth flow and POSTs the token to the AI Adapter's `POST /{tenantId}/v1/credentials/register`. The bearer token comes from `$env:OCTO_BASTION_TOKEN` (preferred) or `-BearerToken` (avoid: it puts the token on the command line); token material is held in memory only and zeroed in a `finally` block. Never echo, log, or persist the bearer token or the device-code output.

## Smart Behaviors

### Natural language mapping
- "rebuild after my change" / "build the engine and what uses it" → `Invoke-BuildRange -branch branches/main -from <changed repo> -to <last consumer> -WhatIf`, then without `-WhatIf`, then `-verifyTests` before hand-off
- "why does the build fail with NU1101/NU1102 on 999.0.0" → the chain is out of sync: `Invoke-BuildAll -branch branches/main -configuration DebugL -excludeFrontend $true`
- "run the tests of X" → `Invoke-OctoTestRun -branch branches/main -repo <X>` (`-rerunFailed` to repeat only failures)
- "build everything" / "build all" / "full reset" → `Invoke-BuildAll -branch branches/main -configuration DebugL`
- "build without frontend" / "build backend" → `Invoke-BuildAll -branch branches/main -configuration DebugL -excludeFrontend $true`
- "build asset repo" → `Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL` (only if no NuGet changes!)
- "rebuild after pull" / "sync and build" → `Sync-AllGitRepos -branch branches/main` then `Invoke-BuildAll -branch branches/main -configuration DebugL -excludeFrontend $true`
- "git status" / "repo status" → `Get-AllGitRepStatus`
- "pull latest" / "sync repos" → `Sync-AllGitRepos -branch branches/main`
- "push everything" / "publish my work" → not `Push-AllGitRepos` (see "Publishing work"); with `octo-claude-pm` installed its `agent-operating-rules` decide
- "start services" / "start octo" → `Start-Octo -nonInteractive $true -configuration DebugL` (agent default; never block the session)
- "stop services" / "stop octo" → `Stop-Octo`
- "start infra" / "start docker" → `Start-OctoInfrastructure`
- "stop infra" / "stop docker" → `Stop-OctoInfrastructure`
- "infra status" / "docker status" → `Get-OctoInfrastructureStatus`
- "backup infra" / "backup before testing" → `Backup-OctoInfrastructure` (stop infra first)
- "restore infra" / "list backups" → `Restore-OctoInfrastructure -Name <name>` / `Get-OctoInfrastructureBackup`
- "set up local kubernetes" / "kind cluster" / "install k8s" → `Install-OctoKubernetes` (refuses if docker-compose infra is up)
- "deploy operator" → `Deploy-OctoOperator`
- "k8s status" / "kubernetes status" → `Get-OctoKubernetesStatus`
- "tear down kind" / "uninstall kubernetes" → `Uninstall-OctoKubernetes` (destructive — confirm)
- "clean build" → confirm, then `Remove-BinAndObjFolders -path (Join-Path $rootPath 'branches/main')` (main-checkout profile: `-path $rootPath`; it defaults to the current folder - never run it at the workspace root, it would hit every lane and feature environment) + `Invoke-BuildAll -branch branches/main -configuration DebugL`
- "clean everything" → confirm each destructive step separately
- "switch to local" / "login local" → `Register-OctoCliContext -Installation local -TenantId <tenant>`
- "register context for <installation>" → `Register-OctoCliContext -Installation <name from your installations.json> -TenantId <tenant>`
- "run this octo-cli command on all tenants" → `Invoke-OctoTenantSweep -CliArguments '-c','<Command>' -Installation <name> -AllTenants -WhatIf`, then without `-WhatIf`
- "cluster access" / "kubeconfig for <cluster>" → `Get-RancherKubeConfig -Cluster <name>` (read-only); incident write access → `Request-BreakGlassKubeConfig`
- "compare CK versions" / "diff ck models between branches" → `Compare-CkVersions <otherBranch>`
- "start work on AB#1234" / "feature worktree" / "work on a library change" → `New-OctoEnvironment -env ab1234-<desc> -repos <repo> -workItem AB#1234`, then `Invoke-BuildEnvironment -env ab1234-<desc> -verifyTests` (or octo-devstack `lane_create` / `lane_build`); never publish feature work into `branches/main/nuget`
- "which repos does my change affect" → `Get-OctoAffectedRepos -env <env>`
- "use my existing worktree" → `Add-OctoEnvironmentRepo -env <env> -path <worktree>` (`-inPlace`: see the in-place caveat)
- "adopt a hand-made environment" (`wt-<lane>` with worktrees but no `.octo/environment.json`; its own name is refused) → `New-OctoEnvironment -env <new name> -workItem AB#..` (no `-repos`: empty), then `Add-OctoEnvironmentRepo -env <new name> -path <worktree> -inPlace` per worktree - only when no session works there
- "done with the feature" → `Remove-OctoEnvironment -env <env>` after the PR is merged
- "create test branch" → `New-TestBranch` with user-provided version + description

### Default configuration
Always use `-configuration DebugL` for build commands unless the user explicitly specifies a different configuration. This is the standard local development configuration.

### Build order awareness
Feature work on a work item is built in its feature environment (`Invoke-BuildEnvironment`), not in `branches/main`. For main itself: after a change use `Invoke-BuildRange` over the changed repository and its consumers (`-WhatIf` first); after a pull, a branch switch or NU1101/NU1102 on `999.0.0` use `Invoke-BuildAll` (see "Build Strategy"). Do NOT orchestrate `Invoke-Build` calls in dependency order or copy NuGet packages by hand — both cmdlets take the order from `OctoBuildOrder.psm1` and propagate the packages. Only use `Invoke-Build` for a single service repo where no package is affected.

### Workflow suggestions
When the user describes a high-level goal (e.g., "set up a fresh dev environment"), suggest the appropriate multi-step workflow from `references/workflows.md` and offer to execute it step by step.

## Execution Flow

1. **Parse intent** — Map natural language to cmdlet(s) from the tables above
2. **Check safety level** — Determine if read-only, mutating, destructive, or interactive
3. **Confirm if needed** — For mutating/destructive ops, show the command + summary, wait for confirmation
4. **Non-interactive services** — When starting services, always use `Start-Octo -nonInteractive $true` and stop with `Stop-Octo`. Never run `Invoke-BuildAndStartOcto` from an agent session. Only warn about session blocking if a human explicitly requests an interactive foreground run.
5. **Execute** — Run via the wrapper script and present results clearly
6. **Suggest next steps** — After completion, suggest logical follow-up actions (e.g., after build → start services)
