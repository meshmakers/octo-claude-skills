# Blueprint authoring — CK model, manifest, seed data, catalogs

Everything here was first verified live on 2026-06-09 (local kind, tenant `test`)
while building a ticket demo blueprint (CK model `Demo.Tickets`); the dependency
ranges below follow the current System.Communication 4.x. Engine-level reference:
`octo-construction-kit-engine/docs/blueprints.md`.

## CK model source (the minimal three-file layout)

```
ck/ConstructionKit/
├── ckModel.yaml
├── attributes/<domain>.yaml
└── types/<domain>.yaml
```

`ckModel.yaml`:

```yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-meta.schema.json
modelId: Demo.Tickets-1.0.0
description: One-time secret tickets for the OctoMesh capability demo.
dependencies:
- System-[2.0,3.0)
```

`attributes/ticket.yaml` — attribute ids are unversioned here; valueType is one of
String|Boolean|DateTime|Int|Double|… :

```yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
attributes:
- id: TicketSecret
  description: The secret delivered on a successful redeem. Cleared after redemption.
  valueType: String
- id: TicketRedeemed
  valueType: Boolean
- id: TicketRedeemedAt
  valueType: DateTime
```

`types/ticket.yaml` — derive from `${System}/Entity-1`; reference own attributes as
`${this}/<AttrId>-1`; `name:` is what pipelines/queries use:

```yaml
$schema: https://schemas.meshmakers.cloud/construction-kit-elements.schema.json
types:
- typeId: Ticket
  description: A one-time secret voucher.
  derivedFromCkTypeId: ${System}/Entity-1
  attributes:
  - id: ${this}/TicketName-1
    name: Name
  - id: ${this}/TicketSecret-1
    name: Secret
  - id: ${this}/TicketRedeemed-1
    name: Redeemed
  - id: ${this}/TicketRedeemedAt-1
    name: RedeemedAt
    isOptional: true
```

Mark attributes that runtime/services own (status enums, sync counters, timestamps)
with `isRuntimeState: true` so blueprint re-applies never trample them.

### Compile + publish

`octo-ckc` is the CK compiler CLI of `octo-construction-kit-engine`, not on PATH by default. <!-- developer-machine -->(on a developer machine: the build output `bin/DebugL/net10.0/` of that repository)<!-- /developer-machine -->

```bash
octo-ckc -c Compile -p ./ck/ConstructionKit -o ./ck/out      # → ck-<modelid>.yaml
octo-ckc -c Publish -f ./ck/out/ck-demo.tickets.yaml -r      # default catalog: LocalFileSystemCatalog
```

Publish writes into `~/.octo/local-catalog/ck-models/v2/<letter>/<Name>/<major>/`
and maintains the nested `catalog.json` indexes. `-r` replaces an existing version.
Other octo-ckc commands: `Find -id <Model-[range]>`, `Get`, `GetCatalogs`,
`RefreshCatalogCache`, `New -p <path>` (scaffold).

The asset-repo service resolves `ckModelDependencies` against its configured CK
catalogs (LocalFileSystem + GitHub) — publishing locally is sufficient for local
development; shared environments need the model in a shared catalog.

### ID formats (three different contexts!)

| Context | Format | Example |
|---|---|---|
| ImportRt / seed YAML | `Model/Type-Version`, `Model/Attr-Version` | `Demo.Tickets/Ticket-1`, `Demo.Tickets/TicketSecret-1` |
| Pipeline YAML (`ckTypeId` in nodes) | unversioned `Model/Type` | `Demo.Tickets/Ticket` |
| GraphQL delete mutations | unversioned `Model/Type` | `Demo.Tickets/Ticket` |

