# Mesh Adapter Node Reference

Nodes provided by the **Mesh Adapter** (`octo-mesh-adapter`) — one of several adapter implementations sharing the unified `System.Communication/Adapter` CK type. These nodes are available on any adapter that includes the Mesh Adapter SDK. Use `NodeName@Version` syntax in YAML (e.g., `GetRtEntitiesByType@1`).

## Extract Nodes

### GetRtEntitiesByType@1

Retrieve runtime entities by CK type ID.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ckTypeId` | string | optional | CK type ID (e.g., `Industry.Basic/Machine`) |
| `ckTypeIdPath` | string | optional | JSONPath to CK type ID |
| `skip` | int | optional | Number of items to skip |
| `take` | int | optional | Number of items to take |
| `fieldFilters` | array | optional | Field filter conditions |
| `sortOrders` | array | optional | Sort order specifications |
| `targetPath` | string | required | Where to store results |
| `documentMode` | enum | Extend | Extend/Replace |
| `targetValueKind` | enum | Simple | Simple/Array |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |

Each `sortOrders` entry has `attributeName` (the attribute to sort by — **not** `attributePath`) and `sortOrder` (`Ascending`/`Descending`). `GetAssociationTargets@1` uses the same `SortOrderDto` shape.

```yaml
- type: GetRtEntitiesByType@1
  ckTypeId: Industry.Basic/Machine
  targetPath: $.machines
  take: 100
  fieldFilters:
    - attributePath: Status
      operator: Equals
      comparisonValue: Active
  sortOrders:
    - attributeName: CreatedAt      # attributeName, not attributePath
      sortOrder: Descending
```

### GetRtEntitiesById@1

Retrieve specific entities by their IDs.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ckTypeId` | string | optional | CK type ID |
| `ckTypeIdPath` | string | optional | JSONPath to CK type ID |
| `rtIds` | array | optional | Collection of runtime IDs |
| `rtIdsPath` | string | optional | JSONPath to runtime IDs |
| `skip` | int | optional | Skip count |
| `take` | int | optional | Take count |
| `fieldFilters` | array | optional | Field filters |
| `targetPath` | string | required | Where to store results |

```yaml
- type: GetRtEntitiesById@1
  ckTypeId: Industry.Basic/Machine
  rtIdsPath: $.machineIds
  targetPath: $.machines
```

### GetRtEntitiesByWellKnownName@1

Look up entities by well-known name. Enriches source data with matching entity IDs and optionally generates insert operations for missing entities.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ckTypeId` | string | optional | CK type ID |
| `ckTypeIdPath` | string | optional | JSONPath to CK type ID |
| `path` | string | required | Source data path (applies to each item) |
| `wellKnownNamePath` | string | required | Path to well-known name in source |
| `rtIdTargetPath` | string | `$.rtId` | Where to write found RtId |
| `ckTypeIdTargetPath` | string | `$.ckTypeId` | Where to write CkTypeId |
| `modOperationPath` | string | `$.modOperation` | Where to write mod operation (0=Insert, 1=Update) |
| `generateInsertOperation` | bool | false | Generate Insert op if entity not found |
| `attributeTargetPath` | string | optional | Path to write entity attributes as dictionary |

```yaml
- type: GetRtEntitiesByWellKnownName@1
  ckTypeId: Industry.Manufacturing/ProductionOrder
  path: $.orders[*]
  wellKnownNamePath: $.OrderNumber
  rtIdTargetPath: $.rtId
  ckTypeIdTargetPath: $.ckTypeId
  modOperationPath: $.modOperation
  generateInsertOperation: true
```

### GetOrCreateRtEntitiesByType@1

Find an entity by field filters or generate a new ID if not found.

> **fieldFilters attributePath casing:** The `attributePath` value is **case-sensitive** and passed directly to the MongoDB query engine without normalization. Use **PascalCase** matching the database field names (same casing as GraphQL query results: `Name`, `SerialNumber`, `MachineState`). For system properties, use their exact names: `RtWellKnownName`, `RtId`, `CkTypeId`.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ckTypeId` | string | optional | CK type ID |
| `ckTypeIdPath` | string | optional | JSONPath to CK type ID |
| `fieldFilters` | array | required | Filters to find entity |
| `rtIdTargetPath` | string | `$.rtId` | Where to write RtId |
| `ckTypeIdTargetPath` | string | `$.ckTypeId` | Where to write CkTypeId |
| `modOperationPath` | string | `$.modOperation` | Where to write mod operation |

```yaml
- type: GetOrCreateRtEntitiesByType@1
  ckTypeId: Industry.Basic/Sensor
  fieldFilters:
    - attributePath: SerialNumber          # PascalCase — matches DB field name
      operator: Equals
      comparisonValuePath: $.key.serial
  rtIdTargetPath: $.key.rtId
  modOperationPath: $.key.modOp

# System property filter example:
- type: GetOrCreateRtEntitiesByType@1
  ckTypeId: Basic/Tree
  fieldFilters:
    - attributePath: RtWellKnownName       # system property, PascalCase
      comparisonValue: "My Container"
  rtIdTargetPath: $.parentRtId
  modOperationPath: $.parentModOp
```

### GetAssociationTargets@1

Retrieve target entities through association relationships.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `graphDirection` | enum | optional | Inbound, Outbound, or Any |
| `graphDirectionPath` | string | optional | JSONPath to direction |
| `originRtIdPath` | string | optional | JSONPath to origin RtId |
| `originRtId` | string | optional | Static origin RtId |
| `originCkTypeId` | string | optional | Static origin CK type |
| `originCkTypeIdPath` | string | optional | JSONPath to origin type |
| `targetCkTypeId` | string | optional | Static target CK type |
| `targetCkTypeIdPath` | string | optional | JSONPath to target type |
| `associationRoleId` | string | optional | Static association role |
| `associationRoleIdPath` | string | optional | JSONPath to role |
| `fieldFilters` | array | optional | Field filters on targets |
| `sortOrders` | array | optional | Sort orders |
| `path` | string | `$` | Source data path (inherited) |
| `targetPath` | string | required | Where to store results |

```yaml
- type: GetAssociationTargets@1
  graphDirection: Outbound
  originRtIdPath: $.Document.RtId
  originCkTypeId: Industry.Basic/Alarm
  targetCkTypeId: Industry.Basic/Machine
  targetPath: $.Machine
  associationRoleId: Industry.Basic/EventSource
```

### GetQueryById@1

