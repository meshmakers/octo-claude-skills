---
name: octo
description: Natural language interface for OctoMesh CLI (octo-cli), data model exploration, and runtime instance browsing via GraphQL. Trigger on anything related to OctoMesh CLI operations — managing users, roles, tenants, clients, identity providers, service hooks, authentication, environment switching, or any platform administration task. Also trigger for data model exploration — Construction Kit models, CK types, enums, attributes, associations, GraphQL schema introspection, or any question about the tenant's data model. Also trigger for runtime instance queries — listing, counting, searching, filtering, or inspecting runtime entities/instances of any CK type. Trigger whenever the user mentions octo, OctoMesh, tenant management, user management, identity services, data model, construction kit, CK types, CK enums, runtime instances, show instances, list machines, count entities, or wants to interact with the mesh platform.
---

# OctoMesh CLI Natural Language Interface

## Overview

Single entry point: `/octo <natural language>`
Claude infers the correct `octo-cli` command from the user's intent, resolves context (environment, tenant, auth status), and executes it — with confirmation for mutating operations.

## Context Discovery

Run these checks once per session and cache the results. If any check has already been performed in this conversation, skip it.

### 1. Authentication Check

Run `octo-cli -c AuthStatus` to determine:
- Whether authenticated (token valid)
- Current identity service URL (determines environment)
- JWT claims: subject, roles, issuer, audience, expiration

If not authenticated: inform the user and offer to run `octo-cli -c LogIn -i`.

### 2. Settings File

Read `~/.octo-cli/settings.json` to extract:
- Configured tenant ID
- Service endpoint URLs (identity, asset, bot, communication, reporting)

The settings structure uses the `OctoToolOptions` section with keys:
- `IdentityServiceUrl`, `AssetServiceUrl`, `BotServiceUrl`
- `CommunicationServiceUrl`, `ReportingServiceUrl`, `AdminPanelUrl`
- `TenantId`

### 3. Environment Detection from URLs

| URL Pattern | Environment |
|---|---|
| `localhost:500x` | local |
| `*.test-2.mm.cloud` | test-2 |
| `*.staging.meshmakers.cloud` | staging |
| `*.meshmakers.cloud` (no subdomain prefix) | production |

## Invocation Syntax

```
octo-cli -c <CommandValue> [flags]
```

Flags use short form with `-` prefix: `-un userName`, `-e email`, `-tid tenantId`, etc.

## Command Reference (Quick Lookup)

For full flag details, read `references/command-reference.md` in this skill directory.
For environment URLs, read `references/environments.md` in this skill directory.

### General (no group)

| Command | Description | Type |
|---|---|---|
| `Config` | Configures tool endpoints and tenant | Mutating |
| `LogIn` | Login to identity services (`-i` for interactive/browser) | Mutating |
| `AuthStatus` | Gets authentication status | Read-only |

### Identity Services (group: "Identity Services")

