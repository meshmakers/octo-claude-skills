# Pipeline Examples

Real-world annotated pipeline examples from OctoMesh deployments.

## 1. Watch Entity Trigger with Email Notification

Watches for new Alarm entities, navigates the association tree to find context (machine, department, plant), then sends a templated email notification.

**Origin:** a manufacturing customer deployment (external — not in this monorepo; names anonymized)

```yaml
triggers:
  # Fire on every new Alarm entity
  - type: FromWatchRtEntity@1
    updateTypes: Insert
    ckTypeId: Industry.Basic/Alarm

transformations:
  # Follow association from Alarm → Machine
  - type: GetAssociationTargets@1
    graphDirection: Outbound
    originRtIdPath: $.Document.RtId
    originCkTypeId: Industry.Basic/Alarm
    targetCkTypeId: Industry.Basic/Machine
    targetPath: $.Machine
    associationRoleId: Industry.Basic/EventSource

  # Only process alarms for machines matching "MAFEB"
  - type: If@1
    path: $.Machine.Attributes.Name
    operator: Contains
    value: MAFEB
    valueType: String
    transformations:
      # Walk up hierarchy: Machine → Department → Area → Plant
      - type: GetAssociationTargets@1
        graphDirection: Outbound
        originRtIdPath: $.Machine.RtId
        originCkTypeId: Industry.Basic/Machine
        targetCkTypeId: Basic/TreeNode
        targetPath: $.Department
        associationRoleId: System/ParentChild

      - type: GetAssociationTargets@1
        graphDirection: Outbound
        originRtIdPath: $.Department.RtId
        originCkTypeId: Basic/TreeNode
        targetCkTypeId: Basic/TreeNode
        targetPath: $.Area
        associationRoleId: System/ParentChild

      - type: GetAssociationTargets@1
        graphDirection: Outbound
        originRtIdPath: $.Area.RtId
        originCkTypeId: Basic/TreeNode
        targetCkTypeId: Basic/TreeNode
        targetPath: $.Plant
        associationRoleId: System/ParentChild

      # Load email template
      - type: GetNotificationTemplate@1
        notificationTemplateName: <alarm-template>
        targetPath: $.body
        subjectTargetPath: $.subject

      # Fill placeholders in subject and body
      - type: PlaceholderReplace@1
        path: $.subject
        targetPath: $.resultSubject
        replaceRules:
          - placeholder: MachineName
            path: $.Machine.Attributes.Name

      - type: PlaceholderReplace@1
        path: $.body
        targetPath: $.resultBody
        replaceRules:
          - placeholder: MachineName
            path: $.Machine.Attributes.Name
          - placeholder: AlarmDate
            path: $.Document.Attributes.Time
          - placeholder: ErrorCode
            path: $.Document.Attributes.Type
          - placeholder: ErrorText
            path: $.Document.Attributes.Message
          - placeholder: Department
            path: $.Department.Attributes.Name
          - placeholder: Area
            path: $.Area.Attributes.Name
          - placeholder: Plant
            path: $.Plant.Attributes.Name

      # Set recipients and send
      - type: SetPrimitiveValue@1
        value:
          - user@example.com
        targetValueKind: Simple
        targetPath: $.to

      - type: SendEMail@1
        serverConfiguration: sendgrid
        subjectPath: $.resultSubject
        path: $.resultBody
        toPath: $.to
```

**Key patterns:** FromWatchRtEntity trigger, association traversal, conditional processing, template-based email.

---

## 2. Cross-Adapter DataFlow (Zenon Variable Sync)

Two-part DataFlow with cross-adapter communication: a pipeline on the Mesh Adapter watches for entity changes and sends data via the event hub; a pipeline on the Zenon Adapter receives it and writes to PLC variables. Both pipelines belong to the same DataFlow.

**Origin:** a manufacturing customer deployment (external — not in this monorepo; names anonymized)

### Mesh Adapter Pipeline (sends data)

