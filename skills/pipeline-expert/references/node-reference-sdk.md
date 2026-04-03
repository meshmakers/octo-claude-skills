# SDK Node Reference

All nodes from `octo-sdk`. Use `NodeName@Version` syntax in YAML (e.g., `ForEach@1`).

## Control Flow

### ForEach@1

Iterate over array elements, execute child transformations per item.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `iterationPath` | string | required | JSONPath to array to iterate |
| `keyPath` | string | `$.key` | Where current item is stored |
| `fullDocumentPath` | string | `$.full` | Where full original document is preserved |
| `mergePath` | string | `$.key` | Path to collect iteration result from |
| `targetPath` | string | `$` | Where to write collected results |
| `maxDegreeOfParallelism` | int | 0 | 0=CPU count, -1=unlimited, >0=explicit limit |
| `path` | string | `$` | Source path |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |
| `targetValueKind` | enum | Simple | Simple/Array |
| `documentMode` | enum | Extend | Extend/Replace |
| `transformations` | array | required | Child nodes to execute per item |

```yaml
- type: ForEach@1
  iterationPath: $.Items
  targetPath: $.Results
  fullDocumentPath: $.full
  keyPath: $.key
  mergePath: $.key
  maxDegreeOfParallelism: 4
  transformations:
    - type: SetPrimitiveValue@1
      valuePath: $.key.Name
      targetPath: $.key.processed
```

### For@1

Execute child nodes a fixed number of times.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `count` | uint | required | Number of iterations |
| `indexTargetPath` | string | optional | Path to store current index |
| `path` | string | `$` | Source path |
| `targetPath` | string | `$` | Where to write results |
| `maxDegreeOfParallelism` | int | 0 | Parallelism control |
| `transformations` | array | required | Child nodes per iteration |

```yaml
- type: For@1
  count: 10
  indexTargetPath: $.index
  targetPath: $.results
  transformations:
    - type: SetPrimitiveValue@1
      value: "item"
      targetPath: $.key.label
```

### If@1

Conditional execution — run child nodes only when condition is true.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Path to value to compare |
| `operator` | enum | Equal | Equal, NotEqual, Contains, LessThan, LessEqualsThan, GreaterThan, GreaterEqualsThan, StartsWith, EndsWith, RegexMatch |
| `value` | object | optional | Static comparison value |
| `valuePath` | string | optional | Dynamic comparison value path |
| `valueType` | enum | optional | Type for comparison (String, Int, Double, Boolean, DateTime) |
| `transformations` | array | required | Child nodes to execute if true |

```yaml
- type: If@1
  path: $.key.Status
  operator: Contains
  value: REL
  valueType: String
  transformations:
    - type: PrintDebug@1
```

### Switch@1

Multi-branch conditional — match value against cases.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Path to value to switch on |
| `cases` | array | required | Array of case objects |
| `default` | array | optional | Transformations if no case matches |
| `valueType` | enum | String | Type for comparison |

Each case has `value` (single or array of values) and `transformations`.

```yaml
- type: Switch@1
  path: $.key.Type
  valueType: Int
  cases:
    - value: 1
      transformations:
        - type: SetPrimitiveValue@1
          value: "TypeA"
          targetPath: $.key.label
    - value: [2, 3]
      transformations:
        - type: SetPrimitiveValue@1
          value: "TypeBC"
          targetPath: $.key.label
  default:
    - type: SetPrimitiveValue@1
      value: "Unknown"
      targetPath: $.key.label
```

### SelectByPath@1

Select and transform multiple paths with independent configurations.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `selectPath` | array | required | Array of path property configurations |

Each entry: `path`, `targetPath`, `targetValueWriteMode`, `targetValueKind`, `documentMode`, `transformations`.

```yaml
- type: SelectByPath@1
  selectPath:
    - path: $.source1
      targetPath: $.output1
      targetValueWriteMode: Overwrite
    - path: $.source2
      targetPath: $.output2
```

---

## Extract Nodes

### SetPrimitiveValue@1

