# Changelog

All notable changes to the octo-claude-skills plugin. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
