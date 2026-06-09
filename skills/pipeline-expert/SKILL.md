---
name: pipeline-expert
description: Authoring, reading, editing, debugging, and validating OctoMesh ETL pipeline YAML — the node-by-node config, DataContext/JSONPath data flow, triggers, transformations, entity CRUD via CreateUpdateInfo/ApplyChanges, archive (CrateDB) writes, inter-pipeline chaining within a DataFlow, and deployment/debug troubleshooting. Use whenever someone builds or fixes a pipeline definition or asks what a node does. Trigger on: pipeline YAML, pipeline node, node configuration, DataContext, ForEach, For, DataFlow, PipelineTrigger, cron schedule, ToPipelineDataEvent, FromPipelineDataEvent, FromPipelineTriggerEvent, FromExecutePipelineCommand, GetRtEntities, CreateUpdateInfo, CreateAssociationUpdate, ApplyChanges, association updates, field filters, SaveStreamDataInArchive, TimeRangeArchive, BackfillFromRtEntity, SetPipelineExecutionResult, OutputData empty, Group node, DataPointMapping, ApplyDataPointMappings, BuildMappingTargets, GenerateDataPointMappings, ValidateDataPointCoverage, ToDiscord, AnthropicAiQuery, MCP, Zenon, SAP, anomaly detection, CSV/Excel import, SFTP, Grafana, Teams, OCR, pipeline schema, pipeline validation, pipeline debug, deploy pipeline, pipeline error.
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/pipeline-expert/references/*)"
  - "Grep"
  - "Glob"
  - "Read"
---

# OctoMesh Pipeline Expert

## Overview

OctoMesh pipelines are YAML-defined ETL data flows executed by adapters. Each pipeline has **triggers** that start execution and **transformations** (an ordered list of nodes) that process data through a shared **DataContext** — a mutable JSON document accessed via JSONPath.

An **Adapter** (`System.Communication/Adapter`) is a unified runtime that executes pipelines. Different implementations exist (Mesh, Zenon, Simulation, …) but all share the same CK type and execution model; each registers the nodes it supports — SDK-shared nodes plus adapter-specific ones. Pipelines handle entity CRUD, cross-adapter sync, import/export, notifications, reports, AI queries, anomaly detection, and more.

## Source Code Research (MANDATORY)

**NEVER guess how a pipeline node behaves.** The reference docs are summaries; the C# source is ground truth. Read the source before answering or writing YAML whenever you are not 100% certain of a node's property names/defaults, need to know what it does at runtime, hit a node you don't recognize, or a user reports unexpected behavior. All paths below are **relative to the monorepo root** — the parent directory of this plugin's repo, containing both `octo-sdk/` and `octo-mesh-adapter/` (use `../` or search upward).

### Where Node Source Code Lives

| Node set | Configuration classes (properties/defaults) | Handler classes (runtime behavior) |
|----------|----------------------------------------------|-------------------------------------|
| **SDK** (ForEach, If, Switch, For, Group, SelectByPath, SetPrimitiveValue, Concat, Math, FromPolling, ToPipelineDataEvent, SetPipelineExecutionResult, BufferData, …) | `octo-sdk/src/Sdk.Common/EtlDataPipeline/Nodes/` under `Control/`, `Extracts/`, `Transforms/`, `Triggers/`, `Loads/`, `Buffering/` — config + handler usually in the same file | (same files) |
| **Mesh Adapter** (GetRtEntitiesByType, CreateUpdateInfo, ApplyChanges, SaveStreamDataInArchive, ToDiscord, ApplyDataPointMappings, …) | `octo-mesh-adapter/src/MeshNodes.Sdk/` under `Extract/`, `Transform/`, `Load/`, `Trigger/` | `octo-mesh-adapter/src/MeshAdapter.Sdk/Nodes/` under the same four folders |
| **Zenon Adapter** (the six archive/Editor nodes) | `octo-plug-zenon/src/Octo.Edge.Adapter.Zenon.WindowsService/Nodes/` — config record + handler in the same file | (same files) |
| **Simulation** (`Simulation@1`) | `octo-sdk/src/Sdk.SimulationNodes/Nodes/Extracts/SimulationNode.cs`; generators under `Sdk.SimulationNodes/Generators/` | (same) |

### Naming Conventions & Lookup

| What | Pattern | Example |
|------|---------|---------|
| Config class | `[NodeName]NodeConfiguration.cs` (versioned: `…Configuration2.cs`) | `CheckDuplicateNodeConfiguration.cs` |
| Handler class | `[NodeName]Node.cs` (versioned: `…Node2.cs`) | `CheckDuplicateNode.cs` |
| Config attribute | `[NodeName("DisplayName", Version)]` | `[NodeName("CheckDuplicate", 1)]` |
| Handler attribute | `[NodeConfiguration(typeof(ConfigClass))]` | `[NodeConfiguration(typeof(CheckDuplicateNodeConfiguration))]` |

Find a node: Grep for `NodeName\("CheckDuplicate"` in `octo-mesh-adapter/src/` (else `octo-sdk/src/`), or Glob `**/CheckDuplicate*Configuration*.cs`. Read the **config class** for properties/defaults/required-vs-optional (from XML docs), then the **handler** for runtime behavior, DataContext reads/writes, and error conditions.

## DataFlows and Pipeline Triggers

A **DataFlow** (`System.Communication/DataFlow`) is a logical grouping of related pipelines that work together as part of a single data processing workflow. It serves as the parent container for Pipeline and PipelineTrigger instances.

> **Migration note:** CK migration `3.1.0→3.1.1` unified the old `EdgeAdapter`/`MeshAdapter` into a single `Adapter` type, and `EdgePipeline`/`MeshPipeline` into a single `Pipeline` type. Earlier migrations renamed `DataPipeline` → `DataFlow` and `DataPipelineTrigger` → `PipelineTrigger`. These are handled automatically by `ChangeCkType` transforms.

**Key concepts:**
- Pipelines belong to a DataFlow via `System/ParentChild` association
- A DataFlow establishes a **shared topic exchange** in the event hub, enabling inter-pipeline communication
- Pipelines within the same DataFlow can send data to each other using `ToPipelineDataEvent@1` (with `targetPipelineRtId`) and `FromPipelineDataEvent@1`

A **PipelineTrigger** (`System.Communication/PipelineTrigger`) is a child of a DataFlow that triggers pipeline execution on a cron schedule via the Bot Service:
- Has `Enabled` and `CronExpression` attributes
- Has a `Triggers` association linking to one or more Pipeline entities
- The target pipelines must use `FromPipelineTriggerEvent@1` as their trigger node
- Cron format: standard 5-field `minute hour dayOfMonth month dayOfWeek` (no year field; e.g. `0 * * * *` = top of every hour). Scheduled via the MassTransit/Hangfire recurring scheduler.

**Entity relationships:**
```
DataFlow
  ├── Pipeline (child, via ParentChild) ── executes on ── Adapter
  └── PipelineTrigger (child, via ParentChild) ── triggers ── Pipeline(s)
