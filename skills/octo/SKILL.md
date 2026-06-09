---
name: octo
description: Primary entry point and router for ALL OctoMesh tasks. Drives the octo-cli for platform administration (users, roles, groups, tenants, clients, identity providers, blueprints, CK catalog/library management, stream-data archives, communication adapters/pipelines, AI services) and explores the data model and runtime instances via GraphQL. Routes specialized work to sibling skills. When unsure which OctoMesh skill to use, start here. Trigger on: OctoMesh, octo-cli, CLI command, environment switch, auth/login, AuthStatus, tenant, temporary tenant, test tenant, user, role, group, client credentials, non-interactive login, headless authentication, LogInClientCredentials, client mirroring, identity provider, blueprint install/update/rollback, CK catalog, library management, LibraryStatus, stream data archive, archive activation, EnableAi, adapter, deploy pipeline, data flow, MovePipelines, data model, Construction Kit, CK type, enum, association, GraphQL introspection, runtime instance query, list/count/search/filter entities, building, services, Docker, debugging, pipeline YAML, ETL, commit, PR, AB#, MCP server, Refinery Studio, communication operator, Helm.
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
| Pipeline **YAML creation/editing/debugging**, pipeline node configuration, DataContext, ForEach, transformations, `ApplyChanges`, `CreateUpdateInfo`, writing ETL pipelines — anything about *authoring pipeline YAML* | `Skill("pipeline-expert", args: "<user's request>")` |
| Committing changes, finishing work, creating PRs, pushing code, linking Azure DevOps work items (`AB#`), creating feature branches (`dev/`), wrapping up tasks, "ship it", "I'm done" | `Skill("octo-commit", args: "<user's request>")` |
| Developing/extending the **OctoMesh MCP server** itself (code in `octo-mcp-service`), adding MCP tools/resources, MCP server build/config | `Skill("octo-mcp", args: "<user's request>")` |
| **Refinery Studio Angular frontend** development (code in `octo-frontend-refinery-studio`), components, GraphQL codegen, Angular build/lint/test for the studio app | `Skill("refinery-studio", args: "<user's request>")` |
| **Kubernetes Communication Operator** + Helm chart development/deployment (operator code, CRDs, Helm values, K8s manifests) | `Skill("octo-operator", args: "<user's request>")` |
| **Building a new OctoMesh-powered app/workload end to end** — custom CK model + blueprint authoring (`blueprint.yaml`, seed data, `ckModelDependencies`), HTTP APIs from `FromHttpRequest@1` pipelines, operator-deployed Application web apps, CK/blueprint catalog publishing | `Skill("octo-app-builder", args: "<user's request>")` |

**Routing rule for Communication / Pipelines:** If the user wants to *write or understand pipeline YAML*, route to `pipeline-expert`. If they want to *deploy, run, inspect status, or debug executions*, handle it here in `octo`. For end-to-end workflows ("set up a new data flow"), `octo` orchestrates and routes to `pipeline-expert` only for the YAML authoring step.

Only continue with this skill if the request is about: CLI commands (`octo-cli`), data model exploration (CK models/types/enums), runtime instance browsing, GraphQL introspection, environment/auth management, or **communication operations** (adapters, pipeline deployment/execution/status, data flows, triggers).

## Context Discovery

Run these checks once per session and cache the results. If any check has already been performed in this conversation, skip it.

### 1. Active Context

Read `~/.octo-cli/contexts.json` to extract:
- `ActiveContext` — name of the currently active context (e.g., `local_meshtest`, `staging-1_meshtest`)
- From the active context entry:
  - `OctoToolOptions.TenantId` — configured tenant ID
  - `OctoToolOptions.IdentityServiceUrl`, `OctoToolOptions.AssetServiceUrl`, `OctoToolOptions.BotServiceUrl`, `OctoToolOptions.CommunicationServiceUrl`, `OctoToolOptions.ReportingServiceUrl`, `OctoToolOptions.AiServiceUrl`, `OctoToolOptions.AdminPanelUrl` — service endpoints
  - `Authentication.AccessToken` — current auth token (if logged in)

To list all available contexts: `octo-cli -c ListContexts` — the dedicated command. Shows each context's identity URL, tenant, and auth status (none/authenticated/expired). Add `-n <name>` for single-context detail or `-j` for JSON. (`octo-cli -c UseContext` with no `-n` still lists contexts as a legacy fallback.)

### 2. Authentication Check

Run `octo-cli -c AuthStatus` to determine:
- Whether authenticated (token valid)
- Current identity service URL (determines environment)
- JWT claims: subject, roles, issuer, audience, expiration

If not authenticated: inform the user and offer to run `octo-cli -c LogIn -i` (interactive browser device login). For headless/CI scenarios use `octo-cli -c LogInClientCredentials` instead (reads `-id`/`-s` or the `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET` env vars; tenant comes from the active context). `AuthStatus` shows an "Auth Method" line and omits the User Info section for client-credentials tokens. Agent-driven tasks that need a throwaway tenant never require interactive login — see `references/temp-tenants.md`.

### 3. Environment Detection from URLs

| URL Pattern | Environment |
|---|---|
| `localhost:500x` | local |
| `*.test-2.mm.cloud` | test-2 |
| `*.staging.octo-mesh.com` | staging-1 |
| `*.prod-1.octo-mesh.com` | prod-1 (Exoscale SKS Vienna) |
| `*.prod-2.octo-mesh.com` | prod-2 (Azure AKS) |
| `*.staging.meshmakers.cloud` | staging (legacy domain) |
| `*.meshmakers.cloud` (no subdomain prefix) | production (legacy domain) |

