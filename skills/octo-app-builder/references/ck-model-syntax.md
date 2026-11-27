# CK model source: enums, association roles and multiplicities

How to declare an enum, an association role and its multiplicities in the source folder `ConstructionKit/` of a
CK model, how a type uses them, and what the multiplicities do at runtime. The minimal three-file layout
(`ckModel.yaml`, `attributes/`, `types/`) is in `blueprint-authoring.md` §CK model source. Validate every draft
with `validate_ck_model` before anything is imported (`draft-and-validate.md`). Every example here passes it.

Every attribute a type lists is **required unless it is marked `isOptional: true`** on the type. Pipelines and seeds
that insert the type set every required attribute; mark an attribute optional when an insert may leave it out. No
validation tool reports a required attribute a pipeline does not set.

## Enums: declare one and use it as an attribute type

An enum lives in its own file under `enums/` (any file of the folder may hold the key `enums:`):

```yaml
# enums/ticketStatus.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
enums:
- enumId: TicketStatus
  description: Lifecycle state of a support ticket.
  values:
  - key: 0
    name: Open
  - key: 1
    name: InProgress
  - key: 2
    name: Closed
    description: Solved or rejected; no further work.
```

- `enumId` is Pascal case. Every value needs an integer `key` (unique within the enum, not negative) and a `name`
  that starts with an upper-case letter and has only letters and digits (no blanks, no `_`).
- Optional: `description` on the enum and on each value, `useFlags: true` for a flags enum (values combine).

The enum is used through an **attribute** of value type `Enum` that names it in `valueCkEnumId`; the type then
lists that attribute like any other:

```yaml
# attributes/ticket.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
attributes:
- id: TicketStatus
  valueType: Enum
  valueCkEnumId: ${this}/TicketStatus
```

```yaml
# types/ticket.yaml (excerpt)
  attributes:
  - id: ${this}/TicketStatus-1
    name: Status
```

`${this}` is the model itself; an enum of a dependency is named by its alias, e.g. `${System}/<EnumId>`. Seed data
and imports write the value's `key` (`value: 1`), see `blueprint-authoring.md` §Seed data.

Errors of `validate_ck_model`: `valueType: Enum` without `valueCkEnumId` - "is defined as Enum, but the
ValueCkEnumId is missing"; an enum id the model and its dependencies do not declare - "uses unknown CkEnumId"; a key
used twice - "has defined key '<key>' which is used several times"; a negative key - "cannot be negative". The last
two drop the enum, so its attributes also report "uses unknown CkEnumId": fix the enum first.

## Association roles: declare one and use it on a type

An association role is declared once, under the key `associationRoles:` (by convention in `associations/`). It
names the two ends and their multiplicities, but **no type**: the types come from the type that uses it.

```yaml
# associations/ticketCustomer.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
associationRoles:
- id: TicketCustomer
  description: The customer a ticket belongs to.
  outboundName: Customer
  outboundMultiplicity: One
  inboundName: Tickets
  inboundMultiplicity: N
```

All five keys are required: `id`, `outboundName`, `outboundMultiplicity`, `inboundName`, `inboundMultiplicity`
(names in Pascal case; multiplicities `ZeroOrOne`, `One` or `N`).

A type uses the role in its `associations:` list. The type that lists it is the **origin**, `targetCkTypeId` the
**target**:

```yaml
# types/ticket.yaml (excerpt)
- typeId: Ticket
  derivedFromCkTypeId: ${System}/Entity-1
  associations:
  - id: ${this}/TicketCustomer
    targetCkTypeId: ${this}/Customer
```

- The origin (`Ticket`) gets the navigation `outboundName` (`Customer`) with `outboundMultiplicity`: how many targets
  one origin has.
- The target (`Customer`) gets the navigation `inboundName` (`Tickets`) with `inboundMultiplicity`: how many origins
  one target has.