Execute a saved query by its runtime ID.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `queryRtId` | string | required | The saved query entity ID |
| `skip` | int | optional | Skip count |
| `take` | int | optional | Take count |
| `fieldFilters` | array | optional | Additional field filters |
| `targetPath` | string | required | Where to store QueryResult |

Handles all three query types: `RtSimpleRtQuery`, `RtAggregationRtQuery`, and `RtGroupingAggregationRtQuery`. QueryResult contains a `Rows` array; each row has `RtId`, `CkTypeId`, and a `Values` array. For aggregation/grouping queries, **`RtId` and `CkTypeId` on a row may be null** (there is no single source entity). Throws a `MeshAdapterPipelineExecutionException` if the query is not found. The query cache is disabled for this node, so it always reads fresh data.

```yaml
- type: GetQueryById@1
  queryRtId: 688b047f5f17dc195d83ca1d
  targetPath: $.query
  take: 100
  fieldFilters:
    - attributePath: state
      operator: Equals
      comparisonValue: 0
```

### GetPipelineConfigByWellKnownName@1

> **This is an SDK node, not Mesh-specific.** It lives in `octo-sdk/src/Sdk.Common/EtlDataPipeline/Nodes/Extracts/` and is available on **all** adapters. See `node-reference-sdk.md` for its full property table. (Listed here only because pipelines commonly combine it with the Mesh extract nodes below.)

### GetPipelineConfigByCkTypeId@1

Retrieve all pipeline configurations matching a CK type ID.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ckTypeId` | string | optional | Static CK type ID |
| `ckTypeIdPath` | string | optional | JSONPath to CK type ID |
| `targetPath` | string | required | Where to store config array |

### GetNotificationTemplate@1

Retrieve notification template (subject and body) by name.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `notificationTemplateName` | string | optional | Static template name |
| `notificationTemplateNamePath` | string | optional | JSONPath to name |
| `subjectTargetPath` | string | required | Where to write subject |
| `targetPath` | string | required | Where to write body template |

```yaml
- type: GetNotificationTemplate@1
  notificationTemplateName: alarm-notification
  targetPath: $.body
  subjectTargetPath: $.subject
```

### BackfillFromRtEntity@1

Backfill missing attributes on a list of `EntityUpdateInfo<RtEntity>` items from each item's persistent MongoDB entity, using the target archive's column spec to decide which attributes are needed. **Replaces the removed `EnrichWithMongoData@1`** — the contract is now archive-driven (no per-attribute config). Designed to sit immediately before `SaveStreamDataInArchive@1` in event-sourced pipelines where each upstream event carries only one attribute; the result is a complete row snapshot that satisfies the archive's NOT NULL columns.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `archiveRtId` | string | required | RtId of the target `CkArchive`. Its `Columns` list is the schema that drives backfill — every column not yet populated on an update item is loaded from the persistent entity by its `RtId` |
| `path` | string | `$` | Source path for the `EntityUpdateInfo` list (inherited from `PathNodeConfiguration`) |

```yaml
- type: BackfillFromRtEntity@1
  path: $._updates
  archiveRtId: cc0000000000000000000aa1
```

---

## Transform Nodes

### CreateUpdateInfo@1

Create `EntityUpdateInfo` objects for database operations (Insert/Update/Delete).

> **WARNING: Attribute Name Casing** — `attributeName` must match the CK model's exact casing (typically camelCase: `name`, `machineState`, `operatingHours`). Do NOT assume PascalCase. Use `ck_explorer.py preflight <type>` to discover correct names.

> **Intended workflow:** Use `GetOrCreateRtEntitiesByType@1` or `GetRtEntitiesByWellKnownName@1` upstream to resolve/generate RtIds (via `rtIdTargetPath`), then pass the ID here via `rtIdPath`. This makes the RtId available for `CreateAssociationUpdate` path references downstream. Avoid `generateRtId: true` when you need to reference the ID in associations.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `updateKind` | enum | optional | Insert, Update, or Delete |
| `updateKindPath` | string | optional | JSONPath to operation type |
| `rtIdPath` | string | optional | JSONPath to RtId |
| `rtId` | string | optional | Static RtId |
| `generateRtId` | bool | false | Auto-generate RtId if missing |
| `ckTypeId` | string | optional | CK type ID |
| `ckTypeIdPath` | string | optional | JSONPath to CK type ID |
| `timestampPath` | string | optional | JSONPath to timestamp |
| `rtWellKnownNamePath` | string | optional | JSONPath to well-known name |
| `attributeUpdates` | array | optional | Attributes to set |
| `path` | string | `$` | Source data path (inherited) |
| `targetPath` | string | required | Where to write EntityUpdateInfo |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |
| `targetValueKind` | enum | Simple | Simple/Array |

Each `attributeUpdate`:
| Property | Type | Description |
|----------|------|-------------|
| `attributeName` | string | Attribute name |
| `attributeValueType` | enum | String, Int, Int64, Double, Boolean, DateTime, TimeSpan, Enum |
| `valuePath` | string | JSONPath to value (takes precedence) |
| `value` | object | Static value |

```yaml
- type: CreateUpdateInfo@1
  targetPath: $.key.entityUpdate
  updateKind: INSERT
  ckTypeId: Industry.Manufacturing/ProductionOrder
  rtWellKnownNamePath: $.key.OrderNumber
  generateRtId: true
  attributeUpdates:
    - attributeName: OrderNumber
      attributeValueType: String
      valuePath: $.key.OrderNumber
    - attributeName: Status
      attributeValueType: Enum
      value: 1
    - attributeName: PlannedQuantity
      attributeValueType: Double
      valuePath: $.key.Quantity
