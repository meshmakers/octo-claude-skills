# Construction Kit Model Internals

## CK Model YAML Structure

Each CK model lives in a `ConstructionKit/` directory within a project:

```
src/MyCkModel/
  ConstructionKit/
    ckModel.yaml              # Model identity and dependencies
    types/                    # Entity type definitions
    records/                  # Record (value object) definitions
    attributes/               # Attribute definitions
    enums/                    # Enumeration definitions
    associations/             # Relationship definitions
    migrations/               # Version migration scripts
      migration-meta.yaml
      2.0.4-to-2.0.5.yaml
```

### ckModel.yaml

```yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-meta.schema.json
modelId: "ModelName-Major.Minor.Patch"
description: "Human-readable description"
dependencies:
  - DependencyModel-[MinVersion,MaxVersion)
```

The `modelId` is the canonical identifier: `{Name}-{SemVer}`.

### Dependency Ranges

Dependencies use NuGet-style version ranges:
- `System-[2.0,3.0)` — any System version >= 2.0.0 and < 3.0.0
- `Basic-[2.0.1,)` — any Basic version >= 2.0.1

At import time, the runtime resolves ranges to **exact pinned versions** stored in the `CkModel` MongoDB collection. For example, `System-[2.0,3.0)` resolves to `System-2.2.0` if that's the installed version. (Current core versions: `System-2.2.0`, `System.StreamData-1.4.0`, `System.Identity-2.6.0`, `System.Bot` via V3, `System.Communication` via V3.)

## CK Model Versioning

### Source-Level vs Runtime-Level

| Concept | Source (YAML) | Runtime (MongoDB) |
|---------|--------------|-------------------|
| Model ID | `System-2.2.0` | `_id: "System-2.2.0"` |
| Dependencies | Range: `System-[2.0,3.0)` | Pinned: `["System-2.2.0"]` |
| State | N/A | `modelState: 1` (Available), `2` (ResolveFailed) |

### Version Bump Impact

**Critical knowledge from testing:** Bumping a base model version (e.g., System 2.1.0 -> 2.2.0) without recompiling all dependent CK models causes cascading `ResolveFailed` states:

1. The old model document (e.g., `System-2.1.0`) gets **deleted** from MongoDB
2. The new version (e.g., `System-2.2.0`) gets inserted
3. Models compiled into the same binary get auto-updated (e.g., `System.Notification`)
4. Models from other repos still reference the old pinned version -> `ResolveFailed`
5. This cascades: if `Basic` fails, all of `Basic`'s dependents also fail

**Rule:** When bumping a base CK model version, ALL dependent CK models across ALL repos must be recompiled and redeployed.

**Error code 66 (multi-version conflict):** When transitive resolution finds two incompatible versions of the *same* model (e.g., different catalogs pin different versions), the compiler raises a fatal **error 66** listing the conflicting versions and their origins (instead of a cryptic dictionary-key collision). Resolutions: rebuild the conflicting dependents against one common version, narrow the dependency range in the consumer's `ckModel.yaml`, or disable stale catalogs via the MSBuild toggles **`OctoPublicGitHubCatalogIsEnabled`** / **`OctoPrivateGitHubCatalogIsEnabled`** (set on the `CkCompile`/`CkRestore` tasks).

### Models Compiled Per Binary

This table maps each model to the binary/repo that **registers and loads** it at runtime (where its `AddCkModel…V…()` call lives) — the place to look when a model is missing or stuck:

| Binary/Repo | CK Models Registered (`AddCkModel…`) |
|-------------|-------------------|
| `octo-construction-kit-engine` (via `octo-construction-kit-engine-mongodb`) | `System` (`AddCkModelSystemV2`) |
| `octo-construction-kit-engine-mongodb` | `System.StreamData` (`AddCkModelSystemStreamDataV1`, loaded only when StreamData is enabled) |
| `octo-common-services` | `System.Notification` (`AddCkModelSystemNotificationV2`) |
| `octo-identity-services` | `System.Identity` (`AddCkModelSystemIdentityV2`) |
| `octo-bot-services` | `System.Bot` (`AddCkModelSystemBotV3`) |
| `octo-communication-controller-services` | `System.Communication` (`AddCkModelSystemCommunicationV3`) |
| `octo-report-services` | `System.Reporting` (`AddCkModelSystemReportingV2`) |
| `octo-frontend-admin-panel` | `System.UI` (`AddCkModelSystemUIV2`) |
| `octo-construction-kit` | `Basic`, `Industry.Basic`, `Industry.Energy`, `Industry.Fluid`, `Industry.Maintenance`, `Environment`, `EnergyCommunity`, `OctoSdkDemo` |