- Roles of a dependency are used the same way, e.g. `id: ${System}/ParentChild` with the child as origin (its
  `Parent` is `One`, the parent's `Children` are `N`).

Errors of `validate_ck_model`: a role id the model and its dependencies do not declare - "defines unknown
association role" and "defines AssociationRoleId '<id>' that is unknown"; an unknown target type - "defines unknown
association role target CkTypeId"; a missing key of the role - "Schema validation failed ... Required properties
[...] are not present".

## Multiplicities and their effect at runtime

| Value | Meaning for one entity at that end |
|---|---|
| `ZeroOrOne` | at most one association of this role |
| `One` | exactly one: mandatory |
| `N` | any number, none included |

A 1:N relation ("a ticket belongs to one customer, a customer has many tickets") is `outboundMultiplicity: One`
(or `ZeroOrOne` when optional) and `inboundMultiplicity: N`, declared on the "many" side (the ticket).

The runtime engine checks them on every write of entities and associations (GraphQL, seed, pipeline):

- **Mandatory on create.** An origin type whose outbound multiplicity is `One` can only be created together with
  that association, in the same request. Without it the write fails with: "Entity with CkTypeId '<type>': Inbound
  association '<role>' has minimum multiplicity of 'One'. There is no create statement for creating this
  association." The seed entity lists the association under `associations:` (`roleId`, `targetRtId`,
  `targetCkTypeId`, see `blueprint-authoring.md` §Seed data); a pipeline builds it with `CreateAssociationUpdate@1`
  and writes entity and association in one `ApplyChanges@2` (`entityUpdatesPath` and `associationUpdatesPath`,
  `node-reference-mesh.md` §CreateAssociationUpdate@1).
- **At most one.** A second association of a role whose end is `One` or `ZeroOrOne` fails with: "Inbound
  association '<role>' has maximum multiplicity of 'One'. Adding another association violates the model." To
  change the target, delete the old association and create the new one in the same request.
- **Cannot remove a mandatory one.** Deleting the only association of an end that is `One` fails with "... has
  maximum multiplicity of 'One'. Association deletion violates the model.", unless the entity itself is deleted in
  the same request.
- **Only the declared types.** An association to a type that is neither the target type nor derived from it fails
  with "Outbound association '<role>' to CkTypeId '<type>' is not allowed".

The mandatory check on create applies to the origin only: a target whose `inboundMultiplicity` is `One` can be
created without an origin. Put a mandatory relation on the type that must have it, as its outbound end.

## Complete example: tickets with a status, each belonging to exactly one customer

A model with an enum, a mandatory 1:N association (ticket to customer) and an optional one (a ticket merged into
another ticket). Six files under `ConstructionKit/`:

```yaml
# ckModel.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-meta.schema.json
modelId: Demo.Helpdesk-1.0.0
description: Support tickets of customers.
dependencies:
- System-[2.0,3.0)
```

```yaml
# enums/ticketStatus.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
enums:
- enumId: TicketStatus
  values:
  - key: 0
    name: Open
  - key: 1
    name: InProgress
  - key: 2
    name: Closed
```

```yaml
# attributes/helpdesk.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
attributes:
- id: CustomerName
  valueType: String
- id: TicketTitle
  valueType: String
- id: TicketStatus
  valueType: Enum
  valueCkEnumId: ${this}/TicketStatus
```

```yaml
# associations/helpdesk.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
associationRoles:
- id: TicketCustomer
  outboundName: Customer
  outboundMultiplicity: One
  inboundName: Tickets
  inboundMultiplicity: N
- id: TicketMergedInto
  outboundName: MergedInto
  outboundMultiplicity: ZeroOrOne
  inboundName: MergedTickets
  inboundMultiplicity: N
```

```yaml
# types/customer.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
types:
- typeId: Customer
  derivedFromCkTypeId: ${System}/Entity-1
  attributes:
  - id: ${this}/CustomerName-1
    name: Name
```

```yaml
# types/ticket.yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
types:
- typeId: Ticket
  derivedFromCkTypeId: ${System}/Entity-1
  attributes:
  - id: ${this}/TicketTitle-1
    name: Title
  - id: ${this}/TicketStatus-1
    name: Status
  associations:
  - id: ${this}/TicketCustomer
    targetCkTypeId: ${this}/Customer
  - id: ${this}/TicketMergedInto
    targetCkTypeId: ${this}/Ticket
```

A `Ticket` is created together with its `TicketCustomer` association; `TicketMergedInto` may be left out.

## Reference: the JSON schemas of the CK model source

Every file names its schema in `$schema`; the schemas are public and list every key with its allowed values. Use
them for all keys this page does not show (records, indexes, interfaces, ownership, default values):

- `https://schemas.meshmakers.cloud/construction-kit-meta.schema.json` - `ckModel.yaml`
- `https://schemas.meshmakers.cloud/construction-kit-elements.schema.json` - every other file: `attributes`,
  `types`, `associationRoles`, `enums`, `records`, `interfaces`; one schema per element under the same host
  (`construction-kit-elements-enum.schema.json`, `-associationRole`, `-type`, `-attribute`, `-record`).