```yaml
triggers:
  - type: FromWatchRtEntity@1
    updateTypes: Update
    ckTypeId: Industry.Manufacturing/ProductionOrderItem
    fieldFilters:
      - attributePath: RtWellKnownName
        operator: Equals
        comparisonValue: "000003265748_000000"

transformations:
  # Find the machine linked to this order item
  - type: GetAssociationTargets@1
    graphDirection: Outbound
    originRtIdPath: $.Document.RtId
    originCkTypeId: Industry.Manufacturing/ProductionOrderItem
    targetCkTypeId: Industry.Basic/Machine
    targetPath: $.Machine
    associationRoleId: Industry.Manufacturing/MachineOrderAssignment

  # Find the Zenon tag for quantity on this machine
  - type: GetAssociationTargets@1
    graphDirection: Inbound
    originRtIdPath: $.Machine.RtId
    originCkTypeId: Industry.Basic/Machine
    targetCkTypeId: System.Communication/Tag
    targetPath: $.Tag
    associationRoleId: System.Communication/Tag
    fieldFilters:
      - attributePath: Tag
        operator: Like
        comparisonValue: StandardDaten.Artikelmenge

  # Find the Zenon tag for article number
  - type: GetAssociationTargets@1
    graphDirection: Inbound
    originRtIdPath: $.Machine.RtId
    originCkTypeId: Industry.Basic/Machine
    targetCkTypeId: System.Communication/Tag
    targetPath: $.TagArtNr
    associationRoleId: System.Communication/Tag
    fieldFilters:
      - attributePath: Tag
        operator: Like
        comparisonValue: StandardDaten.AktArtikel

  # Send entire context to the Zenon Adapter pipeline (both pipelines must be in the same DataFlow)
  - type: ToPipelineDataEvent@1
    targetPipelineRtId: <zenon-pipeline-rtId>
```

### Zenon Adapter Pipeline (receives data)

```yaml
triggers:
  - type: FromPipelineDataEvent@1

transformations:
  # Write values to Zenon PLC variables
  - type: SetZenonVariables@1
    dataPointConfigurations:
      - variablePath: $.Tag.Attributes.Tag
        valuePath: $.Document.Attributes.PlannedQuantity
        valueType: Double
      - variablePath: $.TagArtNr.Attributes.Tag
        valuePath: $.Document.Attributes.ArticleNumber
        valueType: String
```

**Key patterns:** ToPipelineDataEvent/FromPipelineDataEvent pair, Inbound/Outbound association traversal, field filter with Like operator, SetZenonVariables.

---

## 3. Polling Pipeline with SAP Import and ForEach

Cross-adapter DataFlow: one pipeline polls SAP for production orders, iterates with conditional processing, and sends data to a second pipeline that creates entities and associations.

**Origin:** a manufacturing customer deployment (external — not in this monorepo; names anonymized)

### SAP Polling Pipeline (data extraction)

```yaml
triggers:
  - type: FromPolling@1
    interval: 00:01:00

transformations:
  - type: SapLogin@1
    sapConfiguration: <sap-configuration>

  - type: GetProductionOrderList@1
    productionPlant: <plant>
    orderNumberStart: 3265680
    targetPath: "$.orders"

  # Iterate orders, conditionally fetch details
  - type: ForEach@1
    iterationPath: $.orders
    targetPath: $.orders
    fullDocumentPath: $.full
    keyPath: $.key
    mergePath: $.key
    transformations:
      # Only process Released orders
      - type: If@1
        operator: Contains
        value: REL
        valueType: String
        path: $.key.SystemStatus
        transformations:
          - type: GetProductionOrderDetails@1
            path: $.key.OrderNumber
            readHeader: true
            readOperations: true
            targetPath: $.key.result

          # Keep only needed fields (SequenceNumber builds the orderItemId
          # key and ItemNumber in the entity-creation pipeline below)
          - type: Project@1
            clear: true
            fields:
              - path: $.key.result.Header.OrderNumber
                inclusion: true
              - path: $.key.result.Header.Material
                inclusion: true
              - path: $.key.result.Header.SystemStatus
                inclusion: true
              - path: $.key.result.Operation.SequenceNumber
                inclusion: true
              - path: $.key.result.Operation.WorkCenter
                inclusion: true
              - path: $.key.result.Operation.Quantity
                inclusion: true

  - type: Flatten@1
    path: $.orders[*].result
    targetPath: $.orders

  # Send to entity-creation pipeline (both must be in the same DataFlow)
  - type: ToPipelineDataEvent@1
    targetPipelineRtId: <entity-creation-pipeline-rtId>
```

### Entity Creation Pipeline (receives data)

