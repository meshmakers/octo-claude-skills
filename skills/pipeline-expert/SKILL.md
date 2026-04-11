---
name: pipeline-expert
description: Expert for OctoMesh ETL pipeline YAML — creation, reading, editing, debugging, validation. This skill should be used when the user mentions pipeline YAML, YAML pipeline, pipeline creation, pipeline nodes, node configuration, DataContext, ForEach iteration, ETL pipelines, adapter pipelines, triggers, transformations, ApplyChanges, CreateUpdateInfo, data mapping, pipeline debugging, pipeline error, data flow, DataFlow, dataflow, pipeline chaining, inter-pipeline communication, cross-adapter communication, PipelineTrigger, pipeline trigger, cron schedule, ToPipelineDataEvent, FromPipelineDataEvent, FromPipelineTriggerEvent, FromExecutePipelineCommand, targetPipelineRtId, GetRtEntities, entity CRUD, association updates, field filters, switch cases, polling pipelines, HTTP triggers, watch entity triggers, scheduled pipeline, cron trigger, email trigger, Zenon integration, SAP integration, EDA processing, email notifications, time series, anomaly detection, AI queries, buffering, webhook, Base64 encoding, logging, debug output, pipeline config lookup, report generation, pipeline schema, pipeline validation, CSV import, Excel import, SFTP upload, file hash, duplicate check, Grafana provisioning, Microsoft Teams, Microsoft Graph, simulation data, OCR, pipeline JSON schema, pipeline example.
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/pipeline-expert/references/*)"
  - "Grep"
  - "Glob"
  - "Read"
---

# OctoMesh Pipeline Expert

## Overview

OctoMesh pipelines are YAML-defined ETL data flows executed by adapters. Each pipeline has **triggers** that start execution and **transformations** (an ordered list of nodes) that process data through a shared **DataContext** — a mutable JSON document accessed via JSONPath.

An **Adapter** (`System.Communication/Adapter`) is a unified runtime that executes pipelines. Different adapter implementations exist (Mesh Adapter, Zenon Adapter, Simulation Adapter, etc.) but they all share the same CK type and pipeline execution model. Each adapter registers the pipeline nodes it supports — SDK-shared nodes plus adapter-specific ones.

Pipelines handle: entity CRUD, cross-adapter data synchronization, data import/export, notifications, report generation, AI queries, anomaly detection, and more.

## Source Code Research (MANDATORY)

**NEVER guess how a pipeline node behaves.** When you are unsure about a node's properties, behavior, defaults, or edge cases, you MUST read the actual C# source code before answering or generating YAML. The reference docs in this skill are summaries — the source code is the ground truth.

### When to Research

You MUST read source code when:
- You are **not 100% certain** about a node's available properties or their exact names
- You need to understand **what a node actually does** at runtime (read the handler)
- You need to know **default values** for optional properties
- A user asks **why a node behaves a certain way** or reports unexpected behavior
- You are writing YAML for a node you haven't used recently in this conversation
- You encounter a node name you don't recognize or that isn't in the reference docs

### Where Node Source Code Lives

Pipeline nodes are split across two repositories in the monorepo. All paths below are **relative to the monorepo root** (the parent directory containing `octo-sdk`, `octo-mesh-adapter`, etc.):

**SDK nodes** (ForEach, If, Switch, SetPrimitiveValue, For, SelectByPath, etc.):
```
octo-sdk/src/Sdk.Common/EtlDataPipeline/Nodes/
├── Control/       (ForEach, If, Switch, For, SelectByPath)
├── Extracts/      (SetPrimitiveValue, SetArrayOfPrimitiveValues, WriteJson)
├── Transforms/    (Concat, FormatString, TransformString, Hash, Math, etc.)
├── Triggers/      (FromPolling, FromPipelineDataEvent)
├── Loads/         (ToPipelineDataEvent, ToWebhook)
└── Buffering/     (BufferData, BufferRetrievalNode)
```

**Mesh Adapter nodes** (GetRtEntitiesByType, CreateUpdateInfo, ApplyChanges, etc.):
- **Configuration classes** (properties, defaults, validation):
  ```
  octo-mesh-adapter/src/MeshNodes.Sdk/
  ├── Extract/     (GetRtEntitiesByType, GetRtEntitiesById, GetOrCreate, etc.)
  ├── Transform/   (CreateUpdateInfo, CreateAssociationUpdate, CheckDuplicate, etc.)
  ├── Load/        (ApplyChanges, SaveInTimeSeries, SendEMail, SftpUpload, etc.)
  └── Trigger/     (FromWatchRtEntity, FromHttpRequest, FromEmail, etc.)
  ```
- **Handler classes** (execution logic — what the node actually does):
  ```
  octo-mesh-adapter/src/MeshAdapter.Sdk/Nodes/
  ├── Extract/
  ├── Transform/
  ├── Load/
  └── Trigger/
  ```

**Finding the monorepo root:** The monorepo root is the parent directory of this plugin's repository. Use `../` relative to the plugin working directory, or search upward for a directory containing both `octo-sdk/` and `octo-mesh-adapter/`.

### Naming Conventions

| What | Pattern | Example |
|------|---------|---------|
| Config class | `[NodeName]NodeConfiguration.cs` | `CheckDuplicateNodeConfiguration.cs` |
| Config class (versioned) | `[NodeName]NodeConfiguration[N].cs` | `ApplyChangesNodeConfiguration2.cs` |
| Handler class | `[NodeName]Node.cs` | `CheckDuplicateNode.cs` |
| Handler class (versioned) | `[NodeName]Node[N].cs` | `ApplyChangesNode2.cs` |
| SDK nodes | Config + handler in same file | `ForEachNode.cs` |
| Config attribute | `[NodeName("DisplayName", Version)]` | `[NodeName("CheckDuplicate", 1)]` |
| Handler attribute | `[NodeConfiguration(typeof(ConfigClass))]` | `[NodeConfiguration(typeof(CheckDuplicateNodeConfiguration))]` |

### How to Research a Node

**Step 1 — Find the source file** (use Grep and Glob from the monorepo root):
```
# Search by node name (e.g., "CheckDuplicate")
Grep for: NodeName\("CheckDuplicate"
  in: octo-mesh-adapter/src/   (mesh adapter nodes)
  or: octo-sdk/src/            (SDK nodes)

# Or find the file by naming convention
Glob for: **/CheckDuplicate*Configuration*.cs
  in: octo-mesh-adapter/src/MeshNodes.Sdk/