Inject a primitive value (static or dynamic) into the data context.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `targetPath` | string | required | Where to set value |
| `value` | object | optional | Static value |
| `valuePath` | string | optional | JSONPath to dynamic value (takes precedence) |
| `valueType` | enum | optional | Target type: String, Int, Int64, Double, Boolean, DateTime, TimeSpan, Binary, StringArray, IntArray |
| `documentMode` | enum | Extend | Extend/Replace |
| `targetValueKind` | enum | Simple | Simple/Array |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |

```yaml
- type: SetPrimitiveValue@1
  value: 42
  valueType: Int
  targetPath: $.count

- type: SetPrimitiveValue@1
  valuePath: $.source.Name
  targetPath: $.target.Name
  valueType: String
```

### SetArrayOfPrimitiveValues@1

Inject an array of primitive values.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `targetPath` | string | required | Where to set array |
| `values` | array | required | Array of values |
| `documentMode` | enum | Extend | Extend/Replace |
| `targetValueKind` | enum | Simple | Simple/Array |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |

```yaml
- type: SetArrayOfPrimitiveValues@1
  values: ["a@example.com", "b@example.com"]
  targetPath: $.recipients
```

### WriteJson@1

Inject raw JSON from a string.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `targetPath` | string | required | Where to set JSON |
| `jsonString` | string | required | JSON string to parse and inject |
| `documentMode` | enum | Extend | Extend/Replace |
| `targetValueKind` | enum | Simple | Simple/Array |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |

```yaml
- type: WriteJson@1
  jsonString: '{"key": "value", "count": 5}'
  targetPath: $.config
```

---

## Trigger Nodes

### FromPipelineDataEvent@1

Listen for pipeline data events on the distributed event hub. Used for edge-to-mesh and mesh-to-edge communication.

No additional configuration properties.

```yaml
triggers:
  - type: FromPipelineDataEvent@1
```

### FromPolling@1

Poll at regular intervals.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `interval` | TimeSpan | required | Polling interval (e.g., `00:01:00`) |
| `input` | object | optional | Static input data passed on each poll |

```yaml
triggers:
  - type: FromPolling@1
    interval: 00:05:00
```

---

## Load Nodes

### ToPipelineDataEvent@1

Publish data to the distributed event hub. Pairs with `FromPipelineDataEvent@1` for cross-adapter communication.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | `$` | Source data path |
| `targetPath` | string | `$` | Where to place in output |

```yaml
- type: ToPipelineDataEvent@1
  description: Send to mesh
```

### ToWebhook@1

Send data to an HTTP endpoint via POST.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Data to send |
| `uri` | string | required | Target HTTP endpoint URI |
| `apiKey` | string | optional | Value for `XApiKey` header |
| `timeoutSeconds` | int | 30 | HTTP timeout |

```yaml
- type: ToWebhook@1
  path: $.results
  uri: https://api.example.com/webhook
  apiKey: my-secret-key
  timeoutSeconds: 60
```

---

## Transform Nodes

### Concat@1

Concatenate string parts (static values and dynamic paths).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Path to objects to process |
| `parts` | array | required | Array of `{value, valuePath}` objects |
| `concatSubPath` | string | required | Sub-path to store result on each object |

```yaml
- type: Concat@1
  path: $.orders[*]
  concatSubPath: $.compositeKey
  parts:
    - valuePath: $.OrderNumber
    - value: "_"
    - valuePath: $.ItemNumber
```

### FormatString@1

Format string with JSONPath placeholders.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `format` | string | required | Format string with `{$.jsonpath}` placeholders |
| `nullValue` | string | `NULL` | Replacement for null values |
| `targetPath` | string | required | Where to store result |
| `documentMode` | enum | Extend | Extend/Replace |
| `targetValueKind` | enum | Simple | Simple/Array |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append/Prepend/Merge |

```yaml
- type: FormatString@1
  format: "Order {$.key.OrderNumber} has {$.key.ItemCount} items"
  targetPath: $.key.summary
```

### TransformString@1

