# Database Operations and Diagnostics

## Docker Volume Backup and Restore

PowerShell functions (loaded via `profile.ps1`) manage Docker volume snapshots for safe rollback during testing.

### Create a Backup

```powershell
Backup-OctoInfrastructure -Name "my-backup"
```

**Prerequisites:** Infrastructure must be **stopped** first.

```powershell
# Full workflow
Stop-Octo                            # Stop services if running
Stop-OctoInfrastructure              # Stop Docker containers
Backup-OctoInfrastructure -Name "my-backup"
Start-OctoInfrastructure             # Restart infrastructure
```

This backs up all 6 Docker volumes:
- `mongo-data0`, `mongo-data1`, `mongo-data2` (MongoDB replica set)
- `crate-data1`, `crate-data2`, `crate-data3` (CrateDB cluster)

Backups are stored in `octo-tools/infrastructure/backups/<name>/`. Omitting `-Name` generates a timestamp-based name.

### Restore a Backup

```powershell
Restore-OctoInfrastructure -Name "my-backup"
```

**Prerequisites:** Infrastructure must be **stopped** first.

```powershell
Stop-Octo                            # Stop services if running
Stop-OctoInfrastructure              # Stop Docker containers
Restore-OctoInfrastructure -Name "my-backup"
Start-OctoInfrastructure             # Restart infrastructure
```

### List Backups

```powershell
Get-OctoInfrastructureBackup
```

Shows all available backups with volume count and total size.

### Delete a Backup

```powershell
# Prompts for confirmation
Remove-OctoInfrastructureBackup -Name "my-backup"

# Skip confirmation
Remove-OctoInfrastructureBackup -Name "my-backup" -Force
```

## MongoDB Direct Queries

For diagnostics, query MongoDB directly using the MongoDB MCP server (must be configured and connected). The connection string for the local replica set is (replica set name is **`rs`**, not `rs0`):
```
mongodb://localhost:27017,localhost:27018,localhost:27019/?replicaSet=rs
```

For a remote environment, use `Invoke-MongoPortForward` to port-forward MongoDB to localhost before connecting.

### Key Databases

| Database | Purpose |
|----------|---------|
| `octosystem` | System tenant — identity, notification, bot CK models |
| `meshtest` | Default test tenant — all CK models deployed here |
| `maco` | Additional tenant (if configured) |

### Diagnostic Queries

#### Check CK Model Health
Query `CkModel` collection to see all models and their states:
```javascript
db.CkModel.find({}, { modelId: 1, modelState: 1, dependencies: 1 })
```

- `modelState: 1` = Available (healthy)
- `modelState: 2` = ResolveFailed (broken dependency)

#### Find Broken Models
```javascript
db.CkModel.find({ modelState: 2 })
```

#### Check Specific Model Dependencies
```javascript
db.CkModel.find({ _id: "Basic-2.0.1" })
```

#### Count Runtime Entities Per Type
```javascript
db.RtEntity.aggregate([
  { $group: { _id: "$ckTypeId", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

#### Find Runtime Entities by Type
```javascript
db.RtEntity.find({ ckTypeId: /Machine/ }).limit(5)
```

#### Check Schema Versions
```javascript
db.CkModel.find({}, { _id: 1, modelState: 1 }).sort({ _id: 1 })
```

## Multi-Tenant Data Isolation

Each tenant gets its own MongoDB database. The database name matches the tenant ID:
- Tenant `meshtest` -> database `meshtest`
- Tenant `maco` -> database `maco`

The system tenant (`octosystem`) stores:
- System CK models (System, System.Identity, System.Bot, etc.)
- Identity data (users, roles, clients)

### OIDC Persistent Grants (Token-Refresh Debugging)

OIDC persistent grants — authorization codes, refresh tokens, and consent — are stored as **`RtPersistedGrant`** runtime entities (CK type `System.Identity/PersistedGrant`) in the **tenant database the OIDC client authenticated against**, resolved per request by `OidcTenantResolutionMiddleware`. They are not centralized in one collection.

When debugging token-refresh failures after a service restart: the middleware re-resolves the tenant for a refresh by SHA256-hashing the incoming token and querying the persistent grant store (the tenant id is also stamped in each grant's `Description` field), then re-populates its in-memory cache. So look in the grant rows of the **tenant that issued the token**. A `TokenCleanupHostService` periodically prunes expired grants. If a backend OIDC client unexpectedly lands on `/tenant-discovery`, the deployment may predate the PAR (RFC 9126) tenant-resolution fix.

Regular tenants store:
- All CK models (System models + domain models like Basic, Industry.*)
- Runtime entities (instances of CK types)
- Queries, associations, file references

### Tenant Operations via octo-cli

```bash
# Create a new tenant
octo-cli -c Create -tid mytenant -db mytenant

# Clean a tenant (reset to factory defaults — destructive!)
octo-cli -c Clean -tid mytenant

# Update system CK model in a tenant
octo-cli -c UpdateSystemCkModel -tid mytenant

# Clear tenant cache (forces reload from DB)
octo-cli -c ClearCache -tid mytenant

# Dump tenant to a tar.gz archive (backup) — the -f file is a *.tar.gz, NOT .json
octo-cli -c Dump -tid mytenant -f ./mytenant-dump.tar.gz

# Restore tenant from a tar.gz dump (-db = target database name)
octo-cli -c Restore -tid mytenant -db mytenant -f ./mytenant-dump.tar.gz
```

`Dump` / `Restore` operate on `*.tar.gz` archives (per `octo-cli` help: `--file (-f) Required. File of backup (*.tar.gz)`). `Restore` also takes optional `-oldDb` if the dump's database name differs from the new one.

## Service Log Locations

Service logs are written to `logFiles/` in the workspace root:

| File | Service |
|------|---------|
| `logFiles/AssetRepositoryServices.log` | Asset Repo (5001/5000) |
| `logFiles/IdentityServices.log` | Identity (5003/5002) |
| `logFiles/BotServices.log` | Bot (5009/5008) |
| `logFiles/CommunicationControllerServices.log` | Comm Controller (5015/5014) |
| `logFiles/ReportingServices.log` | Reporting (5007/5006) |
| `logFiles/MeshAdapter.log` | Mesh Adapter (5020/5021) |
| `logFiles/McpServices.log` | MCP Service (5017/5016) |
| `logFiles/AiServices.log` | AI Services (5019/5018) |
| `logFiles/AiWorker.log` | AI Worker (5023/5022) |

Log format: `timestamp|LEVEL|LoggerName.Method|message`

### Useful Log Searches

```bash
# Find CK model import activity
grep -i "CkModel\|ImportCk\|modelState" logFiles/AssetRepositoryServices.log

# Find errors only
grep "|ERROR|" logFiles/AssetRepositoryServices.log

# Find warnings
grep "|WARN|" logFiles/AssetRepositoryServices.log

# Find MongoDB operations
grep "MongoRepositoryClient" logFiles/AssetRepositoryServices.log | grep -v DEBUG
```

## Service Health Endpoints

| Service | Health URL |
|---------|-----------|
| Identity | `https://localhost:5003/.well-known/openid-configuration` |
| Asset Repo | `https://localhost:5001/health` |
| Bot | `https://localhost:5009/health` |
| Comm Controller | `https://localhost:5015/health` |
| Reporting | `https://localhost:5007/health` |
| Mesh Adapter | `https://localhost:5020/health` |

Check with: `curl -sk -o /dev/null -w "%{http_code}" <url>`