```yaml
triggers:
  - type: FromPipelineDataEvent@1

transformations:
  # Generate composite keys
  - type: Concat@1
    path: $.orders[*]
    concatSubPath: $.orderItemId
    parts:
      - valuePath: $.Header.OrderNumber
      - value: _
      - valuePath: $.Operation.SequenceNumber

  # Lookup or prepare INSERT for orders
  - type: GetRtEntitiesByWellKnownName@1
    ckTypeId: Industry.Manufacturing/ProductionOrder
    path: $.orders[*]
    wellKnownNamePath: $.Header.OrderNumber
    rtIdTargetPath: $.order.rtId
    ckTypeIdTargetPath: $.order.ckTypeId
    modOperationPath: $.order.modOperation
    generateInsertOperation: true

  # Lookup or prepare INSERT for order items
  - type: GetRtEntitiesByWellKnownName@1
    ckTypeId: Industry.Manufacturing/ProductionOrderItem
    path: $.orders[*]
    wellKnownNamePath: $.orderItemId
    rtIdTargetPath: $.orderItem.rtId
    ckTypeIdTargetPath: $.orderItem.ckTypeId
    modOperationPath: $.orderItem.modOperation
    generateInsertOperation: true

  # For each order: create entities + associations
  - type: ForEach@1
    iterationPath: $.orders
    targetPath: $.updateItems
    fullDocumentPath: $.full
    keyPath: $.key
    mergePath: $.key
    transformations:
      # Find machine by work center name
      - type: GetRtEntitiesByWellKnownName@1
        ckTypeId: Industry.Basic/Machine
        path: $.key.Operation
        wellKnownNamePath: $.WorkCenter
        rtIdTargetPath: $.machine.rtId
        modOperationPath: $.machine.modOperation

      # Only create entities if machine was found (modOperation=1 means Update=found)
      - type: If@1
        valueType: Int
        path: $.key.Operation.machine.modOperation
        value: 1
        transformations:
          # Create/update order entity
          - type: CreateUpdateInfo@1
            targetPath: $.key.orderUpdate
            updateKindPath: $.key.order.modOperation
            rtIdPath: $.key.order.rtId
            ckTypeId: Industry.Manufacturing/ProductionOrder
            rtWellKnownNamePath: $.key.Header.OrderNumber
            attributeUpdates:
              - attributeName: OrderNumber
                attributeValueType: String
                valuePath: $.key.Header.OrderNumber

          # Create/update order item entity
          - type: CreateUpdateInfo@1
            targetPath: $.key.orderItemUpdate
            updateKindPath: $.key.orderItem.modOperation
            rtIdPath: $.key.orderItem.rtId
            ckTypeId: Industry.Manufacturing/ProductionOrderItem
            rtWellKnownNamePath: $.key.orderItemId
            attributeUpdates:
              - attributeName: ItemNumber
                attributeValueType: Int
                valuePath: $.key.Operation.SequenceNumber
              - attributeName: PlannedQuantity
                attributeValueType: Double
                valuePath: $.key.Operation.Quantity

          # Create association: OrderItem → Order (ParentChild)
          - type: If@1
            valueType: Int
            path: $.key.orderItemUpdate.ModOption
            value: 0
            transformations:
              - type: CreateAssociationUpdate@1
                targetPath: $.key.assoc
                targetValueWriteMode: Append
                targetValueKind: Array
                targetRtIdPath: $.key.orderUpdate.RtId
                targetCkTypeId: Industry.Manufacturing/ProductionOrder
                originRtIdPath: $.key.orderItemUpdate.RtId
                originCkTypeId: Industry.Manufacturing/ProductionOrderItem
                associationRoleId: System/ParentChild

              # Association: OrderItem → Machine
              - type: CreateAssociationUpdate@1
                targetPath: $.key.assoc
                targetValueWriteMode: Append
                targetValueKind: Array
                targetRtIdPath: $.key.Operation.machine.rtId
                targetCkTypeId: Industry.Basic/Machine
                originRtIdPath: $.key.orderItemUpdate.RtId
                originCkTypeId: Industry.Manufacturing/ProductionOrderItem
                associationRoleId: Industry.Manufacturing/MachineOrderAssignment

  # Flatten and apply all changes
  - type: Flatten@1
    path: $.updateItems[*].orderUpdate
    targetPath: $.entityUpdateItems
  - type: Flatten@1
    path: $.updateItems[*].orderItemUpdate
    targetPath: $.entityUpdateItems
    targetValueWriteMode: Append

  - type: Flatten@1
    path: $.updateItems[*].assoc[*]
    targetPath: $.assocUpdateItems

  - type: Project@1
    clear: true
    fields:
      - path: $.entityUpdateItems
        inclusion: true
      - path: $.assocUpdateItems
        inclusion: true

  - type: ApplyChanges@2
    entityUpdatesPath: $.entityUpdateItems
    associationUpdatesPath: $.assocUpdateItems
```