```

## Pipeline YAML Structure

```yaml
triggers:
  - type: NodeType@Version      # trigger-specific properties
transformations:
  - type: NodeType@Version      # node-specific properties
    transformations:            # control-flow nodes nest child nodes
      - type: ChildNode@Version
```

**Triggers** define how the pipeline starts: polling interval, HTTP request, entity change watch, event hub message, explicit command, or email. Each trigger type populates the DataContext with different initial paths — see `references/data-context-guide.md` "Trigger DataContext Placement" for the full table. Key examples:
- `FromHttpRequest@1`: body at `$.body`, query params at `$.query`, files at `$.files`
- `FromWatchRtEntity@1`: changed entity at `$.Document`
- `FromExecutePipelineCommand@1` / `FromPipelineTriggerEvent@1`: empty context. `FromExecutePipelineCommand@1` now lives in `Sdk.Common` and is available on **all** adapters (Edge and Mesh), not Mesh-only — the pipeline must still belong to a DataFlow.

**Transformations** define the processing steps. Each node reads from and writes to the DataContext. Control flow nodes (ForEach, If, Switch) nest child transformations.

## Common Pipeline YAML Mistakes

These errors cause deployment failures. Check your YAML against this table before deploying:

| Mistake | Error | Fix |
|---------|-------|-----|
| `version: '1'` at root level | `Property 'version' not found on NodeDefinitionRoot` | Remove it — pipeline YAML has only `triggers:` and `transformations:` at root |
| `path: $` on `PrintDebug@1` | `Property 'path' not found` | `PrintDebug@1` has no `path` property — it prints the entire DataContext by default |
| `path: $` on `SetPrimitiveValue@1` | `Property 'path' not found` | Use `targetPath` instead — `SetPrimitiveValue@1` writes to `targetPath`, not `path` |
| `valueType: Int32` | `Not in enum` | Use the short enum name: `Int`, `Boolean`, `String`, `Double`, `DateTime`, etc. |
| `ckTypeId: Model-Version/Type` | Deployment error | Use unversioned: `Model/Type` (pipeline YAML ckTypeId refs are unversioned, unlike ImportRt YAML) |

**Prevention:** before deploying, fetch the schema (`octo-cli -c GetPipelineSchema --adapterId <rtId> --outputFile schema.json`) and confirm each node's property names and enum values in `$defs`, or use `pipeline_validate.py`.

## DataContext Essentials

The DataContext is a mutable JSON document. All nodes share it.

**Reading:** Use `path` or `valuePath` properties with JSONPath (`$.property`, `$.array[*]`, `$.nested.path`).

**Writing:** Use `targetPath` with three modifiers:
- `documentMode`: **Extend** (merge into existing, default) or **Replace** (clear and set)
- `targetValueWriteMode`: **Overwrite** (default), **Append**, **Prepend**, or **Merge**
- `targetValueKind`: **Simple** (scalar/object, default) or **Array** (wrap in array)

Common write pattern for collecting items:
```yaml
targetPath: $.key.updates
targetValueWriteMode: Append
targetValueKind: Array
```

For full details on write semantics and field filters, read `references/data-context-guide.md`.

## ForEach Iteration

> **For@1 is different:** For@1 deep-clones the parent context directly — it does NOT create `$.full`/`$.key` paths. Access data at the same paths as the parent (e.g., `$.body.count`, not `$.full.body.count`). Supports both static `count` and dynamic `countPath` (JSONPath). See `references/data-context-guide.md` for a full comparison table.

ForEach creates a **child context** per array element with three key paths:

| Path | Default | Purpose |
|------|---------|---------|
| `fullDocumentPath` | `$.full` | Complete copy of parent context (read-only reference) |
| `keyPath` | `$.key` | Current iteration item |
| `mergePath` | `$.key` | Where to collect each iteration's result |

**Inside ForEach**, access data as:
- `$.key.Field` — current item
- `$.full.OtherData` — parent context data

**Nested ForEach** chains `$.full`:
- `$.key` — innermost item
- `$.full.key` — outer item (one level up)
- `$.full.full.Config` — root context (two levels up)

**Parallelism:** `maxDegreeOfParallelism` controls concurrency (0=CPU count, -1=unlimited, >0=explicit). Use 1 for sequential when order matters.

For a deeper explanation of context hierarchy, write modes, and field filters, read `references/data-context-guide.md`.

## Node Categories

This is an operational overview of the **most-used** nodes. The full property tables for every node live in `references/node-reference-sdk.md` (SDK nodes, available on all adapters) and `references/node-reference-mesh.md` (Mesh Adapter nodes). Read those before writing YAML for any node not summarized here.

### Triggers

| Node | Purpose |
|------|---------|
| `FromPolling@1` | Poll at interval (e.g., `00:05:00`) |
| `FromHttpRequest@1` | HTTP endpoint (method + path) |
| `FromWatchRtEntity@1` | Entity change stream (Insert/Update/Delete) |
| `FromPipelineDataEvent@1` | Receive data from another pipeline in the same DataFlow |
| `FromExecutePipelineCommand@1` | Manual execution command (SDK node — all adapters); pipeline must be in a DataFlow |
| `FromPipelineTriggerEvent@1` | Scheduled execution via PipelineTrigger entity (5-field cron) |
| `FromSendNotification@1`, `FromEmail@1`, `FromMicrosoftGraph@1` | Notification message / IMAP email / Teams channel poll |

### Control Flow (SDK)

| Node | Purpose |
|------|---------|
| `ForEach@1` | Iterate array with child context (`$.full`/`$.key`/merge) |
| `For@1` | Execute N times — deep-clones parent context; `count` (static) or `countPath` (dynamic, wins); `maxDegreeOfParallelism` |
| `If@1` | Conditional (Equal, Contains, GreaterThan, RegexMatch, etc.) |
| `Switch@1` | Multi-branch by value (supports array case values) |
| `SelectByPath@1` | Select and transform multiple paths |
| `Group@1` | Structural no-op container — runs children inline on the same context; editor-grouping only, NO runtime effect |

### Extract (Data In)

| Node | Purpose |
|------|---------|
| `SetPrimitiveValue@1` / `SetArrayOfPrimitiveValues@1` / `WriteJson@1` | Inject static/dynamic value, value array, or raw JSON (SDK) |
| `GetRtEntitiesByType@1` / `GetRtEntitiesById@1` / `GetRtEntitiesByWellKnownName@1` | Query entities by CK type / by ID / by well-known name (enriches with IDs) |
| `GetOrCreateRtEntitiesByType@1` | Find by field filters or generate a new ID |
| `GetAssociationTargets@1` | Traverse associations |
| `GetQueryById@1` | Execute a saved query (simple/aggregation/grouping queries; cache disabled — always fresh) |
| `GetPipelineConfigByWellKnownName@1` (SDK) / `GetPipelineConfigByCkTypeId@1` (Mesh) | Load global config by name / by CK type |
| `GetNotificationTemplate@1` | Load notification template (subject + body) |
| `BackfillFromRtEntity@1` | Backfill missing attributes from MongoDB using a CkArchive's column spec (replaces removed `EnrichWithMongoData@1`); sits before `SaveStreamDataInArchive@1` |

### Transform

Common: `CreateUpdateInfo@1` (build entity Insert/Update/Delete), `CreateAssociationUpdate@1` (build association Create/Delete), `CreateFileSystemUpdate@1`, `DataMapping@1` (value mapping), `Concat@1`, `FormatString@1`, `TransformString@1`, `Flatten@1`, `Project@1`, `Join@1`, `Math@1`, `SumAggregation@1`, `FilterLatestUpdateInfo@1`, `Distinct@1` (SDK — all adapters), `PlaceholderReplace@1`, `Base64Encode@1`/`Base64Decode@1`, `Hash@1`, `ConvertDataType@1`, `Map@1`, `LinearScaler@1`, `MinMax@1`, `Logger@1`/`PrintDebug@1`, `ExecuteCSharp@1`, `MakeHttpRequest@1`, `CheckDuplicate@1`, `ComputeFileHash@1`, `QueryResultToMarkdownTable@1`.

Specialized (see `node-reference-mesh.md`): `AnthropicAiQuery@1` (Claude AI; MCP-aware), `PdfOcrExtraction@1`, `StatisticalAnomalyDetection@1`, `MachineLearningAnomalyDetection@1`, `ImportFromCsv@1`, `ImportFromExcel@1`, `ReplyToTeamsChannel@1`.

DataPointMapping family (Mesh): `ApplyDataPointMappings@1` (evaluate mappings with mXparser expressions), `BuildMappingTargets@1` (resolve mappings to acquisition targets), `GenerateDataPointMappings@1` (deterministic rule-based generator — non-AI alternative to `AnthropicAiQuery@1`), `ValidateDataPointCoverage@1` (coverage report), `MapToRecordArray@1`, `UpdateRecordArrayItem@1`.

Simulation: `Simulation@1` is an **Extract** node (not Transform) — Bogus/Math/Energy generators; `SimulateEnergyMeasurements@1` (Mesh) generates 15-min EnergyMeasurement slots from BDEW/PV profiles.

### Load (Data Out)

| Node | Purpose |
|------|---------|
| `ApplyChanges@1` | Apply entity updates to MongoDB |
| `ApplyChanges@2` | Apply entity + association updates (preferred) |
| `SaveStreamDataInArchive@1` | Write entity data to a named CrateDB **CkArchive** (replaces removed `SaveInTimeSeries@1`); requires `archiveRtId` pointing at an **Activated** archive |
| `SaveTimeRangeStreamDataInArchive@1` | Write pre-aggregated time-range points to an Activated `TimeRangeArchive` (requires `archiveRtId`) |
| `UpdateRtEntityIfNewer@1` | Timestamp dedup: keep only strictly-newer candidates for the RT write, emit all for the archive write |
| `SetPipelineExecutionResult@1` (SDK) | **REQUIRED to persist pipeline OutputData.** Without it the execution result is never stored — `GetLatestPipelineExecution` shows empty OutputData. See "Persisting OutputData" below |
| `ToPipelineDataEvent@1` (SDK) | Send data to another pipeline in the same DataFlow (`targetPipelineRtId`); optional await-result mode for synchronous request/response |
| `ToWebhook@1` (SDK) | HTTP POST to external endpoint |
| `ToDiscord@1` | Post message/embed/attachment to a Discord channel via a `DiscordConfiguration` entity |
| `DeployPipeline@1` | Deploy another pipeline in the same DataFlow via the Communication Controller REST API |
| `SendEMail@1`, `GenerateAndStoreReport@1`, `SftpUpload@1` | Email / report generation / SFTP upload |
| `GrafanaProvisionTenant@1` / `GrafanaDeprovisionTenant@1` | Provision / deprovision a tenant Grafana org |

### Buffering (SDK)

`BufferData@1` (buffer with time-based flush) and `BufferRetrievalNode@1` (retrieve buffered data).

### Domain-Specific

SAP nodes (SapLogin, GetProductionOrderList, GetProductionOrderDetails), Zenon nodes (variable/AML read-write **plus** the six archive/Editor nodes `ReadZenonArchiveInfo@1`, `ReadZenonArchiveData@1`, `ListZenonProjects@1`, `GetZenonDynamicProperties@1`, `GetZenonDynamicProperty@1`, `SetZenonDynamicProperty@1`), Microsoft Teams nodes, and Grafana nodes are documented in `references/node-reference-mesh.md`. EDA energy nodes ship in an **external adapter not present in this monorepo** — see that file's external-adapter note.

## Persisting OutputData (why is OutputData empty?)

Pipeline execution output is **only** stored when the pipeline includes `SetPipelineExecutionResult@1` (SDK Load node). It captures the data-context value at its `path` and stores it as the `PipelineExecution.OutputData` retrieved via `GetLatestPipelineExecution`. Without this node nothing is persisted — this is by design (avoids storing large results from high-frequency pipelines), and it explains an empty/missing OutputData. `maxLength` (default 1 048 576 chars) truncates oversized results.

```yaml
- type: SetPipelineExecutionResult@1
  path: $.result        # value to persist as OutputData
  # maxLength: 1048576  # optional cap