```

### CreateAssociationUpdate@1

Create `AssociationUpdateInfo` for creating or deleting associations between entities.

> **RtId referencing:** Use `originRtIdPath`/`targetRtIdPath` to read RtIds that were resolved upstream by `GetOrCreateRtEntitiesByType@1` or `GetRtEntitiesByWellKnownName@1` (via their `rtIdTargetPath`). Only create associations on INSERT (check the `modOperationPath` value from the upstream GetOrCreate node).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `updateKind` | enum | optional | CREATE or DELETE |
| `updateKindPath` | string | optional | JSONPath to kind |
| `originRtIdPath` | string | optional | JSONPath to origin RtId |
| `originRtId` | string | optional | Static origin RtId |
| `originCkTypeId` | string | optional | Static origin CK type |
| `originCkTypeIdPath` | string | optional | JSONPath to origin type |
| `targetRtIdPath` | string | optional | JSONPath to target RtId |
| `targetRtId` | string | optional | Static target RtId |
| `targetCkTypeId` | string | optional | Static target CK type |
| `targetCkTypeIdPath` | string | optional | JSONPath to target type |
| `associationRoleId` | string | optional | Static role ID |
| `associationRoleIdPath` | string | optional | JSONPath to role |
| `path` | string | `$` | Source data path (inherited) |
| `targetPath` | string | required | Where to write result |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append |
| `targetValueKind` | enum | Simple | Simple/Array |

```yaml
- type: CreateAssociationUpdate@1
  targetPath: $.key.assocUpdates
  targetValueWriteMode: Append
  targetValueKind: Array
  updateKind: CREATE
  originRtIdPath: $.key.childUpdate.RtId
  originCkTypeId: Industry.Manufacturing/ProductionOrderItem
  targetRtIdPath: $.key.parentUpdate.RtId
  targetCkTypeId: Industry.Manufacturing/ProductionOrder
  associationRoleId: System/ParentChild
```

### CreateFileSystemUpdate@1

Create file system items with binary content.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `rtIdPath` | string | optional | JSONPath to RtId |
| `generateRtId` | bool | false | Auto-generate RtId |
| `fileName` | string | optional | Static file name |
| `fileNamePath` | string | optional | JSONPath to file name |
| `generateFileName` | bool | false | Auto-generate from content type |
| `contentType` | string | optional | MIME content type |
| `contentTypePath` | string | optional | JSONPath to content type |
| `contentLength` | long | optional | Static content length |
| `contentLengthPath` | string | optional | JSONPath to length |
| `rootFolderWellKnownName` | string | required | Root folder reference |
| `path` | string | `$` | Source path for base64 content (inherited) |
| `targetPath` | string | required | Where to write result |

### DataMapping@1

Map source values to target values based on configured mappings.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `sourceValueType` | enum | required | Source value type (Int, String, Double, etc.) |
| `targetValueType` | enum | required | Target value type |
| `mappings` | array | required | Mapping rules |
| `path` | string | `$` | Source data path (inherited) |
| `targetPath` | string | required | Where to write mapped value |

Each mapping: `{sourceValue, targetValue, description}`.

```yaml
- type: DataMapping@1
  path: $.key.Direction
  targetPath: $.key.entityType
  sourceValueType: Int
  targetValueType: String
  mappings:
    - sourceValue: 1
      targetValue: EnergyCommunity/Consumer
    - sourceValue: 2
      targetValue: EnergyCommunity/Producer
```

### FilterLatestUpdateInfo@1

Filter duplicate entity updates, keeping only the latest for each entity.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | `$` | Source path for updates (inherited) |
| `targetPath` | string | required | Where to write filtered updates |

```yaml
- type: FilterLatestUpdateInfo@1
  path: $._entityUpdates
  targetPath: $._entityUpdates
```

### Distinct@1

> **Now an SDK node, available on all adapters** (moved from MeshAdapter.Sdk to `Sdk.Common`). Documented here for continuity; it is not Mesh-specific.

Remove duplicate objects based on a unique property value.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `distinctValuePath` | string | required | JSONPath to unique value |
| `path` | string | `$` | Source array path (inherited) |
| `targetPath` | string | required | Where to write distinct array |

### PlaceholderReplace@1

Replace `${placeholder}` patterns in strings.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `replaceRules` | array | required | Replacement rules |
| `path` | string | `$` | Source template string path (inherited) |
| `targetPath` | string | required | Where to write result |

Each rule: `{placeholder, path}` — placeholder is the name without `${}`.

```yaml
- type: PlaceholderReplace@1
  path: $.body
  targetPath: $.resultBody
  replaceRules:
    - placeholder: MachineName
      path: $.Machine.Attributes.Name
    - placeholder: AlarmDate
      path: $.Document.Attributes.Time
```

### CheckDuplicate@1

Check whether an entity with a given attribute value already exists in the database.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ckTypeId` | string | required | CK type to search for duplicates |
| `attributeName` | string | required | Attribute name to match against |
| `valuePath` | string | required | JSONPath to the value to check |
| `existingEntityPath` | string | optional | Where to write the existing entity if found |
| `targetPath` | string | required | Where to write boolean result (`true` = duplicate found) |

```yaml
- type: CheckDuplicate@1
  ckTypeId: Industry.Basic/Machine
  attributeName: SerialNumber
  valuePath: $.key.serial
  existingEntityPath: $.key.existing
  targetPath: $.key.isDuplicate
```

### ComputeFileHash@1

Compute a SHA-256 hash of base64-encoded file data.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | `$` | Source path for base64 file data |
| `targetPath` | string | required | Where to write the hex hash string |

```yaml
- type: ComputeFileHash@1
  path: $.fileData
  targetPath: $.fileHash
```

### ImportFromCsv@1

Parse a CSV file and produce an array of typed objects. The file is sourced from `$.files[]` (populated by `FromHttpRequest@1` for multipart uploads).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `fileIndex` | int | 0 | Index in `$.files[]` array |
| `delimiter` | string | `;` | Column delimiter character |
| `encoding` | string | `utf-8` | File encoding |
| `hasHeaderRow` | bool | true | Whether first data row is a header |
| `skipRows` | int | 0 | Number of rows to skip before header/data |
| `columnMappings` | array | required | Column-to-property mappings |
| `targetPath` | string | required | Where to write the parsed array |

Each `columnMapping`:
| Property | Type | Description |
|----------|------|-------------|
| `sourceColumn` | string | Source column name (matches header) |
| `sourceIndex` | int | Source column index (zero-based, alternative to name) |
| `targetProperty` | string | Output JSON property name |
| `dataType` | enum | `String`, `Int`, `Double`, `Boolean`, `DateTime` |
| `dateFormat` | string | Date format for DateTime parsing (e.g., `dd.MM.yyyy`) |
| `numberCulture` | string | Culture for number parsing (e.g., `de-AT`) |

```yaml
- type: ImportFromCsv@1
  fileIndex: 0
  delimiter: ";"
  hasHeaderRow: true
  targetPath: $.rows
  columnMappings:
    - sourceColumn: OrderNumber
      targetProperty: OrderNumber
      dataType: String
    - sourceColumn: Quantity
      targetProperty: Quantity
      dataType: Double
      numberCulture: de-AT
    - sourceColumn: Date
      targetProperty: Date
      dataType: DateTime
      dateFormat: "dd.MM.yyyy"
```

### ReplyToTeamsChannel@1