**Key patterns:** FromPolling trigger, ForEach with If, Concat for composite keys, GetRtEntitiesByWellKnownName with generateInsertOperation, dynamic updateKindPath, CreateAssociationUpdate, Flatten with Append, ApplyChanges@2.

---

## 4. Variable Import with Type Switch

Receives Zenon variable data via inter-pipeline communication (DataFlow event hub), looks up each variable, switches on data type to create type-specific updates, saves to both a CrateDB archive and MongoDB.

**Origin:** a manufacturing customer deployment (external — not in this monorepo; names anonymized)

```yaml
triggers:
  - type: FromPipelineDataEvent@1

transformations:
  # Batch lookup all variables by well-known name
  - type: GetRtEntitiesByWellKnownName@1
    ckTypeId: Industry.Basic/RuntimeVariable
    wellKnownNamePath: $.VariableName
    rtIdTargetPath: $.rtId
    ckTypeIdTargetPath: $.ckTypeId
    modOperationPath: $.modOperation
    attributeTargetPath: $.attributes
    path: $.Data[*]

  # For each variable, create type-appropriate update
  - type: ForEach@1
    iterationPath: $.Data
    targetPath: $.Data
    fullDocumentPath: $.full
    keyPath: $.key
    mergePath: $.key
    transformations:
      # Switch on IEC data type to pick correct attribute
      - type: Switch@1
        path: $.key.attributes.IecDataType
        valueType: Int
        cases:
          - value: 8                    # Boolean
            transformations:
              - type: CreateUpdateInfo@1
                updateKind: Update
                rtIdPath: $.key.rtId
                ckTypeIdPath: $.key.ckTypeId
                timestampPath: $.key.Timestamp
                attributeUpdates:
                  - attributeName: BooleanValue
                    attributeValueType: Boolean
                    valuePath: $.key.Value
                targetPath: $.key._entityUpdates
                targetValueWriteMode: Append
                targetValueKind: Array
          - value: [12, 21]             # String types
            transformations:
              - type: CreateUpdateInfo@1
                updateKind: Update
                rtIdPath: $.key.rtId
                ckTypeIdPath: $.key.ckTypeId
                timestampPath: $.key.Timestamp
                attributeUpdates:
                  - attributeName: StringValue
                    attributeValueType: String
                    valuePath: $.key.Value
                targetPath: $.key._entityUpdates
                targetValueWriteMode: Append
                targetValueKind: Array
          - value: [1, 2, 3, 4, 9, 10, 22, 23, 24]  # Integer types
            transformations:
              - type: CreateUpdateInfo@1
                updateKind: Update
                rtIdPath: $.key.rtId
                ckTypeIdPath: $.key.ckTypeId
                timestampPath: $.key.Timestamp
                attributeUpdates:
                  - attributeName: IntValue
                    attributeValueType: Int
                    valuePath: $.key.Value
                targetPath: $.key._entityUpdates
                targetValueWriteMode: Append
                targetValueKind: Array
          - value: [5, 6]               # Floating point types
            transformations:
              - type: CreateUpdateInfo@1
                updateKind: Update
                rtIdPath: $.key.rtId
                ckTypeIdPath: $.key.ckTypeId
                timestampPath: $.key.Timestamp
                attributeUpdates:
                  - attributeName: DoubleValue
                    attributeValueType: Double
                    valuePath: $.key.Value
                targetPath: $.key._entityUpdates
                targetValueWriteMode: Append
                targetValueKind: Array

  # Flatten all updates from all iterations
  - type: Flatten@1
    path: $.Data[*]._entityUpdates[*]
    targetPath: $._entityUpdates

  # Save to a CrateDB archive (archiveRtId must reference an Activated CkArchive)
  - type: SaveStreamDataInArchive@1
    path: $._entityUpdates
    archiveRtId: cc0000000000000000000aa1

  # Keep only latest per entity for MongoDB
  - type: FilterLatestUpdateInfo@1
    path: $._entityUpdates
    targetPath: $._entityUpdates

  # Apply to MongoDB
  - type: ApplyChanges@2
    entityUpdatesPath: $._entityUpdates
```