```

## RT Entity Data Structures

`GetRtEntitiesByType@1` returns an **IResultSet object**, not a plain array:

```json
{ "TotalCount": 3, "Items": [ { "RtId": "...", "CkTypeId": "...", "RtWellKnownName": "...", "Attributes": { "Name": "value", "StartDateTime": "2026-01-01T06:00:00Z" } }, ... ] }
```

**Key rules:**
- **Iterate with `.Items`**: `iterationPath: $.result.Items` (NOT `$.result`)
- **Check count**: `$.result.TotalCount`
- **Access attributes inside ForEach**: `$.key.Attributes.AttributeName` (short name, no CK prefix or version suffix)
- **System properties**: `$.key.RtId`, `$.key.CkTypeId`, `$.key.RtWellKnownName`
- All property names are **PascalCase**

## Attribute Name Casing in CreateUpdateInfo

**CRITICAL:** The `attributeName` field in `CreateUpdateInfo@1` must use the **exact casing from the CK model definition** — typically **camelCase** (e.g., `name`, `machineState`, `operatingHours`).

This is **different** from the PascalCase you see in GraphQL query results (where attributes appear as `$.key.Attributes.Name`). The distinction:

| Context | Casing | Example |
|---------|--------|---------|
| Reading RT entities (GraphQL response) | PascalCase | `$.key.Attributes.MachineState` |
| Writing RT entities (`attributeName` in CreateUpdateInfo) | camelCase (from CK model) | `attributeName: machineState` |
| Field filters (`attributePath` in fieldFilters) | PascalCase (matches DB field names) | `attributePath: SerialNumber` |
| System properties in fieldFilters | PascalCase | `attributePath: RtWellKnownName` |

**Always run `ck_explorer.py preflight <type>` before writing CreateUpdateInfo to get the exact attribute names.**

## EntityUpdateInfo JSON Structure

`CreateUpdateInfo@1` writes an `EntityUpdateInfo`: a nested `RtEntity` (with `RtId`, `RtChangedDateTime`, `CkTypeId`, `Attributes`) plus top-level `RtId`, `CkTypeId`, and `ModOption` (0=Insert, 1=Update, 2=Delete).

```json
{ "RtEntity": { "RtId": "cc...bb01", "CkTypeId": "Industry.Basic/Machine", "Attributes": { "MachineState": 0 } }, "RtId": "cc...bb01", "CkTypeId": "Industry.Basic/Machine", "ModOption": 0 }
```

The top-level `RtId` is populated only when a static `rtId` is given or an upstream node resolved/generated it. Do NOT use `generateRtId: true` — obtain IDs first via `GetOrCreateRtEntitiesByType@1` or `GetRtEntitiesByWellKnownName@1` so they can be referenced in associations.

## Mandatory Associations

Some CK types have **mandatory outbound associations** (multiplicity = ONE). Creating an entity of such a type WITHOUT the required association will fail at `ApplyChanges` time with: `"Inbound association 'X' has minimum multiplicity of 'One'"`.

**Pre-flight check:** Always run `ck_explorer.py preflight <type>` before writing CreateUpdateInfo for a new entity type. If the output shows mandatory associations, you MUST include `CreateAssociationUpdate@1` nodes in the same `ApplyChanges@2` call.

**Common mandatory association:** `System/ParentChild` — types like Machine, TreeNode, and many domain entities require a parent.

### The intended workflow for creating entities with associations

Use `GetOrCreateRtEntitiesByType@1` to resolve/generate IDs for both parent and child (each writes `rtId` + `modOp` paths), then have `CreateUpdateInfo@1` and `CreateAssociationUpdate@1` reference those IDs **via paths** — never `generateRtId: true`:

```yaml
- type: GetOrCreateRtEntitiesByType@1   # parent → $.parentRtId / $.parentModOp
  ckTypeId: Basic/Tree
  fieldFilters: [{ attributePath: RtWellKnownName, comparisonValue: "My Container" }]
  rtIdTargetPath: $.parentRtId
  modOperationPath: $.parentModOp