(`octo-asset-repo-services` registers **no** CK model directly — it consumes them and sets the StreamData descriptor.) The `System` and `System.StreamData` CK YAML/source-gen both live as separate projects in `octo-construction-kit-engine` (`Models.System` / `Models.StreamData`), but `System.StreamData` is only wired into the runtime by the engine-mongodb layer.

To discover which CK models a binary registers, search for `AddCkModel` calls in its `Program.cs` or startup code.

## Source Generation

Two source generation systems produce C# from CK model YAML:

### CK Engine Source Generation (`Meshmakers.Octo.ConstructionKit.SourceGeneration`)
- Input: `ConstructionKit/` YAML files
- Output: C# entity classes + DI registration method
- Generated method: `AddCkModel{Name}V{Major}()` (e.g., `AddCkModelSystemV2()`)
- Name transformation: `s.Trim().Replace(".", "")` on model name

### SDK Source Generation (`Meshmakers.Octo.Sdk.SourceGeneration`)
- Input: Compiled CK model assemblies
- Output: GraphQL query/mutation DTOs

### DI Registration Order (Critical)

CK models **must** be registered before `AddMongoDbRuntimeRepository()`:

```csharp
services.AddCkModelSystemV2();         // Base model first
services.AddCkModelSystemBotV3();      // Dependents after (Bot model is V3)
services.AddRuntimeEngine()
    .AddMongoDbRuntimeRepository();    // MongoDB last — needs BSON class maps
```

The generated method name uses the **major** version (`V{Major}`): `AddCkModelSystemBotV3()` for `System.Bot` major 3, `AddCkModelSystemCommunicationV3()` for `System.Communication` major 3.

## CK Model Migrations

### Migration Meta File

`ConstructionKit/migrations/migration-meta.yaml`:
```yaml
$schema: ck-migration-meta.schema.json
migrations:
  - from: "2.0.4"
    to: "2.0.5"
    file: "2.0.4-to-2.0.5.yaml"
```

### Migration Script

`ConstructionKit/migrations/2.0.4-to-2.0.5.yaml`:
```yaml
$schema: ck-migration.schema.json
transforms:
  - type: RenameAttribute
    ckTypeId: MyModel/MyType
    from: OldAttributeName
    to: NewAttributeName
  - type: ChangeCkType
    from: MyModel/OldType
    to: MyModel/NewType
  - type: SetValue
    ckTypeId: MyModel/MyType
    attributeName: Status
    value: "Active"
  - type: MapValue
    ckTypeId: MyModel/MyType
    attributeName: Priority
    mappings:
      "1": "Low"
      "2": "Medium"
      "3": "High"
  - type: CopyAttribute
    ckTypeId: MyModel/MyType
    from: SourceAttr
    to: TargetAttr
  - type: DeleteAttribute
    ckTypeId: MyModel/MyType
    attributeName: ObsoleteField
```

### Migration Runner Integration

Migrations run automatically during `ImportCkModelAsync`:
1. `GetSchemaVersionsDirectAsync()` captures current versions before import
2. CK model YAML is compiled and imported
3. `RunCkModelMigrationsForImportAsync()` compares old vs new versions and applies migration transforms

### Migration Path Resolution

When the installed tenant version differs from the requested version, `CkModelMigrationService` resolves a path in this order: **Direct → Multi-Hop → Auto-Bridge-Start → Auto-Bridge-Both → Post-Chain-Bridge → No-Migrations Bridge → Partial → No Path.** Two rules to know when debugging "migration failed":

- **Post-chain schema-only bridge** — when migration scripts exist but the chain ends *below* the tenant's installed version, the runner synthesises a no-op step covering the remaining gap (no script needed).
- **No-migrations bridge** — purely **additive** version bumps with no migration script are handled automatically; you do not need to author an empty migration.