## Invocation Syntax

`octo-cli -c <CommandValue> [flags]` — flags use the short form with a `-` prefix (`-un userName`, `-e email`, `-tid tenantId`), or the long form (`--userName`). All flags have both long and short forms (e.g. `--json (-j)`, `--identifier (-id)`); the tables below and `references/command-reference.md` give the exact names.

## Command Reference (Quick Lookup)

Command-name + one-line purpose + safety type only. **For full flag detail, read `references/command-reference.md`** (organized by the same command groups). For environment URLs read `references/environments.md`. Verify flags there before assembling any mutating command.

### Context Management & Auth (no group)

| Command | Purpose | Type |
|---|---|---|
| `AddContext` | Create/update a named context (service URLs incl. `-aisu` AI URL, tenant) | Mutating |
| `Config` | Edit the **active** context's service URLs + tenant in-place (no `-n`) | Mutating |
| `UseContext` | Switch active context (`-n`); without `-n` lists contexts (legacy) | Mutating |
| `ListContexts` | List all contexts with auth status; `-n` detail, `-j` JSON | Read-only |
| `RemoveContext` | Remove a named context | Mutating |
| `LogIn` | Interactive browser/device login (`-i`) | Mutating |
| `LogInClientCredentials` | Headless OAuth2 client_credentials login (`-id`/`-s` or env vars) | Mutating |
| `AuthStatus` | Show authentication status, claims, environment | Read-only |

### Identity Services

| Command | Purpose | Type |
|---|---|---|
| `Setup` | Initial identity services setup | Mutating |
| `GetUsers` / `CreateUser` / `UpdateUser` / `DeleteUser` | Manage users | R / Mut |
| `ResetPassword` | Reset a user's password | Mutating |
| `AddUserToRole` / `RemoveUserFromRole` | Manage user↔role membership | Mutating |
| `GetRoles` / `CreateRole` / `UpdateRole` / `DeleteRole` | Manage roles | R / Mut |
| `GetGroups` / `GetGroup` / `CreateGroup` / `UpdateGroup` / `DeleteGroup` | Manage groups | R / Mut |
| `UpdateGroupRoles` | Set the roles assigned to a group | Mutating |
| `AddUserToGroup` / `RemoveUserFromGroup` | Manage group membership | Mutating |
| `AddGroupToGroup` / `RemoveGroupFromGroup` | Nest/un-nest groups | Mutating |
| `GetEmailDomainGroupRules` / `GetEmailDomainGroupRule` | List/get email-domain→group rules | Read-only |
| `CreateEmailDomainGroupRule` / `UpdateEmailDomainGroupRule` / `DeleteEmailDomainGroupRule` | Manage auto-grouping by email domain | Mutating |
| `GetExternalTenantUserMappings` / `GetExternalTenantUserMapping` | List/get cross-tenant user mappings | Read-only |
| `CreateExternalTenantUserMapping` / `UpdateExternalTenantUserMapping` / `DeleteExternalTenantUserMapping` | Manage cross-tenant user mappings | Mutating |
| `GetAdminProvisioningMappings` | List admin-provisioning mappings for a target tenant | Read-only |
| `CreateAdminProvisioningMapping` / `DeleteAdminProvisioningMapping` | Manage admin provisioning (run from system tenant) | Mutating |
| `ProvisionCurrentUser` | Provision current user as admin in a target tenant | Mutating |
| `GetClients` / `GetClient` | List/get clients | Read-only |
| `AddAuthorizationCodeClient` / `AddDeviceCodeClient` | Add OIDC clients | Mutating |
| `AddClientCredentialsClient` | Add client-credentials client (`-apic` auto-provision into sub-tenants) | Mutating |
| `UpdateClient` / `DeleteClient` / `AddScopeToClient` | Manage clients | Mutating |
| `GetClientMirrors` | List sub-tenants a client is mirrored into | Read-only |
| `SetClientAutoProvision` | Flip a client's auto-provision flag (no backfill) | Mutating |
| `ProvisionClientInExistingTenants` | Backfill a flagged client into all existing sub-tenants | Mutating |
| `ProvisionClientInTenant` | Provision a flagged client into one sub-tenant (`-ctid`) | Mutating |
| `UnprovisionClientFromTenant` | Remove a single client mirror (`-ctid`) | Destructive |
| `GetIdentityProviders` | List identity providers | Read-only |
| `AddOAuthIdentityProvider` / `AddOpenLdapIdentityProvider` / `AddAdIdentityProvider` / `AddAzureEntryIdIdentityProvider` | Add IdP (all accept `-asr`, `-dgid`) | Mutating |
| `AddOctoTenantIdentityProvider` | Add cross-tenant IdP via a parent tenant (`-ptid`) | Mutating |
| `UpdateIdentityProvider` / `DeleteIdentityProvider` | Manage IdPs | Mutating |
| `GetApiScopes` / `CreateApiScope` / `UpdateApiScope` / `DeleteApiScope` | Manage API scopes | R / Mut |
| `GetApiResources` / `CreateApiResource` / `UpdateApiResource` / `DeleteApiResource` | Manage API resources | R / Mut |
| `GetApiSecretsApiResource` / `GetApiSecretsClient` | List secrets | Read-only |
| `CreateApiSecret*` / `UpdateApiSecret*` / `DeleteApiSecret*` (ApiResource & Client) | Manage API secrets | Mutating |