**Key patterns:** Switch with array case values, timestampPath for archive rows, SaveStreamDataInArchive + FilterLatestUpdateInfo + ApplyChanges@2 triple for the dual-store pattern (`SaveStreamDataInArchive@1` replaces the removed `SaveInTimeSeries@1` and requires `archiveRtId`).

---

## 5. HTTP-Triggered Billing with Nested ForEach and Math

Complex billing calculation pipeline: loads config, queries data with joins, iterates billing documents and their line items, performs math calculations, creates entities and associations.

**Origin:** energy-community deployment (external — not in this monorepo)

```yaml
triggers:
  # The deployment used the deprecated FromHttpRequest@1, which is always public; @2 keeps the route
  # authenticated (any valid token of the tenant; requiredRoles narrows it).
  - type: FromHttpRequest@2
    path: /createBillingItems
    method: POST

transformations:
  # Load configuration from global config store
  - type: GetPipelineConfigByWellKnownName@1
    wellKnownName: "EnergyCommunityConfiguration"
    targetPath: $.config

  # Extract config values into typed properties
  - type: SetPrimitiveValue@1
    targetPath: $.Configuration.taxRate
    valuePath: $.config.taxRate
    valueType: Double
  - type: SetPrimitiveValue@1
    targetPath: $.Configuration.consumerPrice
    valuePath: $.config.consumerPrice
    valueType: Double

  # Query billing documents
  - type: GetQueryById@1
    queryRtId: "683177dcb90d979b8ae558a1"
    targetPath: $.documents
    fieldFilters:
      - attributePath: billingDocumentState
        operator: Equals
        comparisonValue: 0
      - attributePath: rtId
        operator: In
        comparisonValuePath: $.body.billingDocumentRtIds

  # Query metering points with association-path filter
  - type: GetQueryById@1
    queryRtId: "693996d37a64d9a8f73b3832"
    targetPath: $.meteringPoints
    fieldFilters:
      - attributePath: parent.facility->customer.company->rtId
        operator: In
        comparisonValuePath: $.documents.Rows[*].Values[2]

  # Join metering data with billing documents
  - type: Join@1
    path: $.documents.Rows[*]
    keyPath: $.Values[2]
    joinPath: $.meteringPoints.Rows[*]
    joinKeyPath: $.Values[1]
    itemPath: $.meteringPoints

  # Outer loop: iterate billing documents
  - type: ForEach@1
    iterationPath: $.documents.Rows
    mergePath: $._updateItems
    targetPath: $._updateItems
    transformations:
      # Inner loop: iterate metering points per document
      - type: ForEach@1
        iterationPath: $.key.meteringPoints
        mergePath: $.updates
        targetPath: $.updates
        transformations:
          # Initialize accumulator
          - type: SetPrimitiveValue@1
            targetPath: $.key.data.sum
            value: 0
            valueType: Int

          - type: If@1
            path: $.key.quantities[0].RtId
            operator: NotEqual
            value: null
            valueType: String
            transformations:
              # Sum energy quantities
              - type: SumAggregation@1
                targetPath: $.key.data.sum
                aggregations:
                  - path: $.key.quantities[*]
                    filterPath: null          # no filter, but the key must be present
                    comparisonValue: null
                    aggregationPath: $.Values[2]
                    value: 1

              # Set price based on entity type
              - type: Switch@1
                path: $.key.quantities[0].Values[7].SemanticVersionedFullName
                valueType: String
                cases:
                  - value: "EnergyCommunity/Consumer"
                    transformations:
                      - type: SetPrimitiveValue@1
                        targetPath: $.key.data.unitPrice
                        # Access root config via $.full.full (two levels up)
                        valuePath: $.full.full.Configuration.consumerPrice
                        valueType: Double
                  - value: "EnergyCommunity/Producer"
                    transformations:
                      - type: SetPrimitiveValue@1
                        targetPath: $.key.data.unitPrice
                        valuePath: $.full.full.Configuration.producerPrice
                        valueType: Double

              # Calculate: netAmount = unitPrice * quantity
              - type: Math@1
                path: $.key.data
                itemPath: $.sum
                operation: Multiply
                valuePath: $.key.data.unitPrice
                itemTargetPath: $.netAmount

              # Calculate: taxFactor = taxRate / 100
              - type: Math@1
                path: $.key.data
                itemPath: $.taxRate
                operation: Divide
                value: 100
                itemTargetPath: $.taxFactor

              # Calculate: taxAmount = netAmount * taxFactor
              - type: Math@1
                path: $.key.data
                itemPath: $.netAmount
                operation: Multiply
                valuePath: $.key.data.taxFactor
                itemTargetPath: $.taxAmount

              # Calculate: grossAmount = netAmount + taxAmount
              - type: Math@1
                path: $.key.data
                itemPath: $.netAmount
                operation: Add
                valuePath: $.key.data.taxAmount
                itemTargetPath: $.grossAmount

              # Create billing line item entity
              - type: CreateUpdateInfo@1
                targetPath: $.updates._items
                updateKind: Insert
                ckTypeId: EnergyCommunity/BillingDocumentLineItem
                rtIdPath: $.key.data.lineItemRtId   # empty: generateRtId needs rtIdPath to create the id
                generateRtId: true                  # the association below reads it from the update item
                attributeUpdates:
                  - attributeName: GrossAmount
                    attributeValueType: Double
                    valuePath: $.key.data.grossAmount
                  - attributeName: NetAmount
                    attributeValueType: Double
                    valuePath: $.key.data.netAmount
                  - attributeName: TaxAmount
                    attributeValueType: Double
                    valuePath: $.key.data.taxAmount
                  - attributeName: UnitPrice
                    attributeValueType: Double
                    valuePath: $.key.data.unitPrice

              # Associate line item to billing document
              - type: CreateAssociationUpdate@1
                targetPath: $.updates._assocUpdateItems
                targetValueKind: Array
                targetValueWriteMode: Append
                updateKind: CREATE
                originRtIdPath: $.updates._items.RtId
                originCkTypeIdPath: $.updates._items.CkTypeId
                targetRtIdPath: $.full.key.Values[0]
                targetCkTypeIdPath: $.full.key.Values[1].SemanticVersionedFullName
                associationRoleId: System/ParentChild

  # Flatten all entity and association updates
  - type: Flatten@1
    path: $._updateItems[*]._items[*]
    targetPath: $._result.billingItems

  - type: Flatten@1
    path: $._updateItems[*]._assocUpdateItems[*]
    targetPath: $._result.assocUpdateItems

  # Apply all changes
  - type: ApplyChanges@2
    entityUpdatesPath: $._result.billingItems
    associationUpdatesPath: $._result.assocUpdateItems
```

