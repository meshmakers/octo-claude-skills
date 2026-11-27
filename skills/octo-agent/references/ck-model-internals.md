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

At import time, a **classic** model's ranges resolve to **exact pinned versions** stored in the `CkModel` MongoDB collection. For example, `System-[2.0,3.0)` resolves to `System-2.2.0` if that's the installed version. A **range-retaining** model keeps its ranges (`dependencyRanges`) and is re-resolved against whatever is installed — see *CK Language 2 and range retention* below.

**Versions in this file are examples, never the current state.** Read the current versions where they live: the System models of the engine in octo-construction-kit-engine `docs/system-ck-models.md`, any model in its `ConstructionKit/ckModel.yaml` (and `ConstructionKit/CHANGELOG.md` where the repository keeps one), a tenant's installed versions in its `CkModel` collection or with `octo-cli -c LibraryStatus`.

## CK Model Versioning

### Source-Level vs Runtime-Level

Example values (a classic model on an old System line):

| Concept | Source (YAML) | Runtime (MongoDB) |
|---------|--------------|-------------------|
| Model ID | `System-2.2.0` | `_id: "System-2.2.0"` |
| Dependencies | Range: `System-[2.0,3.0)` | Pinned: `["System-2.2.0"]` (classic); the range is kept for a range-retaining model |
| State | N/A | `modelState: 1` (Available), `2` (ResolveFailed) |

### Version Bump Impact

**Critical knowledge from testing:** Bumping a base model version (e.g., System 2.1.0 -> 2.2.0) without recompiling all dependent CK models causes cascading `ResolveFailed` states:

1. The old model document (e.g., `System-2.1.0`) gets **deleted** from MongoDB
2. The new version (e.g., `System-2.2.0`) gets inserted
3. Models compiled into the same binary get auto-updated (e.g., `System.Notification`)
4. Models from other repos still reference the old pinned version -> `ResolveFailed`
5. This cascades: if `Basic` fails, all of `Basic`'s dependents also fail

**Rule:** When bumping a base CK model version, ALL dependent **classic (exact-pinned)** CK models across ALL repos must be recompiled and redeployed. A range-retaining dependent keeps resolving as long as the new version is inside its range. A `ResolveFailed` model is re-validated after every import and recovers by itself once its dependencies resolve again (see *Import guard and re-validation* below).

**Error code 66 (multi-version conflict):** When transitive resolution finds two incompatible versions of the *same* model (e.g., different catalogs pin different versions), the compiler raises a fatal **error 66** listing the conflicting versions and their origins (instead of a cryptic dictionary-key collision). Resolutions: rebuild the conflicting dependents against one common version, narrow the dependency range in the consumer's `ckModel.yaml`, or disable stale catalogs via the MSBuild toggles **`OctoPublicGitHubCatalogIsEnabled`** / **`OctoPrivateGitHubCatalogIsEnabled`** (set on the `CkCompile`/`CkRestore` tasks).

### CK Language 2 and range retention

The CK v2 engine adds a second model language and keeps dependency ranges at runtime. The rules live in octo-construction-kit-engine — read them there, this section only tells you what to look for:

| Topic | What it means in a diagnosis | Source of truth (octo-construction-kit-engine) |
|-------|------------------------------|-----------------------------------------------|
| `ckLanguage: 2` in `ckModel.yaml` | Stricter defaults (e.g. `derivable` defaults to `Model`, so a type other models derive from needs `derivable: Any`); a language switch that changes the surface is a Major. | `docs/system-ck-models.md` ("System on ckLanguage 2"), `docs/ck-semver-rules.md` |
| Range retention | The compiler default: compiled output keeps `dependencyRanges` and `Name@major/` references instead of exact pins. The old switches (`OctoCkRangeRetention`, `octo-ckc -rr`) are ignored and warn `OCTO-CK300`. The first publish of an existing model after the flip needs a Minor bump. | `docs/ck-versioning.md` ("CK v2 Range Retention") |
| `minEngineVersion` | Written for `ckLanguage: 2` and range-retaining models (and inherited from dependencies). An engine below it refuses the model with **message 126**; DebugL (`999.0.0`) reads it. | `docs/ck-versioning.md` |
| Catalog roots `ck-models/v2/` and `ck-models/v3/` | Classic models publish to `v2`, `ckLanguage: 2`, range-retaining models and anything with `minEngineVersion` to `v3`. Engines before CK v2 read only `v2`, so a model "missing from the catalog" for an old service may simply live in `v3`. | `docs/ck-publishing.md` (section "CK Model Publishing Lanes (CI)", paragraph "Two catalog roots") |
| Version-less `RtCkId` | Runtime code must never look up a CK element by a generated **versioned** id (`SystemCkIds.Ck…Id`): a tenant can hold a newer model than the service embeds, and the versioned id is not in its CK cache. Use the version-less `RtCk…` constant or `.ToRtCkId()`; analyzer **OM1005** reports it. | `docs/ck-versioned-id-guard.md` |
| Shared-environment gate | Never publish a `ckLanguage: 2` (v3-only) model into a shared catalog or environment before every service there runs the CK v2 engine. Older services would refuse it (126) or not see it. | `docs/system-ck-models.md` (section "System on ckLanguage 2", bullet "Publishing"; the reason for all v3-only models is given where it describes the range-retention MINOR bumps) |

