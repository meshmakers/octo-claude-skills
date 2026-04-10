# Common OctoMesh Development Workflows

Multi-step workflows for typical development scenarios.

## 1. First-Time Setup

For a brand new development environment:

```
1. Invoke-CloneMainRepos                           # Clone all repos
2. Install-OctoInfrastructure                      # Set up Docker containers
3. Start-OctoInfrastructure                        # Start MongoDB, RabbitMQ, CrateDB
4. Invoke-BuildAll -configuration DebugL           # Build everything
5. Start-Octo                                      # Start all services (interactive)
```

After services are running, authenticate the CLI:
```
6. Invoke-OctoCliLoginLocal                        # Configure + log in to local env
```

## 2. Daily Development Start

When infrastructure is already installed:

```
1. Start-OctoInfrastructure                        # Start Docker containers
2. Get-OctoInfrastructureStatus                    # Verify containers are healthy
3. Invoke-BuildAll -configuration DebugL           # Build all repos
4. Start-Octo                                      # Start services (interactive)
```

Or build + start in one step:
```
1. Start-OctoInfrastructure
2. Invoke-BuildAndStartOcto -configuration DebugL  # Build + start (interactive)
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

**Changes affect NuGet packages — use Invoke-BuildAll with scope flags:**
```
# Build base libraries + services (no frontend) — handles NuGet propagation automatically
Invoke-BuildAll -configuration DebugL -excludeFrontend $true

# Build only core libraries (no services, no frontend)
Invoke-BuildAll -configuration DebugL -excludeFrontend $true -excludeAdditional $true
```

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

```
# Local
Invoke-OctoCliLoginLocal

# Test-2
Invoke-OctoCliLoginTest2

# Staging
Invoke-OctoCliLoginStaging

# Production (use with caution!)
Invoke-OctoCliLoginProduction
```

Each login cmdlet creates/updates a named context via `octo-cli -c AddContext`, activates it with `octo-cli -c UseContext`, and then authenticates with `octo-cli -c LogIn -i`. The context name follows the `{environment}_{tenantId}` convention (e.g., `local_meshtest`).

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