> Active Directory IdPs support AD-group→OctoMesh-group sync: on **every** login, users in an AD group are added to the OctoMesh group whose name matches the AD group CN (case-insensitive). The matching OctoMesh group must already exist and carry the desired role associations.

### Asset Repository Services

| Command | Purpose | Type |
|---|---|---|
| `GetTenants` | List all child tenants | Read-only |
| `Create` | Create a new tenant + provision current user (`-tid`, `-db`, `-np` to skip) | Mutating |
| `Clean` | Reset tenant to factory defaults (deletes CK + RT model) | Destructive |
| `Attach` | Attach an existing database to a tenant | Mutating |
| `Delete` | Delete a tenant | Destructive |
| `ClearCache` | Clear a tenant's cache | Mutating |
| `UpdateSystemCkModel` | Update a tenant's System CK model to latest | Mutating |
| `ImportCk` | Import construction kit model from file (`-w` to wait) | Mutating |
| `ImportRt` | Import runtime model from file (`-r` replace, `-w` to wait) | Mutating |
| `ExportRtByQuery` | Export runtime entities by query → ZIP (`-f`, `-q`) | Read-only |
| `ExportRtByDeepGraph` | Export by association graph → ZIP (`-f`, `-id`, `-t`) | Read-only |
| `CreateFixupScript` | Create a fixup script | Mutating |
| **CK catalog / library** (see below) | Catalog browse, dependency/upgrade checks, import, status, fix | R / Mut |
| **Blueprints** (see below) | Install/update/rollback/uninstall blueprints | R / Mut |
| **Stream-data archives** (see below) | Enable stream data; archive lifecycle + rollups | R / Mut / Destr |

#### CK Catalog / Library Management

Requires the **DataModelManagement** role for catalog import/refresh.

| Command | Purpose | Type |
|---|---|---|
| `ListCatalogs` | List CK model catalog sources | Read-only |
| `ListCatalogModels` | List models in catalogs (`-cn` filter, `-q` search) | Read-only |
| `CheckDependencies` | Show dependency tree for a catalog model (`-cn`, `-m`) | Read-only |
| `CheckUpgrade` | Pre-flight an upgrade/migration (`-cn`, `-m`) | Read-only |
| `LibraryStatus` | Installed models + catalog availability (`-na`, `-io`) | Read-only |
| `ImportFromCatalog` | Import a catalog model + deps (`-cn`, `-m`, `-w`) | Mutating |
| `RefreshCatalogs` | Refresh catalog caches (`-cn` optional) | Mutating |
| `FixAll` | Import all models needing update/fix (`-w`, `-y`) | Mutating |

#### Blueprints

| Command | Purpose | Type |
|---|---|---|
| `ListBlueprints` | List blueprints across catalogs | Read-only |
| `ListBlueprintInstallations` | List blueprints installed on the active tenant | Read-only |
| `ListBlueprintBackups` | List pre-update tenant backups | Read-only |
| `GetBlueprintHistory` | Blueprint application history for the tenant | Read-only |
| `PreviewBlueprintUpdate` | Preview an update without applying (`-tv`, `-m`) | Read-only |
| `InstallBlueprint` | Install a blueprint (`-b`, `-f` force re-apply) | Mutating |
| `UpdateBlueprint` | Apply an update (`-tv`, `-m`, `-nb`, `-dr`) | Mutating |
| `RollbackBlueprint` | Roll tenant back to a backup (`-bid`) | Destructive |
| `UninstallBlueprint` | Remove a blueprint (`-n`, `-c` cascade) | Destructive |

> Blueprint history/preview/update used to live in `octo-bpm`; those commands were removed — use these octo-cli commands. `octo-bpm` now only has `Apply`, `Init`, `version`.

#### Stream-Data Archives (Time Series)

Archive lifecycle mutations require the **StreamDataAdminRole**.

| Command | Purpose | Type |
|---|---|---|
| `EnableStreamData` / `DisableStreamData` | Enable/disable stream data for the tenant | Mutating |
| `ActivateArchive` | Provision the per-archive CrateDB table → Activated (`-id`) | Mutating |
| `EnableArchive` / `DisableArchive` | Re-enable / disable an archive (`-id`) | Mutating |
| `RetryArchiveActivation` | Retry activation after a DDL failure (`-id`) | Mutating |
| `DeleteArchive` | Drop the CrateDB table + soft-delete archive (`-id`) | Destructive |
| `ListRollupsForArchive` | List rollups attached to a source archive (`-id`) | Read-only |
| `FreezeRollupArchive` | Freeze a rollup at a timestamp (`-id`, `-u`) | Mutating |
| `UnfreezeRollupArchive` | Clear FrozenUntil (`-id`, `-ag` accept gaps) | Mutating |
| `RewindRollupWatermark` | Rewind a rollup's watermark to re-aggregate (`-id`, `-t`) | Destructive |

### Bot Services

| Command | Purpose | Type |
|---|---|---|
| `Dump` | Dump a tenant to a `.tar.gz` file (`-tid`, `-f`) | Read-only |
| `Restore` | Restore a tenant from a dump (`-tid`, `-db`, `-f`, `-w` to wait) | Mutating |
| `RunFixupScripts` | Run fixup scripts for the current tenant (`-w` to wait) | Mutating |

