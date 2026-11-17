# Changelog

All notable changes to the octo-claude-skills plugin. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.28.12] — 2026-11-16

### Changed

- **`octo-app-builder`, `pipeline-expert`, `octo`** — app HTTP APIs are authenticated by default (AB#9128, Feature AB#8777; decided by Gerald 2026-11-16). The build sequence, `references/http-api-pipelines.md` and the blueprint seed example use `FromHttpRequest@2` instead of the deprecated, always public `FromHttpRequest@1`; new sections "Route security" (token of the tenant's identity service → `401`, token of another tenant → `403`, `requiredRoles` → `403`; the `Authorization` header never reaches the DataContext) and "Public routes (only on purpose)" with the warning (callable by anyone with the URL, no identity, tenant or role check; only for webhooks, public forms and one-time links; `allowAnonymous: true` explicit with a comment; minimal response; verify in the pipeline; never `@1`). Pattern 3 (one-time link) is the public example, noting that an rtId is not a secret. The response semantics now name the envelope the adapter strips (AB#5674) and that only the route authorization answers `401`/`403`; the `ServiceTokenEnforcement=Warn` relaxation is named; one eval assertion checks `@2` and an explicit public route. `references/app-workload.md`: the proxy passes the caller's `Authorization` header through, the SPA signs the user in with an OIDC client of the tenant (authorization code with PKCE) and sends the access token; never a fixed proxy token for every caller. The recipe no longer turns off TLS verification for https upstreams: verification stays on (cluster CA via `NODE_EXTRA_CA_CERTS`), because the proxy now forwards tokens. Troubleshooting row for `401`/`403`; the design constraint "no auth on adapter HTTP routes" is replaced. `node-reference-mesh.md` `FromHttpRequest@2`: authorization steps and the warning that every `@1` route is public; the billing example uses `@2`.

- **`octo`, `octo-app-builder`, `octo-deploy`, `pipeline-expert`, `octo-agent`, `octo-devtools`** — M1 correction round for the Builder knowledge pages (AB#9163, Feature AB#8777):
  - client role assignment: `AddClientToRole` / `RemoveClientFromRole` / `UpdateClientRoles` / `AddClientToGroup` / `RemoveClientFromGroup` with their MCP tools (`add_client_to_role`, `get_client_roles`, `add_client_to_group`, …) in the command reference (Roles and Clients) and the octo quick lookup;
  - `GetPools` → `GetDeploymentSites`, and the REST-only pool deploy with a hand-made bearer token → `DeployDeploymentSite` / `UndeployDeploymentSite` (octo-cli AB#4924);
  - blueprint catalogs refresh with `octo-cli -c RefreshBlueprintCatalogs [-cn <catalog>]` (role `DataModelManagement`, no restart) instead of `kubectl rollout restart` of the asset repository; the app-workload iteration no longer restarts deployments with kubectl on shared clusters, verification uses octo-cli signals;
  - the `one-time-ticket/` workspace references are gone (the `Demo.Tickets` example in the references is self-contained); shell examples in octo-app-builder and octo-deploy are bash with `/` paths;
  - customer and internal cluster names in tenant-facing content replaced with placeholders (`<CustomerModel>`, `<context>`, `<cluster-domain>`, anonymized pipeline example origins);
  - System.Communication dependency ranges in examples follow the current major (`[4.0,5.0)`);
  - `http-api-pipelines.md`: how to validate required body fields with `If@1` (null/empty checks, guarded write), where a route is reachable (in-cluster service address; from outside only with the opt-in adapter ingress `IngressEnabled` + `DeployWorkload`, AB#9166), token passed as a header on stdin; `blueprint-authoring.md`: seeding a `System.Identity/Role` (and group) for `requiredRoles`, granting it after the install;
  - GitHub tokens of `octo-ckc`/`octo-bpm` go into their settings files instead of `-gt` on the command line; octo-deploy eval expects `RefreshBlueprintCatalogs`.
  - context-name and tenant examples are neutral (`local_mytenant`, `staging_…`, `production_…`, `<root-context>`, `tenant-a,tenant-b,tenant-c`); the environment detection table names `staging`/`production` and keeps the Meshmakers installations in a developer-machine note; octo-deploy no longer names the internal catalog repositories or CI templates in tenant-facing sections, and `test-2-environment.md` § *Creating a tenant on test-2* is renamed *Creating a tenant* (page-plan key).
  - batch review: the `octo` command reference and quick lookup have a `RefreshBlueprintCatalogs` entry and say that `RefreshCatalogs` covers CK model catalogs only; octo-deploy eval 0 expects both refreshes, and the octo-app-builder eval accepts `GetPipelineExecutions` / debug points for the route check and names the stripped request envelope.
  - CodeRabbit round 1: testing a route pipeline without an ingress needs `FromExecutePipelineCommand@1` beside `FromHttpRequest@2` (and tests the logic, not the route authorization); octo-deploy polls `GetDeploymentSites` until Deployed, marks `Register-OctoCliContext` as PowerShell; the temp-tenant teardown keeps the contexts when `Delete` fails; the octo routing row for octo-deploy names test-2 again (its workflow targets test-2 only).

## [0.28.11] — 2026-11-16

### Changed

- **`pipeline-expert`, `octo-app-builder`, `octo-operator`** — secret defaults of an Application (AB#7252, Feature AB#7219; System.Communication 4.15.0, value Hidden since 4.16.0; controller AB#7244/AB#7245, mesh adapter AB#7246/AB#7251). `pipeline-expert`: `VerifyCaptcha@1` in `node-reference-mesh.md` (settings, output `{ valid, source, reason }`, tenant secret else the default, an override encrypted with an unknown key id falls back to the default, any other undecryptable override does not; two entities with the same well-known name are refused and count as not set; check `valid` before `reason`) and `RevealSecret@1` with why it refuses `System.Communication/SecretDefault` (platform-only: no tenant identity may obtain it); `GetPipelineConfigByCkTypeId@1` refuses the type; `MakeHttpRequest@1` is not for CAPTCHA checks; one line each in the `SKILL.md` node tables. `octo-app-builder`: `references/app-workload.md` §Secrets — secret-flagged `ValueOverride` only for secrets the pod needs, `SecretDefaults` for secrets only platform nodes need; the seed declares no `SecretDefaults` entry (an entry without a value makes the deploy refuse the Application; the secret seed lint refuses values, placeholders and `${...}` variables, and blueprints have no install-time parameters); the operator adds key and value after the install (Studio *Further attributes*, GraphQL with the secret as a variable, or a CD from Vault as EC on test-2) and deploys, re-apply keeps the entry; `AllowedTenantIds` absent or empty = own tenant and whole subtree, a non-empty list only narrows it (a later tenant must be added to it); projection on deploy, on tenant load and on `POST {tenant}/v1/secretDefaults/reconcile`, Pending and Deployed Applications are sources, undeploy withdraws, a refused redeploy (state Error) keeps the defaults already projected, removing the entry or narrowing `AllowedTenantIds` revokes at the next projection, not while the Application is in Error (controller PR #100), and an invalid entry keeps the default already projected in every tenant all entries of its key allow; best effort per tenant with events linked to the Application (read them; the controller's per-deploy summary is logged only when a count is not 0 and does not count a tenant whose secret defaults could not be read (it keeps the withdrawn default until its next reconcile), so before revoking an old secret query the projected `SecretDefault` in every served tenant); the projected entity is the "set" signal because the value is Hidden; keys are one namespace per target tenant, so overlapping Applications need distinct keys; pointer in `SKILL.md`. `octo-operator`: secret defaults are not a Helm tier — they never reach the operator, a values file or the release Secret. Worked sample: `octo-communication-controller-services/samples/Blueprints/SecretDefaultDemo/` (controller PR #96).
- **`octo`, `octo-deploy`** — `LogInClientCredentials` runs in a context of the agent's own (`agent_<lane>_octosystem`), never in a human's context such as `local_octosystem` (octo-cli AB#9063): the old temp-tenant workflow logged the client into `local_octosystem` and replaced the human's interactive login, and context names match case-insensitively. `temp-tenants.md` (workflow step 1, teardown, new pitfall), `command-reference.md` (`--replace-login` / `-rl` and the refusal), `test-2-environment.md`.
- **`octo`** — `temp-tenants.md`: `TenantOwners` carries every built-in platform role **including** `SecretManagement` (identity AB#8161), so a `--scratch` creator client holds it in its scratch tenant and can create clients with a secret there; the earlier "except `SecretManagement`" was wrong (AB#9065).
- **`octo-mcp`** — new section "Entity Query Paging" (AB#8904, octo-mcp-service): `query_entities`, `query_entities_simple`, `navigate_associations`, `get_association_tree` (roots) and `execute_runtime_query` (`RtSimpleRtQuery`) page with a default of 100 and refuse a page size above the maximum of 1000 (never capped; an installation may configure both lower); the paging arguments per tool, the `Paging` result block, the config rule (`MaxQueryResultLimit` can be lowered, not raised) and how a new entity-returning tool uses `QueryPaging`. One new "Things NOT to Do" line.
- **`octo`, `octo-app-builder`, `pipeline-expert`** — passages that only apply on a developer machine (local stack ports, kind domains, developer-shell helpers `Register-OctoCliContext` / `Invoke-OctoTenantSweep`, build-output paths) are wrapped in `<!-- developer-machine -->` ... `<!-- /developer-machine -->`, and the `octo-cli` context examples use `https://<service-host>/` placeholders instead of `localhost` ports. Claude Code reads the skills unchanged; the System.Ai.Builder knowledge pages (octo-ai-services `tools/SkillPages`) leave the marked passages out. `pipeline-expert` "Pipeline Validation" now names the tenant path first (`validate_pipeline_definition`, `dry_run_pipeline`, `GetPipelineSchema`) and keeps the build-time schema table for developer machines. `octo-ckc`/`octo-bpm` are described as the CLIs of `octo-construction-kit-engine`, the `bin/DebugL` path only in marked passages (AB#9083).
- **`octo-deploy`, `octo-agent`** — developer-machine passages (kind domain, `Register-OctoCliContext`, `Invoke-OctoTenantSweep`, `bin/DebugL` paths of `octo-ckc`/`octo-bpm`) are marked the same way, so the "Deploy and promote" and "Diagnose and fix" knowledge pages keep only what a tenant can do (AB#9084).
- **`octo`, `octo-app-builder`, `pipeline-expert`, `octo-deploy`** — the Python explorer scripts (`ck_explorer.py`, `rt_explorer.py`, `gql_introspect.py`, `pipeline_validate.py`) and Tailscale are developer-machine passages too: each mention now names the tenant path first (MCP `get_type_schema` / `search_types` / `validate_pipeline_definition`, Studio, GraphQL) and keeps the script in a marked passage. Registry probes use `curl -sI` with the registry CA trusted (no `-k`); the CSV upload example reads the Authorization header from stdin. ImportRt references link `references/command-reference.md#models` (AB#9083, CodeRabbit on octo-ai-services#50).
- **`pipeline-expert`** — new worked example "CSV Import with Upsert per Natural Key" (`references/pipeline-examples.md`, section 7): `FromHttpRequest@2` upload, `ImportFromCsv@1`, natural key per meter and month with `Concat@1`, `GetRtEntitiesByWellKnownName@1` lookup with insert generation, `CreateUpdateInfo@1` in `ForEach@1`, one `ApplyChanges@2`, shaped response; checked against the Mesh Adapter pipeline schema. `node-reference-mesh.md` documents `FromHttpRequest@2` (security properties, response envelope) and marks `@1` deprecated, and marks the three target paths of `GetRtEntitiesByWellKnownName@1` as required — the two schema errors of builder brief b5 (AB#9085).

## [0.28.10] — 2026-11-16

### Changed

- **CLAUDE.md** — Versioning: story branches no longer bump the version; they add CHANGELOG lines under `## [Unreleased]` and are pushed without a pull request. The daily docs batch of octo-claude-pm sets the version once (next patch after `main`) and turns Unreleased into that version's header (AB#9020).

## [0.28.9] — 2026-11-15

### Changed

- **`octo-devtools`** — Feature environments in both workspace layouts (octo-tools AB#9007): `New-OctoEnvironment` detects the base lane (`$env:OCTO_ENVIRONMENT_BASE`, `branches/main`, or `$rootPath` itself in the flat layout, manifest `base: "."`) and takes `-base`; without `-repos` it creates an empty environment, so a hand-made environment is adopted with `Add-OctoEnvironmentRepo -path <worktree> -inPlace`. `SKILL.md`, `references/command-reference.md`, `references/workflows.md`.

## [0.28.8] — 2026-11-15

### Fixed

- **`octo`** — the SKILL.md body has headroom under the release gate again (499 → 477 lines, limit 500, target ≤ 480; AB#8991). The `gql_introspect.py` and `pipeline_validate.py` reference, the `::` association meta columns and the stream-data / blueprint CK types moved verbatim into the new `references/data-model-scripts.md`; the body keeps a short summary of each with a pointer. The duplicated ImportRt ID-format list now points to `references/command-reference.md` (ImportRt), which already holds the full rules. Description, triggers and the routing table are unchanged.

## [0.28.7] — 2026-11-15

### Changed

- **`octo`** — `SKILL.md` (Secrets Rule) and `references/command-reference.md` name `-p`/`--password` as deprecated with the removal date to be announced (AB#9010, AB#8861). No example in the skills passes a password as an argument; check: `git grep -nE 'octo-cli.*-c +(ResetPassword|CreateUser|Setup)( |$).*( -p( |$)|--password( |=|$))' -- skills` finds nothing.
- **`octo`** — `SKILL.md` body back under the 500-line budget (504 → 499 lines, `validate_skill_frontmatter.py` failed on `main`): the `pipeline_validate.py` usage is written more compactly, no content removed.

## [0.28.6] — 2026-11-15

### Changed

- **`pipeline-expert`** — `ExecuteCSharp@1` documents the new argument fields `optional` and `defaultValue` (AB#9006, octo-communication-sdk): an optional argument whose `valuePath` is missing is silent, `defaultValue` replaces null for a missing or null path and must be convertible to `dataType`, and a missing path of a non-optional argument is reported once per pipeline execution with a record count instead of one warning per record. Table, example and behaviour in `references/node-reference-sdk.md`, one line in `SKILL.md`.

## [0.28.5] — 2026-11-15

### Changed

- **`octo-commit`** — Step 9 points to the `octo-claude-pm` verify gate (0.46.0, AB#8988, AB#8989, AB#8990): what it refuses, the order local review → fix commit → `verify_record.py run` and `review` on that commit, and where the rules are (`agent-operating-rules` §2.1–§2.3). The rules themselves are not restated.

## [0.28.4] — 2026-11-13

### Changed

- **`octo`** — `references/command-reference.md`: `CreateUser` and `ResetPassword` run the CK methods `System.Identity/User.CreateUser-1` / `User.ResetPassword-1` (AB#8418, octo-cli): needed identity versions (3.5.57 / 3.5.52 with `Methods:Identity:EnablePasswordMethods`), no REST fallback, server-side refusals as `CODE: message`. The password examples already use `--password-stdin` only.

## [0.28.3] — 2026-11-11

### Added

- **`CLAUDE.md`** — section "Skills shipped as knowledge pages" (AB#8490): `octo-app-builder` and `pipeline-expert` are cut into knowledge pages of the opt-in blueprint System.Ai.Builder by the generator `tools/SkillPages` of octo-ai-services. Documents what that means for skill authors (headings are page boundaries, a section must fit one page of 12,000 characters, relative links become page links, no machine-local paths or internal host names) and the sync procedure after a skill change. No skill content changed.

## [0.28.2] — 2026-11-11

### Changed

- **`pipeline-expert`** — `McpToolCall@1` documents the new optional `executionIdArgument` (AB#8703, octo-mesh-adapter): it writes the id of the current pipeline execution into the named tool argument (e.g. `runRef` of `knowledge_upsert_page`), replacing a value from `argumentsPath`; in a pipeline started by `ToPipelineDataEvent@1` it is the called pipeline's id. Table, example and behaviour in `references/node-reference-mesh.md`, one line in `SKILL.md`.

## [0.28.1] — 2026-11-11

### Fixed

- **`octo-commit`** — no longer merges a PR (AB#8768). The CodeRabbit loop of Step 9 (agent merge with `gh pr merge --squash`, one push per finding, inline comments only, re-review with `@coderabbitai resolve`) is replaced by a pointer: with `octo-claude-pm` installed its `agent-operating-rules` §2.3 decide the review rounds, the merge queue (`request_merge`) and the developer's test and merge. Without it a short fallback remains (title check, judge every finding, answer every thread, upstream PRs of a cross-repo change merged and their packages published first with the merge order reported, report ready only after the review of the head commit) that leaves the merge to the developer or a maintainer. Frontmatter description, Common Mistakes and the `README.md` skill table updated accordingly.

## [0.28.0] — 2026-11-10

### Added

- **`octo`** — operations of asynchronous CK methods (AB#8446, octo-cli + octo-sdk): new commands `GetOperation` (`-id`, `-w`, `-j`) and `ListOperations` (`-m`, `-s`, `-since`, `-a`, `-sk`, `-t`, `-j`) in `SKILL.md` and `references/command-reference.md`. `Dump` now documents `-iad`, the method path for the context's tenant (operation id, progress, `retryAfterSeconds`), the fallback to the job API and the failure codes.

## [0.27.2] — 2026-11-10

### Changed

- **`pipeline-expert`** — `node-reference-mesh.md`: `AnthropicAiQuery@1` authenticates MCP with the token of exactly the configured `mcpServiceAccountConfigName`; a configured account that yields no token now means one warning, no MCP call and a query without tools (before: MCP calls sent unauthenticated). The caveat about a shared service-account token is removed — fixed in octo-mesh-adapter (AB#8699).

## [0.27.1] — 2026-11-09

### Changed

- **`pipeline-expert`** — `node-reference-mesh.md`: `AnthropicAiQuery@1` states that MCP needs an identity — an MCP URL (node or inherited from the AiConfiguration) is used only with `mcpServiceAccountConfigName` or `mcpDelegateToCaller` / `identity: Caller`; otherwise the node skips MCP with one warning naming the node and the missing setting and runs without tools. Adds the missing `mcpServiceAccountConfigName` and `mcpDelegateToCaller` rows to the property table and an example; `SKILL.md` node list notes the rule (AB#8685, octo-mesh-adapter).

## [0.27.0] — 2026-11-09

### Added

- **`pipeline-expert`** — `node-reference-mesh.md`: new node `McpToolCall@1` (deterministic call of an allowlisted MCP tool as a `ServiceAccountConfiguration`, allowlist checked before any network call, fail-closed identity, MCP error code and message in the pipeline error, result into the data context) and, on `AnthropicAiQuery@1`, `usageOutputPath` (input/output/cache-read/cache-creation tokens and a cost estimate, summed over all successfully answered calls; not written when no call succeeded) and `cacheSource` (prompt-cache breakpoint on the source block, with the byte-identity caveat for `dataPaths`). `SKILL.md` node list updated (AB#8658, octo-mesh-adapter).

## [0.26.2] — 2026-11-09

### Changed

- **`octo`** — `temp-tenants.md` notes that a `--scratch` creator client can no longer grant itself an app role a blueprint seeds later (identity AB#8569, `403 self-grant`); a user administrator or another client must grant it. `TenantOwners` is described as every built-in platform role except `SecretManagement`, not "all roles" (AB#8583).

## [0.26.1] — 2026-11-09

### Changed

- **`pipeline-expert`** — `node-reference-mesh.md`: `AnthropicAiQuery@1` documents guaranteed JSON (`jsonSchema`, `maxJsonRepairAttempts`: constrained decoding, local validation, at most two context-free repair calls, failure names the JSONPath) and prompt by name (`promptTemplateName`: `AiPromptTemplate` with `PromptPurpose: KnowledgeGeneration` via the pipeline's `Uses` hand-over, inline `question`/`systemPrompt` override, model settings template → AiConfiguration → node, redeploy after a prompt change) (AB#8498, octo-mesh-adapter). Fixed stale facts in the same section: `question` is no longer always required, and there is no default model (the table named a retired model id).

## [0.25.3] — 2026-11-08

### Changed

- **`octo-deploy`** — `test-2-environment.md` documents the per-workstation agent client on test-2 (AB#8475): `claude-agent-<user>-<workstation>` in `octosystem`, client_credentials only, role `TenantManagement` only, `-apic` without mirroring into existing child tenants, secret file created before the client, verification with `AuthStatus`. Replaces the note that the `claude-agent` client on test-2 was unverified.
- **`octo`** — `temp-tenants.md` points shared environments to the per-workstation client and notes that a client created with an unknown secret must be recreated.

## [0.25.2] — 2026-11-08

### Changed

- **`octo`** — changing the data model needs the tenant role `DataModelManagement` (AB#8529, asset repository from r3.5.67): `ImportCk`, `ImportFromCatalog`, `FixAll`, `RefreshCatalogs`, `RefreshBlueprintCatalogs` and the blueprint install/update/uninstall commands answer `403` with code `DataModelManagementRequired` without it. SKILL.md and `command-reference.md` no longer say the scope `octo_api.data_model_management` is enough.

## [0.25.1] — 2026-11-05

### Changed

- **`octo`** — `temp-tenants.md` no longer says `LogInClientCredentials` reads the secret from `-s` (AB#8303, follow-up of AB#8142): the secret comes from `--secret-stdin`, `OCTO_CLI_CLIENT_SECRET` or the hidden prompt, and `-s` is named only as deprecated (shell history, process list). No other client-secret example with `-s` was left in the skills. The `-s` of `UpdateApiSecret*`/`DeleteApiSecret*` stays: it takes the stored secret hash, not a secret. The other `-p`/`-s` hits are a port, a server name and a path.

## [0.25.0] — 2026-11-05

### Changed

- **`octo`, `octo-deploy`** — secrets never on the command line (AB#8142, follows octo-cli AB#8044). `command-reference.md`, `temp-tenants.md`, `SKILL.md` and the test-2 authentication note use the prompt, `--password-stdin` / `--secret-stdin` / `--client-secret-stdin` and the `OCTO_CLI_*` environment variables instead of `-p`, `-s` and `-cs` (deprecated in octo-cli) for `ResetPassword`, `Setup`, `CreateUser`, `AddClientCredentialsClient`, `AddDeviceCodeClient`, `AddOAuthIdentityProvider`, `AddAzureEntryIdIdentityProvider`, `UpdateIdentityProvider` and `LogInClientCredentials`. New short "Secrets Rule" section in `octo/SKILL.md`: never put secrets in arguments, never echo them. `temp-tenants.md` reads the client secret with `read -r` instead of command substitution (no value in `set -x` traces); the command reference names the two commands without a prompt (`CreateUser`, `UpdateIdentityProvider`).

## [0.24.0] — 2026-11-05

### Changed

- **`octo-commit`** — CodeRabbit review and merge (AB#8295): every CodeRabbit finding is checked for validity against the code and the work item instead of being applied blindly; every thread is answered (`Fixed in <commit>` or `Declined: <reason>`), then `@coderabbitai resolve`; the PR is merged after CodeRabbit's approval (`reviewDecision` `APPROVED`), green checks and `mergeStateStatus` `CLEAN` — never `--admin` or `--auto`, never another person's PR; larger changes or doubt get a CoreDev review instead. Three new rows in *Common Mistakes*, `gh pr checks` added to the allowed tools, description and README row updated. With `octo-claude-pm` 0.32.0 its merge guard checks the conditions on GitHub.

## [0.23.0] — 2026-11-04

### Changed

- **`octo-commit`** — commit and PR title convention of the org (AB#8271, Wiki "Development Guidelines for meshmaker Teams", CodeRabbit title check in `meshmakers/coderabbit`): `AB#<id> <Type>: <description>` with `<Type>` one of `Fix`, `New`, `Chore`, `Refactor`, `Test`, `Docs` (before: `New`/`Fix` only), a table which type fits which change, and a new last part of step 9: see the PR through the CodeRabbit review — read the pre-merge checks in CodeRabbit's PR comment (a failed title check leaves the `CodeRabbit` status green), fix the title with `gh pr edit`, answer every finding. `gh pr view` and `gh pr edit` added to the allowed tools. README row updated.
- **`octo`, `octo-mcp`** — local-day bins (AB#7362, Feature AB#7357; engine AB#7360, GraphQL AB#7361): the `octo` skill names the downsampling arguments `timeZone`, `binInterval`/`binIntervalDays` and `binOrigin`, the day-rollup fields `referenceTimeZone` + `dayStartOffsetMs` and the gas-day example (`Europe/Vienna`, `06:00`, 1 day; 23/24/25-hour days, empty day Count 0). `octo-mcp`: how `query_stream_data_downsampling` validates and passes the new parameters, the day-start fields of `get_rollup_query_metadata`, and (AB#5346) the removed `{Function}({path})` fallback, lower-case built-in keys and the stream-data `count` path rule. Needs the octo-mcp-service PRs of AB#5346 and AB#7362. The `octo` command reference documents the `timeZone=` / `dayStart=` fields of `ListRollupsForArchive` (octo-cli and octo-sdk PRs of AB#7362).
- **`octo`, `octo-app-builder`** — blanked-attribute reasons of `PreviewBlueprintUpdate` / `UpdateBlueprint` (AB#8263, octo-construction-kit-engine): `SeedEmpty` only for an empty seed value; a non-empty JSON seed that empties one field is the new reason `SeedEmptiesJsonField` with the field path in the incoming summary (`string (184 chars), empties $.valueAttribute`). The command reference has the reason table, the `-cb`/`--confirm-blanking` and `-ab`/`--allow-blanking` flags of `UpdateBlueprint` and how to force the seed value after an adoption install (`UpdateBlueprint -tv <same id> --confirm-blanking <rtId>:<attribute>`). Needs the asset-repository release that carries the engine change.
- **`octo`, `octo-app-builder`** — `PreviewBlueprintUpdate` for a blueprint that is not installed (AB#8256, octo-construction-kit-engine): diffs the seed against the tenant by rtId (adoption) with the normal output instead of a placeholder; `InstallBlueprint` applies exactly the listed adds and updates. Documented in the `octo` command reference and the blueprint lifecycle of `octo-app-builder`. Needs the asset-repository release that carries the engine change.
- **`octo`** — `Integral` from rollups (AB#7920, engine + engine-mongodb): the stream-data paragraph no longer says "raw archives only": a rollup that stores a `TimeWeightedAvg` of the column answers `Integral` from its stored integral (aligned windows equal the raw result, unaligned windows read every overlapping bucket in full, an `Avg`-only rollup refuses it naming the missing aggregation), downsampling only on such rollups. Needs the services release that carries the engine change.
- **`pipeline-expert`** — `ApplyDataPointMappings@1` emits one update per target entity (AB#7962, octo-mesh-adapter): mappings of one source value onto the same entity are merged into one `EntityUpdateInfo` with one `RtChangedDateTime` per invocation, so `SaveStreamDataInArchive@1` writes one row per entity and state change instead of one per mapping. Documented in `node-reference-mesh.md`. Needs the Mesh Adapter release of the bug.
- **`octo`, `octo-mcp`** — `Integral` aggregation (AB#7919, System 2.8.0 from AB#7918): the `octo` skill lists the stream-data aggregation functions with `Integral` (step integral over `[from, to)` in value unit x hours, LOCF, carry-in, rtIds summed, empty window = null, `from`/`to` required, raw archives only, sign split by computed column, never by field filter) and corrects the persisted query type ids (`System/SimpleSdQuery`, `AggregationSdQuery`, `GroupingAggregationSdQuery`, `DownsamplingSdQuery`). `octo-mcp`: `AggregationFunctionDto.integral`, where it is accepted, and the real engine result key `{column}_{token}` the stream-data tools read now (octo-mcp-service PR of AB#7919).
- **`pipeline-expert`** — attribute access in pipelines (AB#7768, octo-mesh-adapter): extract nodes (`GetRtEntitiesByType@1` incl. `ckInterfaceId`, `GetRtEntitiesById@1`, `GetRtEntitiesByWellKnownName@1`, `GetAssociationTargets@1`, `CheckDuplicate@1`, `BackfillFromRtEntity@1`, `FromWatchRtEntity@1`) emit entities without `Hidden` values; a filter, sort or query column on a `Hidden` path fails with `RT_ATTRIBUTE_HIDDEN`; load nodes refuse `Hidden` and `ReadOnly` always and `MethodOnly` outside the method-handler run of the entity's type (`RT_ATTRIBUTE_WRITE_RESTRICTED`, dry runs included, `Replace` that would clear such an attribute included). Documented in `references/method-handler-pipelines.md` and one sentence in `SKILL.md`. Needs the Mesh Adapter release of the story.
- **`pipeline-expert`** — `GetRtEntitiesByType@1` selects by CK interface (AB#6933, octo-mesh-adapter; engine method AB#7019): `ckInterfaceId` instead of `ckTypeId`, all implementing types in one global order, same result shape; `take` required, `skip + take` at most 1000, filters and sort orders only on interface members, no text search/aggregation/navigation; "filter instead of paging deep, index the sort field"; failures carry stable data (`NODE_CONFIGURATION_INVALID` reasons, `INTERFACE_QUERY` with message number 7019 and the engine's reason and parameters). Documented in `node-reference-mesh.md` and the `SKILL.md` node table. Needs the Mesh Adapter and engine releases of the two stories.
- **`octo`** — runbook "repair tenants after a System bump" (AB#7567, AB#7562) in `references/repair-after-system-bump.md`: after a release bumped `System` and exact-pinned catalog models went `ResolveFailed`, `FixAll -w -y` imports every range-retaining catalog successor (no `CheckUpgrade` + `ImportFromCatalog` per model); all tenants of an installation in one `Invoke-OctoTenantSweep`, with before/after `LibraryStatus`. Needs services and octo-cli 3.5.43 or newer.
- **`pipeline-expert`** — pipelines that insert entities of a type whose CK method replaces the generic create (AB#7464): `ApplyChanges@1/@2` and `ImportFromExcel@1` refuse every insert outside the method's own pipeline run, chained pipelines included, with `GENERIC_CREATE_REPLACED_BY_METHOD` (`GENERIC_CREATE_CHECK_UNAVAILABLE` when the CK cache cannot be loaded). Other write nodes are not covered by this check. The method-handler section moved into `references/method-handler-pipelines.md` (content unchanged) so the `SKILL.md` body fits the 500-line budget.
- **`pipeline-expert`** — `CreateUpdateInfo@1` `recordArrayItemUpdates` (AB#7442, octo-mesh-adapter; engine AB#7445): atomic update of single RecordArray records in one database statement without reading the entity (`attributeName`, `matchAttributeName` + `matchValue`/`matchValuePath`, `attributeUpdates`, optional `updatesPath`), documented in `node-reference-mesh.md` and the node overview. The read-modify-write of a RecordArray (`GetRtEntitiesByType@1` → `UpdateRecordArrayItem@1/@2` → whole array) is marked **unsafe under parallel executions** (measured: one of two parallel changes lost in every pair). Needs the engine and adapter releases of the two stories.
- **`pipeline-expert`** — new Mesh node `UpdateRecordArrayItem@2` (AB#7439, octo-mesh-adapter): updates several records of one RecordArray in one pass (`updatesPath`, `itemMatchValuePath`/`valuePath` relative to each change), documented in `node-reference-mesh.md` with the recipe "N updates of one entity in one batch" (`GroupBy@1` → `UpdateRecordArrayItem@2` → one `ApplyChanges@2`, why not one ApplyChanges per change) and the concurrency limit between executions.
- **`pipeline-expert`** — new SDK node `GroupBy@1` (AB#7438, octo-communication-sdk): groups the items of an array by a key (`keyPath`) into `[{ key, items }]`, first-occurrence order, one warning for skipped items; documented in `node-reference-sdk.md` and the transform overview, with the pointer from `Group@1` (editor container) to it.
- **`octo-operator`** — Helm values layering now includes the typed CPU/memory settings of a workload (AB#7428, octo-communication-controller-services): the controller projects `CpuRequest`/`CpuLimit`/`MemoryRequest`/`MemoryLimit` into `ValueOverride[]` unless `ValueOverride[]` or `ValuesYaml` already sets the path; precedence chart default < typed < `ValuesYaml` < `ValueOverride[]` < pool `replicaCount` pin; an overridden typed value is reported in `LastDeploymentWarning` and in the deploy response. The operator is unchanged.
- **`octo`** — `UpdateWorkloadResources` (AB#7429, octo-cli PR #55): shows, sets and clears the typed CPU/memory requests and limits of an adapter or application without deploying; `GetAdapter` shows them as `resources`. Documents the flags (a flag without a value clears), the local validation, the precedence (chart default < typed settings < explicit `valuesYaml`/`values[]`) and that adapter pools use `PoolMember*`. The MCP tools `update_workload_resources` / `get_workload_resources` are in octo-mcp-service PR #33.
- **`octo`** — `ImportFromCatalog -m A,B,C` imports a comma-separated list as one guarded set in dependency order, without `-f` (AB#7376, octo-cli): documents the joint upgrade of models that pin each other exactly (octo-mesh-energy group), the ready-to-run joint command a blocked single import prints, and that `FixAll` now tries blocked rows together (never forces).

## [0.22.0] — 2026-10-22

### Changed

- **`octo`, `octo-deploy`, `octo-agent`, `octo-mcp`** — scratch tenants for agents (AB#7192): `references/temp-tenants.md` now uses `Create --scratch` (the creating client-credentials client becomes administrator of the tenant it creates; refused for user tokens) and `Delete --disable-features -y` (switches off the enabled capabilities with the child token, then deletes; activated archives are reported, never deleted; child secret `OCTO_CLI_CHILD_CLIENT_SECRET`). The client needs `-apic` and the role `TenantManagement`. The line that tenant create/delete is authorized by scope only is gone (role-based). Updated the `octo` command reference and tool table, the test-2 tenant creation step, the database-operations example and the MCP development notes (`scratch`, `disableFeatures`, `enable_ai`/`disable_ai`, `AiClientContext`).
- **`octo`, `octo-deploy`, `octo-agent`** — per-tenant authentication and the multi-tenant helper (AB#6840, after AB#6836/AB#6839): a command addresses the tenant of its context and only carries a token issued for it; authority in a child tenant comes only from `ProvisionCurrentUser -ttid <child>` (per child tenant, new tenants included); denial = exit `-4` with a message naming tenant and cause. New `octo/references/tenant-tokens.md` (rules, denial causes, worked example with `Register-OctoCliContext -TenantId a,b,c` and `Invoke-OctoTenantSweep`), a decision-tree branch and a "Denied in a Child Tenant" entry for `octo-agent`, the provisioning step in `octo-deploy`. The skills no longer tell the agent to read `contexts.json` (context discovery uses `ListContexts -j`; `Read(contexts.json)` removed from the `octo` allowed tools); the remaining REST-only pool deploy and the GraphQL delete snippet state that the token must be issued for the target tenant. The Python explorers keep working for the context's own tenant. The octo-cli command `GraphQl` (AB#7027) is documented in the `octo` command reference (flags, exit codes) with a sweep example (`Invoke-OctoTenantSweep ... -IncludeOutput`); it replaces the curl stop-gap for deleting runtime entities; impersonation loops use `SwitchServiceAccountsToImpersonation`; pool deploy stays the documented REST-only gap.
- **`octo-mcp`** — file-transfer flow matches octo-mcp-service AB#6989 (PR #28): `store.GetUpload` now takes the caller label (`McpSessionContext.GetCallerLabel(server)`), so an upload is consumable only by the session that reserved it; downloads are single-use.
- **`pipeline-expert`, `octo`** — `DataMapping@1` maps whole arrays (AB#6589, octo-mesh-adapter): a `path` with a wildcard (`$.sd.Rows[*].Values[5]`), recursive descent or filter maps every addressed element in place, without `ForEach@1` or a script; `targetPath` is the same path or left out (anything else is a node error), `null` elements are skipped, unmapped elements stay, no match is a warning. Documented in `node-reference-mesh.md` (properties, behaviour table, example), the transform node overview and the `octo` schema-discovery section, with the measured speed (~1.3x `ForEach@1` on 123,000 rows, about a third less extra memory). Compatibility: a path without wildcard behaves exactly as before; the audit of the repositories, the local blueprint catalog and the local tenants found no deployed `DataMapping@1` with a multi-match path, so no existing pipeline changes behaviour.
- **`pipeline-expert`** — new node reference entry `DateTime@1` (AB#6854, octo-communication-sdk): all operations, the new `ConvertFromTimeZone` (local wall-clock time of an IANA zone → UTC; spring gap fails the node, autumn repeat resolves to the earlier instant) and `StartOfMonth` (keeps the source Kind), the Kind rules and a Vienna month-start example for `GetStreamData@1` bounds.
- **`pipeline-expert`** — new section "Pipeline as a CK method handler" (AB#6879): binding by `rtWellKnownName` = qualified method id, the input document (`$.parameters`, `$.target`, `$.method`), the `{"value": ...}` / `{"error": {...}}` output contract of `SetPipelineExecutionResult@1`, the error mapping, the refusal of methods with sensitive parameters and the consistency notes.
- **`pipeline-expert`** — new node reference entries `ConvertToCsv@1` (AB#6733, octo-mesh-adapter PR #74: array of records to a real CSV document with RFC 4180 quoting, per-column `dataType`/`format`/`decimals`/`factor`/`timeZone`/`culture`, optional BOM and base64 output with content length) and `RenderDelimitedText@1` (AB#4846, fixed layouts without quoting), plus the specialized-node overview in `SKILL.md` (AB#6799). Documents the `dataType`-not-`type` trap: `type` inside a pipeline definition is taken by the serializer and never reaches a column.

## [0.21.4] — 2026-10-11

### Changed

- **`octo-operator`** — idempotent dispatch after a controller restart (AB#6471, operator PR #32 `a0fff62`, controller docs PR #52 `e609f3e`): single-flight `DeployAsync` per release, `octo-deploy:<fingerprint>` stamp in the helm revision description, reconciliations that helm already satisfies skip helm and report success, user deploys never skip. Updated the reconciliation flow, the pre-flight/watcher/cancellation section, the reverse-sync note, the test seams and the unit/E2E coverage map (`DuplicateDispatchTests`, `ControllerRestartRedispatchKindE2ETests`); added a troubleshooting note (double helm revisions or `Error` after a controller restart = operator older than the fix).
- **`pipeline-expert`** — file nodes (AB#6177): `CreateFileSystemUpdate@1`, `CreateZipArchive@1` (persist mode), `GetFileSystemContent@1` and `ToDiscord@1` attachments use `System.Files/FileSystemItem` / `System.Files/FolderRoot`, with `System.Reporting` as transition fallback on tenants that are not migrated yet; pipeline configuration (`rootFolderWellKnownName`) is unchanged. Added reference entries for `GetFileSystemContent@1` and the `CreateZipArchive@1` persist mode.

## [0.21.3] — 2026-10-11

### Changed

- **Environment URLs are placeholders** (AB#6475). `octo`, `octo-deploy`, `octo-devtools` and `octo-app-builder` (skills, references, evals, README, CLAUDE.md) no longer contain internal hostnames: the shared environments appear as `<test-2-domain>`, `<staging-domain>`, `<prod-1-domain>`, `<prod-2-domain>`, `<legacy-domain>`, the image registry as `<registry>` and the Rancher UI as `<rancher-url>`; hosting-provider remarks are gone. Each affected file points to the internal reference of the private `octo-claude-pm` plugin (`agent-operating-rules/references/environments.md`) when it is installed. Public schema URLs (`schemas.meshmakers.cloud`) are unchanged. No behaviour change.

## [0.21.2] — 2026-10-11

### Changed

- **`octo-logs`, `octo-logs-setup`** — made generic (AB#6472). The public plugin no longer names the organization's Dash0 datasets, MCP endpoint, cluster hosting providers, retention window, infrastructure repository paths or example tenant/app service names. The skills describe "logs, traces and metrics via the Dash0 MCP server" and point to the internal reference of the private `octo-claude-pm` plugin (`agent-operating-rules/references/dash0.md`) when it is installed. `/octo-logs-setup` takes the MCP endpoint as a placeholder (`<mcp-endpoint>`); the dataset comes from `listDatasets`. Behaviour of the tools, filters and D0QL recipes is unchanged.

## [0.21.1] — 2026-10-09

### Changed

- **`octo-commit`** — product theme teams work without sprints: new work items stay on the project root iteration `OctoMesh`; iterations only for customer-project, sales and bizops teams. `AI Platform Team` added to the theme teams.

## [0.21.0] — 2026-10-08

### Changed

- **`octo-logs`** — rebuilt on **Dash0** (AB#6116). Loki + Promtail no longer run on any cluster and were removed from the IaC, so the skill now reads logs through the read-only Dash0 MCP tools (`getLogRecords`, `sql`, `getFullLogRecord`, `getAttributeValues`, `getLogCorrelations`, `getSpans`/`getTraceDetails`) against the datasets `test-2`, `staging-1`, `prod-1`, `prod-2`. Filters on `k8s.namespace.name` / `k8s.container.name` / `k8s.pod.name` / `service.name` / `otel.log.severity.range` / `otel.log.body`; D0QL recipes (verified against test-2) in `references/d0ql-cheatsheet.md`, including a LogQL → Dash0 translation table. Skill name unchanged.
- **`octo-logs-setup`** — now sets up / checks the Dash0 MCP connection (`claude mcp add` + `/mcp` OAuth login + `listDatasets`). The Loki credential flow (`LOKI_USERNAME` / `LOKI_PASSWORD` in the private profile) is retired; the skill explains how to remove the obsolete variables. Skill name unchanged.

### Removed

- `octo-logs/scripts/run_logcli.sh`, `octo-logs/scripts/_logcli.ps1`, `octo-logs/references/logql-cheatsheet.md`, `octo-logs-setup/scripts/setup_loki_creds.sh` — `logcli` and the monitoring-Grafana Loki datasource no longer exist.

## [0.20.5] — 2026-10-08

### Changed

- **`octo-commit`** — follows the new Azure DevOps backlog hierarchy Epic → Feature → User Story / Bug → Task (effective 2026-10-09). New work items are created as **User Story** (with mandatory acceptance criteria), Bug or Task — never as the legacy **Issue** type — and User Stories / Bugs are linked to a parent **Feature** (`az boards work-item relation add --relation-type parent`); maintenance work goes to the team's `Sustain Q<n>/<year> – <Team>` Feature. Commits reference requirement-level items, not Epics or Features. Bug descriptions go into `Microsoft.VSTS.TCM.ReproSteps`. Team list extended with the theme teams `Core Platform Team`, `Studio UX Team`, `Platform Ops Team`, `Apps Team`.

## [0.20.4] — 2026-09-10

### Fixed

- **All 13 `SKILL.md` files** — the `description` frontmatter is now a quoted YAML scalar. Six skills (`octo`, `octo-agent`, `octo-logs`, `octo-logs-setup`, `octo-mcp`, `pipeline-expert`) had an unquoted plain scalar containing `Trigger on: ` (and, for `octo-logs`, `(test-2/staging-1/prod-1/prod-2): `). In YAML a plain scalar ends at a `": "`, so the frontmatter failed to parse with `ScannerError: mapping values are not allowed here`. Claude Code then registered those skills by directory name with **no description**, which drops them from the model's skill listing — they were reachable only by typing `/<name>` explicitly, and auto-routing from `/octo` to its siblings was broken. Reported against 0.20.3 on Claude Code 2.1.267.

### Added

- **`scripts/validate_skill_frontmatter.py`** — parses every skill's frontmatter and checks name/description presence, the 1200-char description budget and the 500-line body budget. `claude plugin validate . --strict` passes on broken frontmatter, so this check is what actually guards the regression. Run it before every release:

  ```bash
  bash skills/octo/scripts/run_python.sh scripts/validate_skill_frontmatter.py
  ```

## [0.20.3] — 2026-09-08

### Fixed

- **`octo/scripts/rt_explorer.py`** — `query` ignored `--first` and fetched every row of the transient query (the limit was applied to the query-result items, not to the `rows` connection). `--first` now bounds the rows, so `query` on a large type no longer dumps tens of thousands of rows.

## [0.20.0] — 2026-08-06

### TL;DR

octo-cli now supports **`--context <name>`**, a per-invocation context selector that runs a single command against a named context **without changing the active context** (resolution order `--context` > env var `OCTO_CLI_CONTEXT` > persisted active context; token is read from — and, for logins, written back to — the selected context, and saves merge per-context). This makes **parallel Claude sessions safe**: previously `UseContext` mutated the one global active context in `~/.octo-cli/contexts.json`, so a second session (or a `_train`/CI job) silently flipped the context — including onto prod. All octo skills now document `--context`/`OCTO_CLI_CONTEXT` as the default for agent, scripted, or parallel use and demote `UseContext` to "human setting a persistent default". Verified against the local octo-cli build (`Runner.cs`/`ContextSelection.cs`/`IContextManager.SaveEffectiveContext`).

### Changed

- **`octo` SKILL.md** — new **Targeting a context** paragraph under Invocation Syntax (full `--context` semantics, precedence, parallel-safety, `OCTO_CLI_CONTEXT` session pin, full-term-only matching); Context Discovery notes the effective-vs-active distinction; Command Reference `UseContext` row demoted; **Environment Switching** and **Temporary Tenants** rewritten to authenticate/work via `--context` instead of `UseContext` round-trips.
- **`octo/references/command-reference.md`** — added a `--context` global-flag note atop Context Management; `AddContext` and `UseContext` sections updated (create ≠ activate; `UseContext` mutates global state, prefer `--context`).
- **`octo/references/environments.md`** — all four "Switch to <env>" blocks and the "work against a previously authenticated context" block now use `LogIn -i --context <ctx>` / `AuthStatus --context <ctx>`; `UseContext` only for a persistent default.
- **`octo/references/temp-tenants.md`** — the full non-interactive lifecycle (one-time client setup, create → mirror-login → work → teardown) now runs entirely via `--context`, never touching the active context; pitfalls updated (per-context tokens, explorer scripts follow `OCTO_CLI_CONTEXT`).
- **`octo/scripts/_octo_common.py`** — `load_context()` now honors `OCTO_CLI_CONTEXT` (falls back to `ActiveContext`), so the Python explorers and octo-cli resolve the same context without mutating global state; error hints no longer prescribe `UseContext`. `_verify_data_layer.py` leftover-context warning updated.
- **`octo-deploy`** SKILL.md + `references/test-2-environment.md` — test-2 targeting via `--context test-2_<tenantId>` (create tenant / `EnableCommunication` / `AuthStatus`) instead of relying on the switched active context.
- **`octo-devtools`** `references/workflows.md` + `references/command-reference.md` — note that the `Invoke-OctoCliLogin*` / `Register-OctoCliContext` cmdlets still `UseContext`; recommend `-NoSwitch` + `--context`/`OCTO_CLI_CONTEXT` for parallel-safe agent use.
- **`CLAUDE.md`** — `_octo_common.py` description updated to reflect `OCTO_CLI_CONTEXT` resolution.

## [0.19.2] — 2026-07-08

### Changed

- `octo-commit` SKILL.md: default branch pattern is now **`feat/<username>/<short_meaningful_description>`** (e.g. `feat/reimar/implement-skill`). Every OctoMesh repo's CI triggers on `dev/*` (most also `test/*`) and `main` — `feat/*` matches no trigger, so pushes build nothing and CI runs only when a PR is opened. The long-running `dev/AB#<wi-id>_...` pattern (build on every push) remains the explicit opt-in alternative; the previous default `<username>/AB#<wi-id>_...` row is replaced by `feat/`. Work-item-resolution hint, `checkout -b` example, and review-checkpoint summary updated accordingly.
- `octo` SKILL.md: routing row for octo-commit now references `feat/` feature branches (was `dev/`).

## [0.19.1] — 2026-06-28

### Changed

- `octo-commit` SKILL.md: aligned the **Branch Naming** convention with the [meshmaker Development Guidelines](https://dev.azure.com/meshmakers/OctoMesh/_wiki/wikis/OctoMesh.wiki/141/Development-Guidelines-for-meshmaker-Teams). Default is now the user-specific pattern `<username>/AB#<wi-id>_<short_meaningful_description>` (no build on push, only on PR); the long-running feature pattern `dev/AB#<wi-id>_<short_meaningful_description>` (build on every push) is documented as the explicit alternative. Replaces the previous `dev/<username>/<feature-name>` scheme across the branch table, work-item resolution hint, `checkout -b` example, and review-checkpoint summary.

## [0.19.0] — 2026-06-22

### TL;DR

Two new skills for **deployed-cluster log access** via Loki + `logcli`: **`octo-logs`** (query and trace logs) and **`octo-logs-setup`** (safe one-time credential setup). The query skill never handles credentials — it loads the octo-tools PowerShell profile, which dot-sources the private profile that holds `LOKI_USERNAME`/`LOKI_PASSWORD`, then resolves the cluster's Loki datasource-proxy URL and runs `logcli`. Verified end-to-end against the live `test-2` cluster (label list, error queries, an `instant-query` error breakdown, and a real cross-deployment `ObjectDisposedException` trace).

### Added

**New skill `octo-logs`** (SKILL.md + 2 references + 2 scripts)
- `scripts/run_logcli.sh` (bash) — finds the monorepo root, preflights `pwsh`/`logcli`, then hands off to `_logcli.ps1` via `pwsh -File` so the LogQL query (braces/pipes/quotes) survives without re-parsing.
- `scripts/_logcli.ps1` — dot-sources the octo-tools profile (suppressing its chatter), maps cluster → `monitoring.*` base URL, reads `LOKI_USERNAME`/`LOKI_PASSWORD` (with per-cluster `LOKI_*_<CLUSTER>` override + generic fallback), **discovers the Loki datasource UID at runtime** via `GET /api/datasources` (no hard-coded UID), sets `LOKI_ADDR` to the Grafana datasource-proxy path, and runs `logcli`.
- `references/clusters.md` — the two-Grafana warning (`monitoring.*` has Loki, `grafana.*` doesn't), cluster→URL table, why logcli must target the datasource-proxy path (the wiki's `LOKI_ADDR=monitoring.<domain>` returns Grafana HTML), `mesh-admin` login source (Keeper/Vault), ~7-day retention + ~30-day query-span limit, and the corrected `brew install logcli` formula (not `grafana/tap/logcli`).
- `references/logql-cheatsheet.md` — label model (`level`/`source` only on parsed `octo` app logs; non-octo namespaces need inline filters), service/level/body-search recipes, `instant-query` rate/count forms, and the **cross-deployment tracing** pattern (drop `pod`, keep `container`, group by `pod` = by ReplicaSet rollout; prefer `|=` over `source=`).

**New skill `octo-logs-setup`** (SKILL.md + 1 script)
- `scripts/setup_loki_creds.sh` — `status` (reports private-profile path/perms and which `LOKI_*` variable **names** exist, never values) and `write` (reads the password from **STDIN only**, never a CLI arg; idempotently writes `LOKI_USERNAME`/`LOKI_PASSWORD` — or per-cluster `-c <cluster>` variants — into the private profile with perms forced to 600; PowerShell single-quote escaping verified against `pwsh`).
- SKILL.md encodes the safety contract: secret sourced from Keeper/Vault and piped straight in (Vault-pipe for the assistant, or user-pasted via the `!` session prefix); the assistant must never embed the password in a command or print it.

**Routing/docs** — `octo` hub routing rows for both skills (distinct from `octo-agent`'s local-dev debugging), README + CLAUDE.md entries.

## [0.18.1] — 2026-06-18

### Changed

- `octo-ck-miro` SKILL.md: bumped the Miro 403 cool-off from ~20 s to **~45–60 s** based on empirical observation during the v0.18.0 live test (12-CK board creation). 20 s was too short and triggered repeat 403s on the next call; ~60 s recovered cleanly. Both the workflow Step 4 note and the Common Pitfalls entry updated.

## [0.18.0] — 2026-06-17

### TL;DR

One new skill: **`octo-ck-miro`** — visualizes all Construction Kits in `octo-construction-kit` as detailed UML class diagrams on a Miro board (types with attributes/datatypes, records, enums, inheritance, associations with multiplicity, cross-CK references). Picks a git branch (default `main`) and reads YAMLs non-destructively via `git show`; targets a new Miro board or an existing one by URL.

### Added

**New skill `octo-ck-miro`** (SKILL.md + `scripts/ck_to_miro.py` + `run_python.sh` wrapper + `requirements.txt`)
- Parser reads every CK under `src/ConstructionKits/<dir>/ConstructionKit/` from a given git branch via `git ls-tree` + `git show` — never checks out, never touches the working tree.
- Handles both YAML schema variants: standard (top-level `types:/records:/enums:/attributes:/associationRoles:` arrays, `${CkName}/Element` refs) AND compact (filename-as-id, `derivedFrom: CK/Name`, `attributeName`, enum `value`) used by `Octo.Energy.Demo`.
- Emits Miro UML class DSL per CK: types blue, records green, enums yellow, external CK refs gray. Inheritance via `<|--`, associations with resolved multiplicity (`N`→`*`, `One`→`1`, `ZeroOrOne`→`0..1`, etc.). Attribute datatypes resolved through the attribute registry, including `«Record»` and `<Enum>` references with cross-CK qualification (e.g. `Basic.Address`).
- Single-column layout (x=0, y step 3500) — avoids Miro auto-layout overlap that hits multi-column grids when wider CKs (Basic auto-arranges to ~8500 px) collide with neighbors.
- Generates two top-of-board doc cards: legend (color/notation key) and dependency tree (sourced from `ckModel.yaml` `dependencies`) + content stats table.
- `--ck <name>` flag for single-CK mode.
- Operational notes in SKILL.md: sequential diagram calls (Miro 403s on bursts; ~20 s cool-off on failure), no in-place update on existing boards (no MCP delete for diagrams — "update existing" means add alongside), board URL input format validation.

### Changed

- README: switched "Ten skills" → "Eleven skills"; added `/octo-ck-miro` row with one-line summary.
- CLAUDE.md plugin-structure block: added `octo-ck-miro/` entry.
- `plugin.json` + `marketplace.json`: bumped to `0.18.0`, description extended with "Construction Kit UML visualization on Miro boards", added `miro` and `uml` keywords.

## [0.17.0] — 2026-06-10

### TL;DR

One new skill: **`octo-deploy`** — guides the promotion of an OctoMesh-powered app (built with `octo-app-builder`) from local dev to the shared **test-2** environment. Staging and production are deliberately out of scope for now. Research-verified against octo-tools cmdlet sources, the engine's catalog implementations, the `blueprint-libraries-build` commit history, live registry probes, and the test-2 cluster values in `meshmakers_staging`.

### Added

**New skill `octo-deploy`** (SKILL.md + 2 references)
- The promotion model: what must move (CK model → shared catalog or direct ImportCk, blueprint → `meshmakers/blueprint-libraries-build` via `octo-bpm`, image → `docker.mm.cloud`) vs. what is environment-portable by design (`${octo.tenantId}`, `{{domain.default}}`, the `670…001/002/003` seed associations, ChartName/ChartVersion, pipeline YAML, operator-injected registry prefix).
- Two lanes: the CI lane (Azure DevOps pipeline publishing on `main`, worked example `one-time-ticket/devops-build/azure-pipelines.yml` with the seed-tag guard) and the manual lane with verified `octo-ckc -c Publish -c PrivateGitHubCatalog` / `octo-bpm -c publish -c PrivateGitHubBlueprintCatalog` commands incl. one-time token config.
- `references/test-2-environment.md` — service URL table, `Register-OctoCliContext -Installation test-2` (incl. the `test-2_…` vs legacy `test2_…` context-name divergence), headless auth, tenant creation (`-np` for machine tokens), the `octo.environment` gate ambiguity (helm default says `dev`, blueprint comments say `test` — unresolved at runtime; mandate `[dev, test]` + the `WasSkipped` probe), Tailscale requirement for `docker.mm.cloud` off-site.
- `references/publishing.md` — catalog mechanics (what Publish writes where, per-file Octokit commits, three-level catalog.json indexes), the source-verified `ckModelDependencies` short-circuit that makes direct `ImportCk` a valid catalog-free path for CK models (but not blueprints), server-side `RefreshCatalogs` (the local cache-file-delete trick explicitly does NOT apply to test-2), image-tag rules (static tags for app workloads; same-tag re-push doesn't restart pods).
- kubectl-free verification story for test-2: `GetAdapters`/`GetDataFlowStatus`/`GetWorkloadsByChart` plus the workload entities' `deploymentState`/`statusMessage`/`lastDeploymentError` attributes as the `kubectl describe` substitute.
- Routing rows in the `octo` hub and `octo-app-builder`, README + CLAUDE.md entries.

### Changed — live-validated against a real first-time deployment (one-time-ticket → `tickets` tenant, https://tickets.test-2.mm.cloud)

- **Pool-first bring-up** (corrects the research draft): `EnableCommunication` only seeds entities; the pool starts `Undeployed` and `DeployWorkload` triggers fired in that state are silently lost (workload `Pending` forever, no error). Pool deploy is REST-only (`POST …/v1/Pool/deploy?poolRtId=…` — no octo-cli command); then (re-)run `DeployWorkload -id 670…002`. Also documented in the `octo` hub + command reference (Pools section).
- **`RefreshCatalogs` covers CK MODEL catalogs only** — blueprint catalogs have no refresh API anywhere (engine `RefreshAllCatalogCachesAsync` never exposed). New blueprint ids/versions stay invisible until the asset-repo pod restarts (`kubectl --context test-2 -n octo rollout restart deploy/octo-mesh-asset-rep-services`); only the index is cached — content of already-listed versions is fetched live from Pages (`InstallBlueprint -f`).
- **kubectl access to test-2 exists** via Rancher kubeconfig download (`rancher.mm.cloud`, no VPN; downloaded yaml must be merged into `~/.kube/config`). The kubectl-free signals remain documented as the fallback.
- CI-agent gotchas in publishing.md: octo-ckc 3.3.x `-lce false` crashes on cold-cache agents (configure via `~/.octo-ckc/settings.json` instead); `octo-bpm -c publish` soft-fails with exit 0 (grep for "published successfully").

## [0.16.0] — 2026-06-10

### TL;DR

One new skill: **`octo-app-builder`** — the end-to-end recipe for building a complete OctoMesh-powered application (custom CK model → CK catalog → blueprint → HTTP-API pipelines on the Mesh Adapter → operator-deployed Application web app). Every command, format, and pitfall in it was extracted from a real build-and-ship run on 2026-06-09 (the one-time-ticket demo: blueprint-installed, operator-deployed, browser-verified on a live tenant) — which also served as a field validation of the 0.15.0 skill set.

### Added

**New skill `octo-app-builder`** (SKILL.md + 3 references)
- The verified build sequence: CK model authoring (3-file layout, `${System}`/`${this}` reference syntax) → `octo-ckc Compile`/`Publish` into the local CK catalog → scratch-dataflow pipeline iteration → blueprint authoring (`ckModelDependencies`, seed entities with stable hand-assigned rtIds, `requires:` environment gate) → local blueprint catalog install → `InstallBlueprint` + `DeployDataFlow` + `DeployWorkload` → verification matrix.
- `references/blueprint-authoring.md` — CK source syntax, manifest fields, seed-data format, `${octo.*}` (apply-time) vs `{{domain.*}}` (deploy-time) variables, catalog layouts, lifecycle commands, ownership stamps.
- `references/http-api-pipelines.md` — verbatim, live-verified pipeline YAML for the three core API patterns (create entity, list without sensitive fields, conditional read-and-update), HTTP route/request/response semantics (response = full final DataContext; `Project@1 clear: true` as the only shaping tool), scratch-iteration loop, debugging via adapter logs.
- `references/app-workload.md` — web UI as `System.Communication/Application` workload: the property-walker chart contract (PORT/UPSTREAM_URL/probe-on-`/`), proxy-server app shape, image double-tagging for the injected `docker.mm.cloud` registry prefix + `kind load`, the Application seed entity, deploy/triage loop.
- Routing row in the `octo` hub, README + CLAUDE.md structure entries.

**Temporary tenants without user interaction** (`octo` skill)
- `references/temp-tenants.md` — verified end-to-end workflow (2026-06-10, local env) for agents to create, use, and delete a throwaway tenant with **zero interactive logins**: `LogInClientCredentials` (machine token via `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET`) + an `-apic`-flagged client in `octosystem` that mirrors (same id/secret/scopes) into every new tenant synchronously at create time. Covers the one-time client setup, why `-np` is mandatory on `Create` (machine tokens carry no user to provision), the authorization facts (tenant create/delete require only the `octo_api.full_access` scope claim — no user subject, no roles), and mirror backfill for pre-existing tenants.
- New SKILL.md section "Temporary Tenants (Non-Interactive)", safety-rule exception allowing `-y` deletion of session-created `tmp-` tenants, and trigger keywords for temporary tenant / headless auth.

**Platform pitfalls newly documented (discovered during the validation build)**
- Local blueprint catalog cache (`~/.octo/blueprint-catalog/cache/local-blueprint-catalog-cache.json`) only rebuilds when the file is *missing* — stale cache hides new blueprints from `ListBlueprints`.
- Pipeline registration rotation: after `ImportRt -r` on a live dataflow, `DeployDataFlow` can remove an unchanged pipeline while re-registering a changed one (symptom: 200/empty body in ~0.1 ms on one route).
- `SetPrimitiveValue@1` fails the whole pipeline on missing source paths — optional CK attributes need `If@1` guards.
- `SetPipelineExecutionResult@1` does not shape `FromHttpRequest@1` responses; without a final `Project@1 clear: true` the response leaks the request body and lookup results.

### Validation notes (0.15.0 rework, field-tested)

The one-time-ticket build ran against the skill set in anger: hub routing, context discovery, `ImportCk`/`ImportRt -w`, `preflight --for-import`, communication workflows, and the pipeline-expert node references all held up — pipeline YAML authored from the references worked on first deploy except for the pitfalls above, which are now documented. No factual errors found in the 0.15.0 content during this run.

## [0.15.0] — 2026-06-09

### TL;DR

Full overhaul of the plugin against the OctoMesh platform state of 2026-06-09 (the skills had last been updated 2026-04-11). An exhaustive audit found **58 factual discrepancies** in the five existing skills — **12 of them breaking** (following the docs would fail outright) — all fixed and re-verified against source code and live `octo-cli` help output. The `octo` skill gains ~70 previously undocumented CLI commands (blueprints, CK catalogs, stream-data archives, groups, client mirrors, workloads, AI services). `pipeline-expert` replaces two removed nodes and documents 20+ new ones. **Three new skills** cover platform pieces that emerged since the plugin was created: `octo-mcp` (MCP server development), `refinery-studio` (Angular frontend), and `octo-operator` (Kubernetes operator + Helm). The whole plugin is modernized to the current Claude Code plugin spec: prose-first descriptions under the listing cap, SKILL.md bodies under 500 lines, `$schema`-validated manifests, corrected versioning guidance, plus a new README and this changelog.

### Added

**New skills**
- **`octo-mcp`** — developing/extending the OctoMesh MCP server (`octo-mcp-service`, ~181 tools): the three tool families, `*ClientContext` helper pattern, `[McpRisk]` risk classification + confirm-gate convention, mandatory test conventions (~525 tests), the adding-a-new-tool checklist, file-transfer architecture, local run/connect instructions.
- **`refinery-studio`** — Angular development on the Data Refinery Studio: verified tech stack (Angular 21.2, Apollo Angular 13, Kendo 23.2, TS 5.9), multi-tenant routing, `OctoGraphQlDataSource` list-view pattern, GraphQL codegen workflow, LCARS two-tier theme token system, `octo-frontend-libraries` linking, common pitfalls. Includes `references/lcars-theme.md` and `references/data-source-and-components.md`.
- **`octo-operator`** — the .NET 10 KubeOps Communication Operator: edge vs central deployment, Helm values layering (context < base < overrides), release-name contract (`{tenantId}-{workloadRtId}`), secret injection tiers, CRD generation, TUnit + Microsoft.Testing.Platform test workflow, kind developer loop (cross-referencing octo-devtools), and the `octo-helm-core` chart repo. Includes `references/operator-internals.md` with the full `OperatorOptions` env-var table.

**octo**
- Documented (each verified via `octo-cli <Command> --help`): `ListContexts`, `LogInClientCredentials` (CI/headless auth via `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET`), `Config`, `GetTenants`; 9 blueprint commands; 8 CK catalog/library commands (`ListCatalogs` … `FixAll`); 9 archive-lifecycle/rollup commands; 5 client-mirror commands; `GetPools`; 4 workload commands; `SetPipelineDebug`/`GetPipelineDebug`; `MovePipelines`; `EnableAi`/`DisableAi` (with `EnableCommunication`-first and `-aisu` prerequisites); 10 group, 5 email-domain-group-rule, 5 external-tenant-user-mapping, and 4 admin-provisioning identity commands; `AddOctoTenantIdentityProvider`.
- New flags: `--aiServicesUri (-aisu)` on `AddContext`/`Config`, `--autoProvision (-apic)` on `AddClientCredentialsClient`, `-asr`/`-dgid` on all identity-provider Add commands.
- Documented `pipeline_validate.py`; System.StreamData CK type hierarchy + blueprint CK types for rt_explorer; the `::` association meta-query syntax (`…::totalCount`/`::exists`); StreamData roles (`StreamDataAdminRole` required for archive lifecycle) and the `DataModelManagement` role.
- Routing rows for the three new sibling skills.

**octo-devtools**
- **Non-interactive service management as the agent default**: `Start-Octo -nonInteractive $true` + standalone `Stop-Octo` (signal-file based); explicit rule never to use `Invoke-BuildAndStartOcto` from an agent session.
- Local Kubernetes (kind) group: `Install-OctoKubernetes`, `Deploy-OctoOperator`, `Get-OctoKubernetesStatus`, `Uninstall-OctoKubernetes`, `Import-OctoImageToKind`, `Add-/Remove-OctoLocalCaTrust` — with the docker-compose mutual-exclusivity note.
- `Register-OctoCliContext` as the recommended context/auth setup (installations `local|test-2|staging-1|prod-1|prod-2`); `Invoke-OctoCliLoginStaging/Production` marked legacy.
- Infrastructure backup cmdlets (`Backup-/Restore-/Get-/Remove-OctoInfrastructureBackup`), `Compare-CkVersions`, `Compare-Pipelines`, `Register-AiBastion`/`Get-AiBastionStatus`, `Get-BranchAvailability`, `Remove-KubeConfig`, `Invoke-SetDebugConfiguration`.
- Start-Octo AI/MCP service flags (`-aiService`, `-aiWorker`, `-mcpService`, `-dataRefineryStudio`, `-frontendLibraries`) with verified defaults and ports.

**octo-agent**
- Blueprint debugging (System/BlueprintInstallation|History|Backup CK types, `BlueprintOperationFailed` events, `LibraryStatus`/`FixAll` as diagnostics).
- CK migration internals: post-chain schema-only bridge, `CreateBackup` default false, error code 66 (multi-version conflict), GitHub catalog MSBuild toggles, `EnsureCkModelInstalledAsync` pre-2026-06-02 silent-skip bug history.
- CrateDB `Runtime.Engine.CrateDb` project split; 3-node cluster note; services table now includes MCP (5017/5016), AI services (5019/5018), AI worker (5023/5022).
- OIDC persistent-grant debugging (per-tenant since AB#1586 — see Fixed), AD-group sync behavior, Hangfire 1s polling default, mongorestore-EOF pattern, `Compare-CkVersions`.
- New `octo-distributedEventHub` reference section: the four messaging patterns and `AddDistributionEventHub` registration.

**octo-commit**
- Explicit review checkpoint: never push or open a PR without explicit user approval in the current session ("I'll look at it later" = STOP).
- Task work-item type (default prefix `New`, based on a 422/237 New/Fix tally of repo history); all six real ADO teams; `az repos pr create --work-items`; initial-push `-u` requirement; full repo-remotes table in new `references/repo-remotes.md` with every remote verified.

**pipeline-expert**
- New nodes (every property verified against C# configuration classes): `SetPipelineExecutionResult@1` (the only way pipeline OutputData is persisted — prominent "why is OutputData empty?" callout), `Group@1`, `ToDiscord@1`, `DeployPipeline@1`, `UpdateRtEntityIfNewer@1`, `BackfillFromRtEntity@1`, `ApplyDataPointMappings@1`, `BuildMappingTargets@1`, `GenerateDataPointMappings@1`, `MapToRecordArray@1`, `UpdateRecordArrayItem@1`, `ValidateDataPointCoverage@1`, `SimulateEnergyMeasurements@1`, and six Zenon nodes (`ReadZenonArchiveInfo/Data`, `ListZenonProjects`, `Get/SetZenonDynamicProperty(-ies)`).
- `ToPipelineDataEvent@1`/`FromPipelineDataEvent@1` await-result mode; `For@1` `countPath`; `AnthropicAiQuery@1` MCP integration (`ApiKeyConfigurationName`, `McpServerUrl`, `MaxToolRounds`, `McpToolNames`, `ConversationHistoryPath`); `Simulation@1` Energy.* simulator keys; pipeline debug toggle + DataFlow-level operations in the deployment workflow.

**Plugin/repo level**
- `README.md` (skill overview + installation), this `CHANGELOG.md`.
- Manifests: `$schema`, `displayName`, `homepage`, `repository`, `keywords`, author email; `claude plugin validate --strict` passes and is documented as the pre-release gate.

### Changed
- All 8 frontmatter descriptions rewritten prose-first ("what + key use case" first, `Trigger on:` tail) and brought under the 1536-char listing cap — `pipeline-expert`'s old keyword-dump description sat at the cap and was being silently truncated.
- `octo` SKILL.md restructured 616 → 494 lines, `pipeline-expert` 661 → 497 (both under the 500-line guideline); exhaustive flag/property detail moved into `references/`.
- `environments.md` rewritten around `Register-OctoCliContext` installations and current `*.octo-mesh.com` cluster domains (legacy `*.meshmakers.cloud` domains retained as documented legacy).
- `ListContexts` replaces `UseContext` (without `-n`) as the documented way to list contexts.
- `octo-commit` `allowed-tools` tightened from broad grants (`Bash(git:*)`, `Bash(az:*)`, `Bash(gh:*)`, `Bash(dotnet:*)`, `Bash(npm:*)`) to the specific subcommands the workflow uses.
- Co-Authored-By convention documented as model-specific (`Claude <model name> <noreply@anthropic.com>`).
- `CLAUDE.md` versioning guidance corrected: semver bump per release (not per commit); when both manifests declare a version, `plugin.json` wins.

### Fixed
Breaking documentation errors (following the old docs failed outright):
- **octo**: removed dead commands `DeployAdapter` (replaced by `DeployWorkload`), `GetServiceHooks`/`CreateServiceHook`/`UpdateServiceHook`/`DeleteServiceHook` (removed from platform 2026-02-28), and `Detach` (never registered in the CLI).
- **octo-devtools**: `Start-Octo` parameter model was entirely wrong — the documented `-noBot`/`-noReporting`/`-noIdentity`… switches do not exist; real interface is Boolean flags (`-botService $false`, …). `AspNetDeveloperCertificate` is a module, not a cmdlet (real functions: `New-/Test-/Remove-AspNetDeveloperCertificate`). `Invoke-OctoCliReconfigureLogLevel` has three mandatory parameters. `Remove-GlobalNuGetPackages` takes no parameters.
- **octo-agent**: MongoDB replica set is `rs`, not `rs0`; CK model compile table corrected (System ← engine, System.Notification ← common-services, System.StreamData ← engine-mongodb, System.UI ← admin-panel); `AddCkModelSystemBotV3`; `Dump`/`Restore` use `*.tar.gz`, not `.json`; build chain now shows `octo-communication-controller-services` as explicit step 9 (feeds `octo-ai-services`); all framework references are net10.0.
- **octo-commit**: WIQL queries use `az boards query --wiql` (`az boards work-item query` does not exist); team is "Solutions Team" (plural); the docs repo is `reikla/ai-docs`, not `reikla/docs`.
- **pipeline-expert**: `SaveInTimeSeries@1` no longer exists → `SaveStreamDataInArchive@1` (+ `SaveTimeRangeStreamDataInArchive@1`); `EnrichWithMongoData@1` no longer exists → `BackfillFromRtEntity@1`; cron expressions are standard 5-field (the documented 6-field with-year format was wrong); `octo-adapter-eda` does not exist locally (EDA nodes moved to an external-adapter note); `AnthropicAiQuery@1` `apiKey` is optional, not required; `sortOrders` uses `attributeName`, not `attributePath`; `GetPipelineConfigByWellKnownName@1`, `FromExecutePipelineCommand@1`, and `Distinct@1` are SDK nodes available on all adapters; `Simulation@1` is an Extract node.
- Research-input correction surfaced during verification: OIDC persistent grants are stored **per-tenant** (CK type `System.Identity/PersistedGrant`, since AB#1586) — the identity-services CLAUDE.md claiming "always system tenant" is stale relative to its own source; this skill documents the verified per-tenant behavior.

### Removed
- All references to the dead commands listed under Fixed, including the legacy `GetPool`/`DeployPoolAdapters`/`UndeployPoolAdapters` trio.
- The committed-docs claim that `UseContext` is the primary context-listing mechanism.

## [0.14.0] and earlier

Pre-changelog era (2026-02-26 → 2026-04-11); see git history.
