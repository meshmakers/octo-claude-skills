# Common OctoMesh Development Workflows

Multi-step workflows for typical development scenarios.

> **Agent note:** Whenever Claude or a CI job starts services, ALWAYS use `Start-Octo -nonInteractive $true` and stop them with `Stop-Octo` from a separate invocation. Never use `Invoke-BuildAndStartOcto` from an agent session — it chains into the interactive `Start-Octo` and blocks indefinitely. The interactive `Start-Octo` (no `-nonInteractive`) is only for a human running it directly in a terminal.

> **Which lane:** `-branch` is a lane folder relative to `$rootPath`. With the profile loaded from the `octo-tools` checkout at the workspace root (`$rootPath` = the workspace root - the setup feature environments need), pass `-branch branches/main` to build main; without `-branch` the cmdlets build `$rootPath` itself. With a profile loaded from inside the main checkout (`$rootPath` = `branches/main`) omit `-branch` and use `-path $rootPath` for `Remove-BinAndObjFolders` - `branches/main` would point at a nested folder there. The same applies to `Sync-AllGitRepos -branch` and `Invoke-BuildRange -branch`. The `Invoke-BuildAll` / `Sync-AllGitRepos` examples below omit it.

## 1. First-Time Setup

For a brand new development environment:

```
1. Invoke-CloneMainRepos                                  # Clone all repos (incl. octo-helm-core)
2. Install-OctoKubernetes                                 # kind cluster with MongoDB, RabbitMQ, CrateDB, CRDs, operator
3. Get-OctoKubernetesStatus                               # Pods, Helm releases, host-port reachability
4. Invoke-BuildAll -configuration DebugL                  # Full build once after a fresh clone
5. Start-Octo -nonInteractive $true -configuration DebugL # Start all services (agent-safe)
```

The docker-compose infrastructure (`Install-OctoInfrastructure`, `Start-OctoInfrastructure`) is deprecated in octo-tools; use it only on a machine that still runs it (section 10).

After services are running, authenticate the CLI (in a separate invocation — step 5 is blocking):
```
6. Register-OctoCliContext -Installation local -TenantId meshtest
```

When finished, stop the services:
```
7. Stop-Octo                                              # Writes the .octo-stop signal file
```

## 2. Daily Development Start

When the kind cluster is already installed:

```
1. Get-OctoKubernetesStatus                               # Verify the in-cluster infrastructure is up
2. Invoke-BuildRange -from <repo> -to <repo> -WhatIf      # Rebuild what changed, then without -WhatIf
3. Start-Octo -nonInteractive $true -configuration DebugL # Start services (agent-safe)
```

After a pull or branch switch use `Invoke-BuildAll -configuration DebugL -excludeFrontend $true` in step 2 instead (section 3).

Stop the services when done with `Stop-Octo`.

A human working interactively in a terminal can instead build + start in one step (this BLOCKS until a keypress, so never run it from an agent session):
```
1. Start-OctoInfrastructure
2. Invoke-BuildAndStartOcto -configuration DebugL         # Build + start (interactive only)
```

## 2a. Inner loop after a change in the build chain

```
1. Invoke-BuildRange -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -WhatIf   # the plan
2. Invoke-BuildRange -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -stopServices
3. Start-Octo -nonInteractive $true -configuration DebugL                                                                    # verify
4. Invoke-BuildRange -from octo-construction-kit-engine -to octo-common-services -include octo-asset-repo-services -verifyTests # tests compile
5. Invoke-OctoTestRun -branch branches/main -repo octo-construction-kit-engine                                              # run the tests
```

Restores fail with NU1101/NU1102 on a `999.0.0` package: the chain is out of sync — `Invoke-BuildAll -configuration DebugL -excludeFrontend $true`. `-purgeStaleCache` removes cache folders that hold another build of a `999.0.0` package.

## 3. Pull Latest Changes

Sync all repos and rebuild:

```
1. Get-AllGitRepStatus                             # Check current state
2. Sync-AllGitRepos                                # Pull all repos (rebase)
3. Invoke-BuildAll -configuration DebugL -excludeFrontend $true   # Full reset build (backend)
```

If frontend dependencies changed:
```
4. Invoke-BuildAll -configuration DebugL           # Full rebuild includes frontend
```

## 4. Build a Single Repo

**IMPORTANT:** `Invoke-Build` is ONLY safe for isolated changes within a single service repo that do NOT affect NuGet packages. If changes touch a library repo or affect NuGet packages, use `Invoke-BuildRange` over the repo and its consumers (section 2a).