Send a message card to a Microsoft Teams channel via an Incoming Webhook URL.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `webhookUrl` | string | optional | Static Incoming Webhook URL |
| `webhookUrlPath` | string | optional | JSONPath to webhook URL |
| `messageBody` | string | optional | Static message body (supports `${jsonPath}` placeholders) |
| `messageBodyPath` | string | optional | JSONPath to message body |
| `title` | string | optional | Card header title |
| `themeColor` | string | `0076D7` | Card theme color (hex without `#`) |
| `continueOnError` | bool | true | Continue pipeline if send fails |

```yaml
- type: ReplyToTeamsChannel@1
  webhookUrlPath: $.config.teamsWebhookUrl
  title: "New Alert"
  messageBodyPath: $.alertMessage
  themeColor: "FF0000"
```

### QueryResultToMarkdownTable@1

Convert QueryResult objects to Markdown table format.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | `$` | Source path for QueryResult (inherited) |
| `targetPath` | string | required | Where to write Markdown table |

### MinMax@1

Find object with minimum or maximum value in array.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `valuePath` | string | required | JSONPath to comparable value |
| `mode` | enum | Min | Min or Max |
| `path` | string | `$` | Source array path (inherited) |
| `targetPath` | string | required | Where to write selected object |

### MakeHttpRequest@1

Make HTTP requests and store response.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `method` | string | GET | HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS) |
| `url` | string | optional | Static URL |
| `urlPath` | string | optional | JSONPath to URL |
| `body` | string | optional | Static request body |
| `bodyPath` | string | optional | JSONPath to body |
| `pathParameters` | array | optional | URL path parameters: `{name, value, valuePath}` |
| `headerParameters` | array | optional | HTTP headers: `{name, value, valuePath}` |
| `targetPath` | string | required | Where to store response |

```yaml
- type: MakeHttpRequest@1
  method: POST
  url: https://api.example.com/data
  bodyPath: $.payload
  headerParameters:
    - name: Authorization
      valuePath: $.auth.token
    - name: Content-Type
      value: application/json
  targetPath: $.response
```

### StatisticalAnomalyDetection@1

Detect anomalies using statistical methods.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `detectors` | array | required | Detector configurations |
| `resetStatistics` | bool | false | Reset on each run |
| `path` | string | `$` | Source data path (inherited) |
| `targetPath` | string | required | Where to write anomaly results |

Each detector: `{groupByPath, path, contextPath, method (ZScore/IQR/PercentChange/MovingAverage), threshold (3.0), minSamples (10), maxSamples (1000), windowSize (10)}`.

### MachineLearningAnomalyDetection@1

Time series anomaly detection using ML.NET (spike/change point).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `detectors` | array | required | ML detector configurations |
| `resetStatistics` | bool | false | Reset on each run |
| `path` | string | `$` | Source data path (inherited) |
| `targetPath` | string | required | Where to write results |

Each detector: `{groupByPath, path, contextPath, detectSpikes (true), detectChangePoints (true), spikeConfidence (95), changePointConfidence (95), pValueHistoryLength (30), changeHistoryLength (10), minDataPoints (20), maxDataPoints (1000)}`.

### ImportFromExcel@1

Import hierarchical data from Excel files (TreePath or TreeColumn import).

### PdfOcrExtraction@1

Extract text and data from PDFs using OCR.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `pageNumbers` | int[] | optional | Specific pages to process |
| `language` | string | `en` | OCR language (en, de, fr, es, it, pt, nl, ru, zh, ja, ko, ar) |
| `extractTables` | bool | false | Extract table data |
| `tablesOutputPath` | string | optional | Where to store tables |
| `extractBarcodes` | bool | false | Extract barcodes |
| `barcodesOutputPath` | string | optional | Where to store barcodes |
| `includeConfidence` | bool | false | Include OCR confidence score |
| `confidenceOutputPath` | string | optional | Where to store confidence |
| `continueOnError` | bool | false | Continue if extraction fails |
| `path` | string | `$` | Source path for base64 PDF (inherited) |
| `targetPath` | string | required | Where to write extracted text |

### GenerateAndStoreReport@1

Generate reports via reporting service and store to file system.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `fileSystemFolderUri` | string | `/` | Folder path for reports |
| `reportDefinitionUri` | string | optional | URI of report template |
| `reportFileNamePrefix` | string | optional | Prefix for generated file |
| `relatedRtIdPath` | string | optional | JSONPath to related entity RtId |
| `relatedCkTypeId` | string | optional | Static related CK type |
| `reportParameters` | array | optional | Report parameters: `{name, value, valuePath}` |
| `targetPath` | string | required | Where to store response |

### AnthropicAiQuery@1

Query Claude AI for document analysis, information extraction, and (optionally) live OctoMesh data queries via MCP.

**Only `question` is required.** The API key is optional — prefer `apiKeyConfigurationName` (references an `AiConfiguration` CK entity; the key is never exposed in the pipeline data context) over the inline `apiKey`.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `question` | string | **required** | Question/prompt for the AI |
| `apiKeyConfigurationName` | string | optional | Name of the `AiConfiguration` entity in GlobalConfiguration to load the API key from. **Takes precedence over `apiKey`** — preferred, secure |
| `apiKey` | string | optional | Inline Anthropic API key (nullable). Avoid — exposes the key in the pipeline definition |
| `model` | string | `claude-sonnet-4-20250514` | Claude model ID |
| `dataPaths` | string[] | optional | Additional context paths to include in the query |
| `systemPrompt` | string | (built-in default) | System prompt |
| `maxTokens` | int | 1000 | Max response tokens |
| `temperature` | double | 0.1 | Response temperature (0.0-1.0) |
| `responseFormat` | string | `json` | Expected format: `json` or `text` |
| `jsonFormatSample` | string | (built-in sample) | Example JSON structure for structured responses |
| `includeRawResponse` | bool | false | Store the raw AI response |
| `rawResponseOutputPath` | string | optional | Where to store the raw response |
| `continueOnError` | bool | false | Continue the pipeline if the query fails |
| `mcpServerUrl` | string | optional | OctoMesh MCP server URL (e.g. `https://localhost:5017`). When set, Claude can call MCP tools to query live OctoMesh data; the tenant ID is appended automatically as `{url}/{tenantId}/mcp` |
| `maxToolRounds` | int | 10 | Max MCP tool-use rounds (loop guard) |
| `mcpToolNames` | string[] | optional | Whitelist of MCP tool names to expose (reduces context; e.g. `["query_entities_simple"]`). If unset, all tools are available |
| `conversationHistoryPath` | string | optional | JSONPath to a conversation-history array (entries `{role, content}`) for multi-turn conversations |
| `path` | string | `$` | Source path for main content (inherited) |
| `targetPath` | string | required | Where to store the response |