```

**Step 2 — Read the configuration class** to learn:
- All available properties and their C# types
- Default values
- Required vs optional properties
- XML doc comments explaining each property

**Step 3 — Read the handler class** to learn:
- What the node actually does at runtime
- How it reads from and writes to the DataContext
- Error conditions and edge cases
- How properties interact with each other

### Quick Lookup Examples

All paths below are relative to the monorepo root:

```
# Find where a specific node is defined
Grep pattern: NodeName\("CreateUpdateInfo"
Path: octo-mesh-adapter/src/

# If not found in mesh-adapter, search the SDK
Grep pattern: NodeName\("CreateUpdateInfo"
Path: octo-sdk/src/

# Find all available nodes for a category
Glob pattern: **/*NodeConfiguration*.cs
Path: octo-mesh-adapter/src/MeshNodes.Sdk/Transform/

# Find the handler to understand runtime behavior
Glob pattern: **/CheckDuplicateNode.cs
Path: octo-mesh-adapter/src/MeshAdapter.Sdk/
```

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
- Cron format: `minute hour dayOfMonth month dayOfWeek year` (6 fields)

**Entity relationships:**
```
DataFlow
  ├── Pipeline (child, via ParentChild) ── executes on ── Adapter
  └── PipelineTrigger (child, via ParentChild) ── triggers ── Pipeline(s)
```

## Pipeline YAML Structure

```yaml
triggers:
  - type: NodeType@Version
    # trigger-specific properties

transformations:
  - type: NodeType@Version
    # node-specific properties
    # control flow nodes nest child nodes:
    transformations:
      - type: ChildNode@Version
```

**Triggers** define how the pipeline starts: polling interval, HTTP request, entity change watch, event hub message, explicit command, or email. Each trigger type populates the DataContext with different initial paths — see `references/data-context-guide.md` "Trigger DataContext Placement" for the full table. Key examples:
- `FromHttpRequest@1`: body at `$.body`, query params at `$.query`, files at `$.files`
- `FromWatchRtEntity@1`: changed entity at `$.Document`
- `FromExecutePipelineCommand@1` / `FromPipelineTriggerEvent@1`: empty context

**Transformations** define the processing steps. Each node reads from and writes to the DataContext. Control flow nodes (ForEach, If, Switch) nest child transformations.

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

> **For@1 is different:** For@1 deep-clones the parent context directly — it does NOT create `$.full`/`$.key` paths. Access data at the same paths as the parent (e.g., `$.body.count`, not `$.full.body.count`). Its `count` is static only (no `countPath`). See `references/data-context-guide.md` for a full comparison table.

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

### Triggers

| Node | Purpose |
|------|---------|
| `FromPolling@1` | Poll at interval (e.g., `00:05:00`) |
| `FromHttpRequest@1` | HTTP endpoint (method + path) |
| `FromWatchRtEntity@1` | Entity change stream (Insert/Update/Delete) |
| `FromPipelineDataEvent@1` | Receive data from another pipeline in the same DataFlow |
| `FromExecutePipelineCommand@1` | Manual execution command (via service or UI) |
| `FromPipelineTriggerEvent@1` | Scheduled execution via PipelineTrigger entity (cron) |
| `FromSendNotification@1` | Notification service message |
| `FromEmail@1` | Incoming email via IMAP |
| `FromMicrosoftGraph@1` | Poll Microsoft Teams channels via Graph API |

### Control Flow

| Node | Purpose |
|------|---------|
| `ForEach@1` | Iterate array with child context (`$.full`/`$.key`/merge) |
| `For@1` | Execute N times (deep-clones parent context, static count only — see data-context-guide.md) |
| `If@1` | Conditional (Equal, Contains, GreaterThan, RegexMatch, etc.) |
| `Switch@1` | Multi-branch by value (supports array case values) |
| `SelectByPath@1` | Select and transform multiple paths |

### Extract (Data In)

| Node | Purpose |
|------|---------|
| `SetPrimitiveValue@1` | Set static or dynamic value |
| `SetArrayOfPrimitiveValues@1` | Set array of values |
| `WriteJson@1` | Inject raw JSON string |
| `GetRtEntitiesByType@1` | Query entities by CK type |
| `GetRtEntitiesById@1` | Fetch entities by ID |
| `GetRtEntitiesByWellKnownName@1` | Lookup by name, enrich with IDs |
| `GetOrCreateRtEntitiesByType@1` | Find or generate new ID |
| `GetAssociationTargets@1` | Traverse associations |
| `GetQueryById@1` | Execute saved query |
| `GetPipelineConfigByWellKnownName@1` | Load global config |
| `GetPipelineConfigByCkTypeId@1` | Load configs by CK type |
| `GetNotificationTemplate@1` | Load notification template |
| `EnrichWithMongoData@1` | Enrich updates with current DB state |

### Transform

| Node | Purpose |
|------|---------|
| `CreateUpdateInfo@1` | Build entity Insert/Update/Delete operations |
| `CreateAssociationUpdate@1` | Build association Create/Delete operations |
| `CreateFileSystemUpdate@1` | Create file system items |
| `DataMapping@1` | Map values (e.g., int→string enum) |
| `Concat@1` | Concatenate string parts |
| `FormatString@1` | Format with `{$.path}` placeholders |
| `TransformString@1` | String ops (Trim, ToUpper, Substring, etc.) |
| `Flatten@1` | Flatten nested arrays |
| `Project@1` | Include/exclude fields |
| `Join@1` | Inner join two arrays |
| `Math@1` | Add, Subtract, Multiply, Divide, Round |
| `DateTime@1` | Now, StartOfDay, AddDays/Hours/Minutes/Seconds, DaysBetween, Format, CombineDateTime, ExtractDate/Time |
| `SumAggregation@1` | Weighted sum with optional filter |
| `FilterLatestUpdateInfo@1` | Deduplicate entity updates |
| `Distinct@1` | Remove duplicates by property |
| `PlaceholderReplace@1` | Replace `${name}` in strings |
| `Base64Encode@1` / `Base64Decode@1` | Base64 encoding/decoding |
| `Hash@1` | Cryptographic hash (MD5–SHA512) |
| `ConvertDataType@1` | Type conversion |
| `Map@1` | Pivot/transpose arrays |
| `LinearScaler@1` | Linear value scaling |
| `Logger@1` / `PrintDebug@1` | Log message / print data context |
| `ExecuteCSharp@1` | Dynamic C# execution |
| `MakeHttpRequest@1` | HTTP request (GET/POST/PUT/DELETE) |
| `AnthropicAiQuery@1` | Claude AI document analysis |
| `PdfOcrExtraction@1` | PDF text extraction via OCR |
| `QueryResultToMarkdownTable@1` | Query results → Markdown |
| `StatisticalAnomalyDetection@1` | Z-Score/IQR anomaly detection |
| `MachineLearningAnomalyDetection@1` | ML.NET spike/change detection |
| `ImportFromExcel@1` | Excel data import |
| `ImportFromCsv@1` | Import tabular data from CSV files |
| `MinMax@1` | Find min/max in array |
| `CheckDuplicate@1` | Check if entity with matching attribute already exists |
| `ComputeFileHash@1` | SHA-256 hash of base64 file data |
| `ReplyToTeamsChannel@1` | Send message card to Teams channel via webhook |
| `Simulation@1` | Generate simulated data values (Bogus-based) |

### Load (Data Out)

| Node | Purpose |
|------|---------|
| `ApplyChanges@1` | Apply entity updates to MongoDB |
| `ApplyChanges@2` | Apply entity + association updates (preferred) |
| `SaveInTimeSeries@1` | Save to CrateDB time series |
| `ToPipelineDataEvent@1` | Send data to another pipeline in the same DataFlow (requires `targetPipelineRtId`) |
| `ToWebhook@1` | HTTP POST to external endpoint |
| `SendEMail@1` | Send email (Markdown → HTML) |
| `GenerateAndStoreReport@1` | Generate and store report |
| `SftpUpload@1` | Upload file to SFTP server |
| `GrafanaProvisionTenant@1` | Provision Grafana org and datasource for tenant |
| `GrafanaDeprovisionTenant@1` | Deprovision Grafana org for tenant |

### Buffering

| Node | Purpose |
|------|---------|
| `BufferData@1` | Buffer with time-based flush |
| `BufferRetrievalNode@1` | Retrieve buffered data |

### Domain-Specific

SAP nodes (SapLogin, GetProductionOrderList, GetProductionOrderDetails), Zenon nodes (SetZenonVariables, FromZenonAml, ReadZenonAmlMessages), EDA energy nodes (EdaParseMessage, EdaStartProcess, etc.), Microsoft Teams nodes (FromMicrosoftGraph, ReplyToTeamsChannel), and Grafana nodes (GrafanaProvisionTenant, GrafanaDeprovisionTenant) are documented in `references/node-reference-mesh.md`.

For full property documentation, read `references/node-reference-sdk.md` and `references/node-reference-mesh.md`.

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

When `CreateUpdateInfo@1` writes to the DataContext, it produces this JSON structure:

```json
{
  "RtEntity": {
    "RtId": "cc000000000000000000bb01",
    "RtChangedDateTime": "2026-04-10T22:17:12Z",
    "CkTypeId": "Industry.Basic/Machine",
    "Attributes": { "Name": "...", "MachineState": 0 }
  },
  "RtId": "cc000000000000000000bb01",
  "CkTypeId": "Industry.Basic/Machine",
  "ModOption": 0
}
```

**Note:** The `RtId` field is only populated when either a static `rtId` is provided or the RtId was resolved/generated by an upstream node (like `GetOrCreateRtEntitiesByType@1`). Do NOT use `generateRtId: true` in `CreateUpdateInfo` — use `GetOrCreateRtEntitiesByType@1` or `GetRtEntitiesByWellKnownName@1` to obtain IDs first.

## Mandatory Associations

Some CK types have **mandatory outbound associations** (multiplicity = ONE). Creating an entity of such a type WITHOUT the required association will fail at `ApplyChanges` time with: `"Inbound association 'X' has minimum multiplicity of 'One'"`.

**Pre-flight check:** Always run `ck_explorer.py preflight <type>` before writing CreateUpdateInfo for a new entity type. If the output shows mandatory associations, you MUST include `CreateAssociationUpdate@1` nodes in the same `ApplyChanges@2` call.

**Common mandatory association:** `System/ParentChild` — types like Machine, TreeNode, and many domain entities require a parent.

### The intended workflow for creating entities with associations

The correct pattern uses `GetOrCreateRtEntitiesByType@1` to resolve/generate IDs, then `CreateUpdateInfo@1` and `CreateAssociationUpdate@1` reference those IDs via paths:

```yaml
# 1. Resolve or create the parent entity (provides RtId via rtIdTargetPath)
- type: GetOrCreateRtEntitiesByType@1
  ckTypeId: Basic/Tree
  fieldFilters:
    - attributePath: RtWellKnownName
      comparisonValue: "My Container"
  rtIdTargetPath: $.parentRtId
  modOperationPath: $.parentModOp

# 2. Resolve or create the child entity
- type: GetOrCreateRtEntitiesByType@1
  ckTypeId: Industry.Basic/Machine
  fieldFilters:
    - attributePath: RtWellKnownName
      comparisonValue: "My Machine"
  rtIdTargetPath: $.childRtId
  modOperationPath: $.childModOp

# 3. Create entity update for the child (uses RtId from step 2)
- type: CreateUpdateInfo@1
  targetPath: $.entityUpdates
  targetValueWriteMode: Append
  targetValueKind: Array
  updateKindPath: $.childModOp
  rtIdPath: $.childRtId
  ckTypeId: Industry.Basic/Machine
  rtWellKnownNamePath: $.machineName
  attributeUpdates:
    - attributeName: name
      attributeValueType: String
      valuePath: $.machineName
    - attributeName: machineState
      attributeValueType: Enum
      value: 1

# 4. Create mandatory ParentChild association (only on INSERT)
- type: If@1
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

# 5. Persist everything together
- type: ApplyChanges@2
  entityUpdatesPath: $.entityUpdates
  associationUpdatesPath: $.assocUpdates
```

**Key points:**
- `GetOrCreateRtEntitiesByType@1` provides the RtId (existing or newly generated) via `rtIdTargetPath`
- `CreateUpdateInfo@1` reads that RtId via `rtIdPath` — do NOT use `generateRtId: true`
- `CreateAssociationUpdate@1` reads RtIds via `originRtIdPath`/`targetRtIdPath`
- Only create associations on INSERT (check `modOperationPath` value = 0)

## Common Patterns

### Entity CRUD

Query entities, create update operations, apply to database:

```yaml
- type: GetRtEntitiesByWellKnownName@1
  ckTypeId: MyModel/MyType
  path: $.items[*]
  wellKnownNamePath: $.Name
  rtIdTargetPath: $.rtId
  modOperationPath: $.modOp
  generateInsertOperation: true

- type: ForEach@1
  iterationPath: $.items
  targetPath: $.updates
  transformations:
    - type: CreateUpdateInfo@1
      targetPath: $.key.update
      updateKindPath: $.key.modOp
      rtIdPath: $.key.rtId
      ckTypeId: MyModel/MyType
      attributeUpdates:
        - attributeName: Name
          attributeValueType: String
          valuePath: $.key.Name

- type: Flatten@1
  path: $.updates[*].update
  targetPath: $.entityUpdates

- type: ApplyChanges@2
  entityUpdatesPath: $.entityUpdates
```

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

### Dual Store (Time Series + MongoDB)

Save high-frequency data to both time series and entity store:

```yaml
- type: SaveInTimeSeries@1
  path: $._updates

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
| EDA Adapter | `octo-adapter-eda/bin/DebugL/net10.0/pipeline-schema.json` |
| Zenon Adapter | `octo-plug-zenon/src/Octo.Edge.Adapter.Zenon.WindowsService/bin/DebugL/net10.0/pipeline-schema.json` |
| Simulation Adapter | `octo-sdk/src/Sdk.Plug.Simulation/bin/DebugL/net10.0/pipeline-schema.json` |

**Which schema to use:** Pick the adapter implementation that will execute the pipeline. The Mesh Adapter schema is the most common choice as it has the richest set of nodes. If the adapter hasn't been built locally, fall back to the node reference docs.

**Validation steps:**
1. **Look up each node** by its `type` value (e.g., `CheckDuplicate@1`) in the schema's `$defs.TriggerNode.oneOf` or `$defs.TransformationNode.oneOf`.
2. **Check required properties** — the `required` array lists mandatory keys.
3. **Check property names** — any property not in the schema's `properties` object is invalid.
4. **Check enum values** — enum-typed properties list valid values in their `$defs` entry.

For schema structure details, extraction commands, and fallback rules, read `references/pipeline-schema-guide.md`.

## Pipeline Creation Workflow

1. **Plan the DataFlow** — Will this pipeline work alone or chain with others? If chaining, group all related pipelines under a single DataFlow entity.
2. **Identify the trigger** — What starts this pipeline? Manual command (`FromExecutePipelineCommand@1`), cron schedule (`FromPipelineTriggerEvent@1` + PipelineTrigger entity), data from another pipeline (`FromPipelineDataEvent@1`), polling, HTTP, entity change watch, or email?
3. **Plan the data flow** — What data comes in? What entities need to be read/created/updated?
4. **Choose nodes** — Select from the node reference tables above
5. **Research node properties** — For every node you plan to use, read the C# configuration class to confirm exact property names, types, and defaults. Do NOT rely on memory alone. See "Source Code Research" section.
6. **Define DataContext paths** — Plan `$.path` names for each step's input and output
7. **Handle iterations** — Use ForEach for arrays; plan `$.full`/`$.key` access patterns
8. **Build update operations** — Use CreateUpdateInfo + CreateAssociationUpdate for entity CRUD
9. **Persist with ApplyChanges@2** — Always Flatten updates before applying; use Append for collecting

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

6. **Inspect debug points** — `octo-cli -c GetPipelineDebugPoints --identifier <pipelineId> --executionId <guid> --json` → shows which nodes ran and their data

7. **Activate triggers** (if using cron) — `octo-cli -c DeployTriggers`

### Discovering available nodes at runtime

`octo-cli -c GetPipelineSchema --adapterId <rtId>` returns a JSON Schema (draft/2020-12) that describes all pipeline nodes available on a specific adapter. This complements the build-time schema files — use it when you need to discover what's available in the target environment, especially if the adapter has custom plugins loaded.

To hand off to the `octo` skill for any of these operational commands, tell the user to invoke `/octo <their intent>` (e.g., `/octo deploy this pipeline`, `/octo run pipeline X`).

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

**Priority order** — when you need to understand a node, use sources in this order:

1. **C# source code** (ground truth) — configuration classes for properties/defaults, handler classes for behavior. See "Source Code Research" section above.
2. **Pipeline JSON Schema** (auto-generated from source) — authoritative for property names, types, required fields: `references/pipeline-schema-guide.md`
3. **Reference docs** (hand-maintained summaries) — useful for quick lookups but may lag behind the source:
   - SDK nodes: `references/node-reference-sdk.md`
   - Mesh Adapter nodes: `references/node-reference-mesh.md`
4. **DataContext mechanics** (paths, write modes, field filters, iterations): `references/data-context-guide.md`
5. **Real examples** (annotated pipelines from deployments): `references/pipeline-examples.md`

**If there is ANY doubt about a node's properties or behavior, read the source code. Do not guess.**
