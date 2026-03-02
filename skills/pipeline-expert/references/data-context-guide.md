# DataContext Deep Dive

The DataContext is the mutable JSON document that flows through a pipeline. Every node reads from and writes to this shared context using JSONPath expressions.

## JSONPath Conventions

- `$` — root of the current context document
- `$.property` — access a property
- `$.nested.property` — nested access
- `$.array[0]` — specific array index
- `$.array[*]` — all array elements
- `$.array[*].field` — field from each array element

The context stores data as Newtonsoft.Json `JToken` objects (JObject, JArray, JValue). Writing to a path that doesn't exist creates the intermediate structure automatically.

## Reading from Context

Nodes read values using `path` or `valuePath` properties:

| Pattern | Meaning |
|---------|---------|
| `path: $.items` | Read the `items` property from context root |
| `valuePath: $.key.Name` | Read `Name` from current iteration item |
| `path: $.orders[*]` | Select all elements in the orders array |

When both `value` and `valuePath` are specified on a node property, `valuePath` takes precedence.

## Writing to Context

Nodes write values using `targetPath` combined with three write configuration properties:

### Document Mode

Controls how the target document is treated before writing.

| Mode | Behavior |
|------|----------|
| **Extend** (default) | Preserve existing document, merge new content into it |
| **Replace** | Clear entire document, then set new content |

### Write Mode (targetValueWriteMode)

Controls how the value is written to the target path.

| Mode | For Objects | For Arrays |
|------|------------|------------|
| **Overwrite** (default) | Replace property value | Replace entire array |
| **Append** | Merge properties | Add to end of array |
| **Prepend** | N/A | Insert at start of array |
| **Merge** | Deep merge (both must be JObject) | N/A |

### Value Kind (targetValueKind)

Controls whether the value is treated as a scalar or array element.

| Kind | Behavior |
|------|----------|
| **Simple** (default) | Write value as-is |
| **Array** | Always wrap value in JArray before applying write mode |

### Common Combinations

```yaml
# Overwrite a simple value (default)
targetPath: $.result
# → $.result = newValue

# Append to an existing array
targetPath: $.items
targetValueWriteMode: Append
targetValueKind: Array
# → $.items.push(newValue)

# Collect items into an array during ForEach
targetPath: $.key.updates
targetValueWriteMode: Append
targetValueKind: Array
# → Each iteration appends to $.key.updates

# Replace entire document with new content
targetPath: $
documentMode: Replace
# → Context cleared, then set to newValue
```

## ForEach Iteration

ForEach creates child data contexts for each array element. Understanding the context hierarchy is essential.

### Context Structure

```
Root Context
├── $.orders = [{...}, {...}, {...}]   ← iterationPath
├── $.config = {...}
│
└── ForEach Child Context (per iteration)
    ├── $.full = (copy of entire root context)    ← fullDocumentPath
    ├── $.key = {current array item}              ← keyPath
    └── (child node results written here)
```

### Key Properties

| Property | Default | Purpose |
|----------|---------|---------|
| `iterationPath` | required | Array to iterate (e.g., `$.orders`) |
| `fullDocumentPath` | `$.full` | Stores complete copy of parent context |
| `keyPath` | `$.key` | Stores current iteration item |
| `mergePath` | `$.key` | Path to collect results from after each iteration |
| `targetPath` | `$` | Where to write collected results in parent context |

### Accessing Data Inside ForEach

Within ForEach child transformations:
- `$.key.PropertyName` — access current item's properties
- `$.full.OtherArray` — access data from parent context
- `$.full.config.setting` — access root-level config

### Nested ForEach

With nested ForEach, `$.full` chains:

```
Root Context
│
└── Outer ForEach (iterating $.documents)
    ├── $.full = root context
    ├── $.key = current document
    │
    └── Inner ForEach (iterating $.key.items)
        ├── $.full = outer ForEach context
        │   ├── $.full.full = root context        ← two levels up
        │   └── $.full.key = current document     ← one level up
        └── $.key = current item
```