**Key patterns:** Nested ForEach (2 levels), `$.full.full` to access root config from inner loop, Math chain for calculations, Switch for conditional pricing, SumAggregation, generateRtId, Join with query results.

---

## 6. Execute Pipeline Command with Data Mapping

Processes EDA messages with parsing, joining, and conditional entity creation based on mapped values.

**Origin:** energy-community deployment (external — not in this monorepo). Uses EDA nodes that ship in an external `octo-adapter-eda` repo — node properties here are illustrative and unverified against source.

```yaml
triggers:
  - type: FromExecutePipelineCommand@1

transformations:
  # Query pending EDA messages
  - type: GetQueryById@1
    targetPath: $.query
    queryRtId: 688b047f5f17dc195d83ca1d
    take: 1

  # Only process if messages exist
  - type: If@1
    path: $.query.Rows[0].RtId
    operator: NotEqual
    value: null
    valueType: String
    transformations:
      # Parse each message
      - type: ForEach@1
        iterationPath: $.query.Rows
        mergePath: $.EdaMessage
        targetPath: $.EdaMessages
        transformations:
          - type: EdaParseMessage@1
            messageRtIdPath: $.key.RtId
            messageTypePath: $.key.Values[0]
            processRtIdPath: $.key.Values[1]
            rawMessagePath: $.key.Values[2]
            targetPath: $.EdaMessage

      # Extract and flatten metering points
      - type: Flatten@1
        path: $.EdaMessages[*].MeteringPoints[*]
        targetPath: $.MeteringPoints
      - type: Flatten@1
        path: $.MeteringPoints[*].MeteringPointNumber
        targetPath: $.MeteringPointNumbers

      # Bulk-load entities using IN filter with dynamic values
      - type: GetRtEntitiesByType@1
        ckTypeId: EnergyCommunity/Producer
        targetPath: $.Producer
        fieldFilters:
          - attributePath: MeteringPointNumber
            operator: IN
            comparisonValuePath: $.MeteringPointNumbers

      # Join producers with metering data
      - type: If@1
        path: $.Producer.TotalCount
        operator: GreaterThan
        value: 0
        valueType: Int
        transformations:
          - type: Join@1
            path: $.MeteringPoints[*]
            keyPath: $.MeteringPointNumber
            joinPath: $.Producer.Items[*]
            joinKeyPath: $.Attributes.MeteringPointNumber
            itemPath: $.Producer

      # For each metering point, create typed updates
      - type: ForEach@1
        iterationPath: $.MeteringPoints
        mergePath: $.Updates
        targetPath: $.updates
        transformations:
          # Map direction to CK type
          - type: DataMapping@1
            path: $.key.Direction
            targetPath: $.key.ckType
            sourceValueType: Int
            targetValueType: String
            mappings:
              - sourceValue: 1
                targetValue: EnergyCommunity/Consumer
              - sourceValue: 2
                targetValue: EnergyCommunity/Producer

          # Map active state to enum
          - type: DataMapping@1
            path: $.key.IsActive
            targetPath: $.key.State
            sourceValueType: String
            targetValueType: Int
            mappings:
              - sourceValue: "True"
                targetValue: 1
              - sourceValue: "False"
                targetValue: 2

          # Update existing entity
          - type: If@1
            path: $.key.RtId
            operator: NotEqual
            value: null
            valueType: String
            transformations:
              - type: CreateUpdateInfo@1
                targetPath: $.Updates.UpdateMeteringPoint
                updateKind: Update
                ckTypeIdPath: $.key.ckType
                rtIdPath: $.key.RtId
                attributeUpdates:
                  - attributeName: PartitionFactor
                    attributeValueType: Int
                    valuePath: $.key.ParticipationFactor
                  - attributeName: State
                    attributeValueType: Enum
                    valuePath: $.key.State

          # Create new entity if doesn't exist
          - type: If@1
            path: $.key.RtId
            operator: Equal
            value: null
            valueType: String
            transformations:
              - type: CreateUpdateInfo@1
                targetPath: $.Updates.NewMeteringPoint
                updateKind: Insert
                ckTypeId: EnergyCommunity/EdaMeteringPoint
                attributeUpdates:
                  - attributeName: MeteringPointNumber
                    attributeValueType: String
                    valuePath: $.key.MeteringPointNumber
                  - attributeName: PartitionFactor
                    attributeValueType: Int
                    valuePath: $.key.ParticipationFactor

      # Flatten and apply separately
      - type: Flatten@1
        path: $.updates[*].NewMeteringPoint
        targetPath: $.NewMeteringPoints
      - type: Flatten@1
        path: $.updates[*].UpdateMeteringPoint
        targetPath: $.Result

      - type: ApplyChanges@2
        entityUpdatesPath: $.NewMeteringPoints
      - type: ApplyChanges@2
        entityUpdatesPath: $.Result
```