### Communication Services

All communication commands accept plain runtime object IDs — the SDK builds the composite RtEntityId internally. `GetAdapters`/`GetPools` return human-readable enum names (e.g. `Online`, `Offline`), not integers.

| Command | Purpose | Type |
|---|---|---|
| `EnableCommunication` / `DisableCommunication` | Enable/disable the communication controller | Mutating |
| `GetAdapters` / `GetAdapter` | List/get adapters (`-j`) | Read-only |
| `GetAdapterNodes` | Aggregated node descriptors from connected adapters (`-j`) | Read-only |
| `GetPipelineSchema` | JSON Schema of valid pipeline YAML for an adapter (`-aid`, `-o`) | Read-only |
| `GetPools` | List pools for the tenant (`-j`) | Read-only |
| `GetPipelineStatus` | Pipeline deployment state (`-id`, `-j`) | Read-only |
| `DeployPipeline` | Deploy pipeline YAML to an adapter (`-aid`, `-pid`, `-f`) | Mutating |
| `ExecutePipeline` | Execute a pipeline, returns execution ID (`-id`, `-f` input file) | Mutating |
| `GetPipelineExecutions` / `GetLatestPipelineExecution` | Execution history / most recent (`-id`, `-j`) | Read-only |
| `GetPipelineDebugPoints` | Debug node tree for an execution (`-id`, `-eid`, `-j`) | Read-only |
| `GetPipelineDebug` | Get a pipeline's debug-capture state (`-id`, `-j`) | Read-only |
| `SetPipelineDebug` | Enable/disable debug capture (`-id`, `-e`) | Mutating |
| `MovePipelines` | Bulk-reassign pipelines to a new adapter (`-ids`, `-aid`, `-rd`) | Mutating |
| `DeployTriggers` / `UndeployTriggers` | Deploy/undeploy all pipeline triggers | Mutating |
| `DeployDataFlow` / `UndeployDataFlow` | Deploy/undeploy a data flow (`-id`) | Mutating |
| `GetDataFlowStatus` | Aggregated data-flow status (`-id`, `-j`) | Read-only |
| `GetWorkloadsByChart` | List workloads by Helm chart name (`-cn`) | Read-only |
| `UpdateWorkloadChartVersion` | Set a workload's chart version — no deploy (`-id`, `-cv`) | Mutating |
| `DeployWorkload` | Deploy a workload through its parent pool (`-id`) | Mutating |
| `UndeployWorkload` | Undeploy a workload — operator helm-uninstalls (`-id`) | Destructive |

> Adapters are now Helm-deployed by the Communication Operator when a pool is deployed; there is **no** manual adapter-deploy command anymore (legacy `DeployAdapter`, `GetPool`, `DeployPoolAdapters`, `UndeployPoolAdapters` were removed). Use `DeployWorkload`/`UndeployWorkload` for adapter/application workloads.

### AI Services

| Command | Purpose | Type |
|---|---|---|
| `EnableAi` | Enable the AI Adapter for the tenant | Mutating |
| `DisableAi` | Disable the AI Adapter (keeps seeded AgentConfig + CK model) | Mutating |

> **CRITICAL:** `EnableAi` requires the communication controller first — run `EnableCommunication` (server returns HTTP 409 otherwise) — and the active context must have an AI service URL set via `-aisu` on `Config`/`AddContext` (local default port 5019).

### Reporting Services

| Command | Purpose | Type |
|---|---|---|
| `EnableReporting` / `DisableReporting` | Enable/disable reporting for the tenant | Mutating |

### Diagnostics & DevOps

| Command | Purpose | Type |
|---|---|---|
| `ReconfigureLogLevel` | Reconfigure log level (`-n`, `-minL`, `-maxL`, `-ln`) | Mutating |
| `GenerateOperatorCertificates` | Generate CA + service certs (`-o`, `-s`, `-n`) | Mutating |

## Execution Flow

1. **Parse intent** — Map natural language to one or more commands from the table above
2. **Gather context** — Run `AuthStatus` and read the active context if not cached in this session
3. **Resolve dependencies** — e.g., list users before creating to avoid duplicates; lookup current user's roles for "with my roles"
4. **Build command** — Assemble full `octo-cli -c <CommandValue> <flags>`
5. **Confirm if mutating** — For mutating ops, show the command + a human-readable summary, wait for user confirmation
6. **Execute** — Run the command and present results clearly

### Import and Job-Based Operations

**Always pass `-w` on background-job commands** — `ImportCk`, `ImportRt` (incl. `-r`), `Restore`, `RunFixupScripts`, `ImportFromCatalog`, `FixAll`. Without `-w` they schedule a Hangfire job and return immediately with a job ID; the CLI reports "started" but not whether the job succeeded or failed — errors (duplicate key, missing dependencies) only surface in `BotServices.log`. With `-w` the CLI waits for completion and surfaces success or failure directly.

## Safety Rules