- type: GetOrCreateRtEntitiesByType@1   # child → $.childRtId / $.childModOp
  ckTypeId: Industry.Basic/Machine
  fieldFilters: [{ attributePath: RtWellKnownName, comparisonValue: "My Machine" }]
  rtIdTargetPath: $.childRtId
  modOperationPath: $.childModOp
- type: CreateUpdateInfo@1              # child entity update, RtId from path
  targetPath: $.entityUpdates
  targetValueWriteMode: Append
  targetValueKind: Array
  updateKindPath: $.childModOp
  rtIdPath: $.childRtId
  ckTypeId: Industry.Basic/Machine
  attributeUpdates: [{ attributeName: machineState, attributeValueType: Enum, value: 1 }]
- type: If@1                            # create the mandatory assoc ONLY on INSERT (modOp = 0)
  path: $.childModOp
  value: 0
  valueType: Enum
  transformations:
    - type: CreateAssociationUpdate@1
      targetPath: $.assocUpdates
      targetValueWriteMode: Append
      targetValueKind: Array
      updateKind: CREATE
      originRtIdPath: $.childRtId
      originCkTypeId: Industry.Basic/Machine
      targetRtIdPath: $.parentRtId
      targetCkTypeId: Basic/Tree
      associationRoleId: System/ParentChild