Access pattern in deeply nested context:
- `$.key.field` — current inner item
- `$.full.key.field` — current outer item (one level up)
- `$.full.full.config` — root context (two levels up)

### Parallel Execution

`maxDegreeOfParallelism` controls concurrency:
- `0` (default) — use CPU core count
- `-1` — unlimited parallelism
- `>0` — explicit limit (e.g., `4`)

Set to `1` for sequential execution when order matters or when nodes have side effects.

## Field Filters

Many extract nodes support `fieldFilters` for server-side filtering.

### Filter Structure

```yaml
fieldFilters:
  - attributePath: Status
    operator: Equals
    comparisonValue: Active
  - attributePath: Count
    operator: GreaterThan
    comparisonValue: 0
```

### Operators

| Operator | Description |
|----------|-------------|
| `Equals` | Exact match |
| `NotEquals` | Not equal |
| `LessThan` | Numeric less than |
| `LessEqualThan` | Numeric less than or equal |
| `GreaterThan` | Numeric greater than |
| `GreaterEqualThan` | Numeric greater than or equal |
| `In` / `IN` | Value in list |
| `NotIn` | Value not in list |
| `Like` | String pattern matching |
| `MatchRegEx` | Regular expression match |
| `AnyEq` | Array: any element equals |
| `AnyLike` | Array: any element matches pattern |

### Static vs Dynamic Comparison

- `comparisonValue` — static literal value
- `comparisonValuePath` — JSONPath to dynamic value from context

```yaml
# Static: match exact string
fieldFilters:
  - attributePath: Name
    operator: Equals
    comparisonValue: "SensorA"

# Dynamic: match against values from context
fieldFilters:
  - attributePath: MeteringPointNumber
    operator: IN
    comparisonValuePath: $.MeteringPointNumbers

# Path-based attributes (navigation through associations)
fieldFilters:
  - attributePath: parent.facility->customer.company->rtId
    operator: In
    comparisonValuePath: $.customerIds
```

### Sort Orders

```yaml
sortOrders:
  - attributePath: CreatedAt
    sortOrder: Descending
```

## CreateUpdateInfo Attribute Updates

The `attributeUpdates` array in CreateUpdateInfo defines which entity attributes to set.

### Attribute Update Structure

```yaml
attributeUpdates:
  - attributeName: OrderNumber        # CK attribute name
    attributeValueType: String        # Value type
    valuePath: $.key.OrderNumber      # Dynamic value from context
  - attributeName: Status
    attributeValueType: Enum
    value: 1                          # Static value
```

### Supported Value Types

| Type | Description |
|------|-------------|
| `String` | Text value |
| `Int` | 32-bit integer |
| `Int64` | 64-bit integer |
| `Double` | Floating point |
| `Boolean` | True/false |
| `DateTime` | Date and time |
| `TimeSpan` | Duration |
| `Enum` | Enumeration (stored as integer) |

### Value Resolution

1. If `valuePath` is set: read value from context at that path
2. If `value` is set (and no valuePath): use the literal value
3. If neither: attribute is skipped

## Association Updates

CreateAssociationUpdate defines relationships between entities.

### Structure

```yaml
- type: CreateAssociationUpdate@1
  targetPath: $.key.assocUpdates
  targetValueWriteMode: Append
  targetValueKind: Array
  updateKind: CREATE                              # CREATE or DELETE
  originRtIdPath: $.key.childEntity.RtId          # "from" entity
  originCkTypeId: Industry.Manufacturing/Item     # "from" type
  targetRtIdPath: $.key.parentEntity.RtId         # "to" entity
  targetCkTypeId: Industry.Manufacturing/Order    # "to" type
  associationRoleId: System/ParentChild           # relationship type
```

### Update Kinds

| Kind | Description |
|------|-------------|
| `CREATE` | Create new association between entities |
| `DELETE` | Remove existing association |

### Common Association Roles

| Role | Purpose |
|------|---------|
| `System/ParentChild` | Hierarchical parent-child relationship |
| `System.Communication/Tag` | Tag assignment to entity |
| Domain-specific roles | e.g., `Industry.Manufacturing/MachineOrderAssignment` |