**Safe — isolated service change (no NuGet impact):**
```
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

**Feature work on a work item — use a feature environment instead of building in `branches/main`:**
```
New-OctoEnvironment -env ab1234-my-change -repos octo-construction-kit-engine -workItem AB#1234
Get-OctoAffectedRepos -env ab1234-my-change                     # repos the change reaches
Add-OctoEnvironmentRepo -env ab1234-my-change -repo octo-asset-repo-services -role consumer -addAffected
Invoke-BuildEnvironment -env ab1234-my-change -verifyTests      # incremental, own feed and cache (Windows: stops the env's dotnet processes first, -skipKill opts out)
# after the PR is merged: stop the environment's services first (a lane made with octo-devstack is removed with lane_remove)
Remove-OctoEnvironment -env ab1234-my-change
```
Never publish feature work into the base lane's `nuget/`. The base lane is detected (`branches/main`, or `$rootPath` itself in the flat layout; `-base` / `$env:OCTO_ENVIRONMENT_BASE` override). An existing worktree is adopted with `Add-OctoEnvironmentRepo -env <env> -path <worktree>` (`-inPlace`: not isolated for plain `dotnet build`/Rider, never deleted by `Remove-OctoEnvironment`); a hand-made environment without manifest is adopted into an empty one: `New-OctoEnvironment -env <new name> -workItem AB#..` (no `-repos`), then `Add-OctoEnvironmentRepo -env <new name> -path <worktree> -inPlace`. Adopt a worktree only when no other session works in it: the next `Invoke-BuildEnvironment` clears the environment's kill scope, which includes every in-place worktree, and on Windows stops a dotnet process another session runs there.

**Changes affect NuGet packages in main — use Invoke-BuildRange (section 2a), or the full reset:**
```
# Full reset of libraries + services (no frontend) — handles NuGet propagation automatically
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

Do not add `-excludeAdditional $true` for speed — it skips the service repos, so they keep consuming the previous package version and break later at startup instead of at build time. A narrower build is `Invoke-BuildRange`.

**NEVER manually chain `Invoke-Build` + `Copy-NuGetPackages` to propagate NuGet changes — use `Invoke-BuildRange` or `Invoke-BuildAll` instead.**

## 5. Pre-release 0.x line (test branch)

A pre-release line holds work that is not ready for `main` (e.g. `0.2-dev`, `0.3-demo`). Rules:

- **Branch name** `test/0.<n>-<word>`: `-MinorVersion <n>` (integer 2-999, the major version is always 0) and `-Description <word>` (letters, digits and `_` only; no spaces, no hyphens). `0.2-dev` is `-MinorVersion 2 -Description dev`.
- **Checkout directory**: each line has its own folder next to the main checkout. Without `-branch` the cmdlets use `<parent of rootPath>/0.<n>-<description>` (`$rootPath` is the folder that holds the `octo-tools` checkout the profile was loaded from): with `$rootPath` = `meshmakers/main`, `-MinorVersion 3 -Description demo` is `meshmakers/0.3-demo`; `Invoke-CloneMainRepos -branch ../0.3-demo` creates it. An explicit `-branch` is a folder joined to `$rootPath` and overrides the rule, so existing lines keep their directories (e.g. `-branch ../dev`, `-branch ../demo`).
- **Branched from fresh main**: `New-TestBranch` runs `git fetch origin` in every repository and branches explicitly from `origin/main`, whatever the repository has checked out. A repository with uncommitted changes to tracked files is not branched: it is listed with its reason (console and `-Json`, `status: Dirty`) and the exit code is non-zero; commit or stash there and run the cmdlet again. A branch that already exists is switched to.
- **Scope**: `New-TestBranch`, `Sync-TestBranch` and `Remove-TestBranch` cover exactly the repositories of `Invoke-CloneMainRepos` (one shared list, `mm-common` and the other non-`octo-*` repositories included); a repository the line folder does not hold is skipped. Other repositories (e.g. app repositories) are branched by hand or with `Invoke-SwitchAllBranches -Name test/0.<n>-<word> -branch <line dir>`.

```
1. Invoke-CloneMainRepos -branch ../0.3-demo                               # the line folder, <parent of rootPath>/0.3-demo
2. Get-AllGitRepStatus -branch ../0.3-demo                                 # clean state (a dirty repo is not branched)
3. New-TestBranch -MinorVersion 3 -Description demo                        # test/0.3-demo from origin/main in every repo of the clone list, pushed (-NoPush: local only)
4. # ... work on the line ...
5. Sync-TestBranch -MinorVersion 3 -Description demo                       # merge origin/main into the line; conflicts are listed, not resolved
6. Compare-BranchStatus -branch ../0.3-demo                                # what the line holds compared with main
7. Remove-TestBranch -MinorVersion 3 -Description demo                     # when the line is merged or abandoned; -LocalOnly keeps origin
```

For an existing line in another folder add `-branch <line dir>` to every call (e.g. `-branch ../dev`).

Is a line active? Ask origin: `git ls-remote --heads origin test/0.<n>-<word>` in a repository (empty output = the line does not exist there). `Get-BranchAvailability -targetBranch test/0.<n>-<word> [-Fetch]` is only a rough overview: it scans the `octo-*`/`mm-*` repositories of `$rootPath` only, reads the local remote-tracking refs (without `-Fetch` they can be old) and does not prune, so a removed line can still show up. Never assume a line's state from memory or from older notes: lines are created, merged into `main` and removed.

## 6. Switch All Repos to a Branch

```
1. Get-AllGitRepStatus                             # Check for uncommitted changes
2. Invoke-SwitchAllBranches -Name "release/1.42"   # Switch all repos
3. Invoke-BuildAll -configuration DebugL           # Rebuild on new branch
```

## 7. Clean Build (Nuclear Option)

When builds are broken or stale and `Invoke-BuildAll` alone does not help — this is the last resort:

```
1. Invoke-KillDotnet -branchRootPath (Join-Path $rootPath 'branches/main')   # this lane's dotnet processes only (Windows stops them; main-checkout profile: $rootPath)
2. Remove-BinAndObjFolders -path (Join-Path $rootPath 'branches/main')   # bin/ and obj/ of this lane only (default: current folder; main-checkout profile: -path $rootPath)
3. Remove-GlobalNuGetPackages -path <lane>/.nuget-packages   # Clear the lane's 999.0.0 packages (default path: ~/.nuget/packages for a lane without RestorePackagesPath)
4. Invoke-BuildAll -configuration DebugL           # Full rebuild from scratch
```

## 8. Switch Environment (CLI Auth)

`Register-OctoCliContext` is the login path for every installation; the installation names and their service URL templates come from your octo-tools config (`installations.json`):

```
# Local
Register-OctoCliContext -Installation local -TenantId meshtest