```yaml
- type: AnthropicAiQuery@1
  apiKeyConfigurationName: anthropic-prod   # references an AiConfiguration entity
  model: claude-sonnet-4-20250514
  question: "Extract the invoice number and total from this document"
  systemPrompt: "You are a document analysis assistant."
  responseFormat: json
  jsonFormatSample: '{"invoiceNumber": "string", "total": 0.0}'
  path: $.documentText
  targetPath: $.extractedData
```

### ApplyDataPointMappings@1

Evaluate `System.Communication/DataPointMapping` entities for a source entity, apply their mXparser expressions, and produce `EntityUpdateInfo` for the mapped target entities. Used for live data acquisition (e.g. Loxone control → target attribute).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `sourceRtIdPath` | string | optional | JSONPath to the source entity's RtId |
| `sourceCkTypeIdPath` | string | optional | JSONPath to the source entity's CkTypeId |
| `sourceValuePath` | string | optional | JSONPath to the polled source value — the default mapping input and the `value` variable in expressions |
| `sourceStateNamePath` | string | optional | JSONPath to the incoming state name. When set, only mappings whose `SourceAttributePath` equals it are applied (multi-state sources like Loxone controls). If unset, all mappings for the source are applied |
| `targetPath` | string | required | Where to write the produced update items |

### BuildMappingTargets@1

Resolve all active DataPointMappings into `MappingTarget` records (external identifiers) so an external adapter can acquire data. Generic for Loxone/MQTT/OPC-UA/Modbus. Each target is a plain identifier, or a `identifier|stateName|stateId` triple for sub-state sources.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `sourceCkTypeId` | string | required | CkTypeId of the source entities mappings map from (e.g. `Loxone/Control`) |
| `sourceIdentifierAttribute` | string | required | Attribute on the source holding the external id (e.g. `LoxoneUuid`) |
| `statesAttribute` | string | optional | RecordArray attribute holding sub-states; enables triple output |
| `stateKeyAttribute` | string | optional | State-name attribute within each state record (required when `statesAttribute` is set) |
| `stateValueAttribute` | string | optional | State-id/UUID attribute within each state record (required when `statesAttribute` is set) |
| `defaultAttributePath` | string | `currentValue` | Attribute path that maps to the main value; produces a plain identifier |
| `targetPath` | string | required | Where to write the target list |

### GenerateDataPointMappings@1

Deterministic, rule-based DataPointMapping suggestion generator — the **non-AI alternative to `AnthropicAiQuery@1`** for mapping generation (the output shape is identical, so the downstream GetOrCreate + CreateUpdateInfo + CreateAssociationUpdate pipeline consumes either). Matches source containers to targets by name/normalized/regex/manual strategy, walks the hierarchy to reach controls, and evaluates control rules per (rule, state) pair.

Key config: `sourceContainerCkTypeId`, `sourceControlCkTypeId` (required); optional `sourceCategoryCkTypeId`, `hierarchyAssociationRoleId` (default `System/ParentChild`); `targetCkTypeId` (required); `statesAttribute` (default `States`), `stateNameAttribute` (default `Name`), `defaultSourceAttributePath` (default `CurrentValue`); `containerMatchingStrategies` (ordered, first match wins: `ExactName`/`NormalizedName`/`Regex`/`Manual`); `controlMappingRules` (each `{id, when{controlType,stateName,categoryType,categoryNameRegex,controlNameRegex}, map{targetAttribute,expression,childTargetCkTypeId,childTargetAssociationRoleId}}`); optional `statisticsTargetPath`; `targetPath` (required). Read the config source for the full strategy/rule shapes before authoring rules.

### ValidateDataPointCoverage@1

Traverse a tree hierarchy and, for every node, evaluate which target attribute paths are covered by inbound `MapsTo` DataPointMappings against per-CK-type `CoverageRule` profiles. Emits a JSON report (per-node `status`: ok/warning/error/info) suitable for persisting via `SetPipelineExecutionResult@1` so the Studio can colour-code the tree.

Key config: `rootRtId` or `rootRtIdPath`, `rootCkTypeId` (required); `childRoleId` (default `System/ParentChild`), `childCkTypeId` (default `Basic/TreeNode`), `maxDepth` (default 16); `mappingRoleId` (default `System.Communication/MapsTo`), `mappingCkTypeId` (default `System.Communication/DataPointMapping`), `includeDisabledMappings` (default false); `rules` (list of `CoverageRule {ckTypeId, requiredAttributes[], recommendedAttributes[], requiredAssociations[{associationRoleId, targetCkTypeId}]}`); `targetPath` (required).

### MapToRecordArray@1

Convert a JSON key/value map into a CK RecordArray — each map entry becomes one record with a key attribute and a value attribute.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ckRecordId` | string | required | Semantic-versioned full name of the CK record type (e.g. `Loxone/LoxoneState`) |
| `keyAttributeName` | string | required | Record attribute that receives the map key |
| `valueAttributeName` | string | required | Record attribute that receives the map value |
| `path` | string | `$` | Source map (inherited) |
| `targetPath` | string | required | Where to write the RecordArray |

### UpdateRecordArrayItem@1

Find one record in a CK RecordArray by a key attribute match and update specified attributes without overwriting the whole array (the array is rebuilt from existing items + the patched item). If no record matches, it is skipped.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `matchAttributeName` | string | required | Record attribute to match against (e.g. `Name`, `ExternalId`) |
| `matchValue` | string | optional | Static value to match |
| `matchValuePath` | string | optional | JSONPath to the match value (takes precedence over `matchValue`) |
| `attributeUpdates` | array | required | Each `{attributeName, value, valuePath}` (`valuePath` wins over `value`) |
| `path` | string | `$` | Source RecordArray (inherited) |
| `targetPath` | string | required | Where to write the updated array |

### SimulateEnergyMeasurements@1

Generate per-15-min-slot `EnergyMeasurement` Insert candidates (and their parent `ParentChild` association candidates) for a set of MeteringPoints over a time window, using BDEW H0/G0/L0 load-profile or PV-curve math. Output flows into `UpdateRtEntityIfNewer@1` (dedup) → `ApplyChanges@2` (RT write) → `SaveTimeRangeStreamDataInArchive@1` (archive write).

Key config: `startDate`, `numDays` (required); `energyMeasurementCkTypeId`, `timeRangeCkRecordId`, `amountCkRecordId`, `parentAssociationRoleId` (required); `amountUnit` (default 1), `dataQuality` (default 1); `entityUpdatesOutputPath`, `associationUpdatesOutputPath` (required); `meteringPoints` (≥1 entry of `{meteringPointRtId, meteringPointCkTypeId, profileKind ("Load:H0"/"Load:G0"/"Load:L0"/"PV"), profileParameter (daily kWh or peak kWp), obisCodes[]}`).

---

## Load Nodes

### ApplyChanges@1

Apply EntityUpdateInfo changes to MongoDB with conflict handling and deduplication.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source path for entity update infos |

```yaml
- type: ApplyChanges@1
  path: $._entityUpdates
