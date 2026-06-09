# Debugging Workflows

## Safe Bug Investigation Protocol

When investigating a bug that might corrupt data or break the development environment, follow this protocol:

### 1. Create a Safety Net

Before any destructive or risky operation, back up Docker volumes:

```powershell
# Stop everything
Stop-Octo
Stop-OctoInfrastructure

# Create named backup
Backup-OctoInfrastructure -Name "before-investigation"

# Restart
Start-OctoInfrastructure
```

### 2. Record Baseline State

Query the relevant database to capture the "before" state:
- CK models: `db.CkModel.find()` in the tenant database
- Runtime entities: `db.RtEntity.find({ ckTypeId: /RelevantType/ }).limit(10)`
- Save baseline to a temp file for later comparison

### 3. Make the Change

Apply the minimal change needed to reproduce or test the fix.

### 4. Observe and Verify

- Check service health endpoints
- Query database for changes
- Review service logs for errors
- Compare against baseline

### 5. Restore if Needed

If the investigation caused damage:
```powershell
Stop-Octo
Stop-OctoInfrastructure
Restore-OctoInfrastructure -Name "before-investigation"
Start-OctoInfrastructure
```

## Isolating a Bug in a Specific Repo

### Step 1: Identify the Repo

Determine which repo contains the bug based on:
- Service that exhibits the behavior (map to repo from architecture)
- Stack trace or error message (class/namespace -> NuGet package -> repo)
- Feature area (CK engine, SDK, MongoDB layer, service infrastructure)

### Step 2: Build Only What's Needed

Use selective builds to minimize rebuild time:

**Bug in a service repo (leaf node):**
```powershell
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

**Bug in a library repo (needs downstream rebuild):**
```powershell
# Build the library
Invoke-Build -repositoryPath ./octo-construction-kit-engine -configuration DebugL
Copy-NuGetPackages -directory ./octo-construction-kit-engine

# Rebuild only the service(s) needed for testing
Invoke-Build -repositoryPath ./octo-asset-repo-services -configuration DebugL
```

### Step 3: Start Minimal Services

Only start the services needed to reproduce the bug:
```powershell
Start-Octo -identityAssetRepoOnly $true    # Most common for data bugs
Start-Octo -identityOnly $true             # For auth bugs
```

### Step 4: Run Targeted Tests

```bash
# Run specific test class
dotnet test -c DebugL --filter "FullyQualifiedName~MyBugTest"

# Run integration tests (needs running MongoDB via Testcontainers)
dotnet test -c DebugL --filter "FullyQualifiedName~IntegrationTests"

# Exclude system tests (which need running services)
dotnet test -c DebugL --filter "FullyQualifiedName!~SystemTests"
```

## Common Bug Categories

### CK Model Resolution Failures

**Symptom:** Models show `modelState: 2` in MongoDB.

**Diagnosis:**
1. Query `CkModel` collection for failed models
2. Check their `dependencies` array — look for references to model IDs that don't exist
3. Check if a base model was upgraded without recompiling dependents
4. `octo-cli -c LibraryStatus -na` — lists models needing action with catalog availability (read-only)
5. `Compare-CkVersions <otherBranch> [-Details]` — after a merge/branch switch, diffs every `ckModel.yaml` under `$Global:ROOTPATH`; `$LASTEXITCODE` = count of non-equal models
6. If a fatal **error code 66** appeared at compile time, it is a multi-version conflict — see ck-model-internals.md (rebuild dependents against one version or use the `OctoPublic/PrivateGitHubCatalogIsEnabled` MSBuild toggles)
7. **Stuck at old version after an additive bump?** On a service running a pre-2026-06-02 image, `EnsureCkModelInstalledAsync` compared by name only and silently skipped the upgrade (see ck-model-internals.md)

**Fix approaches:**
- Re-import the missing model version, or `octo-cli -c FixAll -w` to import everything needing a fix (mutating)
- Update and rebuild all dependent CK models
- Run `UpdateSystemCkModel` on affected tenants

### Service Startup Failures

**Symptom:** Service process exits or health endpoint returns non-200.

**Diagnosis:**
1. Check service log file in `logFiles/`
2. Look for `|ERROR|` entries
3. Common causes: MongoDB connection refused, missing CK models, port conflicts

**Fix approaches:**
- Verify infrastructure is running: `Get-OctoInfrastructureStatus`
- Check ports aren't in use: `lsof -i :5001`
- Clean and rebuild: `Invoke-Build -repositoryPath ./<repo> -configuration DebugL`
- Turn up logging at runtime without a rebuild: `octo-cli -c ReconfigureLogLevel -n "AssetRepository" -ln "Meshmakers.*" -minL "Debug" -maxL "Error"` (per-logger reconfigure now works on asset-repo; `maxLogLevel`/`loggerName` were silently dropped before)

### NuGet Package Resolution Failures

**Symptom:** `dotnet build` fails with "unable to find package" or version mismatch errors.

**Diagnosis:**
1. Check `./nuget/` folder for expected packages
2. Check `~/.nuget/packages/` global cache for stale versions
3. Verify upstream repos were built and packages copied

**Fix approaches:**
```powershell
# Clear stale cache
Remove-GlobalNuGetPackages