- **Read-only commands** (Get*, List*, AuthStatus, Export*, Dump, Check*, Preview*, LibraryStatus): execute directly, no confirmation needed
- **Mutating commands** (Create*, Update*, Delete*, Add*, Remove*, Enable*, Disable*, Import*, Install*, Provision*, Activate*, Freeze*/Unfreeze*, Move*, Deploy*/Undeploy*, Clean*, Reset*, AddContext, Config, UseContext, RemoveContext, LogIn, LogInClientCredentials, Setup, Attach, Restore, RunFixupScripts, EnableAi, DisableAi): show command + summary, wait for user confirmation before executing
- **Destructive commands** (`Delete`, `DeleteUser`, `Clean`, `DeleteArchive`, `RewindRollupWatermark`, `RollbackBlueprint`, `UninstallBlueprint`, `UndeployWorkload`, `UnprovisionClientFromTenant`): **never** auto-execute; require explicit confirmation. Most accept `-y` to skip the CLI's own prompt in scripts (`RewindRollupWatermark` has no `-y` flag and always requires confirmation) — do not pass `-y` on the user's behalf without confirmation. **Exception:** a `tmp-`-prefixed temporary tenant that the agent itself created earlier in the same session may be deleted with `-y` without re-confirmation (see `references/temp-tenants.md`).
- **Production environment**: add an explicit warning: "You are targeting PRODUCTION" and double-confirm
- **Batch operations**: confirm the full batch plan before executing any individual command

## Environment Switching

octo-cli uses **named contexts** (like kubectl), each storing its own service URLs, tenant, and auth tokens. Naming convention: `{installation}_{tenantId}` (e.g. `local_meshtest`, `staging-1_meshtest`, `prod-1_meshmakers`); default tenant is `meshtest`.

On "switch to <env>" / "connect to <env>": read `references/environments.md` for URL mappings (installations `local`, `test-2`, `staging-1`, `prod-1`, `prod-2`), then `AddContext -n {ctx}` (add `-aisu` if AI is needed) → `UseContext -n {ctx}` → `AuthStatus`; if the token is invalid, `LogIn -i` (or `LogInClientCredentials` for headless) and re-check. List contexts with `ListContexts`. In the OctoMesh developer shell, the `Register-OctoCliContext` cmdlet wraps this for any installation (it knows the current cluster domains) — route there via `octo-devtools`.

## Smart Behaviors

- **"who am i" / "status":** run `AuthStatus`, summarize user, environment, tenant, roles, token expiry.
- **Generate test credentials:** when details are missing, use unique usernames like `testuser-<4-random-chars>` and suggest a strong password.
- **Batch ("create 3 test users"):** loop the command with unique values; show the full plan, execute after confirmation.
- **"with my roles":** `GetUsers` → identify current user → apply the same roles via `AddUserToRole`.
- **Tenant context:** use the active context's tenant; never add `-tid` to commands that use the configured tenant (`EnableCommunication`, `EnableReporting`, `EnableStreamData`, `EnableAi`, `RunFixupScripts`). Only pass `-tid` on Asset Repository tenant commands that require it.
- **Environment-aware prompts:** always indicate the active environment when confirming (e.g. "**[prod-1]** This will create a new user...").

## Temporary Tenants (Non-Interactive)

When a task needs a throwaway tenant, the agent can run the **entire lifecycle without user interaction** (no `LogIn -i`): `LogInClientCredentials` (machine token, env vars `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET`) + a mirrored client in `octosystem` (`AddClientCredentialsClient ... -apic`) that is auto-provisioned into every new tenant with the same id/secret. Short form: octosystem context → `LogInClientCredentials` → `Create -tid tmp-<x> -db tmp-<x> -np` → `AddContext`/`UseContext` for the new tenant → `LogInClientCredentials` again → work → back to octosystem → `Delete -tid tmp-<x> -y` → `RemoveContext`. Read `references/temp-tenants.md` for the verified workflow, one-time client setup, and pitfalls (`-np` mandatory, per-tenant tokens, no user roles in machine tokens).

## Communication Entity Relationships

Understanding how Communication entities relate allows intelligent resolution of references when executing workflows.

- **Adapter** connects to the communication service via SignalR and *executes* Pipelines (association `System.Communication/Executes-1`, Pipeline→Adapter).
- **DataFlow** is a logical container; Pipelines and PipelineTriggers are its children via `System/ParentChild-1`.
- **Pipeline** holds its YAML in the `PipelineDefinition` attribute; parented to a DataFlow, executed by an Adapter.
- **PipelineTrigger** *triggers* Pipelines (`System.Communication/Triggers-1`); has `cronExpression` and `enabled`; parented to a DataFlow.

CK types for `rt_explorer.py`: `System.Communication/Adapter`, `/Pipeline`, `/DataFlow`, `/PipelineTrigger`, `/PipelineExecution`, `/PipelineStatistics`.

## Communication Workflows

When the user expresses one of these intents, resolve IDs, run the commands, and present results.

- **"What adapters are available?"** — `GetAdapters --json`, then summarize name, rtId, online/offline, config state.
- **"What pipeline nodes can I use?"** — `GetAdapters --json` to find the adapter; `GetAdapterNodes` for the node list (grouped Trigger vs Transform); `GetPipelineSchema --adapterId <rtId>` for the full per-node config schema. With multiple adapters, ask which one.
- **"Deploy this pipeline"** — find the adapter (`GetAdapters --json`) and the pipeline (`rt_explorer.py list System.Communication/Pipeline`); write inline YAML to a temp file; `DeployPipeline --adapterId <id> --pipelineId <id> --file <path>`; verify with `GetPipelineStatus --identifier <pipelineId> --json` = Deployed.
- **"Run this pipeline"** — resolve the pipeline (`rt_explorer.py search System.Communication/Pipeline <name>`); `ExecutePipeline --identifier <rtId>` (capture the execution ID); after a brief wait, `GetLatestPipelineExecution --identifier <rtId> --json`; report status/duration/error; if failed, check debug points.
- **"Show me what happened" / "Debug the last execution"** — `GetLatestPipelineExecution --identifier <pipelineId> --json` for the execution ID + status; if it has debug data, `GetPipelineDebugPoints --identifier <pipelineId> --executionId <guid> --json` and present the node tree. (Toggle capture beforehand with `SetPipelineDebug --identifier <id> --enabled true`.)