| Command | Description | Type |
|---|---|---|
| `Setup` | Initial identity services setup | Mutating |
| `GetUsers` | List all users | Read-only |
| `CreateUser` | Create a new user (`-un`, `-e`, `-p`) | Mutating |
| `UpdateUser` | Update a user (`-un` required, `-e`, `-nun`) | Mutating |
| `DeleteUser` | Delete a user (`-un`) | Mutating |
| `ResetPassword` | Reset user password (`-un`, `-p`) | Mutating |
| `AddUserToRole` | Add user to role (`-un`, `-r`) | Mutating |
| `RemoveUserFromRole` | Remove user from role (`-un`, `-r`) | Mutating |
| `GetRoles` | List all roles | Read-only |
| `CreateRole` | Create a role (`-n`) | Mutating |
| `UpdateRole` | Update a role (`-n`, `-nn`) | Mutating |
| `DeleteRole` | Delete a role (`-n`) | Mutating |
| `GetClients` | List all clients | Read-only |
| `GetClient` | Get a client by ID (`-id`) | Read-only |
| `AddAuthorizationCodeClient` | Add auth code client (`-id`, `-n`, `-u`, `-ru`, `-fclo`) | Mutating |
| `AddClientCredentialsClient` | Add client credentials client (`-id`, `-n`, `-s`) | Mutating |
| `AddDeviceCodeClient` | Add device code client (`-id`, `-n`, `-s`) | Mutating |
| `UpdateClient` | Update a client (`-id`, `-n`, `-u`, `-ru`, `-fclo`) | Mutating |
| `DeleteClient` | Delete a client (`-id`) | Mutating |
| `AddScopeToClient` | Grant scope access to client (`-id`, `-n`) | Mutating |
| `GetIdentityProviders` | List all identity providers | Read-only |
| `AddOAuthIdentityProvider` | Add OAuth provider (`-n`, `-e`, `-cid`, `-cs`, `-t`) | Mutating |
| `AddOpenLdapIdentityProvider` | Add OpenLDAP provider (`-n`, `-e`, `-h`, `-p`, `-ubdn`, `-uan`) | Mutating |
| `AddAdIdentityProvider` | Add Active Directory provider (`-n`, `-e`, `-h`, `-p`) | Mutating |
| `AddAzureEntryIdIdentityProvider` | Add Azure Entra ID provider (`-n`, `-t`, `-e`, `-cid`, `-cs`) | Mutating |
| `UpdateIdentityProvider` | Update identity provider (`-id`, `-n`, `-e`, `-cid`, `-cs`) | Mutating |
| `DeleteIdentityProvider` | Delete identity provider (`-id`) | Mutating |
| `GetApiScopes` | List all API scopes | Read-only |
| `CreateApiScope` | Create API scope (`-n`, `-e`, `-dn`, `-d`) | Mutating |
| `UpdateApiScope` | Update API scope (`-n`, `-nn`, `-e`, `-dn`, `-d`) | Mutating |
| `DeleteApiScope` | Delete API scope (`-n`) | Mutating |
| `GetApiResources` | List all API resources | Read-only |
| `CreateApiResource` | Create API resource (`-n`, `-dn`, `-d`, `-s`) | Mutating |
| `UpdateApiResource` | Update API resource (`-n`, `-dn`, `-d`, `-s`) | Mutating |
| `DeleteApiResource` | Delete API resource (`-n`) | Mutating |
| `GetApiSecretsApiResource` | List secrets of API resource (`-n`) | Read-only |
| `GetApiSecretsClient` | List secrets of client (`-cid`) | Read-only |
| `CreateApiSecretApiResource` | Add secret to API resource (`-n`, `-e`, `-d`) | Mutating |
| `CreateApiSecretClient` | Add secret to client (`-cid`, `-e`, `-d`) | Mutating |
| `UpdateApiSecretApiResource` | Update API resource secret (`-n`, `-s`, `-e`, `-d`) | Mutating |
| `UpdateApiSecretClient` | Update client secret (`-cid`, `-s`, `-e`, `-d`) | Mutating |
| `DeleteApiSecretApiResource` | Delete API resource secret (`-n`, `-s`) | Mutating |
| `DeleteApiSecretClient` | Delete client secret (`-cid`, `-s`) | Mutating |

### Asset Repository Services (group: "Asset Repository Services")

| Command | Description | Type |
|---|---|---|
| `Create` | Create a new tenant (`-tid`, `-db`) | Mutating |
| `Clean` | Reset tenant to factory defaults (`-tid`) | Mutating |
| `Attach` | Attach existing database to tenant (`-tid`, `-db`) | Mutating |
| `Detach` | Detach tenant (`-tid`) | Mutating |
| `Delete` | Delete a tenant (`-tid`) | Mutating |
| `ClearCache` | Clear tenant cache (`-tid`) | Mutating |
| `UpdateSystemCkModel` | Update system CK model to latest (`-tid`) | Mutating |
| `ImportCk` | Import construction kit model (`-f`) | Mutating |
| `ImportRt` | Import runtime model (`-f`, `-r` for replace) | Mutating |
| `ExportRtByQuery` | Export runtime model by query (`-f`, `-q`) | Read-only |
| `ExportRtByDeepGraph` | Export runtime model by deep graph (`-f`, `-id`, `-t`) | Read-only |
| `EnableStreamData` | Enable stream data for current tenant | Mutating |
| `DisableStreamData` | Disable stream data for current tenant | Mutating |
| `CreateFixupScript` | Create a fixup script (`-e`, `-n`, `-f`, `-o`, `-r`) | Mutating |

### Bot Services (group: "Bot Services")

| Command | Description | Type |
|---|---|---|
| `GetServiceHooks` | List service hooks | Read-only |
| `CreateServiceHook` | Create service hook (`-e`, `-n`, `-ck`, `-f`, `-u`, `-a`, `-k`) | Mutating |
| `UpdateServiceHook` | Update service hook (`-id`, `-e`, `-n`, `-ck`, `-f`, `-u`, `-a`, `-k`) | Mutating |
| `DeleteServiceHook` | Delete service hook (`-id`) | Mutating |
| `Dump` | Dump tenant to file (`-tid`, `-f`) | Read-only |
| `Restore` | Restore tenant from dump (`-tid`, `-db`, `-f`, `-oldDb`) | Mutating |
| `RunFixupScripts` | Run fixup scripts for current tenant | Mutating |