```

### ApplyChanges@2

Apply both entity and association updates with transactional support.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `entityUpdatesPath` | string | optional | JSONPath to entity updates |
| `associationUpdatesPath` | string | optional | JSONPath to association updates |

```yaml
- type: ApplyChanges@2
  entityUpdatesPath: $.entityUpdates
  associationUpdatesPath: $.assocUpdates
```

### SaveStreamDataInArchive@1

Route the source entities into a single named CrateDB `CkArchive` (no auto fan-out — one archive per node). **Replaces the removed `SaveInTimeSeries@1`** (breaking YAML rename, same `@1` version, plus a new required `archiveRtId`).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `archiveRtId` | string | **required** | RtId of the `CkArchive` that receives the data points. The archive must exist on the tenant and be in status **`Activated`** at runtime — otherwise the node throws `ArchiveNotActivatedException` |
| `path` | string | `$` | Source path for the entity update infos (inherited) |

```yaml
- type: SaveStreamDataInArchive@1
  path: $._entityUpdates
  archiveRtId: cc0000000000000000000aa1   # must be an Activated CkArchive
```

> Archives are managed via octo-cli (`ActivateArchive`, `DisableArchive`, `EnableStreamData`, etc.) — hand off to the `octo` skill. Attribute capture is type-agnostic: every column the archive declares becomes a queryable CrateDB column; there is no per-attribute "stream data" flag.

### SaveTimeRangeStreamDataInArchive@1

Write externally pre-aggregated time-range data points into a `TimeRangeArchive`. Each upstream entity must carry window boundaries (default top-level attributes `From`/`To`). Re-deliveries of the same `(from, to, rtId, ckTypeId)` upsert.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `archiveRtId` | string | **required** | RtId of the target `TimeRangeArchive` (must be Activated; raw/rollup archives are rejected) |
| `fromAttributePath` | string | `From` | Attribute carrying the inclusive UTC window start. Supports dot notation for record attributes (e.g. `TimeRange.From`) |
| `toAttributePath` | string | `To` | Attribute carrying the exclusive UTC window end |
| `path` | string | `$` | Source path (inherited) |

### UpdateRtEntityIfNewer@1

Filter a list of `EntityUpdateInfo` candidates by comparing each against the existing RT entity with the same `RtWellKnownName`. Strictly-newer candidates go to the RT-write path; older ones are kept (with the existing RtId) on the all-output path so a downstream archive write can still land the corrected slot. Implements the time-range-archive "keep the most recent on the RT entity, full series in the archive" semantics.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `inputPath` | string | **required** | JSONPath to the candidate `EntityUpdateInfo` list |
| `filteredOutputPath` | string | **required** | Where the RT-write list is written (Insert + strictly-newer Update) |
| `outputPathAll` | string | **required** | Where the complete list (including skipped, with existing RtId) is written for the archive write |
| `comparisonAttributePath` | string | **required** | Attribute holding the monotonic comparison value (typically a UTC DateTime). Supports dot notation for record attributes (e.g. `TimeRange.From`) |
| `candidateAssociationsInputPath` | string | optional | JSONPath to candidate parent `AssociationUpdateInfo` list (for filtering association inserts) |
| `filteredAssociationsOutputPath` | string | optional | Where the filtered association list is written (required when `candidateAssociationsInputPath` is set) |

### SendEMail@1

Send emails with Markdown-to-HTML conversion and optional attachments.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `serverConfiguration` | string | required | Global config key for SMTP settings |
| `cssConfiguration` | string | optional | Global config key for CSS styling |
| `subjectPath` | string | required | JSONPath to email subject |
| `toPath` | string | required | JSONPath to recipient addresses (array) |
| `ccPath` | string | optional | JSONPath to CC addresses |
| `ccAddresses` | array | optional | Static CC addresses |
| `bccPath` | string | optional | JSONPath to BCC addresses |
| `bccAddresses` | array | optional | Static BCC addresses |
| `attachmentRtIdPath` | string | optional | JSONPath to attachment RtId |
| `attachmentRtId` | string | optional | Static attachment RtId |
| `attachmentFileName` | string | optional | File name for attachment |
| `attachmentContentType` | string | `application/octet-stream` | MIME type |
| `path` | string | required | Source path for email body (Markdown) |

```yaml
- type: SendEMail@1
  serverConfiguration: sendgrid
  subjectPath: $.resultSubject
  path: $.resultBody
  toPath: $.recipients
```

### SftpUpload@1

Upload a file to a remote SFTP server. The file content is referenced by RtId from MongoDB large binary storage.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `serverConfiguration` | string | required | Global config key for SFTP server credentials |
| `remoteDirectory` | string | required | Target directory path on the SFTP server |
| `fileName` | string | optional | Static file name for the upload |
| `fileNamePath` | string | optional | JSONPath to file name |
| `fileRtId` | string | optional | Static RtId of binary file in MongoDB storage |
| `fileRtIdPath` | string | optional | JSONPath to binary file RtId |
| `path` | string | `$` | Source data path |

```yaml
- type: SftpUpload@1
  serverConfiguration: sftp-server
  remoteDirectory: /exports/reports
  fileNamePath: $.report.fileName
  fileRtIdPath: $.report.fileRtId
```

### GrafanaProvisionTenant@1

Provision a Grafana organization and OctoMesh datasource for the current tenant. Creates the org if it does not exist and configures the datasource.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `serverConfiguration` | string | required | Global config key for GrafanaConfiguration entity |
| `tenantIdPath` | string | optional | JSONPath to tenant ID (defaults to pipeline's tenant) |
| `targetPath` | string | required | Where to write the provisioning result |

```yaml
- type: GrafanaProvisionTenant@1
  serverConfiguration: grafana-main
  targetPath: $.grafanaResult