### Backups Are No Longer Automatic

`CkModelMigrationService` and `BlueprintService.UpgradeModelsAsync` now default `CreateBackup = false` (it used to be `true`, which forced a `mongodump` dependency into every container). Backups happen **only on explicit opt-in**. If your rollback plan assumed a mongodump snapshot was taken before an additive CK migration — it was not. Take an infrastructure volume backup yourself first (see database-operations.md).

### EnsureCkModelInstalledAsync Bug History

`MongoRuntimeRepositoryProvider.EnsureCkModelInstalledAsync` previously compared installed vs requested models **by name only**, so it silently skipped additive upgrades. **Symptom (pre-2026-06-02):** the `CkModel` collection stays at the old version while `ValidateCkModels` expects the new one. The fix compares by **version** too, falling through to `ImportCkModelAsync` when installed < requested. If you see a CkModel stuck at an old version after an additive bump on a service running an older image, this is the likely cause.

## MongoDB CK Collections

Each tenant database contains these CK-related collections:

| Collection | Content |
|-----------|---------|
| `CkModel` | Model metadata: `_id`, `modelId`, `modelState`, `dependencies`, `description` |
| `CkType` | Type definitions within models |
| `CkAttribute` | Attribute definitions for types |
| `CkRecord` | Record (value object) definitions |
| `CkEnum` | Enumeration definitions |
| `CkAssociation` | Relationship definitions between types |

The `octosystem` database contains the system tenant's CK data. Regular tenant databases (e.g., `meshtest`, `maco`) contain tenant-specific CK data.

### Model States

| Value | State | Meaning |
|-------|-------|---------|
| 0 | Pending | Being imported |
| 1 | Available | Fully resolved, operational |
| 2 | ResolveFailed | Dependency resolution failed |

### Blueprint Registry Types (System CK 2.2.0)

Blueprint state lives **tenant-locally** in three CK types defined in `System` CK 2.2.0 (`SystemCkModel/ConstructionKit/types/blueprintRegistry.yaml`) — not in a cross-tenant collection:

| CK type | Stores |
|---------|--------|
| `System/BlueprintInstallation` | One row per applied blueprint (name, version, installed/updated timestamps, seed-data checksum, resolved dependencies, `IsDependency`) |
| `System/BlueprintHistory` | Apply/update/uninstall history entries |
| `System/BlueprintBackup` | Tenant backups created before blueprint updates (rollback source) |

Query these `RtEntity` rows in the affected tenant DB when a blueprint apply/update fails, and check the platform event log for `BlueprintOperationFailed` events emitted over the DistributionEventHub (see build-system.md).

## System.Identity CK Model

`System.Identity` is at **2.6.0** (schema version **16**, constant `IdentityServiceConstants.IdentitySchemaVersionValue = 16`). Registered via `AddCkModelSystemIdentityV2()`. Recent additions relevant to cross-tenant ClientCredentials debugging:

- **`ClientMirror` CK type** (`types/ck-clientMirror.yaml`) — one row per `(parentClientId × childTenantId)` pair, stored in the **parent** tenant's identity DB; tracks `ParentClientId`, `ParentTenantId`, `ChildTenantId`, `ProvisionedAt`, `SecretHashVersion`.
- **`Client.AutoProvisionInChildTenants`** (bool, default `false`) — when set on a parent client, every new sub-tenant gets a mirror of that client.
- **`Client.ProvisionedByParentTenantId`** (string) — set on a mirrored child client to record which parent provisioned it.

## CrateDB / StreamData Project Split

The CrateDB StreamData stack was extracted from `Runtime.Engine.MongoDb` into a dedicated **`Runtime.Engine.CrateDb`** project (in `octo-construction-kit-engine-mongodb`). Namespaces changed from `Meshmakers.Octo.Runtime.Engine.MongoDb.StreamData.*` to **`Meshmakers.Octo.Runtime.Engine.CrateDb.*`** — when navigating logs or source during StreamData debugging, look under the new namespace/package, not the old MongoDb.StreamData path. The CrateDB cluster runs as **3 nodes** (`cratedb01/02/03`, schema-per-tenant layout) and is backed up alongside MongoDB by the infrastructure backup cmdlets.
