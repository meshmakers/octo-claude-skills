# Common OctoMesh Development Workflows

Multi-step workflows for typical development scenarios.

> **Agent note:** Whenever Claude or a CI job starts services, ALWAYS use `Start-Octo -nonInteractive $true` and stop them with `Stop-Octo` from a separate invocation. Never use `Invoke-BuildAndStartOcto` from an agent session — it chains into the interactive `Start-Octo` and blocks indefinitely. The interactive `Start-Octo` (no `-nonInteractive`) is only for a human running it directly in a terminal.

## 1. First-Time Setup

For a brand new development environment:

```
1. Invoke-CloneMainRepos                                  # Clone all repos (incl. octo-helm-core)
2. Install-OctoInfrastructure                             # Set up Docker containers
3. Start-OctoInfrastructure                               # Start MongoDB, RabbitMQ, CrateDB
4. Invoke-BuildAll -configuration DebugL                  # Build everything
5. Start-Octo -nonInteractive $true -configuration DebugL # Start all services (agent-safe)
```

After services are running, authenticate the CLI (in a separate invocation — step 5 is blocking):
```
6. Invoke-OctoCliLoginLocal
   # or, recommended: Register-OctoCliContext -Installation local -TenantId meshtest
```

When finished, stop the services:
```
7. Stop-Octo                                              # Writes the .octo-stop signal file
```

## 2. Daily Development Start

When infrastructure is already installed:

```
1. Start-OctoInfrastructure                               # Start Docker containers
2. Get-OctoInfrastructureStatus                           # Verify containers are healthy
3. Invoke-BuildAll -configuration DebugL                  # Build all repos
4. Start-Octo -nonInteractive $true -configuration DebugL # Start services (agent-safe)
```

Stop the services when done with `Stop-Octo`.

A human working interactively in a terminal can instead build + start in one step (this BLOCKS until a keypress, so never run it from an agent session):
```
1. Start-OctoInfrastructure
2. Invoke-BuildAndStartOcto -configuration DebugL         # Build + start (interactive only)
```

## 3. Pull Latest Changes

Sync all repos and rebuild:

```
1. Get-AllGitRepStatus                             # Check current state
2. Sync-AllGitRepos                                # Pull all repos (rebase)
3. Invoke-BuildAll -configuration DebugL           # Rebuild everything
```

If frontend dependencies changed:
```
4. Invoke-BuildAll -configuration DebugL           # Full rebuild includes frontend
```

## 4. Build a Single Repo

**IMPORTANT:** `Invoke-Build` is ONLY safe for isolated changes within a single service repo that do NOT affect NuGet packages. If changes touch a library repo or affect NuGet packages, use `Invoke-BuildAll` with exclusion flags instead.

**Safe — isolated service change (no NuGet impact):**
```
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

**Changes affect NuGet packages — use Invoke-BuildAll:**
```
# Build base libraries + services (no frontend) — handles NuGet propagation automatically
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

`-excludeFrontend $true` is the only sanctioned way to shorten the build. Do not add `-excludeAdditional $true` for speed — it skips the service repos, so they keep consuming the previous package version and break later at startup instead of at build time.

**NEVER manually chain `Invoke-Build` + `Copy-NuGetPackages` to propagate NuGet changes — use `Invoke-BuildAll` instead.**

## 5. Create and Work on a Test Branch

```
1. Get-AllGitRepStatus                             # Ensure clean state
2. New-TestBranch -MinorVersion "42" -Description "my-feature"  # Create across all repos
3. # ... do work ...
4. Sync-TestBranch -MinorVersion "42" -Description "my-feature"  # Merge latest from base
5. # ... when done ...
6. Remove-TestBranch -MinorVersion "42" -Description "my-feature"  # Clean up
```

## 6. Switch All Repos to a Branch

```
1. Get-AllGitRepStatus                             # Check for uncommitted changes
2. Invoke-SwitchAllBranches -Name "release/1.42"   # Switch all repos
3. Invoke-BuildAll -configuration DebugL           # Rebuild on new branch
```

## 7. Clean Build (Nuclear Option)

When builds are broken or stale:

```
1. Invoke-KillDotnet                               # Kill stale dotnet processes (Windows)
2. Remove-BinAndObjFolders                         # Delete all bin/ and obj/ folders
3. Remove-GlobalNuGetPackages                      # Clear NuGet cache
4. Invoke-BuildAll -configuration DebugL           # Full rebuild from scratch
```

