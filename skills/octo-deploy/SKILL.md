---
name: octo-deploy
description: "Guide the promotion of an OctoMesh-powered app from local dev to the shared test-2 environment — publish the CK model and blueprint to the shared GitHub catalogs (octo-ckc / octo-bpm), push the app image to <registry>, register a test-2 octo-cli context, install + deploy on the target tenant, and verify everything WITHOUT kubectl access. Covers both the repeatable CI lane (azure-pipelines publishing on main) and the manual first-time lane, plus test-2-specific triage (server-side catalog cache refresh, ImagePullBackOff via lastDeploymentError, Tailscale reachability). Staging and production are deliberately out of scope for now. Use this skill whenever someone wants to get an app, blueprint, CK model, or workload onto test-2 or asks how to make their locally working OctoMesh app available to others. Trigger on - deploy to test-2, promote to test, install on test-2, publish blueprint, publish CK model, shared catalog, blueprint-libraries-build, construction-kit-libraries-build, octo-bpm, push to <registry>, registry push, test-2 tenant, Register-OctoCliContext, RefreshBlueprintCatalogs, blueprint not visible on test-2, ImagePullBackOff, ship the demo, make the app available."
---

# OctoMesh Deploy — local → test-2

> **Hostnames are placeholders.** The concrete domains of the shared environments (`<test-2-domain>`, `<staging-domain>`, `<prod-1-domain>`, `<prod-2-domain>`, `<legacy-domain>`, `<registry>`, `<rancher-url>`) are internal. If the plugin `octo-claude-pm` is installed, see its `agent-operating-rules/references/environments.md`; otherwise ask a colleague.

Promote an app built with `octo-app-builder` (CK model + blueprint + pipelines +
Application workload) from local dev to the shared **test-2** cluster.
**Staging and production are deliberately out of scope** — do not extrapolate
these instructions to them.

## Routing

| For... | Use |
|---|---|
| Building the app/blueprint artifacts in the first place | `Skill("octo-app-builder", ...)` |
| Individual octo-cli commands, status checks, tenant admin | `Skill("octo", ...)` |
| Operator/Helm internals (what the operator does with a workload) | `Skill("octo-operator", ...)` |
| Something broke and needs deep investigation | `Skill("octo-agent", ...)` |

## What actually has to move (and what doesn't)

A blueprint built per octo-app-builder is **environment-portable by design** —
the seed itself needs NO changes for the target cluster:

| Seed element | Why it ports |
|---|---|
| `${octo.tenantId}` in hostname/upstreamUrl | resolved at blueprint apply, per tenant |
| `{{domain.default}}` in hostname | resolved at DeployWorkload time to the cluster's default domain<!-- developer-machine -->: `127.0.0.1.nip.io` on kind<!-- /developer-machine -->, `<cluster-domain>` on a shared cluster |
| Deployment site/Adapter/HelmRepo rtIds `670…001/002/003` | seeded by System.Communication on every comm-enabled tenant |
| `ChartName` + empty `ChartVersion` | same dev-channel Helm repo on both clusters |
| Pipeline YAML | standard nodes, available on any Mesh Adapter |
| `image.repository`/`tag` in ValuesYaml | the operator injects `image.privateRegistry=<registry>` on the shared cluster — never set it yourself |

Three things DO have to move to infrastructure the target cluster's services can reach:

1. **CK model** → shared CK catalog (or direct ImportCk on the tenant — see below)
2. **Blueprint** → shared blueprint catalog (a GitHub blueprint catalog the target asset repository reads)
3. **App image** → `<registry>` registry (kind-load is local-only)

## Two lanes

**CI lane (preferred, repeatable):** an Azure DevOps pipeline in the app repo
publishes on `main`: docker image push + `octo-ckc Publish` to
`PrivateGitHubCatalog` + `octo-bpm publish` to `PrivateGitHubBlueprintCatalog`.
Guard steps worth copying: only `main` writes to shared catalogs; `dev/*`/`test/*`
compile + validate only; a guard verifies that the pipeline's image tag matches the
tag pinned in the seed (details in [references/publishing.md](references/publishing.md)).
Set this up once, then promotion = merge to main.

**Manual lane (first time / no CI yet):** run the publish commands yourself —
exact commands and one-time token setup in
[references/publishing.md](references/publishing.md).<!-- developer-machine --> Network prerequisite:
`<registry>` is reachable on office WiFi; off-site requires Tailscale first.<!-- /developer-machine -->

## The promotion sequence

Full command detail for each step lives in the two references. Run the steps in
this order; each has a checkable outcome.

### 1. Publish the artifacts (manual lane)

