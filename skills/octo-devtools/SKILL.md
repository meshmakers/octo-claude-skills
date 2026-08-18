---
name: octo-devtools
description: Drives OctoMesh local development through the octo-tools PowerShell cmdlets — building repos in dependency order, starting and stopping services (always non-interactively for agents via Start-Octo -nonInteractive $true / Stop-Octo), managing Docker or local kind Kubernetes infrastructure, syncing and branching git repos, NuGet package propagation, certificates, and octo-cli context/auth setup. Use it for any OctoMesh dev-environment or DevOps task. Trigger on build, compile, dotnet build, start services, stop services, Start-Octo, Stop-Octo, Invoke-BuildAll, Invoke-Build, infrastructure, docker compose, kind, Kubernetes, Install-OctoKubernetes, Deploy-OctoOperator, git sync, pull repos, push repos, Get-AllGitRepStatus, branch management, test branch, NuGet packages, clean build, kill dotnet, certificates, clone repos, register context, login local/staging/production, infrastructure backup, or any OctoMesh PowerShell cmdlet name.
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

OctoMesh is a monorepo where repos produce NuGet packages consumed by downstream repos. The build system handles copying these NuGet packages between repos automatically — but ONLY when using `Invoke-BuildAll`.

**The one difference that matters: `Invoke-Build` does NOT propagate NuGet packages between repos, `Invoke-BuildAll` does.** A repo built with `Invoke-Build` writes its package nowhere the other repos can see it, so every consumer keeps compiling and running against the previous version. That is why `Invoke-BuildAll` is the default and `Invoke-Build` is the narrow exception.

**The only sanctioned way to make a build cheaper is `-excludeFrontend $true`.** Do not narrow the build any further to save time — see the warning under the examples below.

### When to use `Invoke-BuildAll` (DEFAULT CHOICE)

**Use `Invoke-BuildAll` whenever building after code changes that could affect NuGet packages, or when unsure.** This is the safe default. It builds repos in dependency order AND copies NuGet packages to the shared `nuget/` folder between each step.

```
# Full build (all repos including frontends)
Invoke-BuildAll -configuration DebugL

# Backend only — skips Angular frontends (saves significant time)
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

**Do NOT reach for `-excludeAdditional $true` to save time.** It stops after the core library chain and skips the service repos, so a changed contract lands in the shared `nuget/` folder while identity, asset-repo and the other services keep running against the old one. The failure surfaces later, at service startup or at runtime, far away from the build that caused it. The parameter is documented in `references/command-reference.md` because it exists — not because it is a recommended shortcut.

**Use `Invoke-BuildAll` for:**
- After pulling latest changes (`Sync-AllGitRepos`)
- After switching branches
- When changes touch repos in the explicit build order (mm-common, octo-distributedEventHub, octo-construction-kit-engine, octo-sdk, octo-construction-kit-engine-mongodb, octo-common-services, octo-mesh-adapter, octo-bot-services, octo-communication-controller-services) — these produce NuGet packages consumed downstream
- When unsure whether changes affect NuGet packages
- Clean builds after deleting bin/obj folders
- First build after clone

### When `Invoke-Build` is safe (SINGLE REPO, NO NUGET IMPACT)

`Invoke-Build` builds one repo in isolation. It does NOT handle NuGet package propagation.

**`Invoke-Build` is ONLY appropriate when:**
- Making changes within a single service repo (e.g., `octo-asset-repo-services`, `octo-identity-services`)
- The changes do NOT affect any NuGet package produced by that repo
- All upstream NuGet dependencies are already up-to-date in the `nuget/` folder

```
# Safe: editing a controller in asset repo services
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

**NEVER use `Invoke-Build` to propagate NuGet changes.** Do not attempt to manually chain `Invoke-Build` + `Copy-NuGetPackages` to replicate what `Invoke-BuildAll` does — use `Invoke-BuildAll` instead (with `-excludeFrontend $true` when the frontends are not needed).

## Command Quick Reference

For full parameter details, read `references/command-reference.md` in this skill directory.
For common multi-step workflows, read `references/workflows.md` in this skill directory.

### Build & Compilation

| Cmdlet | Description | Safety |
|---|---|---|
| `Invoke-BuildAll` | Build repos in dependency order WITH NuGet propagation — **use this by default** | Mutating (local) |
| `Invoke-Build` | Build a single repo WITHOUT NuGet handling — only for isolated service changes | Mutating (local) |
| `Invoke-BuildFrontend` | Build Angular frontends | Mutating (local) |
| `Invoke-Publish` | Publish a .NET project | Mutating (local) |
| `Invoke-BuildAndStartOcto` | Build all + start services — chains into **interactive** `Start-Octo`. **Do NOT use from an agent session** (see safety rules) | **Interactive** |
| `Invoke-BuildZenonPlug` | Build Zenon plug-in | Mutating (local) |

### Service Management