# Rebuild from the root of the dependency chain
Invoke-BuildAll -configuration DebugL -excludeFrontend $true
```

### Data Corruption in a Tenant

**Symptom:** Unexpected runtime entity states, missing associations, orphaned references.

**Diagnosis:**
1. Query the tenant database directly
2. Compare CK model states across the system tenant and the affected tenant
3. Check for incomplete migrations

**Fix approaches:**
- Clear tenant cache: `octo-cli -c ClearCache -tid <tenant>`
- Re-import CK models: `octo-cli -c ImportCk -f <model.yaml>`
- Nuclear option: clean tenant and re-import: `octo-cli -c Clean -tid <tenant>`

### Blueprint Apply / Update Failures

**Symptom:** A blueprint install, update, or rollback errors out, or seed data is missing.

**Diagnosis:**
1. Query the tenant DB for `System/BlueprintInstallation` rows (name, version, `SeedDataChecksum`, `IsDependency`) and `System/BlueprintHistory`
2. Check the platform event log for `BlueprintOperationFailed` events (emitted over the DistributionEventHub)
3. Blueprint apply auto-installs missing CK model dependencies (`EnsureCkModelInstalledAsync`); a stuck dependency model surfaces here too
4. Backups created before an update are `System/BlueprintBackup` rows (rollback source)

### Token Refresh Fails After Restart

**Symptom:** Users must re-authenticate after a service restart, or `/connect/token` refresh fails.

**Diagnosis:**
1. OIDC grants are `RtPersistedGrant` entities in the **tenant DB the client authenticated against** (not centralized) — query the issuing tenant (see database-operations.md)
2. After restart the in-memory token→tenant cache is cold; the middleware re-resolves via SHA256 hash lookup against the grant store
3. Backend OIDC client landing on `/tenant-discovery` unexpectedly → deployment may predate the PAR (RFC 9126) tenant-resolution fix

### AD Group Roles Not Applied

**Symptom:** A Microsoft AD user authenticates but does not get the roles their AD group should grant.

**Diagnosis:** Group sync runs on **every** login (`SyncExternalGroupClaimsAsync`), matching AD group CNs (extracted from the `memberOf` DN via `^CN=([^,]*)`) against OctoMesh groups by normalized name. For roles to flow:
- An OctoMesh **Group** must exist in the tenant with the **same name** as the AD group
- That group must have **`AssignedRole`** associations to the desired roles
- The user must be a member of the AD group (`memberOf`)

### Hangfire Cron Not Firing Below 15s

**Symptom:** A simulator/bot pipeline trigger seems floored at ~15s even though its cron is faster (e.g., `*/1 * * * * ?`).

**Diagnosis:** Bot-services now defaults `Hangfire:SchedulePollingIntervalSeconds` to **1s** (was 15s, which silently floor-snapped sub-15s crons). A service still flooring at 15s is running a pre-fix image. Tune polling load via that config key.

### mongorestore EOF on Backup Restore

**Symptom:** A tenant backup restore fails with a cryptic `EOF` error.

**Diagnosis:** The TUS upload of the backup archive produced a **0-byte file** (transfer failed; `File.Exists` passes for empty files). Bot-services now validates the file is non-empty up front ("Upload file ... is empty (0 bytes)"). **Fix:** re-upload the archive.

### Slow Service Cold Start

**Symptom:** A multi-tenant service takes a long time to become healthy.

**Diagnosis:** Deferred tenant startup is now parallelized (`Parallel.ForEachAsync`, bounded to `min(ProcessorCount, 8)`) — baseline was ~44s for 13 tenants. Per-tenant log lines interleave; per-tenant failures are isolated. `RetryFailedTenantsAsync` deliberately stays sequential to avoid bursting MongoDB. A service still serializing tenant startup predates this change.

## Test Framework Reference

| Repo | Framework | Mocking | Test DB |
|------|-----------|---------|---------|
| Most repos | xUnit v3 | FakeItEasy | Testcontainers.MongoDb |
| `octo-communication-controller-services` (unit) | TUnit | NSubstitute | N/A |
| `octo-communication-controller-services` (integration) | xUnit v3 | NSubstitute | Testcontainers.MongoDb |
| Most integration tests | xUnit v3 | FakeItEasy | Testcontainers.MongoDb |

### Test Patterns

**Fixture hierarchy** (octo-construction-kit-engine-mongodb):
```
ServiceCollectionFixture -> ConfigurationFixture -> DatabaseFixture -> SystemFixture
```

- All integration tests use `[Collection("Sequential")]`
- `IClassFixture<T>` for fixture injection via primary constructor
- `SystemFixture` creates/reinitializes the system tenant
- Testcontainers.MongoDb spins up an ephemeral MongoDB for tests

### Running Tests in Specific Repos

```bash
# From the workspace root, target a specific repo
dotnet test ./octo-construction-kit-engine-mongodb -c DebugL

# Filter by namespace
dotnet test -c DebugL --filter "Namespace~IntegrationTests"

# Filter by test name
dotnet test -c DebugL --filter "DisplayName~ShouldResolveModel"
```