# A test installation (optionally a PR sub-environment)
Register-OctoCliContext -Installation test-2 -TenantId <tenant> -UriSuffix pr123

# Production (use with caution!)
Register-OctoCliContext -Installation <production installation> -TenantId <tenant>

# Many tenants at once: one context each, the active context is not switched
Register-OctoCliContext -Installation test-2 -TenantId tenant-a,tenant-b -NoSwitch
```

The former per-environment login helpers were removed from octo-tools; `Register-OctoCliContext` replaces them.

`Register-OctoCliContext` creates a named context via `octo-cli -c AddContext`, activates it with `octo-cli -c UseContext`, and then authenticates with `octo-cli -c Login -i`. The context name follows the `{installation}[_{uriSuffix}]_{tenantId}` convention (e.g., `local_meshtest`), so each environment+tenant keeps its tokens independently. Because they call `UseContext`, they mutate the global active context — for parallel-safe work, use `Register-OctoCliContext -NoSwitch` and then pass `--context <ctx>` (or `export OCTO_CLI_CONTEXT=<ctx>`) on each octo-cli command, so a concurrent session doesn't flip the context out from under you.

## 9. Push Changes

Work reaches `main` through pull requests from work branches. With the `octo-claude-pm` plugin installed its `agent-operating-rules` decide when and how work is pushed; otherwise follow the repository's own contribution rules. `Push-AllGitRepos` (every `octo-*`/`mm-*` repo of the lane) and `Push-GitRepo -repositoryPath <repo>` push whatever is checked out — review with `Get-AllGitRepStatus` first and use them only when that is really what you want.

## 10. Infrastructure Maintenance (docker-compose, deprecated)

Only for a machine that still runs the deprecated docker-compose infrastructure; the kind cluster is section 13.

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

The supported local infrastructure. It and the deprecated docker-compose infra **cannot run at the same time** (same host ports): stop docker-compose infra first.

```
1. Stop-OctoInfrastructure                         # only if compose infra runs; kind refuses to start while it is up
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

A full reset without the Angular frontends (`Invoke-BuildRange` skips them by default):

```
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

## 12. Release Preparation

```
1. Get-AllGitRepStatus                             # Ensure clean state
2. Sync-AllGitRepos                                # Pull latest
3. Invoke-BuildAll -configuration DebugL           # Full build
4. Invoke-OctoTestRun -branch branches/main -repo <repo>   # per repository
5. Update-MeshmakerVersion                         # Bump version numbers
6. Sync-YamlTemplates                              # Sync CI/CD templates
```