```

### GrafanaDeprovisionTenant@1

Deprovision (delete) a Grafana organization for the current tenant, removing all datasources and dashboards.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `serverConfiguration` | string | required | Global config key for GrafanaConfiguration entity |
| `tenantIdPath` | string | optional | JSONPath to tenant ID (defaults to pipeline's tenant) |
| `targetPath` | string | required | Where to write the deprovision result |

```yaml
- type: GrafanaDeprovisionTenant@1
  serverConfiguration: grafana-main
  targetPath: $.grafanaResult
```

### DeployPipeline@1

Deploy another pipeline **within the same DataFlow** to its assigned adapter, via the Communication Controller REST API. Cannot deploy itself; the target must be in the same DataFlow.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `pipelineRtId` | string | optional | Static RtId of the pipeline to deploy |
| `pipelineRtIdPath` | string | optional | JSONPath to the pipeline RtId |
| `serviceAccountConfigName` | string | `ServiceAccountConfig` | Well-known name of the `ServiceAccountConfiguration` entity used for OAuth2 auth |

### ToDiscord@1

Post a message, embed, and/or single file attachment to a Discord channel via the Bot API, using a `DiscordConfiguration` CK entity (bot token + optional guild id) resolved by name. Threads are channels — pass a thread snowflake as `channelId` to post into a thread. **Prerequisite:** a `System.Communication/DiscordConfiguration` entity (and `System.Reporting` loaded when sending attachments). Most fields follow the `{Field}` + `{Field}Path` convention (the `*Path` variant reads from the data context).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `serverConfiguration` | string | required | Global config key for the `DiscordConfiguration` entity |
| `channelId` / `channelIdPath` | string | optional | Discord channel (or thread) snowflake |
| `content` / `contentPath` | string | optional | Message content |
| `embedTitle` / `embedTitlePath` | string | optional | Embed title |
| `embedDescription` / `embedDescriptionPath` | string | optional | Embed description |
| `embedColor` (int) / `embedColorPath` | — | optional | Embed color (24-bit RGB int; path accepts `0xRRGGBB`/`#RRGGBB`/decimal) |
| `attachmentFileSystemItemRtId` / `…Path` | string | optional | RtId of a `System.Reporting/FileSystemItem` to attach (the bound binary is posted — **not** a raw binary RtId) |
| `attachmentFilename` / `attachmentFilenamePath` | string | optional | Override the sent filename |
| `mentionPolicy` | enum | `None` | `None`/`Users`/`Roles`/`UsersAndRoles`/`All`/`Custom` — controls which mentions can ping |
| `allowedMentionsPath` | string | optional | Raw Discord `allowed_mentions` object (only when `mentionPolicy: Custom`) |
| `timeoutSeconds` | int | 30 | HTTP timeout |
| `targetPath` | string | required | Where to write the result |

**Attachment filename precedence:** `attachmentFilename` override → FileSystemItem `Name` attribute → FileSystemItem `Content.Filename`.

---

## Trigger Nodes

### FromHttpRequest@1

Trigger pipeline on HTTP requests.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `method` | enum | required | HTTP method (GET, POST, PUT, DELETE) |
| `path` | string | required | URL path pattern |

**DataContext placement:** The trigger populates the DataContext with these paths:

| Path | Content |
|------|---------|
| `$.body` | JSON request body (parsed object for JSON, string for text, base64 for binary) |
| `$.query` | Query parameters as object (e.g., `$.query.page`). Array values if same key appears multiple times |
| `$.files` | Array of uploaded files (multipart/form-data only). Each: `{fileName, contentType, length, data, encoding}` where `data` is base64 |
| `$.formData` | Form fields from multipart/form-data (e.g., `$.formData.fieldName`) |
| `$.path` | Request path (lowercase) |
| `$.method` | HTTP method (uppercase) |
| `$.contentType` | Request Content-Type header |
| `$.bodyEncoding` | `"base64"` (only present for binary content) |

```yaml
triggers:
  - type: FromHttpRequest@1
    path: /createBillingItems
    method: POST

# In transformations, access the request data:
# $.body.someField      — JSON body field
# $.query.page          — query parameter
# $.files[0].data       — first uploaded file (base64)
# $.formData.fieldName  — form field value
```

### FromWatchRtEntity@1

Trigger pipeline on real-time entity changes (MongoDB change streams).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `updateTypes` | enum | required | Insert, Update, Delete, Replace (comma-separated for multiple) |
| `ckTypeId` | string | required | Entity type to watch |
| `rtId` | string | optional | Specific entity to watch |
| `beforeFieldFilters` | array | optional | Filters on state before change |
| `fieldFilters` | array | optional | Filters on state after change |

The trigger places the changed entity into `$.Document` in the data context.

```yaml
triggers:
  - type: FromWatchRtEntity@1
    updateTypes: Insert
    ckTypeId: Industry.Basic/Alarm
```

### FromExecutePipelineCommand@1

Trigger pipeline on manual execution command (via service API or UI). The pipeline must belong to a DataFlow. The adapter listens on a DataFlow-scoped message queue for execution requests.

> **Now an SDK node** (moved to `Sdk.Common`) — available on **all** adapters (Edge and Mesh), not Mesh-only. The DataFlow requirement still holds.

No additional properties.

```yaml
triggers:
  - type: FromExecutePipelineCommand@1
```

### FromSendNotification@1

Trigger pipeline when notification service sends a message.

No additional properties.

```yaml
triggers:
  - type: FromSendNotification@1
```

### FromPipelineTriggerEvent@1

Trigger pipeline on a cron schedule via a **PipelineTrigger** entity. The PipelineTrigger is a child of the pipeline's DataFlow and has a `CronExpression` attribute and a `Triggers` association linking to one or more target pipelines.

**How it works:** The Bot Service evaluates the cron expression and sends a `PipelineTriggerSchedule` message to a pipeline-specific RabbitMQ queue. The pipeline **must** include `FromPipelineTriggerEvent@1` as a trigger — this registers the adapter as a consumer on that queue. Without it, the scheduled message is sent but never consumed.

The cron expression is interpreted in the **server's local timezone** (`TimeZoneInfo.Local`, e.g. `Europe/Vienna`). Cron format: standard 5-field `minute hour dayOfMonth month dayOfWeek` (no year field; e.g. `0 * * * *` = top of every hour), scheduled via the MassTransit/Hangfire recurring scheduler.

No additional properties.

