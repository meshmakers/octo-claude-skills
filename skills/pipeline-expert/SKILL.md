---
name: pipeline-expert
description: Expert for OctoMesh ETL pipeline YAML — creation, reading, editing, debugging, validation. This skill should be used when the user mentions pipeline YAML, YAML pipeline, pipeline creation, pipeline nodes, node configuration, DataContext, ForEach iteration, ETL pipelines, mesh pipelines, edge pipelines, triggers, transformations, ApplyChanges, CreateUpdateInfo, data mapping, pipeline debugging, pipeline error, data flow, DataFlow, dataflow, pipeline chaining, inter-pipeline communication, PipelineTrigger, pipeline trigger, cron schedule, ToPipelineDataEvent, FromPipelineDataEvent, FromPipelineTriggerEvent, FromExecutePipelineCommand, targetPipelineRtId, GetRtEntities, entity CRUD, association updates, field filters, switch cases, polling pipelines, HTTP triggers, watch entity triggers, scheduled pipeline, cron trigger, email trigger, Zenon integration, SAP integration, EDA processing, email notifications, time series, anomaly detection, AI queries, buffering, webhook, Base64 encoding, logging, debug output, pipeline config lookup, report generation, pipeline schema, pipeline validation, CSV import, Excel import, SFTP upload, file hash, duplicate check, Grafana provisioning, Microsoft Teams, Microsoft Graph, simulation data, OCR, pipeline JSON schema, pipeline example.
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/pipeline-expert/references/*)"
---

# OctoMesh Pipeline Expert

## Overview

OctoMesh pipelines are YAML-defined ETL data flows executed by the mesh adapter (server-side) or edge adapters (device-side). Each pipeline has **triggers** that start execution and **transformations** (an ordered list of nodes) that process data through a shared **DataContext** — a mutable JSON document accessed via JSONPath.

Pipelines handle: entity CRUD, edge-to-mesh synchronization, data import/export, notifications, report generation, AI queries, anomaly detection, and more.

## DataFlows and Pipeline Triggers

A **DataFlow** (`System.Communication/DataFlow`) is a logical grouping of related pipelines that work together as part of a single data processing workflow. It serves as the parent container for Pipeline and PipelineTrigger instances.

> **Migration note:** DataFlow replaces the old `DataPipeline` type from Communication-2. Similarly, `PipelineTrigger` replaces the old `DataPipelineTrigger`. CK migrations `3.0.1→3.0.2` and `3.1.0→3.1.1` handle the rename automatically (`ChangeCkType` transforms). If working with pre-migration data, the CK type IDs are `System.Communication/DataPipeline` → `System.Communication/DataFlow` and `System.Communication/DataPipelineTrigger` → `System.Communication/PipelineTrigger`.

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

**Triggers** define how the pipeline starts: polling interval, HTTP request, entity change watch, event hub message, explicit command, or email.

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
| `ForEach@1` | Iterate array with child context (full/key/merge) |
| `For@1` | Execute N times |
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

### Buffering (Edge)

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

**CRITICAL:** The `RtId` field is **only populated when you provide a static `rtId` value** in the CreateUpdateInfo configuration. When using `generateRtId: true`, the RtId is generated internally at `ApplyChanges` time and is **NOT available** in the EntityUpdateInfo output for path-based references.

**Consequence for associations:** When using `CreateUpdateInfo@1` with `generateRtId: true`, you MUST use static `rtId` values instead, then reference those same values as static `originRtId`/`targetRtId` in `CreateAssociationUpdate`. Path-based references (`originRtIdPath`/`targetRtIdPath`) DO work with nodes that expose RtIds via `rtIdTargetPath` — specifically `GetOrCreateRtEntitiesByType@1` and `GetRtEntitiesByWellKnownName@1`. These nodes write the resolved or generated RtId to a path you can reference downstream.

## Mandatory Associations

Some CK types have **mandatory outbound associations** (multiplicity = ONE). Creating an entity of such a type WITHOUT the required association will fail at `ApplyChanges` time with: `"Inbound association 'X' has minimum multiplicity of 'One'"`.

**Pre-flight check:** Always run `ck_explorer.py preflight <type>` before writing CreateUpdateInfo for a new entity type. If the output shows mandatory associations, you MUST include `CreateAssociationUpdate@1` nodes in the same `ApplyChanges@2` call.

**Common mandatory association:** `System/ParentChild` — types like Machine, TreeNode, and many domain entities require a parent. If the parent doesn't exist yet, create it in the same pipeline.

**Pattern for creating entities with mandatory associations:**

```yaml
# 1. Create parent (with static rtId)
- type: CreateUpdateInfo@1
  targetPath: $.entityUpdates
  targetValueWriteMode: Overwrite
  targetValueKind: Array
  updateKind: INSERT
  rtId: "aa00000000000000parent01"
  ckTypeId: Basic/Tree
  attributeUpdates:
    - attributeName: name
      attributeValueType: String
      value: "My Container"

# 2. Create child (with static rtId)
- type: CreateUpdateInfo@1
  targetPath: $.entityUpdates
  targetValueWriteMode: Append
  targetValueKind: Array
  updateKind: INSERT
  rtId: "aa00000000000000child001"
  ckTypeId: Industry.Basic/Machine
  attributeUpdates:
    - attributeName: name
      attributeValueType: String
      value: "My Machine"
    - attributeName: machineState
      attributeValueType: Enum
      value: 1

# 3. Create mandatory ParentChild association
- type: CreateAssociationUpdate@1
  targetPath: $.assocUpdates
  targetValueWriteMode: Append
  targetValueKind: Array
  updateKind: CREATE
  originRtId: "aa00000000000000child001"
  originCkTypeId: Industry.Basic/Machine
  targetRtId: "aa00000000000000parent01"
  targetCkTypeId: Basic/Tree
  associationRoleId: System/ParentChild

# 4. Persist everything together
- type: ApplyChanges@2
  entityUpdatesPath: $.entityUpdates
  associationUpdatesPath: $.assocUpdates
```

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

Pipelines within the same DataFlow can chain data to each other — even across different adapters (e.g., edge → mesh). The sender uses `ToPipelineDataEvent@1` with the target pipeline's runtime ID; the receiver uses `FromPipelineDataEvent@1` as its trigger.

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
| Zenon Edge Adapter | `octo-plug-zenon/src/Octo.Edge.Adapter.Zenon.WindowsService/bin/DebugL/net10.0/pipeline-schema.json` |
| Simulation Adapter | `octo-sdk/src/Sdk.Plug.Simulation/bin/DebugL/net10.0/pipeline-schema.json` |

**Which schema to use:** Pick the adapter that will execute the pipeline. The mesh adapter schema is the most common choice for server-side pipelines. If the adapter hasn't been built locally, fall back to the node reference docs.

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
5. **Define DataContext paths** — Plan `$.path` names for each step's input and output
6. **Handle iterations** — Use ForEach for arrays; plan `$.full`/`$.key` access patterns
7. **Build update operations** — Use CreateUpdateInfo + CreateAssociationUpdate for entity CRUD
8. **Persist with ApplyChanges@2** — Always Flatten updates before applying; use Append for collecting

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

The mesh adapter returns **HTTP 200** for `FromHttpRequest`-triggered pipelines **even when the pipeline fails internally**. The `GetLatestPipelineExecution` may also show `Status: null` and `DurationMs: null` on failure.

**Always check the adapter log after unexpected results:**

```
logFiles/MeshAdapter.log
```

(Located in the meshmakers development directory, e.g., `C:/dev/meshmakers/logFiles/MeshAdapter.log`)

### Common error patterns in the adapter log

| Error message | Cause | Fix |
|---------------|-------|-----|
| "Inbound association 'X' has minimum multiplicity of 'One'" | Entity type requires a mandatory association | Run `ck_explorer.py preflight <type>`, add `CreateAssociationUpdate` |
| "Value of origin RtId is null" | Path-based RtId reference resolves to null | Use static `originRtId`/`targetRtId` instead of path references |
| "Attribute 'X' does not exist at type 'Y'" | Wrong attribute name or casing | Run `ck_explorer.py preflight <type>` for exact names |

### Debugging workflow

1. **Trigger the pipeline** (HTTP, ExecutePipeline, or scheduled)
2. **Check execution:** `octo-cli -c GetLatestPipelineExecution --identifier <pipelineId> --json`
3. **If Status is null:** the pipeline failed — check `logFiles/MeshAdapter.log` for `ERROR` entries
4. **Check debug tree:** `octo-cli -c GetPipelineDebugPoints` — nodes missing from the tree never executed (pipeline stopped before reaching them)
5. **The last node in the tree** is usually where the error occurred

## References

- **SDK nodes** (control flow, transforms, extracts, loads, buffering, simulation): `references/node-reference-sdk.md`
- **Mesh adapter nodes** (entity CRUD, triggers, domain-specific): `references/node-reference-mesh.md`
- **DataContext mechanics** (paths, write modes, field filters, iterations): `references/data-context-guide.md`
- **Real examples** (annotated pipelines from deployments): `references/pipeline-examples.md`
- **Pipeline JSON Schema** (authoritative property reference, validation workflow): `references/pipeline-schema-guide.md`
