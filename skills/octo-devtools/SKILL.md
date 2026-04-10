---
name: octo-devtools
description: This skill should be used when the user asks about building OctoMesh repositories, starting or stopping services, managing Docker infrastructure, syncing git repositories, creating or managing test branches, managing NuGet packages, cleaning build artifacts, or any development workflow task. Trigger on mentions of build, compile, dotnet build, start services, stop services, infrastructure, docker compose, git sync, pull repos, push repos, branch management, test branch, NuGet packages, clean build, kill dotnet, certificates, clone repos, git status across repos, or development environment setup. Also trigger when user mentions Invoke-BuildAll, Invoke-Build, Start-Octo, Start-OctoInfrastructure, Sync-AllGitRepos, Get-AllGitRepStatus, or any OctoMesh PowerShell commandlet name.
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

### When to use `Invoke-BuildAll` (DEFAULT CHOICE)

**Use `Invoke-BuildAll` whenever building after code changes that could affect NuGet packages, or when unsure.** This is the safe default. It builds repos in dependency order AND copies NuGet packages to the shared `nuget/` folder between each step.

```
# Full build (all repos including frontends)
Invoke-BuildAll -configuration DebugL

# Backend only — skips Angular frontends (saves significant time)
Invoke-BuildAll -configuration DebugL -excludeFrontend $true

# Core repos only — skips optional/additional repos AND frontends
Invoke-BuildAll -configuration DebugL -excludeFrontend $true -excludeAdditional $true
```

**Use `Invoke-BuildAll` for:**
- After pulling latest changes (`Sync-AllGitRepos`)
- After switching branches
- When changes touch library repos (mm-common, octo-construction-kit-engine, octo-sdk, octo-common-services, octo-distributedEventHub, octo-construction-kit-engine-mongodb)
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

**NEVER use `Invoke-Build` to propagate NuGet changes.** Do not attempt to manually chain `Invoke-Build` + `Copy-NuGetPackages` to replicate what `Invoke-BuildAll` does — use `Invoke-BuildAll` with the appropriate exclusion flags instead.

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
| `Invoke-BuildAndStartOcto` | Build all + start services | **Interactive** |
| `Invoke-BuildZenonPlug` | Build Zenon plug-in | Mutating (local) |

### Service Management

| Cmdlet | Description | Safety |
|---|---|---|
| `Start-Octo` | Start all OctoMesh services | **Interactive** |
| `Start-OctoInfrastructure` | Start Docker containers (MongoDB, RabbitMQ, CrateDB) | Mutating |
| `Stop-OctoInfrastructure` | Stop Docker containers | Mutating |

### Infrastructure

| Cmdlet | Description | Safety |
|---|---|---|
| `Install-OctoInfrastructure` | First-time Docker setup | Mutating |
| `Uninstall-OctoInfrastructure` | Remove Docker containers + volumes | **Destructive** |
| `Get-OctoInfrastructureStatus` | Show container status | Read-only |
| `Invoke-CleanupInfraContainerDisks` | Clean unused Docker disk space | **Destructive** |

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

### Authentication / Environment

| Cmdlet | Description | Safety |
|---|---|---|
| `Invoke-OctoCliLoginLocal` | Log in to local environment | Mutating |
| `Invoke-OctoCliLoginTest2` | Log in to test-2 environment | Mutating |
| `Invoke-OctoCliLoginStaging` | Log in to staging environment | Mutating |
| `Invoke-OctoCliLoginProduction` | Log in to production environment | Mutating |
| `Invoke-OctoCliReconfigureLogLevel` | Reconfigure service log levels | Mutating |

### Certificates

| Cmdlet | Description | Safety |
|---|---|---|
| `New-RootCertificate` | Generate root CA certificate | Mutating |
| `New-ServerCertificate` | Generate server certificate | Mutating |
| `AspNetDeveloperCertificate` | Set up ASP.NET dev HTTPS cert | Mutating |

### Kubernetes

| Cmdlet | Description | Safety |
|---|---|---|
| `Join-KubeConfigs` | Merge kubeconfig files | Mutating |
| `Invoke-MongoPortForward` | Port-forward MongoDB from K8s | Mutating |

### Versioning & Templates

| Cmdlet | Description | Safety |
|---|---|---|
| `Sync-YamlTemplates` | Sync CI/CD YAML templates | Mutating |
| `Update-MeshmakerVersion` | Bump version numbers | Mutating |

## Safety Rules