After ImportCk, check the exact attribute IDs with the MCP tool `get_type_schema`<!-- developer-machine --> (or generate the seed template
with the octo skill's `ck_explorer.py preflight <Model>/<Type> --for-import`)<!-- /developer-machine -->.

## Blueprint manifest (`blueprint.yaml`)

```yaml
$schema: https://schemas.meshmakers.cloud/blueprint-meta.schema.json
blueprintId: Tickets-1.0.0                # Name-Major.Minor.Patch; folder name = Name
description: |
  What it installs, prerequisites, and the post-install deploy commands.
ckModelDependencies:
  - Demo.Tickets-[1.0.0,2.0.0)            # auto-imported from CK catalogs at install
# blueprintDependencies: [Other-[1.0,)]   # resolved transitively, topo-sorted
seedDataPath: seed-data/entities.yaml
requires:                                  # optional gate; evaluated on the ROOT blueprint only
  octo.environment:
    - dev
    - test
```

- `requires:` mismatch → install is a **successful no-op** (`WasSkipped: true`).
- Version ranges: `[1.0,)` ≥1.0; `[1.0,2.0)` ≥1.0 <2.0; `[1.5.0]` exact.
- Name prefix `System.` means service-managed (auto-applied, hidden in Studio) —
  never use it for admin-installable blueprints.
- `composedBlueprints` was removed from the schema — do not use it.

## Seed data (`seed-data/entities.yaml`)

Runtime-model format. Hand-assign stable 24-hex rtIds (recognizable prefix) so
re-apply (Upsert by rtId) is idempotent. System.Communication blueprint defaults
available on every comm-enabled tenant: Pool `670000000000000000000001`,
Mesh Adapter `670000000000000000000002`, dev Helm repo `670000000000000000000003`.

```yaml
$schema: https://schemas.meshmakers.cloud/runtime-model.schema.json
dependencies:
- System.Communication-[4.0,5.0)   # current major; raise the lower bound to the minor your pipelines need
entities:
  - rtId: '077100000000000000000001'
    ckTypeId: System.Communication/DataFlow-1
    attributes:
      - id: System/Name-1
        value: "My App API"

  - rtId: '077100000000000000000002'
    ckTypeId: System.Communication/Pipeline-1
    associations:
      - roleId: System/ParentChild-1
        targetRtId: '077100000000000000000001'
        targetCkTypeId: System.Communication/DataFlow-1
      - roleId: System.Communication/Executes-1
        targetRtId: '670000000000000000000002'
        targetCkTypeId: System.Communication/Adapter-1
    attributes:
      - id: System/Name-1
        value: "my-pipeline"
      - id: System/Enabled-1
        value: true
      - id: System.Communication/DeploymentState-1
        value: 0
      - id: System.Communication/PipelineDefinition-1
        value: |
          triggers:
            - type: FromHttpRequest@2       # authenticated by default (http-api-pipelines.md §Route security)
              ...
```

The pipeline YAML lives **inline as a block scalar** in `PipelineDefinition-1` —
no separate files. An Application workload entity goes in the same seed (see
app-workload.md).

**App roles for `requiredRoles`.** A role that a route lists in `requiredRoles` must
exist in the tenant. Seed it as a `System.Identity/Role` entity (add
`System.Identity-[3.0,4.0)` to the seed's `dependencies`), and optionally a group that
carries it, so administrators grant the role by group membership:

```yaml
  - rtId: '077100000000000000000101'
    ckTypeId: System.Identity/Role
    rtWellKnownName: TicketIssuer
    attributes:
      - id: System/Name
        value: TicketIssuer
      - id: System.Identity/NormalizedName
        value: TICKETISSUER                # the name in upper case; form as in production seeds
  - rtId: '077100000000000000000102'
    ckTypeId: System.Identity/Group
    rtWellKnownName: TicketIssuers
    attributes:
      - id: System.Identity/GroupName
        value: TicketIssuers
      - id: System.Identity/NormalizedGroupName
        value: TICKETISSUERS
    associations:
      - roleId: System.Identity/AssignedRole
        targetRtId: '077100000000000000000101'
        targetCkTypeId: System.Identity/Role
```

The role name in the seed is exactly the name in `requiredRoles`. Role members are
runtime state and survive a re-apply of the blueprint. A blueprint cannot assign roles
to users or clients: after the install an administrator adds users to the group
(`AddUserToGroup`) or the role (`AddUserToRole`), and clients with `AddClientToRole` or
`AddClientToGroup` (octo skill, command reference *Client Roles and Groups*). This
includes the pipeline service account when the app's pipelines read data guarded by a
policy for that role.

### Variables

| Syntax | Resolved | By | Examples |
|---|---|---|---|
| `${name}` | at blueprint apply | `IBlueprintVariableProvider` | `${octo.tenantId}`, `${octo.environment}`, `${octo.version}`, `${octo.isSystemTenant}` |
| `{{domain.NAME}}` | at workload deploy | communication controller | `{{domain.default}}` → the cluster's default domain<!-- developer-machine --> (`127.0.0.1.nip.io` on kind)<!-- /developer-machine --> |

`${…}` is substituted only in string attribute values and `rtWellKnownName`.
Unknown `${placeholder}` logs a warning and stays verbatim in the database.

### Ownership stamps (set by the engine on apply)

`System/RtBlueprintSource` (owning blueprint id), `System/RtBlueprintLocked`
(true = blueprint manages the entity; seed `false` explicitly to hand an entity
to the user), `System/RtBlueprintAppliedAt`.

## Catalogs

Local blueprint catalog layout (default root `~/.octo/local-blueprint-catalog`):

```
blueprints/v1/<Name>/<version>/
├── blueprint.yaml
└── seed-data/entities.yaml
```

**Cache pitfall:** the catalog index is cached — `ListBlueprints` serves stale
content until it is refreshed. After adding or changing a blueprint in the catalog run
`octo-cli -c RefreshBlueprintCatalogs -cn LocalFileSystemBlueprintCatalog` (forced, no
restart, role `DataModelManagement`). `octo-bpm`'s own `list`/`get` and the
`unpublish` dry-run refresh by themselves.<!-- developer-machine --> Older local builds
without the refresh command rebuild the cache only when
`~/.octo/blueprint-catalog/cache/local-blueprint-catalog-cache.json` is missing —
delete it there.<!-- /developer-machine -->

GitHub catalogs (e.g. `meshmakers/blueprint-libraries-build`, layout
`blueprints/v1/<letter>/<Name>/<major>/<Name>-<version>/`) are where shared
blueprints get published.

## Lifecycle commands

```bash
octo-cli -c ListBlueprints                              # all catalogs
octo-cli -c InstallBlueprint -b <Name>-<Version>        # -f = force re-apply (upserts seed)
octo-cli -c ListBlueprintInstallations
octo-cli -c GetBlueprintHistory
octo-cli -c PreviewBlueprintUpdate -tv <Name>-<Version> [-m Safe|Merge|Full|Migration]
octo-cli -c UpdateBlueprint -tv <Name>-<Version> [-m <mode>] [-dr]
octo-cli -c UninstallBlueprint -n <Name> [-c] [-y]      # NAME only, no version
```

Installing into a tenant that already holds the content (manual `ImportRt` of the same rtIds): run
`PreviewBlueprintUpdate -tv <Name>-<Version>` first - without an installation it diffs the seed against the
tenant by rtId (AB#8256), and `InstallBlueprint` applies exactly the listed adds and updates. Attributes listed under
`BlankedAttributes` keep the tenant value (`SeedEmpty`: the seed value is empty; `SeedEmptiesJsonField`: a non-empty JSON
seed empties one field, named in the summary; `SeedOmitted`, `ResetToDefault`). To take the seed value anyway, follow up with
`UpdateBlueprint -tv <Name>-<Version> --confirm-blanking <rtId>:<attribute>` (details: `octo` command reference,
`PreviewBlueprintUpdate`).

Expected install output: `Success: true`, `ApplicationMode: Initial`, your model
in `LoadedCkModels`, empty `Warnings`. Before uninstalling a blueprint whose seed
contains a deployed Application, undeploy the workload first
(`UndeployWorkload -id <rtId> -y` helm-uninstalls the release).