Start with the repository's `AGENTS.md`, which maps source paths to these `docs/` files.

### Import guard and re-validation (what the logs say)

octo-construction-kit-engine-mongodb decides what happens when a service imports a CK model into a tenant. Full rules: `docs/ck-model-import.md` in that repository (sections "Embedded CK Model Import Guard" and "Re-validation of ResolveFailed Models after Every Import"). The log lines an agent will see (templates from the source; `{…}` are placeholders):

**Embedded import guard** (`EmbeddedCkModelImportGuard`): every service imports the models it embeds at tenant setup. The guard looks the model up **by name** and never downgrades it:

| Installed in the tenant | Decision | Log |
|-------------------------|----------|-----|
| none or older | import (upgrade + migrations) | INFO |
| same version | short-circuit | DEBUG |
| newer, same major | **skip** | INFO `Embedded CK model import skipped for tenant '{TenantId}': downgrade prevented, the tenant has '{InstalledModelId}', the service embeds '{EmbeddedModelId}'` |
| higher major | **skip** | WARN `Embedded CK model import skipped for tenant '{TenantId}': the service embeds '{EmbeddedModelId}' (major {EmbeddedMajor}), the tenant has '{InstalledModelId}' (major {InstalledMajor}); this service is too old for the tenant` |

A skip is logged once per process (repeats are DEBUG); the suffix ` (installed concurrently by another service, detected under the import lock)` means a parallel service start won the race. A "downgrade prevented" line is normal when services of different builds share a tenant; "too old for the tenant" means that service must be upgraded. Its own exact-pinned service model then goes `ResolveFailed` until it is.

**Missing dependencies** (WARN, the import is retried when the dependency arrives): `Skipping CK model '{CkModelId}' import for tenant '{TenantId}' due to missing dependencies: {Message}. This import will be retried when the dependent CK model becomes available.` — usual during a parallel stack start; a problem only when it does not clear.

**Re-validation after every import** (`DatabaseCkModelRepository`): `Available` and `ResolveFailed` models are re-resolved after each import, so a `ResolveFailed` model heals once its dependencies resolve again:

- WARN `CK model '{CkModelId}' no longer resolves and is marked as ResolveFailed: {Reason}. It is re-validated after every CK model import and returns to Available once it resolves`
- INFO `CK model '{CkModelId}' resolves again (dependencies {Dependencies} satisfied) and is Available`
- DEBUG `CK model '{CkModelId}' still does not resolve: {Reason}` (no log spam while it stays failed)

**Explicit `ImportCk` downgrades** (not service-managed models): an explicit import may downgrade a model; the API's tenant upgrade guard refuses a breaking file unless forced. A downgrade that passes logs WARN `Explicit downgrade of CK model '{CkModelName}' in tenant '{TenantId}' from '{InstalledModelId}' to '{ImportedModelId}'`.

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
| `octo-platform-services` | `System.UI` (`AddCkModelSystemUIV2`; formerly the retired admin panel) |
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

The `octosystem` database contains the system tenant's CK data. Regular tenant databases (e.g., `meshtest`, `<tenant>`) contain tenant-specific CK data.

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