### "Set up a new data flow end-to-end"
Full lifecycle — combines `pipeline-expert` (YAML) with `octo` operations:
1. Clarify the data flow (trigger, transformations).
2. **Pre-flight:** for each CK type the pipeline touches, `ck_explorer.py preflight <type> --for-import --insecure` to discover exact attribute IDs + mandatory associations.
3. Route to `pipeline-expert` via `Skill("pipeline-expert", ...)` for the YAML.
4. Discover the adapter: `GetAdapters --json` → adapter rtId.
5. Create the runtime entities: `ImportRt -f <file> -w` (template below).
6. `DeployPipeline --adapterId <id> --pipelineId <id> --file <yaml>` → verify `GetPipelineStatus --identifier <pipelineId> --json` = Deployed → test `ExecutePipeline --identifier <rtId>`. For cron triggers, `DeployTriggers`.

**Step 5 — ImportRt YAML for DataFlow + Pipeline:** use the full DataFlow+Pipeline template in `references/command-reference.md` (ImportRt section), or generate one for any CK type automatically:
```
ck_explorer.py preflight System.Communication/Pipeline --for-import --insecure
```
The DataFlow holds `System/Name-1`; the Pipeline links to it via `System/ParentChild-1` and to the adapter via `System.Communication/Executes-1`, and carries `System.Communication/DeploymentState-1`, `System/Name-1`, `System/Enabled-1`, and the YAML in `System.Communication/PipelineDefinition-1`.

**ImportRt ID format — `ModelName/TypeName-TypeVersion`:**
- **All IDs** (ckTypeId, attribute id, roleId, targetCkTypeId) use format `ModelName/TypeName-TypeVersion` — no model version, WITH type version suffix
- Examples: `System.Communication/Pipeline-1`, `System/Name-1`, `System/ParentChild-1`
- This matches the format produced by `ExportRtByDeepGraph`
- **NOT** the fully versioned format from `ck_explorer.py` output (e.g., `System.Communication-3.0.0/Pipeline-1`)
- **NOT** the fully unversioned format used by `rt_explorer.py` (e.g., `System.Communication/Pipeline`)
- **rtId** must be exactly 24 hex characters `[0-9a-fA-F]` — validate before importing
- See `references/command-reference.md` for the full ImportRt YAML format reference

- **"What's the status of my data flows?"** — `rt_explorer.py list System.Communication/DataFlow`, then `GetDataFlowStatus --identifier <rtId> --json` for each; summarize name, state, pipeline states, last execution, statistics.

### Pipeline Schema as Node Discovery

`GetPipelineSchema --adapterId <rtId>` returns a JSON Schema (draft/2020-12) of every available pipeline node for that adapter, with each node's config properties (types, descriptions, enums, defaults). The available nodes depend on which adapter is running and which plugins it loaded, so prefer this over the build-time schema files when the user asks "what nodes are available?" or about a node's config, or before authoring YAML for a target environment. Save with `--outputFile <path>` for reuse (and feed to `pipeline_validate.py --schema`).

### FromHttpRequest — Endpoint Location

**CRITICAL:** `FromHttpRequest@1`-triggered pipeline endpoints live on the **mesh adapter** process (default `https://localhost:5020`), NOT the communication service (`https://localhost:5015`, which only does pipeline management — deploy/status/execute). The URL pattern is `https://localhost:5020/{tenantId}/{path}`, where `{path}` matches the trigger's `path` property (e.g. `/create-machines`). The adapter runs its own ASP.NET Core server and registers/unregisters routes as pipelines are deployed/undeployed.

### Pipeline Debugging — After Execution

If a pipeline (especially HTTP-triggered) produces no results: `GetLatestPipelineExecution --identifier <pipelineId> --json` — `Status: null` can mean failure OR that tracking hasn't completed yet, so verify against actual data or the adapter log rather than status alone. Check `logFiles/MeshAdapter.log` for `ERROR` lines with the pipeline ID — it shows the exact exception, stack trace, and which node failed (e.g. `PipelineExecution/CreateAssociationUpdate@1`). Common causes: missing mandatory associations, wrong attribute-name casing, RtId path-resolution failure. In `GetPipelineDebugPoints`, nodes missing from the tree never executed (the pipeline stopped before reaching them).

## Data Model Exploration

### When to Use Scripts vs octo-cli

| User intent | Tool |
|---|---|
| Data model: "show types/enums", "what models are loaded?", "type attributes", "associations of X", "search for Production types" | `ck_explorer.py` (GraphQL) |
| Runtime instances: "show/list/count/search/filter instances", "entity details", "query columns" | `rt_explorer.py` (GraphQL) |
| "What fields does the GraphQL API have?" / "introspect the schema" | `gql_introspect.py` |
| "Validate this pipeline YAML" / "check node types before deploy" | `pipeline_validate.py` |
| "Create user" / "import CK" / "switch environment" / "auth status" | `octo-cli` |