```bash
# CK model -> shared CK catalog (one-time: GitHub token in ~/.octo-ckc/settings.json, see references/publishing.md)
octo-ckc -c Publish -f ./ck/out/ck-<name>.yaml -c PrivateGitHubCatalog -r

# Blueprint -> shared blueprint catalog (one-time: GitHub token in ~/.octo-bpm/settings.json)
octo-bpm -c validateVersion -p ./blueprint/<Name>/<version> -cn PrivateGitHubBlueprintCatalog
octo-bpm -c publish -p ./blueprint/<Name>/<version> -c PrivateGitHubBlueprintCatalog

# App image -> the registry (must be reachable from your network, see pitfall 4)
docker push <registry>/meshmakers/<app>:<tag>
```

`octo-ckc`/`octo-bpm` are the CK and blueprint CLIs of `octo-construction-kit-engine`,
not on PATH by default. <!-- developer-machine -->(on a developer machine: the build output `bin/DebugL/net10.0/` of that repository)<!-- /developer-machine --> The pushed image tag must equal the tag
pinned in the seed's ValuesYaml — verify before pushing.

**CK catalog shortcut:** if publishing the CK model to the shared catalog is not
wanted yet, `octo-cli -c ImportCk -f <compiled> -w` directly on the target
tenant works too — `ckModelDependencies` resolution skips the catalog lookup
when a satisfying model version is already installed in the tenant
(source-verified short-circuit). The blueprint itself has no such shortcut: it
must be in a catalog the target asset repository reads.

### 2. Register the test-2 context + authenticate

```powershell
Register-OctoCliContext -Installation test-2 -TenantId <tenantId>   # octo-tools cmdlet
```

