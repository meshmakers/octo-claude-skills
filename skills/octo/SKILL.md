---
name: octo
description: Primary entry point for ALL OctoMesh tasks — this skill routes to specialized sibling skills when needed. Use this skill for OctoMesh CLI operations (octo-cli), data model exploration, runtime instance browsing via GraphQL, AND as the gateway for building/DevOps (routes to octo-devtools), debugging/investigation (routes to octo-agent), and pipeline YAML (routes to pipeline-expert). Trigger on anything related to OctoMesh — CLI operations, managing users, roles, tenants, clients, identity providers, service hooks, authentication, environment switching, platform administration, data model exploration, Construction Kit models, CK types, enums, attributes, associations, GraphQL schema introspection, runtime instance queries, listing, counting, searching, filtering, inspecting entities, building projects, starting services, Docker, debugging, investigating bugs, pipeline YAML, ETL, or any interaction with the mesh platform. When in doubt about which OctoMesh skill to use, use this one — it will route you to the right place.
allowed-tools:
  - "Read(~/.octo-cli/contexts.json)"
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/octo/references/*)"
  - "Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh:*)"
  - "Bash(octo-cli:*)"
---

# OctoMesh CLI Natural Language Interface

## Overview

Single entry point: `/octo <natural language>`
Claude infers the correct `octo-cli` command from the user's intent, resolves context (environment, tenant, auth status), and executes it — with confirmation for mutating operations.

## Routing — Check Before Proceeding

This skill is the hub for all OctoMesh tasks. Before doing any work, check if the user's request belongs to a specialized sibling skill. If it does, invoke that skill immediately via the Skill tool and pass along the user's request — do NOT attempt to handle it here.

| If the user's intent involves... | Invoke this skill instead |
|---|---|
| Building repos, `dotnet build`, starting/stopping services, Docker compose, git sync, NuGet packages, clean builds, dev environment setup, PowerShell cmdlets (`Invoke-Build`, `Start-Octo`, etc.) | `Skill("octo-devtools", args: "<user's request>")` |
| Debugging bugs, investigating failures, CK model errors (`ResolveFailed`, `modelState`), inspecting MongoDB, selective builds to isolate issues, database backup/restore, service health checks, error logs, cascade failures | `Skill("octo-agent", args: "<user's request>")` |
| Pipeline YAML creation/editing/debugging, pipeline nodes, DataContext, DataFlow, ForEach, triggers, transformations, `ApplyChanges`, `CreateUpdateInfo`, `PipelineTrigger`, cron schedules, ETL pipelines | `Skill("pipeline-expert", args: "<user's request>")` |

Only continue with this skill if the request is about: CLI commands (`octo-cli`), data model exploration (CK models/types/enums), runtime instance browsing, GraphQL introspection, or environment/auth management.

## Context Discovery

Run these checks once per session and cache the results. If any check has already been performed in this conversation, skip it.

### 1. Active Context

Read `~/.octo-cli/contexts.json` to extract:
- `ActiveContext` — name of the currently active context (e.g., `local_meshtest`, `staging_meshtest`)
- From the active context entry:
  - `OctoToolOptions.TenantId` — configured tenant ID
  - `OctoToolOptions.IdentityServiceUrl`, `OctoToolOptions.AssetServiceUrl`, `OctoToolOptions.BotServiceUrl`, `OctoToolOptions.CommunicationServiceUrl`, `OctoToolOptions.ReportingServiceUrl`, `OctoToolOptions.AdminPanelUrl` — service endpoints
  - `Authentication.AccessToken` — current auth token (if logged in)

To list all available contexts: `octo-cli -c UseContext` (no `-n` flag).

### 2. Authentication Check

Run `octo-cli -c AuthStatus` to determine:
- Whether authenticated (token valid)
- Current identity service URL (determines environment)
- JWT claims: subject, roles, issuer, audience, expiration

If not authenticated: inform the user and offer to run `octo-cli -c LogIn -i`.

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

### Context Management

| Command | Description | Type |
|---|---|---|
| `AddContext` | Create/update a named context (`-n`, `-isu`, `-asu`, `-bsu`, `-csu`, `-rsu`, `-apu`, `-tid`) | Mutating |
| `UseContext -n` | Switch active context | Mutating |
| `UseContext` | List all available contexts (no `-n`) | Read-only |
| `RemoveContext` | Remove a named context (`-n`) | Mutating |

### General (no group)

| Command | Description | Type |
|---|---|---|
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
2. **Gather context** — Run `AuthStatus` and read the active context if not cached in this session
3. **Resolve dependencies** — e.g., list users before creating to avoid duplicates; lookup current user's roles for "with my roles"
4. **Build command** — Assemble full `octo-cli -c <CommandValue> <flags>`
5. **Confirm if mutating** — For mutating ops, show the command + a human-readable summary, wait for user confirmation
6. **Execute** — Run the command and present results clearly

## Safety Rules

- **Read-only commands** (Get*, AuthStatus, Export*, Dump): execute directly, no confirmation needed
- **Mutating commands** (Create*, Update*, Delete*, Add*, Remove*, Enable*, Disable*, Import*, Clean*, Reset*, AddContext, UseContext, RemoveContext, LogIn, Setup, Attach, Detach, Restore, RunFixupScripts): show command + summary, wait for user confirmation before executing
- **Production environment**: add an explicit warning: "You are targeting PRODUCTION" and double-confirm
- **Never** auto-execute tenant deletion (`Delete`), user deletion (`DeleteUser`), or clean operations (`Clean`) without confirmation
- **Batch operations**: confirm the full batch plan before executing any individual command

## Environment Switching

octo-cli uses **named contexts** (similar to kubectl) to manage multiple environments. Each context stores its own service URLs, tenant ID, and authentication tokens independently.

Context naming convention: `{environment}_{tenantId}` (e.g., `local_meshtest`, `staging_customer1`, `test2_meshtest`).

When the user says "switch to <env>" or "connect to <env>":

1. Read `references/environments.md` for the URL mappings
2. Determine the context name: `{env}_{tenantId}` (default tenant is `meshtest`)
3. Run `octo-cli -c AddContext -n {contextName}` with the appropriate URLs and tenant
4. Run `octo-cli -c UseContext -n {contextName}` to activate it
5. Run `octo-cli -c AuthStatus` — if the token is still valid, done. If not, run `octo-cli -c LogIn -i` to authenticate, then confirm with `AuthStatus`

To list all available contexts: `octo-cli -c UseContext` (no `-n` flag).

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
Always use the configured tenant from the active context. Never require `-tid` on commands that use the configured tenant (e.g., `EnableCommunication`, `EnableReporting`, `EnableStreamData`, `RunFixupScripts`). Only include `-tid` for Asset Repository tenant commands that explicitly require it.

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

All scripts are in the `scripts/` subdirectory of this skill. They read connection info (endpoint URL, tenant, auth token) from the active context in `~/.octo-cli/contexts.json` automatically.

**Prerequisite:** The user must be authenticated (`octo-cli -c LogIn -i`). If a script fails with a 401/403 error, prompt the user to re-authenticate.

### Script Invocation

All Python scripts MUST be invoked through the virtual environment wrapper using absolute paths via `$CLAUDE_PLUGIN_ROOT`. The wrapper automatically creates a Python virtual environment and installs dependencies on first use. Never invoke scripts directly with `python` or `python3`. Never use `cd` to change into the skill directory.

    bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/<script.py>" [args...]

**CRITICAL — correct path example:**
- CORRECT: `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" models`
- WRONG:   `cd ... && bash scripts/run_python.sh scripts/ck_explorer.py models` (causes permission prompts!)
- WRONG:   `bash scripts/run_python.sh ck_explorer.py models` (file not found!)

### Script Reference

#### `ck_explorer.py` — Construction Kit Schema Explorer

| Subcommand | Purpose | Example |
|---|---|---|
| `models` | List all CK models | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" models` |
| `model <name>` | Model detail + dependencies | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" model Industry.Manufacturing-2.0.0` |
| `types` | List all types | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" types` |
| `types --model X` | List types in a specific model | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" types --model Basic-2.0.1` |
| `type <fullName>` | Type detail: attrs, associations, derived types | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" type System-2.0.2/Entity-1` |
| `enums` | List all enums | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" enums` |
| `enums --model X` | List enums in a specific model | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" enums --model System-2.0.2` |
| `enum <fullName>` | Enum detail: values, flags | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" enum System-2.0.2/AggregationTypes-1` |
| `search <term>` | Search type/enum names (case-insensitive) | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" search maintenance` |

Flags: `--json` for raw JSON output, `--first N` for pagination limit, `--tenant <id>` to override tenant, `--insecure` to disable SSL verification (for localhost with self-signed certs).

#### `gql_introspect.py` — GraphQL Schema Introspection

Safety valve for when field names change between server versions.

| Subcommand | Purpose | Example |
|---|---|---|
| `top` | Show top-level query fields | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/gql_introspect.py" top` |
| `type <name>` | Show fields of a GraphQL type | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/gql_introspect.py" type CkType` |

Flags: `--json`, `--tenant <id>`, `--insecure`

#### `rt_explorer.py` — Runtime Instance Explorer

Browse, search, and inspect runtime entities (instances of CK types).

| Subcommand | Purpose | Example |
|---|---|---|
| `list <ckId>` | List instances of a CK type | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" list Industry.Basic/Machine` |
| `list <ckId> --attrs` | List with all attributes | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" list Industry.Basic/Machine --attrs --first 5` |
| `get <ckId> <rtId>` | Get single entity with full detail | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" get Industry.Basic/Machine 05eb...` |
| `count <ckId>` | Count instances of a CK type | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" count Industry.Basic/Machine` |
| `search <ckId> <term>` | Search by attribute (LIKE match) | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" search Industry.Basic/Machine DAR` |
| `search <ckId> <term> --attr X` | Search on specific attribute | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" search Industry.Basic/Machine 42 --attr machineState` |
| `query <ckId> --columns c1,c2` | Transient query with specific columns | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" query Industry.Basic/Machine --columns name,machineState` |
| `filter <ckId> <attr> <op> <val>` | Filter by attribute value | `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" filter Industry.Basic/Machine machineState EQUALS 2` |

Flags: `--json` for raw JSON output, `--first N` for pagination limit, `--tenant <id>` to override tenant, `--sort attr:asc|desc` for sorting (on list/search/filter/query), `--insecure` to disable SSL verification (for localhost with self-signed certs).

Filter operators: `EQUALS`, `NOT_EQUALS`, `LESS_THAN`, `LESS_EQUAL_THAN`, `GREATER_THAN`, `GREATER_EQUAL_THAN`, `IN`, `NOT_IN`, `LIKE`, `MATCH_REG_EX`, `ANY_EQ`, `ANY_LIKE`.

### CRITICAL: CK Type ID Format Differences

`ck_explorer.py` and `rt_explorer.py` use **different ID formats**:

| Tool | Format | Example |
|---|---|---|
| `ck_explorer.py` output | Versioned: `ModelName-Version/TypeName-Version` | `Industry.Basic-2.1.0/Machine-1` |
| `rt_explorer.py` input | Unversioned: `ModelName/TypeName` | `Industry.Basic/Machine` |

**To convert a CK type ID for use with `rt_explorer.py`:** strip the version suffixes from both the model part and the type part. Remove the `-X.Y.Z` or `-N` segments:
- `Industry.Basic-2.1.0/Machine-1` → `Industry.Basic/Machine`
- `Basic-2.0.1/Employee-1` → `Basic/Employee`
- `System-2.0.2/Entity-1` → `System/Entity`

**NEVER pass versioned CK type IDs (like `Industry.Basic-2.1.0/Machine-1` or `Industry.Basic-2.1.0/Machine`) to `rt_explorer.py`.** Always strip version numbers first.

**NEVER invent or guess CK type IDs.** The actual types loaded in a tenant vary. Always discover real type IDs first by running `ck_explorer.py models` and then `ck_explorer.py types --model <name>` before using any type ID in `rt_explorer.py`.

### Exploration Workflow

Use a progressive drill-down approach when the user asks about the data model:

1. **Models** — `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" models` — see what CK models are loaded
2. **Types in a model** — `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" types --model <name>` — see what types a model defines
3. **Type detail** — `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" type <fullName>` — see attributes, associations, inheritance
4. **Enums** — `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" enums --model <name>` — see available enumerations
5. **Search** — `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/ck_explorer.py" search <term>` — find types/enums by keyword
6. **Runtime instances** — after understanding the schema, explore actual instances:
   - `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" count <ckId>` — how many instances exist?
   - `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" list <ckId> --first 5` — see some instances
   - `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" get <ckId> <rtId>` — drill into a single entity
   - `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" search <ckId> <term>` — search by name
   - `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/rt_explorer.py" query <ckId> --columns name,state --first 10` — tabular view of specific attributes

### Deleting Runtime Entities via GraphQL

There is no `octo-cli` command or script for deleting individual runtime entities. Use the Asset Repo GraphQL mutation directly via `curl`. The endpoint URL is `{AssetServiceUrl}tenants/{TenantId}/GraphQL`.

```bash
TOKEN=$(python3 -c "import json; c=json.load(open('$HOME/.octo-cli/contexts.json')); print(c['Contexts'][c['ActiveContext']]['Authentication']['AccessToken'])")
curl -sk "https://localhost:5001/tenants/maco/GraphQL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { runtime { runtimeEntities { delete(entities: [{rtId: \"<RTID>\", ckTypeId: \"<UnversionedCkTypeId>\"}]) } } }"}'
```

- Multiple entities can be deleted in a single call by adding more objects to the `entities` array
- Uses **unversioned** CK type IDs (e.g., `Industry.Manufacturing/Shift`, not `Industry.Manufacturing-2.0.0/Shift-1`)
- Returns `{"data":{"runtime":{"runtimeEntities":{"delete":true}}}}`
- This is a **mutating** operation — always confirm with the user before executing

### Schema Evolution Handling

If a script fails with a GraphQL error about unknown fields, the schema may have changed between server versions. Use `gql_introspect.py` to discover the current field names:

1. `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/gql_introspect.py" top` — verify top-level fields still exist
2. `bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/gql_introspect.py" type CkType` — check current CkType field names
3. Update the failing query based on the introspection results
