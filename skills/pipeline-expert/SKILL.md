---
name: pipeline-expert
description: Expert for OctoMesh ETL pipeline YAML — creation, reading, editing, debugging, validation. This skill should be used when the user mentions pipeline YAML, YAML pipeline, pipeline creation, pipeline nodes, node configuration, DataContext, ForEach iteration, ETL pipelines, mesh pipelines, edge pipelines, triggers, transformations, ApplyChanges, CreateUpdateInfo, data mapping, pipeline debugging, pipeline error, data flow, ToPipelineDataEvent, FromPipelineDataEvent, GetRtEntities, entity CRUD, association updates, field filters, switch cases, polling pipelines, HTTP triggers, watch entity triggers, scheduled pipeline, cron trigger, email trigger, Zenon integration, SAP integration, EDA processing, email notifications, time series, anomaly detection, AI queries, buffering, webhook, Base64 encoding, logging, debug output, pipeline config lookup, report generation, pipeline schema, pipeline validation, CSV import, Excel import, SFTP upload, file hash, duplicate check, Grafana provisioning, Microsoft Teams, Microsoft Graph, simulation data, OCR, pipeline JSON schema, pipeline example.
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/pipeline-expert/references/*)"
---

# OctoMesh Pipeline Expert

## Overview

OctoMesh pipelines are YAML-defined ETL data flows executed by the mesh adapter (server-side) or edge adapters (device-side). Each pipeline has **triggers** that start execution and **transformations** (an ordered list of nodes) that process data through a shared **DataContext** — a mutable JSON document accessed via JSONPath.

Pipelines handle: entity CRUD, edge-to-mesh synchronization, data import/export, notifications, report generation, AI queries, anomaly detection, and more.

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
| `FromPipelineDataEvent@1` | Event hub message (edge-mesh communication) |
| `FromExecutePipelineCommand@1` | Explicit service command |
| `FromPipelineTriggerEvent@1` | Scheduled/event trigger |
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
| `ToPipelineDataEvent@1` | Publish to event hub |
| `ToWebhook@1` | HTTP POST to external endpoint |
| `SendEMail@1` | Send email (Markdown → HTML) |
| `SendNotification@1` | Send notification via bot service |
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

### Edge-to-Mesh Communication

Send data from edge to mesh (or vice versa) via the distributed event hub:

```yaml
# Edge side: send to mesh
- type: ToPipelineDataEvent@1

# Mesh side: receive from edge
triggers:
  - type: FromPipelineDataEvent@1
```

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

When validating a pipeline YAML (user-written or generated), use the **build-time JSON Schema** as the authoritative source:

1. **Locate the schema** at `octo-mesh-adapter/bin/DebugL/net10.0/pipeline-schema.json` (relative to monorepo root). If absent (adapter not built), fall back to the node reference docs.
2. **Look up each node** by its `type` value (e.g., `CheckDuplicate@1`) in the schema's `$defs.TriggerNode.oneOf` or `$defs.TransformationNode.oneOf`.
3. **Check required properties** — the `required` array lists mandatory keys.
4. **Check property names** — any property not in the schema's `properties` object is invalid.
5. **Check enum values** — enum-typed properties list valid values in their `$defs` entry.

For schema structure details, extraction commands, and fallback rules, read `references/pipeline-schema-guide.md`.

## Pipeline Creation Workflow

1. **Identify the trigger** — What starts this pipeline? (poll, HTTP, entity change, event, command)
2. **Plan the data flow** — What data comes in? What entities need to be read/created/updated?
3. **Choose nodes** — Select from the node reference tables above
4. **Define DataContext paths** — Plan `$.path` names for each step's input and output
5. **Handle iterations** — Use ForEach for arrays; plan `$.full`/`$.key` access patterns
6. **Build update operations** — Use CreateUpdateInfo + CreateAssociationUpdate for entity CRUD
7. **Persist with ApplyChanges@2** — Always Flatten updates before applying; use Append for collecting

For annotated real-world examples covering all these patterns, read `references/pipeline-examples.md`.

## References

- **SDK nodes** (control flow, transforms, extracts, loads, buffering, simulation): `references/node-reference-sdk.md`
- **Mesh adapter nodes** (entity CRUD, triggers, domain-specific): `references/node-reference-mesh.md`
- **DataContext mechanics** (paths, write modes, field filters, iterations): `references/data-context-guide.md`
- **Real examples** (annotated pipelines from deployments): `references/pipeline-examples.md`
- **Pipeline JSON Schema** (authoritative property reference, validation workflow): `references/pipeline-schema-guide.md`