- type: ApplyChanges@2                  # persist entities + associations together
  entityUpdatesPath: $.entityUpdates
  associationUpdatesPath: $.assocUpdates
```

Only create associations on INSERT (guard on `modOperationPath` = 0); `CreateUpdateInfo@1`/`CreateAssociationUpdate@1` read the IDs via `rtIdPath`/`originRtIdPath`/`targetRtIdPath`.

## Common Patterns

### Entity CRUD

The standard CRUD shape is: `GetRtEntitiesByWellKnownName@1` (with `generateInsertOperation: true` to write `rtId`/`modOp` per item) → `ForEach@1` building one `CreateUpdateInfo@1` per item into `$.key.update` → `Flatten@1` the per-item updates into `$.entityUpdates` → `ApplyChanges@2`. See `references/pipeline-examples.md` (example 3) for the full annotated version, and the mandatory-association workflow above when the new entity type requires associations.

### Inter-Pipeline Communication (DataFlow)

Pipelines within the same DataFlow can chain data to each other — even across different adapter instances (e.g., Zenon Adapter → Mesh Adapter). The sender uses `ToPipelineDataEvent@1` with the target pipeline's runtime ID; the receiver uses `FromPipelineDataEvent@1` as its trigger.

```yaml
# Producer pipeline (sends data to consumer)
transformations:
  - type: ToPipelineDataEvent@1
    path: $.sensor
    targetPath: $.input
    targetPipelineRtId: aa0000000000000000000003  # RtId of the consumer pipeline