String manipulation operations.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source objects path |
| `sourcePath` | string | required | Relative path to string value |
| `targetPath` | string | required | Where to store result |
| `operation` | enum | required | Trim, TrimStart, TrimEnd, ToUpper, ToLower, SubstringFromStart, SubstringFromEnd, Substring |
| `startIndex` | int | 0 | Start index for Substring |
| `length` | int | optional | Length for Substring |

```yaml
- type: TransformString@1
  path: $.items[*]
  sourcePath: $.Name
  targetPath: $.NameUpper
  operation: ToUpper
```

### Hash@1

Compute cryptographic hash.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source objects path |
| `sourcePath` | string | required | Relative path to value |
| `targetPath` | string | required | Where to store hex hash |
| `algorithm` | enum | required | Md5, Sha1, Sha256, Sha384, Sha512 |
| `inputFormat` | enum | String | String (UTF-8) or Base64 |

```yaml
- type: Hash@1
  path: $.items[*]
  sourcePath: $.Content
  targetPath: $.ContentHash
  algorithm: Sha256
```

### Base64Encode@1 / Base64Decode@1

Encode/decode Base64.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source objects path |
| `sourcePath` | string | required | Relative path to value |
| `targetPath` | string | required | Where to store result |

```yaml
- type: Base64Encode@1
  path: $.items[*]
  sourcePath: $.RawData
  targetPath: $.EncodedData
```

### ConvertDataType@1

Convert value to different type.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source value path |
| `targetPath` | string | required | Where to store converted value |
| `valueType` | enum | required | String, Int, Int64, Double, Boolean |

```yaml
- type: ConvertDataType@1
  path: $.stringValue
  targetPath: $.intValue
  valueType: Int
```

### Flatten@1

Flatten nested arrays into a single array.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source path with nested arrays |
| `targetPath` | string | required | Where to store flat array |
| `targetValueWriteMode` | enum | Overwrite | Overwrite/Append |

```yaml
- type: Flatten@1
  path: $.items[*].subItems[*]
  targetPath: $.allSubItems

# Append to existing array
- type: Flatten@1
  path: $.more[*].subItems[*]
  targetPath: $.allSubItems
  targetValueWriteMode: Append
```

### Project@1

Field projection — include or exclude fields.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Objects to project |
| `fields` | array | required | Array of `{path, inclusion}` objects |
| `clear` | bool | false | If true, start empty and include only specified fields |

```yaml
- type: Project@1
  clear: true
  fields:
    - path: $.entityUpdates
      inclusion: true
    - path: $.assocUpdates
      inclusion: true
```

### Map@1

Pivot/transpose arrays into a combined result array.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source object path |
| `selectPaths` | array | required | Paths containing arrays to pivot |
| `targetPath` | string | required | Where to store pivoted array |

### Join@1

Inner join two arrays by matching key values.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source records path |
| `keyPath` | string | required | Key field in source records |
| `joinPath` | string | required | Lookup array path |
| `joinKeyPath` | string | required | Key field in lookup records |
| `itemPath` | string | required | Where to attach joined data on each source record |

```yaml
- type: Join@1
  path: $.orders[*]
  keyPath: $.CustomerId
  joinPath: $.customers[*]
  joinKeyPath: $.Id
  itemPath: $.Customer
```

### Math@1

Mathematical operations on numeric values.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source objects path |
| `itemPath` | string | required | Relative path to numeric value |
| `itemTargetPath` | string | `$.Result` | Where to store result |
| `operation` | enum | required | Add, Subtract, Multiply, Divide, Modulo, Round |
| `value` | double | optional | Static operand |
| `valuePath` | string | optional | Dynamic operand path |
| `decimalPlaces` | int | 0 | For Round operation |
| `targetPath` | string | optional | Write configuration |

```yaml
# Multiply price by quantity
- type: Math@1
  path: $.key.data
  itemPath: $.unitPrice
  operation: Multiply
  valuePath: $.key.data.quantity
  itemTargetPath: $.totalPrice

# Round to 2 decimal places
- type: Math@1
  path: $.key.data
  itemPath: $.totalPrice
  operation: Round
  decimalPlaces: 2
  itemTargetPath: $.totalPrice
```

### LinearScaler@1