### Communication Services (group: "Communication Services")

| Command | Description | Type |
|---|---|---|
| `EnableCommunication` | Enable communication for current tenant | Mutating |
| `DisableCommunication` | Disable communication for current tenant | Mutating |

### Reporting Services (group: "Reporting Services")

| Command | Description | Type |
|---|---|---|
| `EnableReporting` | Enable reporting for current tenant | Mutating |
| `DisableReporting` | Disable reporting for current tenant | Mutating |

### Diagnostics (group: "Diagnostics")

| Command | Description | Type |
|---|---|---|
| `ReconfigureLogLevel` | Reconfigure log level (`-n`, `-minL`, `-maxL`, `-ln`) | Mutating |

### DevOps (group: "DevOps")

| Command | Description | Type |
|---|---|---|
| `GenerateOperatorCertificates` | Generate CA and service certs (`-o`, `-s`, `-n`) | Mutating |

## Execution Flow

1. **Parse intent** — Map natural language to one or more commands from the table above
2. **Gather context** — Run `AuthStatus` and read settings if not cached in this session
3. **Resolve dependencies** — e.g., list users before creating to avoid duplicates; lookup current user's roles for "with my roles"
4. **Build command** — Assemble full `octo-cli -c <CommandValue> <flags>`
5. **Confirm if mutating** — For mutating ops, show the command + a human-readable summary, wait for user confirmation
6. **Execute** — Run the command and present results clearly

## Safety Rules

- **Read-only commands** (Get*, AuthStatus, Export*, Dump): execute directly, no confirmation needed
- **Mutating commands** (Create*, Update*, Delete*, Add*, Remove*, Enable*, Disable*, Import*, Clean*, Reset*, Config, LogIn, Setup, Attach, Detach, Restore, RunFixupScripts): show command + summary, wait for user confirmation before executing
- **Production environment**: add an explicit warning: "You are targeting PRODUCTION" and double-confirm
- **Never** auto-execute tenant deletion (`Delete`), user deletion (`DeleteUser`), or clean operations (`Clean`) without confirmation
- **Batch operations**: confirm the full batch plan before executing any individual command

## Environment Switching

When the user says "switch to <env>" or "connect to <env>":

1. Read `references/environments.md` for the URL mappings
2. Run `octo-cli -c Config` with the appropriate URLs for the target environment
3. Run `octo-cli -c LogIn -i` to authenticate
4. Confirm the new environment with `octo-cli -c AuthStatus`

The default tenant ID is `meshtest` unless the user specifies otherwise.

## Smart Behaviors

### "who am i" / "status"
Run `octo-cli -c AuthStatus` and parse the output into a clean summary showing: user, environment, tenant, roles, and token expiry.

### Generate test credentials
When creating users without specific details, generate unique usernames like `testuser-<4-random-chars>` and suggest a strong password.

### Batch operations
"Create 3 test users" — loop `CreateUser` 3 times with unique credentials. Show the full plan first, then execute after confirmation.

### "with my roles"
First run `GetUsers` + identify current user, then apply the same roles to the new user via `AddUserToRole`.

### Tenant context
Always use the configured tenant from settings. Never require `-tid` on commands that use the configured tenant (e.g., `EnableCommunication`, `EnableReporting`, `EnableStreamData`, `RunFixupScripts`). Only include `-tid` for Asset Repository tenant commands that explicitly require it.

### Environment-aware prompts
After context discovery, always indicate which environment is active when presenting commands for confirmation. Example: "**[test-2]** This will create a new user..."

## Data Model Exploration

### When to Use Scripts vs octo-cli

| User intent | Tool |
|---|---|
| "What's in the data model?" / "show types" / "list enums" / "what models are loaded?" | `ck_explorer.py` (GraphQL) |
| "Show type attributes" / "what associations does X have?" / "search for Production types" | `ck_explorer.py` (GraphQL) |
| "Show instances" / "list machines" / "count entities" / "search runtime" / "filter by state" | `rt_explorer.py` (GraphQL) |
| "Get entity details" / "show entity attributes" / "query columns" | `rt_explorer.py` (GraphQL) |
| "What fields does the GraphQL API have?" / "introspect the schema" | `gql_introspect.py` |
| "Create user" / "import CK" / "switch environment" / "auth status" | `octo-cli` |

### Script Location

All scripts are in the `scripts/` subdirectory of this skill. They read connection info (endpoint URL, tenant, auth token) from `~/.octo-cli/settings.json` automatically.

**Prerequisite:** The user must be authenticated (`octo-cli -c LogIn -i`). If a script fails with a 401/403 error, prompt the user to re-authenticate.

