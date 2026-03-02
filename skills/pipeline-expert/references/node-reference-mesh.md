# Mesh Adapter Node Reference

All nodes from `octo-mesh-adapter`. Use `NodeName@Version` syntax in YAML (e.g., `GetRtEntitiesByType@1`).

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

```yaml
- type: GetRtEntitiesByType@1
  ckTypeId: Industry.Basic/Machine
  targetPath: $.machines
  take: 100
  fieldFilters:
    - attributePath: Status
      operator: Equals
      comparisonValue: Active
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
    - attributePath: SerialNumber
      operator: Equals
      comparisonValuePath: $.key.serial
  rtIdTargetPath: $.key.rtId
  modOperationPath: $.key.modOp
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

QueryResult contains `Rows` array, each row has `RtId` and `Values` array.

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

Retrieve pipeline configuration from global config store by well-known name.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `wellKnownName` | string | optional | Static well-known name |
| `wellKnownNamePath` | string | optional | JSONPath to name |
| `targetPath` | string | required | Where to store JSON config |
| `documentMode` | enum | Extend | Extend/Replace |
| `targetValueKind` | enum | Simple | Simple/Array |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |

```yaml
- type: GetPipelineConfigByWellKnownName@1
  wellKnownName: EnergyCommunityConfiguration
  targetPath: $.config
```

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

### EnrichWithMongoData@1

Enrich entity update info with current MongoDB entity data.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `rtIdPath` | string | optional | JSONPath to RtId |
| `rtId` | string | optional | Static RtId |
| `ckTypeId` | string | optional | Static CK type ID |
| `ckTypeIdPath` | string | optional | JSONPath to CK type ID |
| `attributeUpdates` | array | optional | Attributes to fetch from DB |
| `path` | string | `$` | Source path for update infos (inherited) |
| `targetPath` | string | required | Where to write enriched data |

---

## Transform Nodes

### CreateUpdateInfo@1

Create `EntityUpdateInfo` objects for database operations (Insert/Update/Delete).

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

Query Claude AI for document analysis and information extraction.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `apiKey` | string | required | Anthropic API key |
| `model` | string | `claude-sonnet-4-20250514` | Claude model ID |
| `question` | string | required | Question/prompt for AI |
| `dataPaths` | string[] | optional | Additional context paths |
| `systemPrompt` | string | optional | System prompt |
| `maxTokens` | int | 1000 | Max response tokens |
| `temperature` | double | 0.1 | Response temperature (0.0-1.0) |
| `responseFormat` | string | `json` | Expected format: `json` or `text` |
| `jsonFormatSample` | string | optional | Example JSON structure |
| `includeRawResponse` | bool | false | Store raw AI response |
| `rawResponseOutputPath` | string | optional | Where to store raw response |
| `continueOnError` | bool | false | Continue if query fails |
| `path` | string | `$` | Source path for main content (inherited) |
| `targetPath` | string | required | Where to store response |

```yaml
- type: AnthropicAiQuery@1
  apiKey: ${ANTHROPIC_API_KEY}
  model: claude-sonnet-4-20250514
  question: "Extract the invoice number and total from this document"
  systemPrompt: "You are a document analysis assistant."
  responseFormat: json
  jsonFormatSample: '{"invoiceNumber": "string", "total": 0.0}'
  path: $.documentText
  targetPath: $.extractedData
```

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

### SaveInTimeSeries@1

Save entity data to time series database (CrateDB) for analytics.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source path for entity update infos |

```yaml
- type: SaveInTimeSeries@1
  path: $._entityUpdates
```

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

---

## Trigger Nodes

### FromHttpRequest@1

Trigger pipeline on HTTP requests.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `method` | enum | required | HTTP method (GET, POST, PUT, DELETE) |
| `path` | string | required | URL path pattern |

```yaml
triggers:
  - type: FromHttpRequest@1
    path: /createBillingItems
    method: POST
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

Trigger pipeline on explicit execute command from a service.

No additional properties. Listens on message queue for `ExecuteMeshPipelineRequest`.

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

Trigger pipeline on scheduled/event-based triggers.

No additional properties.

```yaml
triggers:
  - type: FromPipelineTriggerEvent@1
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

**FromZenonAml@1** (trigger) — Trigger on Zenon AML data.

**ReadZenonAmlMessages@1** — Read AML messages from Zenon.

**SetZenonVariables@1** — Write variable values to Zenon.
- `dataPointConfigurations`: array — Variable write configurations

Each data point: `{variablePath, valuePath, valueType}`.

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

### EDA Energy Nodes

**EdaStartProcess@1** — Start an EDA process.

**EdaParseMessage@1** — Parse EDA messages.
- `messageRtIdPath`, `messageTypePath`, `processRtIdPath`, `rawMessagePath`, `targetPath`

**ExtractProcesses@1** — Extract processes from EDA data.

**AggregateConsumptionRecord@1** — Aggregate energy consumption records.

**FilterEnergyData@1** — Filter energy data by criteria.

**SearchExistingEnergyQuantities@1** — Search for existing energy quantity records.

### Notification Nodes

**SendNotification@1** — Send notification via the bot service.

**SendEMail@1** — See Load Nodes section above.
