# Pipeline as a CK method handler (`execution.handler: pipeline`)

A CK method declared `execution.handler: pipeline` is implemented by a pipeline; callers get the pipeline's result in the standard method envelope. Contract (communication controller, AB#6879; guide: `technologyGuide/constructionKits/ckLanguage2/pipelineMethodHandlers.md` in the documentation):

- **Binding**: the deployed pipeline in the call's tenant whose **`rtWellKnownName` equals the qualified method id** (for example `Acme.Assets/Device.UpdateFirmware-1`). No other binding. No such pipeline: `METHOD_HANDLER_NOT_AVAILABLE`, reason `pipeline-not-deployed`. A changed pipeline takes effect after `DeployPipeline`.
- **Trigger**: `FromExecutePipelineCommand@1`. Use `callerBinding: BindingRequired` so the pipeline never runs anonymously; it runs as the user who called the method.
- **Input** (data root): `$.parameters.<name>` (camelCase method parameters), `$.target.ckTypeId` / `$.target.rtId` (`rtId` null for a static method), `$.method.id|invocationId|correlationId`. The caller is not in the data.
- **Output**: end with `SetPipelineExecutionResult@1`; the document must be `{"value": <result>}` (type of the method's `result`; required when the method has one) or `{"error": {"code": "DECLARED_CODE", "parameters": {"k": "v"}}}`. The code must be declared in the method's `errors` (or be `METHOD_VALIDATION_FAILED` / `METHOD_TARGET_NOT_FOUND` / `METHOD_FORBIDDEN`); error parameter values must never contain method parameter values. Anything else (no JSON, no `value`, wrong type, undeclared code) is answered `METHOD_HANDLER_FAILED`, never a malformed success. A failed pipeline is `METHOD_HANDLER_FAILED` (its error text stays in the controller log); a pipeline still running at the deadline is `METHOD_TIMEOUT` and is not cancelled.
- **Write the success and the error branch as two `If@1` nodes with complementary conditions** that each write `$.result` once, then one `SetPipelineExecutionResult@1` with `path: $.result`; do not rely on overwriting.
- **Methods with `sensitive` parameters (or `Secret` type) must not be pipeline methods** until the retention of pipeline input and output is decided (OD-3, OD-4, OD-9): the controller refuses them (`sensitive-parameters-not-supported`). Nothing a pipeline execution stores (`InputData`, `OutputData`) is safe for secrets.
- **Consistency**: nodes commit as they run, no rollback; put write nodes last. After `METHOD_TIMEOUT` the pipeline may still finish.
- **Insert of a method-replaced type** (the method declares `replacesGenericCreate`, own or inherited): a new entity of that type may be inserted only in the method's own pipeline run. `ApplyChanges@1`, `ApplyChanges@2` and `ImportFromExcel@1` refuse every other insert (trigger runs, manual execution, a pipeline chained with `ToPipelineDataEvent@1`, which does not inherit the marker) with `GENERIC_CREATE_REPLACED_BY_METHOD`; the whole batch is refused before any write, also in dry runs. A manual execute of the method's pipeline is therefore refused too: test it by calling the method. `GENERIC_CREATE_CHECK_UNAVAILABLE` (CK cache not loadable) is retryable. `ImportFromExcel@1` has no dry-run branch: a dry run writes for real. Do the insert in the method's own pipeline, not in a chained one; a retried method run repeats its inserts, so keep the pipeline idempotent. Only these three nodes make the check; other write nodes are not covered.
- **Attribute access `Hidden` / `MethodOnly` / `ReadOnly`** (octo-mesh-adapter, AB#7768; CK model `access`, see `technologyGuide/constructionKits/ckLanguage2/accessModifiers.md#pipelines`): a pipeline runs with system rights, so the nodes apply the access themselves. **Read:** `GetRtEntitiesByType@1` (type and `ckInterfaceId`), `GetRtEntitiesById@1`, `GetRtEntitiesByWellKnownName@1`, `GetAssociationTargets@1`, `CheckDuplicate@1` (existing entity), `BackfillFromRtEntity@1` and `FromWatchRtEntity@1` emit entities **without `Hidden` values** (also record members), `MethodOnly` and `ReadOnly` are emitted. A field filter, sort order or query column on a `Hidden` path fails the node with `RT_ATTRIBUTE_HIDDEN` (names node and path, never a value): do not look a user up by password hash or token; look up by a normal attribute such as `normalizedEmail`. **Write** (`ApplyChanges@1/@2` and the other nodes that write entities): `Hidden` and `ReadOnly` are always refused (also on insert, also in a method run); `MethodOnly` only in the method-handler run of the entity's type (marker of the controller, method belongs to the entity's type, the running pipeline); otherwise the whole batch fails with `RT_ATTRIBUTE_WRITE_RESTRICTED` before anything is written, dry runs included. A `Replace` of an entity whose type has such an attribute is refused as well (it would clear the value). A value present in an update counts as written: read-modify-write of a whole entity fails on a `ReadOnly`/`MethodOnly` attribute, so write only the attributes that change. To change a `MethodOnly` attribute from a pipeline, make the pipeline the handler of a CK method (`execution.handler: pipeline`).

## Booking a slot without double booking

Pattern for an appointment or reservation method that must stay correct when several callers book the same slot at the same time (octo-mesh-adapter AB#9466, spike AB#9465). The unique index is the only check that holds against concurrent calls: a pipeline's own "is the slot free" lookup reads before it writes, so two callers both pass it. Sample: `docs/examples/slot-booking-method.yaml` in octo-mesh-adapter; its integration test `SlotBookingConflictTests` runs that file against MongoDB (12 parallel bookings of one slot: 1 booked, 11 `CONCURRENT_CHANGE`; 10 parallel moves into one slot: 1 success, 9 conflicts; a second adapter replica that holds, commits or rolls back the slot).

**1. Model: a slot key with a unique index, from the type's first version.** The booking type carries a key that names exactly one slot (`<resourceRtId>|<slotStartUtc>`) and a `UniqueNotDeleted` index on it. The method declares `CONCURRENT_CHANGE` in its `errors`. The key must be **canonical**: the index compares strings, so `2026-12-11T09:00:00Z`, `2026-12-11T09:00:00.000Z` and `2026-12-11T10:00:00+01:00` are three keys for one slot and all three bookings would be stored. Require one fixed UTC format aligned to the slot grid and refuse any other input with `METHOD_VALIDATION_FAILED` (parameter `field`): a pipeline does not stop after a branch, so a non-canonical value must never reach the insert. `If@1` has `RegexMatch` but no negated form: set a flag `$.validSlot` = `false` (`SetPrimitiveValue@1`), let an `If@1` with `operator: RegexMatch` set it to `true`, then nest the insert and its two result branches in an `If@1` on `$.validSlot` equal `true` and write the validation error in the complementary `If@1` on `false`.

```yaml
# Sample.Booking: attributes/booking.yaml
attributes:
  - id: SlotKey
    valueType: String
  - id: BookedBy
    valueType: String
# types/slotBooking.yaml
types:
  - typeId: SlotBooking
    derivedFromCkTypeId: ${System}/Entity
    attributes:
      - id: ${this}/SlotKey
        name: SlotKey
      - id: ${this}/BookedBy
        name: BookedBy
    indexes:
      - indexType: UniqueNotDeleted
        fields:
          - attributePaths: [ SlotKey ]
    methods:
      - methodId: Book-1
        kind: Static
        parameters:
          - { name: resourceRtId, valueType: String }
          - { name: slotStartUtc, valueType: String }   # ISO-8601 UTC
          - { name: bookedBy, valueType: String }
        result: { valueType: Boolean }
        errors:
          - code: CONCURRENT_CHANGE
            description: The slot is already booked, also by a concurrent call.
        execution: { timeoutSeconds: 30, handler: pipeline }
```

`attributeName` in `CreateUpdateInfo@1` must match the attribute id of the model exactly (here `SlotKey`). `CONCURRENT_CHANGE` is a declared method code, not a platform constant: the method must list it, or the controller answers `METHOD_HANDLER_FAILED` (`invalid-result`).

**2. Handler: book = insert.** Deploy the pipeline with `rtWellKnownName` = `Sample.Booking/SlotBooking.Book-1`.

```yaml
triggers:
  - type: FromExecutePipelineCommand@1
    callerBinding: BindingRequired
transformations:
  - type: FormatString@1
    format: "{$.parameters.resourceRtId}|{$.parameters.slotStartUtc}"
    targetPath: $.slotKey
  - type: CreateUpdateInfo@1
    targetPath: $._inserts
    targetValueKind: Array
    updateKind: INSERT
    ckTypeId: Sample.Booking/SlotBooking
    attributeUpdates:
      - { attributeName: SlotKey, attributeValueType: String, valuePath: $.slotKey }
      - { attributeName: BookedBy, attributeValueType: String, valuePath: $.parameters.bookedBy }
  - type: ApplyChanges@2
    entityUpdatesPath: $._inserts
    onDuplicateKey: Report
    duplicateKeyTargetPath: $.slotTaken
  - type: If@1
    path: $.slotTaken
    value: true
    valueType: Boolean
    transformations:
      - type: WriteJson@1
        targetPath: $.result
        jsonString: '{"error": {"code": "CONCURRENT_CHANGE", "parameters": {"reason": "slot-taken"}}}'
  - type: If@1
    path: $.slotTaken
    value: false
    valueType: Boolean
    transformations:
      - type: WriteJson@1
        targetPath: $.result
        jsonString: '{"value": true}'
  - type: SetPipelineExecutionResult@1
    path: $.result
```

What `ApplyChanges@2` writes to `duplicateKeyTargetPath` with `onDuplicateKey: Report`:

| Situation | Flag | Stored |
|-----------|------|--------|
| Write stored | `false` | yes |
| Unique index refused it (duplicate key) | `true` | no, rolled back |
| MongoDB WriteConflict (112) with a second adapter replica | up to six attempts (waits of about 0.4-0.8 s in total), then `false` or `true` as above; a conflict that outlasts the retries is `true` | never a silent success |
| Engine validation error in the operation result | **not written** (logged as error, rolled back, pipeline continues) | no |
| Any other exception | pipeline fails (`METHOD_HANDLER_FAILED`, or `METHOD_OUTCOME_UNKNOWN` for a write the database did not acknowledge) | no, or unknown |

Read only an explicit `false` as "booked": the two `If@1` branches above answer neither when the flag is absent, so the method returns no result and the caller gets `METHOD_HANDLER_FAILED` instead of a false success. Without Report (default `Throw`) the duplicate fails the pipeline and the caller sees `METHOD_HANDLER_FAILED`, not the declared conflict.

**3. Move = update of the key.** An instance method (for example `Move-1` with parameter `slotStartUtc`) builds the new key and writes it with `CreateUpdateInfo@1` `updateKind: UPDATE`, `rtIdPath: $.target.rtId`, `ckTypeId: Sample.Booking/SlotBooking`, the `SlotKey` attribute only, then the same `ApplyChanges@2` (Report) and the same two `If@1` branches and `SetPipelineExecutionResult@1`. The unique index refuses a move into a taken slot exactly like a booking.

**4. How a caller handles the conflict.**

- **GraphQL:** the method is the mutation `runtime { sampleBookingSlotBookings { book(input: { resourceRtId: "…", slotStartUtc: "…", bookedBy: "…" }) { invocationId result } } }` (type field = model and type in camelCase plus `s`; static method: no `rtId`). A conflict is one GraphQL error with `extensions.code = "CONCURRENT_CHANGE"` and `extensions.parameters.reason = "slot-taken"`; the field data is `null`. Show "slot no longer available", reload the free slots and let the user pick another; do not retry the same slot.
- **MCP `invoke_ck_method`** (octo-mcp-service, AB#9467): `ckTypeId` `Sample.Booking/SlotBooking`, `methodId` `Book-1` exactly as the type declares it (or the qualified `Sample.Booking/SlotBooking.Book-1`; the tool does not strip the version, so `Book` is refused), no `rtId` for the static method, `parameters` as one JSON object (`{"resourceRtId": "…", "slotStartUtc": "…", "bookedBy": "…"}`), optional `idempotencyKey`. It calls the same GraphQL mutation with the caller's token. A conflict comes back with `isSuccess: false` and `methodError` `{ code: "CONCURRENT_CHANGE", declared: true, parameters: { reason: "slot-taken" } }`; `declared: false` marks platform codes such as `METHOD_FORBIDDEN`. An agent treats `declared: true` + `CONCURRENT_CHANGE` as "pick another slot", never as a fault to retry.
- An `idempotencyKey` makes a repeated call of the same caller with the same parameters return the first answer (for example after a network error), it does not replace the unique index.

**Limits of the pattern.**

- **Declare the unique index in the type's first version.** Adding a unique index to an existing type that already holds data is a **Major** change of the CK model and fails on duplicates already stored (AB#5347).
- **Cancelling must delete the booking.** Write a `DELETE` update (`ApplyChanges@2`); the default delete archives the entity (soft delete), and `UniqueNotDeleted` covers only entities that are not archived, so the slot is free again. A booking that is only marked cancelled (a status attribute) keeps the key and blocks the slot.
- **Capacity above 1 or variable durations** need one claim entity per slot unit (for example one per 15-minute unit, or per seat), each with its own unique key, all written in the **same `ApplyChanges@2` batch**: the batch is one transaction, so either every unit is claimed or none and the flag is `true`.