Linear scaling of numeric values.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Source numeric value path |
| `targetPath` | string | required | Where to store scaled value |
| `scaleInputMin` | double | -1000000 | Input range minimum |
| `scaleInputMax` | double | 1000000 | Input range maximum |
| `scaleOutputMin` | double | -1000000 | Output range minimum |
| `scaleOutputMax` | double | 1000000 | Output range maximum |

Formula: `output = outputMin + (value - inputMin) * ((outputMax - outputMin) / (inputMax - inputMin))`

```yaml
- type: LinearScaler@1
  path: $.rawSensor
  targetPath: $.scaledValue
  scaleInputMin: 0
  scaleInputMax: 4095
  scaleOutputMin: 0
  scaleOutputMax: 100
```

### SumAggregation@1

Weighted sum aggregation with optional filtering.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `targetPath` | string | required | Where to store sum |
| `aggregations` | array | required | Array of aggregation items |

Each aggregation item:
| Property | Type | Description |
|----------|------|-------------|
| `path` | string | Source objects path |
| `aggregationPath` | string | Path to numeric values |
| `value` | double | Multiplier/weight (use -1 for subtraction) |
| `filterPath` | string | Optional filter field path |
| `comparisonValue` | string | Optional filter value (string comparison) |

```yaml
- type: SumAggregation@1
  targetPath: $.total
  aggregations:
    - path: $.debits[*]
      aggregationPath: $.Amount
      value: 1
    - path: $.credits[*]
      aggregationPath: $.Amount
      value: -1
```

### Logger@1

Log a message.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `message` | string | required | Message to log |

### PrintDebug@1

Print entire data context to log for debugging.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `severity` | enum | Information | Debug, Information, Warning, Error |

```yaml
- type: PrintDebug@1
  severity: Debug
```

### ExecuteCSharp@1

Execute dynamic C# code.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `code` | string | required | C# expression or statement |
| `arguments` | array | optional | Script arguments: `{name, valuePath, value, dataType}` |
| `returnType` | enum | required | String, Int, Int64, Boolean, Double, DateTime |
| `timeoutMs` | int | 5000 | Execution timeout |
| `usings` | array | optional | Additional using statements |
| `targetPath` | string | required | Where to store result |

```yaml
- type: ExecuteCSharp@1
  code: "return input1 + input2;"
  arguments:
    - name: input1
      valuePath: $.key.Value1
      dataType: Double
    - name: input2
      valuePath: $.key.Value2
      dataType: Double
  returnType: Double
  targetPath: $.key.sum
  usings:
    - System.Linq
```

---

## Buffering Nodes

### BufferData@1

Buffer incoming data with time-based flushing. Uses LiteDB edge buffer.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `path` | string | required | Data to buffer |
| `bufferTime` | TimeSpan | `00:05:00` | Flush interval |
| `keepDataAfterSending` | bool | false | Retain data after sending |
| `transformations` | array | required | Child nodes to execute on flush |

```yaml
- type: BufferData@1
  path: $.sensorData
  bufferTime: 00:10:00
  keepDataAfterSending: false
  transformations:
    - type: ToPipelineDataEvent@1
```

### BufferRetrievalNode@1

Retrieve and process previously buffered data.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `keepDataAfterSending` | bool | false | Retain data after retrieval |

---

## Simulation

### Simulation@1

Generate simulated data values using the Bogus library. Useful for testing pipelines without real data sources.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `locale` | string | `en` | Locale for Bogus data generation |
| `simulations` | array | required | List of simulation property configurations |

Each simulation entry:
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `targetPath` | string | required | JSONPath where the generated value is written |
| `simulatorKey` | string | `Increment` | Simulator type key (e.g., `Increment`, `Random`, `Name`) |
| `configuration` | string | `{}` | JSON configuration string for the chosen simulator |

```yaml
- type: Simulation@1
  locale: en
  simulations:
    - targetPath: $.sensor.Temperature
      simulatorKey: Random
      configuration: '{"min": 20.0, "max": 80.0}'
    - targetPath: $.sensor.SerialNumber
      simulatorKey: Increment
      configuration: '{"start": 1000}'
```