# Consumer pipeline (receives data)
triggers:
  - type: FromPipelineDataEvent@1
```

Both pipelines must belong to the **same DataFlow** (linked via `System/ParentChild` association). The DataFlow's shared topic exchange routes messages by `targetPipelineRtId`.

**Await-result (synchronous) mode:** set `awaitResult: true` on `ToPipelineDataEvent@1` to send a command and block until the target pipeline finishes, placing its result at `resultTargetPath` (default `$.pipelineResult`). The receiver `FromPipelineDataEvent@1` needs no extra config — it consumes both the fire-and-forget exchange and the command address. Optional `timeoutSeconds` bounds the wait.

```yaml
- type: ToPipelineDataEvent@1
  path: $.request
  targetPath: $.input
  targetPipelineRtId: aa0000000000000000000003
  awaitResult: true
  timeoutSeconds: 30
  resultTargetPath: $.pipelineResult
```

### Dual Store (Archive + MongoDB)

Save high-frequency data to both a CrateDB archive and the entity store. `SaveStreamDataInArchive@1` requires `archiveRtId` pointing at an **Activated** `CkArchive`; backfill missing columns first if upstream events carry only one attribute.

```yaml
# Optional: complete each row's columns from the persistent entity
- type: BackfillFromRtEntity@1
  path: $._updates
  archiveRtId: cc0000000000000000000aa1   # the CkArchive