| Cmdlet | Description | Safety |
|---|---|---|
| `Start-Octo` | Start OctoMesh services. **From an agent always pass `-nonInteractive $true`** | Mutating (interactive only when `-nonInteractive` is not set) |
| `Stop-Octo` | Stop services started in non-interactive mode (writes a `.octo-stop` signal file) | Mutating |
| `Start-OctoInfrastructure` | Start Docker containers (MongoDB, RabbitMQ, CrateDB) | Mutating |
| `Stop-OctoInfrastructure` | Stop Docker containers | Mutating |

### Infrastructure

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
| `Push-AllGitRepos` | Push all repos to remote | Mutating (remote) |
| `Push-GitRepo` | Push a single repo | Mutating (remote) |
| `Get-AllGitRepStatus` | Git status across all repos | Read-only |
| `Find-AllGitRepos` | Discover all repos in workspace | Read-only |
| `Invoke-CloneMainRepos` | Clone all main repos | Mutating |
| `Sync-AllSubmodules` | Sync git submodules | Mutating |
| `Invoke-CleanAllGitRepos` | Clean all repos (remove untracked) | **Destructive** |

### Branch Management

| Cmdlet | Description | Safety |
|---|---|---|
| `New-TestBranch` | Create test branch across all repos | Mutating |
| `Remove-TestBranch` | Delete test branch from all repos | **Destructive** |
| `Sync-TestBranch` | Merge base into test branch | Mutating |
| `Invoke-SwitchAllBranches` | Switch all repos to a branch | Mutating |
| `Compare-BranchStatus` | Compare branch status | Read-only |

### NuGet Package Management

| Cmdlet | Description | Safety |
|---|---|---|
| `Copy-AllNuGetPackages` | Copy NuGet packages to shared folder | Mutating (local) |
| `Copy-NuGetPackages` | Copy packages from specific directory | Mutating (local) |
| `Sync-NuGetPackages` | Synchronize NuGet cache | Mutating (local) |
| `Remove-GlobalNuGetPackages` | Clear global NuGet cache | **Destructive** |

### Cleanup & Maintenance

| Cmdlet | Description | Safety |
|---|---|---|
| `Invoke-KillDotnet` | Kill all dotnet processes | Mutating |
| `Remove-BinAndObjFolders` | Delete all bin/ and obj/ folders | **Destructive** |

### Authentication / Context (octo-cli)

| Cmdlet | Description | Safety |
|---|---|---|
| `Register-OctoCliContext` | **Recommended** — register a named octo-cli context for any installation (`local`, `test-2`, `staging-1`, `prod-1`, `prod-2`) | Mutating |
| `Invoke-OctoCliLoginLocal` | Log in to local environment (`-tenantId`, `-includeReporting`) | Mutating |
| `Invoke-OctoCliLoginTest2` | Log in to test-2 environment | Mutating |
| `Invoke-OctoCliLoginStaging` | **Legacy** — old `*.meshmakers.cloud` domains; prefer `Register-OctoCliContext -Installation staging-1` | Mutating |
| `Invoke-OctoCliLoginProduction` | **Legacy** — old `*.meshmakers.cloud` domains; prefer `Register-OctoCliContext -Installation prod-1`/`prod-2` | Mutating |
| `Invoke-OctoCliReconfigureLogLevel` | Reconfigure service log levels (3 mandatory params) | Mutating |
| `Invoke-SetDebugConfiguration` | Register the Admin Panel debug OAuth client + scopes (run after local login) | Mutating |
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

### Diagnostics & Comparison

| Cmdlet | Description | Safety |
|---|---|---|
| `Compare-CkVersions` | Diff CK model (`ckModel.yaml`) versions between two branch checkouts | Read-only |
| `Compare-Pipelines` | Diff local pipeline YAML against the deployed versions in a tenant | Read-only |
| `Get-BranchAvailability` | List repos where a given branch exists on remote | Read-only |

### Versioning & Templates

| Cmdlet | Description | Safety |
|---|---|---|
| `Sync-YamlTemplates` | Sync CI/CD YAML templates | Mutating |
| `Update-MeshmakerVersion` | Bump version numbers | Mutating |

## Safety Rules

### Read-only (execute directly, no confirmation)
`Get-AllGitRepStatus`, `Get-OctoInfrastructureStatus`, `Get-OctoKubernetesStatus`, `Get-OctoInfrastructureBackup`, `Find-AllGitRepos`, `Compare-BranchStatus`, `Compare-CkVersions`, `Compare-Pipelines`, `Get-BranchAvailability`, `Test-AspNetDeveloperCertificate`, `Get-AiBastionStatus`