## 8. Switch Environment (CLI Auth)

`Register-OctoCliContext` is the recommended unified path for all installations (uses the current `*.octo-mesh.com` cluster domains):

```
# Local
Register-OctoCliContext -Installation local -TenantId meshtest

# Test-2 (optionally a PR sub-env)
Register-OctoCliContext -Installation test-2 -TenantId voest -UriSuffix pr123

# Staging
Register-OctoCliContext -Installation staging-1 -TenantId meshtest

# Production (use with caution!)
Register-OctoCliContext -Installation prod-1 -TenantId meshmakers
```

The older per-environment cmdlets still work; `Invoke-OctoCliLoginStaging` / `Invoke-OctoCliLoginProduction` are **legacy** (old `*.meshmakers.cloud` domains):

```
Invoke-OctoCliLoginLocal              # -tenantId (default meshtest), -includeReporting
Invoke-OctoCliLoginTest2
```

Each login/register cmdlet creates a named context via `octo-cli -c AddContext`, activates it with `octo-cli -c UseContext`, and then authenticates with `octo-cli -c Login -i`. The context name follows the `{installation}_{tenantId}` convention (e.g., `local_meshtest`), so each environment+tenant keeps its tokens independently. Because they call `UseContext`, they mutate the global active context — for parallel-safe work, use `Register-OctoCliContext -NoSwitch` and then pass `--context <ctx>` (or `export OCTO_CLI_CONTEXT=<ctx>`) on each octo-cli command, so a concurrent session doesn't flip the context out from under you.

## 9. Push Changes

After committing in individual repos:

```
1. Get-AllGitRepStatus                             # Review what will be pushed
2. Push-AllGitRepos                                # Push all repos to remote
```

Or for a single repo:
```
Push-GitRepo -repositoryPath ./octo-asset-repo-services
```

## 10. Infrastructure Maintenance

```
1. Get-OctoInfrastructureStatus                    # Check current state
2. Stop-OctoInfrastructure                         # Stop containers
3. Start-OctoInfrastructure                        # Restart containers
```

For a fresh start:
```
1. Stop-OctoInfrastructure
2. Uninstall-OctoInfrastructure                    # Remove everything (destructive!)
3. Install-OctoInfrastructure                      # Reinstall
4. Start-OctoInfrastructure                        # Start fresh
```

To snapshot/restore the data volumes (safe rollback before risky changes — stop infra first):
```
1. Stop-OctoInfrastructure
2. Backup-OctoInfrastructure -Name before-upgrade  # -Name optional (defaults to a timestamp)
3. # ... do risky work, then if it goes wrong: ...
4. Restore-OctoInfrastructure -Name before-upgrade # Destructive — overwrites current volumes
5. Get-OctoInfrastructureBackup                    # List backups
```

## 13. Local Kubernetes (kind) dev environment

Alternative to docker-compose infra — the two **cannot run at the same time** (same host ports). Stop docker-compose infra first.

```
1. Stop-OctoInfrastructure                         # kind refuses to start while compose infra is up
2. Install-OctoKubernetes                          # Cluster + CRDs + in-cluster infra + ingress + operator
3. Get-OctoKubernetesStatus                        # Pods, Helm releases, host-port reachability
4. Invoke-BuildAll -configuration DebugL
5. Start-Octo -nonInteractive $true -configuration DebugL   # .NET services still run as host processes
```

Re-deploy just the operator after an operator change:
```
Deploy-OctoOperator                                # From the dev registry at :main-latest
```

Tear down (destroys all cluster data):
```
Uninstall-OctoKubernetes                           # Add -KeepCaTrust to keep the local CA trusted
```

Full runbook: `C:\dev\meshmakers\octo-tools\kubernetes\README.md`; from-scratch: `C:\dev\meshmakers\octo-tools\kubernetes\QUICKSTART.md`.

## 11. Build Without Frontend

To speed up backend-only development:

```
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

## 12. Release Preparation

```
1. Get-AllGitRepStatus                             # Ensure clean state
2. Sync-AllGitRepos                                # Pull latest
3. Invoke-BuildAll -configuration DebugL           # Full build
4. # Run tests in individual repos: dotnet test -c DebugL
5. Update-MeshmakerVersion                         # Bump version numbers
6. Sync-YamlTemplates                              # Sync CI/CD templates
```