### Read-only (execute directly, no confirmation)
`Get-AllGitRepStatus`, `Get-OctoInfrastructureStatus`, `Find-AllGitRepos`, `Compare-BranchStatus`

### Mutating — local (execute with brief confirmation)
`Invoke-BuildAll`, `Invoke-Build`, `Invoke-BuildFrontend`, `Invoke-Publish`, `Start-OctoInfrastructure`, `Stop-OctoInfrastructure`, `Install-OctoInfrastructure`, `Sync-AllGitRepos`, `Sync-GitRepo`, `Invoke-CloneMainRepos`, `Sync-AllSubmodules`, `New-TestBranch`, `Sync-TestBranch`, `Invoke-SwitchAllBranches`, `Copy-AllNuGetPackages`, `Copy-NuGetPackages`, `Sync-NuGetPackages`, `Invoke-OctoCliLogin*`, `New-RootCertificate`, `New-ServerCertificate`, `AspNetDeveloperCertificate`, `Join-KubeConfigs`, `Invoke-MongoPortForward`, `Sync-YamlTemplates`, `Update-MeshmakerVersion`, `Invoke-KillDotnet`

### Mutating — remote (confirm with emphasis)
`Push-AllGitRepos`, `Push-GitRepo`

### Destructive (explicit confirmation + warning)
`Remove-BinAndObjFolders`, `Remove-GlobalNuGetPackages`, `Invoke-CleanAllGitRepos`, `Uninstall-OctoInfrastructure`, `Remove-TestBranch`, `Invoke-CleanupInfraContainerDisks`

### Interactive (warn about session blocking)
`Start-Octo`, `Invoke-BuildAndStartOcto` — these commands block the terminal session until services are stopped via keypress. **Always display this warning before executing:**

> **Warning:** This command will block the current session until you press a key to stop the services. The session will not be available for other commands while services are running.

## Smart Behaviors

### Natural language mapping
- "build everything" / "build all" → `Invoke-BuildAll -configuration DebugL`
- "build without frontend" / "build backend" → `Invoke-BuildAll -configuration DebugL -excludeFrontend $true`
- "build core only" / "build libraries" / "build base" → `Invoke-BuildAll -configuration DebugL -excludeFrontend $true -excludeAdditional $true`
- "build asset repo" → `Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL` (only if no NuGet changes!)
- "rebuild after pull" / "sync and build" → `Sync-AllGitRepos` then `Invoke-BuildAll -configuration DebugL`
- "git status" / "repo status" → `Get-AllGitRepStatus`
- "pull latest" / "sync repos" → `Sync-AllGitRepos`
- "push everything" → `Push-AllGitRepos` (confirm first!)
- "start infra" / "start docker" → `Start-OctoInfrastructure`
- "stop infra" / "stop docker" → `Stop-OctoInfrastructure`
- "infra status" / "docker status" → `Get-OctoInfrastructureStatus`
- "clean build" → confirm, then `Remove-BinAndObjFolders` + `Invoke-BuildAll -configuration DebugL`
- "clean everything" → confirm each destructive step separately
- "switch to local" / "login local" → `Invoke-OctoCliLoginLocal`
- "create test branch" → `New-TestBranch` with user-provided version + description

### Default configuration
Always use `-configuration DebugL` for build commands unless the user explicitly specifies a different configuration. This is the standard local development configuration.

### Build order awareness
When the user asks to build, default to `Invoke-BuildAll` with exclusion flags to limit scope — do NOT attempt to manually orchestrate `Invoke-Build` calls in dependency order or manually copy NuGet packages. The `Invoke-BuildAll` script already handles the correct build order and NuGet propagation. Only use `Invoke-Build` for a single service repo where no NuGet packages are affected.

### Workflow suggestions
When the user describes a high-level goal (e.g., "set up a fresh dev environment"), suggest the appropriate multi-step workflow from `references/workflows.md` and offer to execute it step by step.

## Execution Flow

1. **Parse intent** — Map natural language to cmdlet(s) from the tables above
2. **Check safety level** — Determine if read-only, mutating, destructive, or interactive
3. **Confirm if needed** — For mutating/destructive ops, show the command + summary, wait for confirmation
4. **Warn if interactive** — For `Start-Octo` and `Invoke-BuildAndStartOcto`, display blocking warning
5. **Execute** — Run via the wrapper script and present results clearly
6. **Suggest next steps** — After completion, suggest logical follow-up actions (e.g., after build → start services)
