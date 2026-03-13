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

At import time, the runtime resolves ranges to **exact pinned versions** stored in the `CkModel` MongoDB collection. For example, `System-[2.0,3.0)` resolves to `System-2.0.5` if that's the installed version.

## CK Model Versioning

### Source-Level vs Runtime-Level

| Concept | Source (YAML) | Runtime (MongoDB) |
|---------|--------------|-------------------|
| Model ID | `System-2.0.5` | `_id: "System-2.0.5"` |
| Dependencies | Range: `System-[2.0,3.0)` | Pinned: `["System-2.0.5"]` |
| State | N/A | `modelState: 1` (Available), `2` (ResolveFailed) |

### Version Bump Impact

**Critical knowledge from testing:** Bumping a base model version (e.g., System 2.0.5 -> 2.0.6) without recompiling all dependent CK models causes cascading `ResolveFailed` states:

1. The old model document (e.g., `System-2.0.5`) gets **deleted** from MongoDB
2. The new version (e.g., `System-2.0.6`) gets inserted
3. Models compiled into the same binary get auto-updated (e.g., `System.Notification`)
4. Models from other repos still reference the old pinned version -> `ResolveFailed`
5. This cascades: if `Basic` fails, all of `Basic`'s dependents also fail

**Rule:** When bumping a base CK model version, ALL dependent CK models across ALL repos must be recompiled and redeployed.

### Models Compiled Per Binary

| Binary/Repo | CK Models Compiled |
|-------------|-------------------|
| `octo-construction-kit-engine` | `System`, `System.Notification` |
| `octo-identity-services` | `System.Identity` |
| `octo-bot-services` | `System.Bot` |
| `octo-communication-controller-services` | `System.Communication` |
| `octo-report-services` | `System.Reporting` |
| `octo-asset-repo-services` | `System.UI` |
| `octo-construction-kit` | `Basic`, `Industry.Basic`, `Industry.Energy`, `Industry.Fluid`, `Industry.Maintenance`, `Environment`, `EnergyCommunity`, `OctoSdkDemo` |

To discover which CK models a service compiles, search for `AddCkModel` registrations in the service's `Program.cs` or startup code.

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
services.AddCkModelSystemBotV2();      // Dependents after
services.AddRuntimeEngine()
    .AddMongoDbRuntimeRepository();    // MongoDB last — needs BSON class maps
```

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