- type: SaveStreamDataInArchive@1
  path: $._updates
  archiveRtId: cc0000000000000000000aa1   # must be Activated

- type: FilterLatestUpdateInfo@1
  path: $._updates
  targetPath: $._updates

- type: ApplyChanges@2
  entityUpdatesPath: $._updates
```

## Pipeline Validation

When validating a pipeline YAML (user-written or generated), use the **build-time JSON Schema** as the authoritative source. Every OctoMesh adapter generates its own `pipeline-schema.json` at build time, containing all nodes it supports (SDK nodes + adapter-specific nodes).

**Schema locations** (relative to monorepo root):

| Adapter | Schema Path |
|---------|------------|
| Mesh Adapter | `octo-mesh-adapter/bin/DebugL/net10.0/pipeline-schema.json` |
| Zenon Adapter | `octo-plug-zenon/src/Octo.Edge.Adapter.Zenon.WindowsService/bin/DebugL/net10.0/pipeline-schema.json` |
| Simulation Adapter | `octo-sdk/src/Sdk.Plug.Simulation/bin/DebugL/net10.0/pipeline-schema.json` |

**Which schema to use:** Pick the adapter that will execute the pipeline (Mesh Adapter has the richest node set). If it hasn't been built locally, fall back to the node reference docs.

**Validation:** look up each node by its `type` const in `$defs.TriggerNode.oneOf` / `$defs.TransformationNode.oneOf`, then verify all `required` keys are present, every property exists in the node's `properties`, and enum values match. For the extraction commands and fallback rules, read `references/pipeline-schema-guide.md`.

## Pipeline Creation Workflow

1. **Plan the DataFlow** — does this pipeline work alone or chain with others? Group related pipelines under one DataFlow.
2. **Identify the trigger** — manual (`FromExecutePipelineCommand@1`), cron (`FromPipelineTriggerEvent@1` + PipelineTrigger), inter-pipeline (`FromPipelineDataEvent@1`), polling, HTTP, entity-watch, or email.
3. **Plan the data flow and `$.path` names** for each step's input/output; use ForEach for arrays (plan `$.full`/`$.key`).
4. **Research node properties** — read the C# config class for every node before writing it (see "Source Code Research"). Do NOT rely on memory.
5. **Build update operations** with CreateUpdateInfo + CreateAssociationUpdate, **Flatten** before persisting, then **ApplyChanges@2** (use Append to collect).
6. **Persist OutputData** with `SetPipelineExecutionResult@1` if the result must be readable via `GetLatestPipelineExecution`.

For annotated real-world examples covering all these patterns, read `references/pipeline-examples.md`.

## Deploying and Testing Pipelines

After writing pipeline YAML, use the **`octo` skill** to deploy and test it. This skill handles YAML authoring; the `octo` skill handles all operational commands (deployment, execution, status, debugging).

### Typical deployment workflow

1. **Create runtime entities** via `octo-cli -c ImportRt -f <file> -w`:
   - A `System.Communication/DataFlow` entity (logical grouping)
   - A `System.Communication/Pipeline` entity with `ParentChild` association to the DataFlow and `Executes` association to the target Adapter
   - Optionally a `System.Communication/PipelineTrigger` with `ParentChild` to the DataFlow and `Triggers` association to the Pipeline(s)

2. **Deploy the pipeline YAML** — `octo-cli -c DeployPipeline --adapterId <id> --pipelineId <id> --file <yaml-path>`

3. **Verify deployment** — `octo-cli -c GetPipelineStatus --identifier <pipelineId> --json` → confirm state = Deployed

4. **Execute** — `octo-cli -c ExecutePipeline --identifier <pipelineId>` → returns execution ID

5. **Check execution** — `octo-cli -c GetLatestPipelineExecution --identifier <pipelineId> --json` → status, duration, errors

6. **Inspect debug points** — `octo-cli -c GetPipelineDebugPoints --identifier <pipelineId> --executionId <guid> --json` → shows which nodes ran and their data. Debug capture must be **enabled** for a pipeline to record debug points (see toggle below).

7. **Activate triggers** (if using cron) — `octo-cli -c DeployTriggers`

### Pipeline debug toggle (no redeploy)

Enable/disable per-node debug capture on a **live** pipeline without redeploying:

| Operation | Command / REST |
|-----------|----------------|
| Enable/disable debug | `octo-cli -c SetPipelineDebug --identifier <pipelineId> --enabled true|false` (REST `PATCH {tenantId}/v1/pipeline/{id}/debug`) — Mutating |
| Read debug state | `octo-cli -c GetPipelineDebug --identifier <pipelineId> --json` (REST `GET {tenantId}/v1/pipeline/{id}/debug`) — Read-only |

If the adapter is offline, the setting is persisted and applies on the next deploy.

### Reassigning and deploying at the DataFlow level

| Operation | Command | Safety |
|-----------|---------|--------|
| Move pipelines to another adapter | `octo-cli -c MovePipelines --pipelineRtIds <id,id> --targetAdapterRtId <adapterId> [--redeploy] [--yes]` (REST `PATCH {tenantId}/v1/pipeline/move-to-adapter`) | Mutating. Per-pipeline failures do not abort the batch; source and target adapter must share the same CkTypeId. `--redeploy` is best-effort and does not roll the move back on failure |
| Deploy / undeploy a whole DataFlow | `octo-cli -c DeployDataFlow --identifier <dataFlowId>` / `UndeployDataFlow --identifier <dataFlowId>` | Mutating |
| DataFlow status | `octo-cli -c GetDataFlowStatus --identifier <dataFlowId> --json` | Read-only |

### Discovering available nodes at runtime

`octo-cli -c GetPipelineSchema --adapterId <rtId>` returns a JSON Schema (draft/2020-12) of all nodes available on a specific adapter — use it to discover what the target environment supports (e.g. custom plugins). To hand off any operational command, tell the user to invoke `/octo <intent>` (e.g. `/octo deploy this pipeline`).

## Pipeline Troubleshooting

### Silent failures: adapter returns HTTP 200 on error

The Mesh Adapter returns **HTTP 200** for `FromHttpRequest`-triggered pipelines **even when the pipeline fails internally**. The `GetLatestPipelineExecution` may also show `Status: null` and `DurationMs: null` on failure.

> **Status: null does not always mean failure.** For `FromHttpRequest`-triggered executions, the execution tracking may not complete before the HTTP response returns. This means `Status: null` can appear even on a **successful** run. Always verify by checking the actual data (e.g., query the entities that should have been created/updated) rather than relying solely on execution status.

**Always check the adapter log after unexpected results:**

```
logFiles/MeshAdapter.log
```

(Located in `logFiles/MeshAdapter.log` relative to the monorepo root)

### Common error patterns in the adapter log

| Error message | Cause | Fix |
|---------------|-------|-----|
| "Inbound association 'X' has minimum multiplicity of 'One'" | Entity type requires a mandatory association | Run `ck_explorer.py preflight <type>`, add `CreateAssociationUpdate` |
| "Value of origin RtId is null" | Path-based RtId reference resolves to null | Ensure upstream `GetOrCreateRtEntitiesByType@1` or `GetRtEntitiesByWellKnownName@1` writes RtId via `rtIdTargetPath` before this node reads it |
| "Attribute 'X' does not exist at type 'Y'" | Wrong attribute name or casing | Run `ck_explorer.py preflight <type>` for exact names |

### Debugging workflow

1. **Trigger the pipeline** (HTTP, ExecutePipeline, or scheduled)
2. **Check execution:** `octo-cli -c GetLatestPipelineExecution --identifier <pipelineId> --json`
3. **If Status is null:** the pipeline failed — check the adapter log (e.g., `logFiles/MeshAdapter.log`) for `ERROR` entries
4. **Check debug tree:** `octo-cli -c GetPipelineDebugPoints` — nodes missing from the tree never executed (pipeline stopped before reaching them)
5. **The last node in the tree** is usually where the error occurred
6. **Read the handler source code** for the failing node to understand what conditions cause the error — search for the error message text in the handler class

## References

**Priority order** when understanding a node:

1. **C# source code** (ground truth) — config classes for properties/defaults, handlers for behavior. See "Source Code Research".
2. **Pipeline JSON Schema** (auto-generated, authoritative for property names/types/required): `references/pipeline-schema-guide.md`
3. **Reference docs** (hand-maintained summaries, may lag): SDK nodes `references/node-reference-sdk.md`, Mesh Adapter nodes `references/node-reference-mesh.md`
4. **DataContext mechanics** (paths, write modes, field filters, iterations): `references/data-context-guide.md`
5. **Real examples** (annotated pipelines): `references/pipeline-examples.md`

**If there is ANY doubt about a node's properties or behavior, read the source code. Do not guess.**