Creates context `test-2_<tenantId>` with all service URLs, switches to it, and
runs the interactive login. `-TenantId` accepts a list (`a,b,c`): one context per
tenant, no switching, one login each (`-NoLogin` to skip). Flags, URL table, headless auth, and tenant
creation (if the tenant doesn't exist yet): see
[references/test-2-environment.md](references/test-2-environment.md).

**Per-tenant authentication (AB#6836):** every command acts on the tenant of its
context and only with a token for that tenant. In a child tenant, authority comes
only from explicit provisioning: after creating a tenant run `octo-cli -c
ProvisionCurrentUser -ttid <tenantId> --context test-2_octosystem` once (new tenants
included). A missing provisioning stops the command with exit `-4` and a message that
names the tenant and `ProvisionCurrentUser -ttid <tenantId>`.<!-- developer-machine --> For a rollout over several
tenants use `Invoke-OctoTenantSweep` (dry run `-WhatIf`, one result row per tenant, continues
after a denial, never touches a token) instead of a script that copies a token out of the
context file; details in the `octo` skill, `references/tenant-tokens.md`.<!-- /developer-machine -->

**Parallel-safe targeting:** rather than relying on the active context (which
the cmdlet switched, and which a concurrent session could flip), pass
`--context test-2_<tenantId>` on every command — or `export
OCTO_CLI_CONTEXT=test-2_<tenantId>` for the shell. That way the active context
is irrelevant and nothing to switch back. **Double-check `octo-cli -c AuthStatus
--context test-2_<tenantId>` before anything mutating** (and note the `[test-2]`
prod-adjacent warning still applies).

### 3. Prepare the tenant (first time only)

```bash
octo-cli -c EnableCommunication      # seeds deployment site/Adapter/HelmRepo entities — deploys NOTHING yet
octo-cli -c GetDeploymentSites -j    # deployment site 670…001 starts Undeployed
```

**Deploy the deployment site first** (live-verified 2026-06-10): nothing rolls out
while it is `Undeployed`, and workload deploy triggers fired in that state are
silently lost (the workload sits in `Pending` forever, no error):

```bash
octo-cli -c DeployDeploymentSite -id 670000000000000000000001
octo-cli -c GetDeploymentSites -j    # repeat until CommunicationState Online, DeploymentState Deployed
```

Then bring up the Mesh Adapter and wait for it:

```bash
octo-cli -c DeployWorkload -id 670000000000000000000002   # re-trigger AFTER the deployment site is deployed
octo-cli -c GetAdapters -j                                # poll until CommunicationState Online
```

### 4. Refresh the server-side catalog cache + install

```bash
octo-cli -c RefreshCatalogs                       # CK MODEL catalogs
octo-cli -c RefreshBlueprintCatalogs              # blueprint catalogs (-cn <catalog> for one)
octo-cli -c ListBlueprints                        # your blueprint must appear (CatalogName: PrivateGitHubBlueprintCatalog)
octo-cli -c InstallBlueprint -b <Name>-<Version>
```

The asset repository caches the catalog **index**: a **newly published** blueprint
id/version stays invisible to `ListBlueprints`/`InstallBlueprint` until
`RefreshBlueprintCatalogs` runs (always forced, no service restart; `-cn
PrivateGitHubBlueprintCatalog` refreshes one catalog). Both refresh commands need the
tenant role `DataModelManagement`. Published blueprint versions are immutable: every
content change (seed data, `ValuesYaml`, `blueprint.yaml`) gets a new version, which is
published, refreshed and rolled out with `UpdateBlueprint -tv <Name>-<NewVersion>`.
`octo-bpm -c validateVersion` reports changed content under a published version as `OCTO-BP100`.

Confirm: `Success: true`, your CK model in `LoadedCkModels`, no warnings.
`WasSkipped: true` means the `requires:` gate didn't match — see the
section *The environment gate* of the deploy environment
reference.

### 5. Deploy

```bash
octo-cli -c DeployDataFlow -id <dataflowRtId>
octo-cli -c DeployWorkload -id <applicationRtId>
```

### 6. Verify

The octo-cli signals below need no cluster access:

| Signal | Command |
|---|---|
| Adapter online, pipelines deployed | `octo-cli -c GetAdapters -j`, `octo-cli -c GetDataFlowStatus -id <dataflowRtId> -j` |
| Workload state + failure detail | `octo-cli -c GetWorkloadsByChart -cn <chartName>`; the Application entity's `deploymentState` / `statusMessage` / `lastDeploymentError` attributes via Studio<!-- developer-machine --> or rt_explorer<!-- /developer-machine --> |
| App reachable | `https://<app>-<tenantId>.<cluster-domain>` (from the `{{domain.default}}` hostname) |
| API reachable | only when the Mesh Adapter's ingress is on (`IngressEnabled`, opt-in, then `DeployWorkload`; octo-app-builder `references/http-api-pipelines.md`): `https://<Hostname>/<tenantId>/<path>` with a token of the tenant, header on stdin (`printf 'Authorization: Bearer %s\n' "$TOKEN" \| curl -H @- …`); without an ingress test with `ExecutePipeline` |

`lastDeploymentError` carries the Helm error plus pod diagnostics (waiting
reasons like ImagePullBackOff, exit codes, Warning events) collected by the
operator — it is the primary triage signal; no cluster access is needed.

End-to-end: run the same curl matrix used locally (create / list / error paths /
no leaked fields) against the hosts of the target cluster, then the browser flow.

## Pitfalls

| # | Symptom | Cause / fix |
|---|---|---|
| 1 | Blueprint missing from `ListBlueprints` on the target cluster | The server-side blueprint catalog index is cached. Run `octo-cli -c RefreshBlueprintCatalogs [-cn <catalog>]` (needs `DataModelManagement`; `RefreshCatalogs` covers CK model catalogs only). Never restart the asset repository with kubectl; deleting local cache files does nothing for a shared cluster. |
| 2 | `InstallBlueprint` fails resolving the CK model | Model not in a shared catalog and not imported in the tenant. Publish it (`octo-ckc … -c PrivateGitHubCatalog`) or `ImportCk` it directly, then retry. |
| 3 | Workload `lastDeploymentError` shows ImagePullBackOff | Image not in `<registry>` under the exact `meshmakers/<app>:<tag>` from the seed. Push it<!-- developer-machine --> (Tailscale if off-site)<!-- /developer-machine -->, then `DeployWorkload` again. |
| 4 | `docker push` hangs/fails off-site | `<registry>` is not reachable from your network<!-- developer-machine --> (internal-network only — connect Tailscale first)<!-- /developer-machine -->. Probe: `curl -sI https://<registry>/v2/` (with the registry's CA trusted) → expect HTTP 200 or 401. |
| 5 | Install is a silent no-op (`WasSkipped: true`) | `requires: octo.environment` gate mismatch. Use `[dev, test]` (covers both readings of a test cluster's configuration) and re-check. |
| 6 | Mutating the wrong environment | Context confusion. `AuthStatus` before every mutating step; the context name (`<cluster>_<tenant>` vs `local_<tenant>`) is the tell. |
| 7 | Adapter stuck `Unregistered`/`Pending` forever, no pod, no error | The parent **deployment site is Undeployed** — workload deploy triggers fired before it is up are silently lost. Deploy it first (`DeployDeploymentSite -id 670…001`), then re-run `DeployWorkload -id 670…002`. |
| 8 | Wrong tag deployed after a new image push | Same-tag pushes don't restart pods. Either bump the tag (new tag in the seed + new blueprint version + push + publish + `RefreshBlueprintCatalogs` + `UpdateBlueprint` + `DeployWorkload`) or undeploy/redeploy the workload. |

## References

- [references/test-2-environment.md](references/test-2-environment.md) — URLs,
  context registration, auth (interactive + headless), tenant creation, the
  environment-gate ambiguity, network access.
- [references/publishing.md](references/publishing.md) — shared catalogs
  (octo-ckc / octo-bpm, tokens, what gets written where), the ImportCk shortcut,
  registry push, image tag conventions, and the CI lane.