### Script Location & Invocation

Scripts live in this skill's `scripts/` subdirectory and read connection info (endpoint URL, tenant, auth token) from the active context in `~/.octo-cli/contexts.json` automatically. **Prerequisite:** the user must be authenticated (`octo-cli -c LogIn -i`); on a 401/403, prompt to re-authenticate.

All Python scripts MUST be run through the venv wrapper, with absolute paths via `$CLAUDE_PLUGIN_ROOT`. The wrapper creates the venv and installs deps on first use. Never call `python`/`python3` directly and never `cd` into the skill directory (it triggers permission prompts and file-not-found errors). Throughout this reference, **`<RUN>`** is shorthand for the required prefix:

```
<RUN> = bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/<script.py>"
```

So `<RUN> ck_explorer.py models` means run the full wrapper command with `ck_explorer.py models` as the script + args. Always expand `<RUN>` to the literal absolute-path form when executing.

### Script Reference

#### `ck_explorer.py` — Construction Kit Schema Explorer

| Subcommand | Purpose | Example |
|---|---|---|
| `models` | List all CK models | `<RUN> ck_explorer.py models` |
| `model <name>` | Model detail + dependencies | `<RUN> ck_explorer.py model Industry.Manufacturing-2.0.0` |
| `types [--model X]` | List all types (or types in one model) | `<RUN> ck_explorer.py types --model Basic-2.0.1` |
| `type <fullName>` | Type detail: attrs, associations, derived types | `<RUN> ck_explorer.py type System-2.0.2/Entity-1` |
| `enums [--model X]` | List all enums (or enums in one model) | `<RUN> ck_explorer.py enums --model System-2.0.2` |
| `enum <fullName>` | Enum detail: values, flags | `<RUN> ck_explorer.py enum System-2.0.2/AggregationTypes-1` |
| `search <term>` | Search type/enum names (case-insensitive) | `<RUN> ck_explorer.py search maintenance` |
| `preflight <fullName>` | Pre-flight for pipeline authoring (attrs + mandatory assocs) | `<RUN> ck_explorer.py preflight Industry.Basic-2.1.0/Machine-1` |
| `preflight <fullName> --for-import` | Generate ImportRt YAML template with full CK attribute IDs | `<RUN> ck_explorer.py preflight System.Communication/Pipeline --for-import` |

Flags: `--json` (raw JSON), `--first N` (pagination), `--tenant <id>` (override tenant), `--insecure` (skip SSL verify for localhost self-signed certs), `--for-import` (preflight only).

#### `gql_introspect.py` — GraphQL Schema Introspection

Safety valve for when field names change between server versions. `<RUN> gql_introspect.py top` shows top-level query fields; `<RUN> gql_introspect.py type <name>` (e.g. `CkType`) shows a GraphQL type's fields. Flags: `--json`, `--tenant <id>`, `--insecure`.

#### `pipeline_validate.py` — Pipeline YAML Validator

Validates a pipeline YAML file against an adapter's JSON Schema **before** deploying: checks that `triggers` and `transformations` sections exist and that every node `type` is known to the schema, recursing into nested container nodes (`ForEach@1`, `For@1`, `If@1`, `Switch@1`, `BufferData@1`). Use it as a pre-deploy gate so a typo'd node type fails fast locally instead of at `DeployPipeline`. Supply the schema one of two ways (mutually exclusive):

```
# Against a local schema file (e.g. one saved via GetPipelineSchema -o):
<RUN> pipeline_validate.py my-pipeline.yaml --schema schema.json

# Fetch the schema live from an adapter via octo-cli (add --insecure for localhost self-signed certs):
<RUN> pipeline_validate.py my-pipeline.yaml --adapter-id <adapterRtId> --insecure
```

Exits 0 with `PASS` when valid, non-zero with a list of `FAIL` errors (each carrying a JSONPath-like location) otherwise.

#### `rt_explorer.py` — Runtime Instance Explorer

Browse, search, and inspect runtime entities (instances of CK types).

| Subcommand | Purpose | Example |
|---|---|---|
| `list <ckId> [--attrs]` | List instances (optionally with all attributes) | `<RUN> rt_explorer.py list Industry.Basic/Machine --attrs --first 5` |
| `get <ckId> <rtId>` | Get a single entity with full detail | `<RUN> rt_explorer.py get Industry.Basic/Machine 05eb...` |
| `count <ckId>` | Count instances of a CK type | `<RUN> rt_explorer.py count Industry.Basic/Machine` |
| `search <ckId> <term> [--attr X]` | Search by attribute (LIKE; `--attr` targets one) | `<RUN> rt_explorer.py search Industry.Basic/Machine 42 --attr machineState` |
| `query <ckId> --columns c1,c2` | Transient query with specific columns | `<RUN> rt_explorer.py query Industry.Basic/Machine --columns name,machineState` |
| `filter <ckId> <attr> <op> <val>` | Filter by attribute value | `<RUN> rt_explorer.py filter Industry.Basic/Machine machineState EQUALS 2` |

Flags: `--json` (raw JSON), `--first N` (pagination), `--tenant <id>` (override tenant), `--sort attr:asc|desc` (list/search/filter/query), `--insecure` (skip SSL verify).