### Mutating — local (execute with brief confirmation)
`Invoke-BuildAll`, `Invoke-Build`, `Invoke-BuildFrontend`, `Invoke-Publish`, `Invoke-BuildZenonPlug`, `Start-OctoInfrastructure`, `Stop-OctoInfrastructure`, `Install-OctoInfrastructure`, `Backup-OctoInfrastructure`, `Install-OctoKubernetes`, `Deploy-OctoOperator`, `Import-OctoImageToKind`, `Add-OctoLocalCaTrust`, `Sync-AllGitRepos`, `Sync-GitRepo`, `Invoke-CloneMainRepos`, `Sync-AllSubmodules`, `New-TestBranch`, `Sync-TestBranch`, `Invoke-SwitchAllBranches`, `Copy-AllNuGetPackages`, `Copy-NuGetPackages`, `Sync-NuGetPackages`, `Register-OctoCliContext`, `Invoke-OctoCliLogin*`, `Invoke-OctoCliReconfigureLogLevel`, `Invoke-SetDebugConfiguration`, `New-RootCertificate`, `New-ServerCertificate`, `New-AspNetDeveloperCertificate`, `Join-KubeConfigs`, `Invoke-MongoPortForward`, `Sync-YamlTemplates`, `Update-MeshmakerVersion`, `Invoke-KillDotnet`, `Stop-Octo`

### Mutating — remote (confirm with emphasis)
`Push-AllGitRepos`, `Push-GitRepo`, `Register-AiBastion` (writes a token to a remote tenant — see note below)

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

**NEVER use `Invoke-BuildAndStartOcto` from an agent session** — it chains into the interactive `Start-Octo` (no `-nonInteractive` pass-through) and will block the session indefinitely. Build with `Invoke-BuildAll`, then start with `Start-Octo -nonInteractive $true` instead.

### Interactive (only when a human runs it directly)
Interactive blocking applies to `Start-Octo` (without `-nonInteractive $true`) and `Invoke-BuildAndStartOcto`. If a human explicitly asks for an interactive foreground run, warn first:

> **Warning:** This command will block the current session until you press a key to stop the services. The session will not be available for other commands while services are running.

### AI Bastion secret handling
`Register-AiBastion` drives the Anthropic device-code OAuth flow and POSTs the token to the AI Adapter's `POST /{tenantId}/v1/credentials/register`. The bearer token comes from `-BearerToken` or `$env:OCTO_BASTION_TOKEN`; token material is held in memory only and zeroed in a `finally` block. Never echo, log, or persist the bearer token or the device-code output.

## Smart Behaviors

### Natural language mapping
- "build everything" / "build all" → `Invoke-BuildAll -configuration DebugL`
- "build without frontend" / "build backend" → `Invoke-BuildAll -configuration DebugL -excludeFrontend $true`
- "build asset repo" → `Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL` (only if no NuGet changes!)
- "rebuild after pull" / "sync and build" → `Sync-AllGitRepos` then `Invoke-BuildAll -configuration DebugL`
- "git status" / "repo status" → `Get-AllGitRepStatus`
- "pull latest" / "sync repos" → `Sync-AllGitRepos`
- "push everything" → `Push-AllGitRepos` (confirm first!)
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
- "clean build" → confirm, then `Remove-BinAndObjFolders` + `Invoke-BuildAll -configuration DebugL`
- "clean everything" → confirm each destructive step separately
- "switch to local" / "login local" → `Invoke-OctoCliLoginLocal` (or `Register-OctoCliContext -Installation local -TenantId <tenant>`)
- "register context for staging" / "add context for production" → `Register-OctoCliContext -Installation staging-1|prod-1|prod-2 -TenantId <tenant>`
- "compare CK versions" / "diff ck models between branches" → `Compare-CkVersions <otherBranch>`
- "create test branch" → `New-TestBranch` with user-provided version + description

### Default configuration
Always use `-configuration DebugL` for build commands unless the user explicitly specifies a different configuration. This is the standard local development configuration.

### Build order awareness
When the user asks to build, default to `Invoke-BuildAll`, narrowing it at most with `-excludeFrontend $true` — do NOT attempt to manually orchestrate `Invoke-Build` calls in dependency order or manually copy NuGet packages. The `Invoke-BuildAll` script already handles the correct build order and NuGet propagation. Only use `Invoke-Build` for a single service repo where no NuGet packages are affected.

### Workflow suggestions
When the user describes a high-level goal (e.g., "set up a fresh dev environment"), suggest the appropriate multi-step workflow from `references/workflows.md` and offer to execute it step by step.

## Execution Flow

1. **Parse intent** — Map natural language to cmdlet(s) from the tables above
2. **Check safety level** — Determine if read-only, mutating, destructive, or interactive
3. **Confirm if needed** — For mutating/destructive ops, show the command + summary, wait for confirmation
4. **Non-interactive services** — When starting services, always use `Start-Octo -nonInteractive $true` and stop with `Stop-Octo`. Never run `Invoke-BuildAndStartOcto` from an agent session. Only warn about session blocking if a human explicitly requests an interactive foreground run.
5. **Execute** — Run via the wrapper script and present results clearly
6. **Suggest next steps** — After completion, suggest logical follow-up actions (e.g., after build → start services)