**Key patterns:** FromExecutePipelineCommand trigger, DataMapping for value translation, IN filter with comparisonValuePath, Join for entity enrichment, conditional Insert vs Update based on null check, separate ApplyChanges calls for new vs existing entities.


---

## 7. CSV Import with Upsert per Natural Key

Imports monthly electricity meter readings from an uploaded CSV file and stores **one reading per meter and month**: a second upload of the same month updates the reading instead of adding a duplicate. The pattern fits every "import rows, keep one entity per business key" case.

**Verified** (AB#9085): every node and property below is checked against the Mesh Adapter pipeline JSON Schema (strict: required properties and no unknown keys). Validate your own copy on the tenant with `validate_pipeline_definition` and try it with `dry_run_pipeline` before you deploy it.

**CK type** (in your model, e.g. `Demo.MeterReadings`): `MeterReading` with the attributes `MeterNumber` (String), `ReadingMonth` (String, `yyyy-MM`) and `ConsumptionKwh` (Double). The natural key `<meter>_<month>` is the entity's `rtWellKnownName`, so no extra key attribute and no query are needed to find an existing reading.

**Input file** (`;`-separated, header row, Austrian decimal comma):

```text
MeterNumber;Month;ConsumptionKwh
AT0012345;2026-10;312,5
AT0012346;2026-10;128,0
```

```yaml
triggers:
  # POST multipart/form-data with the CSV as first file; any caller with a valid token
  - type: FromHttpRequest@2
    method: POST
    path: /meter-readings/import

transformations:
  # 1. Parse the uploaded file ($.files[0].data) into one object per CSV row
  - type: ImportFromCsv@1
    fileIndex: 0
    delimiter: ";"
    hasHeaderRow: true
    targetPath: $.rows
    columnMappings:
      - sourceColumn: MeterNumber
        targetProperty: meterNumber
        dataType: String
      - sourceColumn: Month            # e.g. 2026-10
        targetProperty: month
        dataType: String
      - sourceColumn: ConsumptionKwh
        targetProperty: consumptionKwh
        dataType: Double
        numberCulture: de-AT

  # 2. Natural key: one reading per meter and month, e.g. "AT0012345_2026-10"
  - type: Concat@1
    path: $.rows[*]
    concatSubPath: $.readingKey
    parts:
      - valuePath: $.meterNumber
      - value: _
      - valuePath: $.month

  # 3. Look up an existing reading by that key (rtWellKnownName); a missing one gets an Insert
  - type: GetRtEntitiesByWellKnownName@1
    ckTypeId: Demo.MeterReadings/MeterReading
    path: $.rows[*]
    wellKnownNamePath: $.readingKey
    rtIdTargetPath: $.rtId
    ckTypeIdTargetPath: $.ckTypeId
    modOperationPath: $.modOperation
    generateInsertOperation: true

  # 4. One update per row: Insert or Update, keyed by the natural key
  - type: ForEach@1
    iterationPath: $.rows
    targetPath: $.updateItems
    fullDocumentPath: $.full
    keyPath: $.key
    mergePath: $.key
    transformations:
      - type: CreateUpdateInfo@1
        targetPath: $.key.update
        updateKindPath: $.key.modOperation
        rtIdPath: $.key.rtId
        ckTypeId: Demo.MeterReadings/MeterReading
        rtWellKnownNamePath: $.key.readingKey
        attributeUpdates:
          - attributeName: MeterNumber
            attributeValueType: String
            valuePath: $.key.meterNumber
          - attributeName: ReadingMonth
            attributeValueType: String
            valuePath: $.key.month
          - attributeName: ConsumptionKwh
            attributeValueType: Double
            valuePath: $.key.consumptionKwh

  # 5. Collect the updates and write them in one transaction
  - type: Flatten@1
    path: $.updateItems[*].update
    targetPath: $.entityUpdates

  - type: ApplyChanges@2
    entityUpdatesPath: $.entityUpdates

  # 6. Answer with the keys that were written, nothing else
  - type: Flatten@1
    path: $.rows[*].readingKey
    targetPath: $.imported

  - type: Project@1
    path: $
    clear: true
    fields:
      - path: $.imported
        inclusion: true
```

**Call it** with a multipart upload; the file becomes `$.files[0]` and its content `$.files[0].data` (base64), which `ImportFromCsv@1` reads by `fileIndex`:

```bash
# the header is read from stdin, so the token stays out of the process arguments and the shell history
printf 'Authorization: Bearer %s\n' "$OCTO_TOKEN" | curl -X POST "https://<mesh-adapter-host>/<tenantId>/meter-readings/import" \
  -H @- -F "file=@readings.csv"
# -> { "imported": [ "AT0012345_2026-10", "AT0012346_2026-10" ] }
```

**Key patterns:**
- `FromHttpRequest@2` (not the deprecated `@1`); without `allowAnonymous` the route needs a valid token, `requiredRoles` narrows it further.
- `ImportFromCsv@1` reads `$.files[<fileIndex>].data`; give every column a `dataType` and, for decimal commas, a `numberCulture`.
- Build the natural key with `Concat@1` on every row (`path: $.rows[*]`, `concatSubPath`), then let `GetRtEntitiesByWellKnownName@1` find existing entities by that key: it writes `rtId`, `ckTypeId` and `modOperation` on each row (all three target paths are **required** properties), and `generateInsertOperation: true` turns a missing entity into an Insert with a new rtId.
- In `ForEach@1`, `CreateUpdateInfo@1` takes the kind from `updateKindPath` (Insert or Update per row) and sets `rtWellKnownNamePath` to the key, so the next import finds the same entity.
- `Flatten@1` collects the per-row updates into one array for a single `ApplyChanges@2` call (one transaction).
- `attributeName` is the name as the model declares it; this example model declares PascalCase names, most models use camelCase (see the casing warning of `CreateUpdateInfo@1`), so look them up with `get_type_schema`.
- One meter and month per file: two rows with the same key are both looked up as missing and both become Inserts with the same `rtWellKnownName`. Reject or merge such rows before the lookup when a file can contain them.
- The HTTP answer is the data root minus the request envelope, so shape it: `Project@1` with `clear: true` keeps only `$.imported`.