Filter operators: `EQUALS`, `NOT_EQUALS`, `LESS_THAN`, `LESS_EQUAL_THAN`, `GREATER_THAN`, `GREATER_EQUAL_THAN`, `IN`, `NOT_IN`, `LIKE`, `MATCH_REG_EX`, `ANY_EQ`, `ANY_LIKE`.

#### `::` Association Meta-Query Columns

N:M associations expose two meta columns via the `::` path syntax, usable as query columns and in field filters (GraphQL and saved queries):
- `navigationProp.TargetType::totalCount` — number of associated entities
- `navigationProp.TargetType::exists` — boolean (has any association)

Example: to find machines with more than 3 sensors, filter on `sensors.Sensor::totalCount` `GREATER_THAN` `3`. The `::totalCount` filter compiles to a MongoDB aggregation pipeline server-side.

#### Stream-Data & Blueprint CK Types

When stream data is enabled (`EnableStreamData`), the `System.StreamData` CK model is loaded. Its hierarchy is `Archive` (abstract) → `RawArchive` / `RollupArchive` / `TimeRangeArchive`. Browse with `rt_explorer.py`:
- `System.StreamData/Archive` (abstract base), `System.StreamData/RawArchive`, `System.StreamData/RollupArchive`, `System.StreamData/TimeRangeArchive`

Stream-data **query** entities live in the `System` model: `System/StreamDataSimpleQuery`, `System/StreamDataAggregationQuery`, `System/StreamDataGroupingAggregationQuery`, `System/StreamDataDownsamplingQuery`.

Blueprint state is stored tenant-locally (no longer in a cross-tenant system DB) as `System/BlueprintInstallation`, `System/BlueprintHistory`, `System/BlueprintBackup` — query these to diagnose blueprint state. Always discover the exact loaded type IDs with `ck_explorer.py` first; the `isDataStream`/`isStreamType` GraphQL fields were removed, so any query selecting them will fail.

### CRITICAL: CK Type ID Format Differences

Three different contexts use three different ID formats:

| Context | Format | Example |
|---|---|---|
| `ck_explorer.py` output | Fully versioned: `Model-Version/Type-Version` | `Industry.Basic-2.1.0/Machine-1` |
| `rt_explorer.py` input | Fully unversioned: `Model/Type` | `Industry.Basic/Machine` |
| **ImportRt YAML** | **Import format: `Model/Type-Version`** | **`Industry.Basic/Machine-1`** |

**Converting from `ck_explorer.py` output:**
- For `rt_explorer.py`: strip ALL versions → `Industry.Basic-2.1.0/Machine-1` → `Industry.Basic/Machine`
- For ImportRt YAML: strip MODEL version only, keep TYPE version → `Industry.Basic-2.1.0/Machine-1` → `Industry.Basic/Machine-1`

The `ck_explorer.py preflight <type> --for-import` command generates the correct import format automatically.

**NEVER pass versioned CK type IDs (like `Industry.Basic-2.1.0/Machine-1` or `Industry.Basic-2.1.0/Machine`) to `rt_explorer.py`.** Always strip version numbers first.

**NEVER invent or guess CK type IDs.** The actual types loaded in a tenant vary. Always discover real type IDs first by running `ck_explorer.py models` and then `ck_explorer.py types --model <name>` before using any type ID in `rt_explorer.py`.

### Exploration Workflow

Progressive drill-down when the user asks about the data model (expand `<RUN>` to the full wrapper command):

1. **Models** — `<RUN> ck_explorer.py models` — what CK models are loaded
2. **Types in a model** — `<RUN> ck_explorer.py types --model <name>`
3. **Type detail** — `<RUN> ck_explorer.py type <fullName>` — attributes, associations, inheritance
4. **Enums** — `<RUN> ck_explorer.py enums --model <name>`
5. **Search** — `<RUN> ck_explorer.py search <term>` — find types/enums by keyword
6. **Runtime instances** — then explore actual instances: `<RUN> rt_explorer.py count <ckId>`, `... list <ckId> --first 5`, `... get <ckId> <rtId>`, `... search <ckId> <term>`, `... query <ckId> --columns name,state --first 10`

### Deleting Runtime Entities via GraphQL

There is no `octo-cli` command or script for deleting individual runtime entities. Use the Asset Repo GraphQL mutation directly via `curl` against `{AssetServiceUrl}tenants/{TenantId}/GraphQL`:

```bash
TOKEN=$(python3 -c "import json; c=json.load(open('$HOME/.octo-cli/contexts.json')); print(c['Contexts'][c['ActiveContext']]['Authentication']['AccessToken'])")
curl -sk "https://localhost:5001/tenants/maco/GraphQL" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"mutation { runtime { runtimeEntities { delete(entities: [{rtId: \"<RTID>\", ckTypeId: \"<UnversionedCkTypeId>\"}]) } } }"}'
```

Add more objects to the `entities` array to delete several at once. Uses **unversioned** CK type IDs (e.g. `Industry.Manufacturing/Shift`). Returns `{"data":{"runtime":{"runtimeEntities":{"delete":true}}}}`. **Mutating** — confirm before executing.

### Schema Evolution Handling

If a script fails with a GraphQL error about unknown fields, the schema may have changed between server versions. Use `gql_introspect.py` to discover the current field names: `<RUN> gql_introspect.py top` to verify top-level fields, then `<RUN> gql_introspect.py type CkType` (or another type) to check current field names, then update the failing query.