### Script Reference

#### `ck_explorer.py` — Construction Kit Schema Explorer

| Subcommand | Purpose | Example |
|---|---|---|
| `models` | List all CK models | `python ck_explorer.py models` |
| `model <name>` | Model detail + dependencies | `python ck_explorer.py model Industry.Manufacturing-2.0.0` |
| `types` | List all types | `python ck_explorer.py types` |
| `types --model X` | List types in a specific model | `python ck_explorer.py types --model Basic-2.0.1` |
| `type <fullName>` | Type detail: attrs, associations, derived types | `python ck_explorer.py type System-2.0.2/Entity-1` |
| `enums` | List all enums | `python ck_explorer.py enums` |
| `enums --model X` | List enums in a specific model | `python ck_explorer.py enums --model System-2.0.2` |
| `enum <fullName>` | Enum detail: values, flags | `python ck_explorer.py enum System-2.0.2/AggregationTypes-1` |
| `search <term>` | Search type/enum names (case-insensitive) | `python ck_explorer.py search maintenance` |

Flags: `--json` for raw JSON output, `--first N` for pagination limit, `--tenant <id>` to override tenant.

#### `gql_introspect.py` — GraphQL Schema Introspection

Safety valve for when field names change between server versions.

| Subcommand | Purpose | Example |
|---|---|---|
| `top` | Show top-level query fields | `python gql_introspect.py top` |
| `type <name>` | Show fields of a GraphQL type | `python gql_introspect.py type CkType` |

Flags: `--json`, `--tenant <id>`

#### `rt_explorer.py` — Runtime Instance Explorer

Browse, search, and inspect runtime entities (instances of CK types).

| Subcommand | Purpose | Example |
|---|---|---|
| `list <ckId>` | List instances of a CK type | `python rt_explorer.py list Industry.Basic/Machine` |
| `list <ckId> --attrs` | List with all attributes | `python rt_explorer.py list Industry.Basic/Machine --attrs --first 5` |
| `get <ckId> <rtId>` | Get single entity with full detail | `python rt_explorer.py get Industry.Basic/Machine 05eb...` |
| `count <ckId>` | Count instances of a CK type | `python rt_explorer.py count Industry.Basic/Machine` |
| `search <ckId> <term>` | Search by attribute (LIKE match) | `python rt_explorer.py search Industry.Basic/Machine DAR` |
| `search <ckId> <term> --attr X` | Search on specific attribute | `python rt_explorer.py search Industry.Basic/Machine 42 --attr machineState` |
| `query <ckId> --columns c1,c2` | Transient query with specific columns | `python rt_explorer.py query Industry.Basic/Machine --columns name,machineState` |
| `filter <ckId> <attr> <op> <val>` | Filter by attribute value | `python rt_explorer.py filter Industry.Basic/Machine machineState EQUALS 2` |

Flags: `--json` for raw JSON output, `--first N` for pagination limit, `--tenant <id>` to override tenant, `--sort attr:asc|desc` for sorting (on list/search/filter/query).

Filter operators: `EQUALS`, `NOT_EQUALS`, `LESS_THAN`, `LESS_EQUAL_THAN`, `GREATER_THAN`, `GREATER_EQUAL_THAN`, `IN`, `NOT_IN`, `LIKE`, `MATCH_REG_EX`, `ANY_EQ`, `ANY_LIKE`.

### Exploration Workflow

Use a progressive drill-down approach when the user asks about the data model:

1. **Models** — `ck_explorer.py models` — see what CK models are loaded
2. **Types in a model** — `ck_explorer.py types --model <name>` — see what types a model defines
3. **Type detail** — `ck_explorer.py type <fullName>` — see attributes, associations, inheritance
4. **Enums** — `ck_explorer.py enums --model <name>` — see available enumerations
5. **Search** — `ck_explorer.py search <term>` — find types/enums by keyword
6. **Runtime instances** — after understanding the schema, explore actual instances:
   - `rt_explorer.py count <ckId>` — how many instances exist?
   - `rt_explorer.py list <ckId> --first 5` — see some instances
   - `rt_explorer.py get <ckId> <rtId>` — drill into a single entity
   - `rt_explorer.py search <ckId> <term>` — search by name
   - `rt_explorer.py query <ckId> --columns name,state --first 10` — tabular view of specific attributes

### Schema Evolution Handling

If a script fails with a GraphQL error about unknown fields, the schema may have changed between server versions. Use `gql_introspect.py` to discover the current field names:

1. `python gql_introspect.py top` — verify top-level fields still exist
2. `python gql_introspect.py type CkType` — check current CkType field names
3. Update the failing query based on the introspection results