```yaml
triggers:
  - type: FromPipelineTriggerEvent@1
  - type: FromExecutePipelineCommand@1  # optional: also allow manual runs
```

### FromEmail@1

Trigger pipeline on incoming emails via IMAP polling.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `serverConfiguration` | string | required | Global config key for IMAP settings |
| `pollingIntervalSeconds` | int | 60 | Check interval |
| `onlyUnread` | bool | true | Only process unread emails |
| `markAsRead` | bool | true | Mark processed as read |
| `deleteAfterProcessing` | bool | false | Delete after processing |
| `senderFilter` | string | optional | Filter by sender (contains) |
| `subjectFilter` | string | optional | Filter by subject (contains) |

```yaml
triggers:
  - type: FromEmail@1
    serverConfiguration: imap-config
    pollingIntervalSeconds: 120
    onlyUnread: true
    senderFilter: notifications@example.com
```

### FromMicrosoftGraph@1

Poll Microsoft Teams channels for new messages via Microsoft Graph API.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `serverConfiguration` | string | required | Global config key for MicrosoftGraphConfiguration entity (OAuth2 settings) |
| `teamId` | string | required | Microsoft Teams team ID (GUID) |
| `channelId` | string | required | Microsoft Teams channel ID |
| `pollingIntervalSeconds` | int | 120 | How often to check for new messages |
| `senderFilter` | string | optional | Filter by sender display name (contains match) |

```yaml
triggers:
  - type: FromMicrosoftGraph@1
    serverConfiguration: ms-graph-config
    teamId: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    channelId: "19:xxxx@thread.tacv2"
    pollingIntervalSeconds: 60
```

---

## Domain-Specific Nodes

### SAP Nodes

**SapLogin@1** — Authenticate to SAP system.
- `sapConfiguration`: string (required) — Global config key for SAP credentials

**GetProductionOrderList@1** — Retrieve production order list.
- `productionPlant`: string — Plant code
- `orderNumberStart`: string — Starting order number
- `targetPath`: string — Where to store results

**GetProductionOrderDetails@1** — Retrieve detailed order info.
- `path`: string — Order number path
- `readHeader`: bool — Include header
- `readOperations`: bool — Include operations
- `targetPath`: string — Where to store details

### Zenon Nodes

Shipped by the **Zenon Adapter** (`octo-plug-zenon`), config records under `src/Octo.Edge.Adapter.Zenon.WindowsService/Nodes/`. The variable/AML nodes:

**FromZenonAml@1** (trigger) — Trigger on Zenon AML data.

**ReadZenonAmlMessages@1** — Read AML messages from Zenon.

**SetZenonVariables@1** — Write variable values to Zenon.
- `dataPointConfigurations`: array — each `{variablePath, valuePath, valueType}`

```yaml
- type: SetZenonVariables@1
  dataPointConfigurations:
    - variablePath: $.Tag.Attributes.Tag
      valuePath: $.Document.Attributes.PlannedQuantity
      valueType: Double
    - variablePath: $.TagArtNr.Attributes.Tag
      valuePath: $.Document.Attributes.ArticleNumber
      valueType: String
```

**Archive (historian) nodes.** Both inherit `SourceTargetPathNodeConfiguration` (`path`/`targetPath` + write modifiers):

**ReadZenonArchiveInfo@1** — List the archives available in the Zenon runtime; writes them to `targetPath`. No extra properties.

**ReadZenonArchiveData@1** — Query archived values for variables over a time window. Each literal property has an optional `*Path` JSONPath override read from the object at `path`.
- `archiveName` / `archiveNamePath` — archive to query (required, else node errors)
- `variableNames` (string[]) / `variableNamesPath` — variables to read (required)
- `startTimeOffset` (default `-1h`) / `startTimeOffsetPath`, `endTimeOffset` (default `now`) / `endTimeOffsetPath` — offsets like `-30m`, `-7d`, or `now`
- `raster` (int) / `rasterPath` — aggregation raster

**Editor dynamic-property nodes.** Operate on the Zenon Editor via `IZenonEditorApi`. All inherit `SourceTargetPathNodeConfiguration`; the inputs below are JSONPaths into the object at `path` (defaults are relative keys, not `$`-rooted):

**ListZenonProjects@1** — List Editor projects to `targetPath`. No extra properties.

**GetZenonDynamicProperties@1** — List the child dynamic-property nodes under a path.
- `projectIdOrNamePath` (default `projectIdOrName`), `pathPath` (default `path`)

**GetZenonDynamicProperty@1** — Read a single dynamic-property value (and optional parameter).
- `projectIdOrNamePath` (default `projectIdOrName`), `pathPath` (default `path`), `targetParameterPath` (default `$.parameter`)

**SetZenonDynamicProperty@1** — Write a dynamic-property value (with type coercion). **Mutating.**
- `projectIdOrNamePath` (default `projectIdOrName`), `pathPath` (default `path`), `typePath` (default `type`), `valuePath` (default `value`)

### EDA Energy Nodes (external adapter — not in this monorepo, cannot be verified locally)

> **`EdaParseMessage@1`, `EdaStartProcess@1`, `ExtractProcesses@1`, `AggregateConsumptionRecord@1`, `FilterEnergyData@1`, `SearchExistingEnergyQuantities@1` ship in a separate EDA adapter repo (`octo-adapter-eda`) that is NOT checked out in this monorepo.** Their property names and behavior cannot be confirmed against source here. The shape below is from pipeline-examples.md usage only — verify against the EDA adapter's `pipeline-schema.json` or source before relying on it.

- `EdaParseMessage@1` — parse EDA messages; observed properties `messageRtIdPath`, `messageTypePath`, `processRtIdPath`, `rawMessagePath`, `targetPath`.
- `EdaStartProcess@1`, `ExtractProcesses@1`, `AggregateConsumptionRecord@1`, `FilterEnergyData@1`, `SearchExistingEnergyQuantities@1` — EDA process orchestration and energy-data filtering (properties unverified).

### Microsoft Teams Nodes

**FromMicrosoftGraph@1** (trigger) — Poll Teams channels for new messages via Graph API. See Trigger Nodes section above.

**ReplyToTeamsChannel@1** — Send message card to Teams via Incoming Webhook. See Transform Nodes section above.

### Grafana Nodes

**GrafanaProvisionTenant@1** — Provision Grafana org and datasource for tenant. See Load Nodes section above.

**GrafanaDeprovisionTenant@1** — Deprovision Grafana org for tenant. See Load Nodes section above.

### Notification Nodes

**SendEMail@1** — See Load Nodes section above.
