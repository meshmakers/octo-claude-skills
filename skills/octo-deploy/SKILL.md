---
name: octo-deploy
description: Guide the promotion of an OctoMesh-powered app from local dev to the shared test-2 environment — publish the CK model and blueprint to the shared GitHub catalogs (octo-ckc / octo-bpm), push the app image to docker.mm.cloud, register a test-2 octo-cli context, install + deploy on the target tenant, and verify everything WITHOUT kubectl access. Covers both the repeatable CI lane (azure-pipelines publishing on main) and the manual first-time lane, plus test-2-specific triage (server-side catalog cache refresh, ImagePullBackOff via lastDeploymentError, Tailscale reachability). Staging and production are deliberately out of scope for now. Use this skill whenever someone wants to get an app, blueprint, CK model, or workload onto test-2 or asks how to make their locally working OctoMesh app available to others. Trigger on - deploy to test-2, promote to test, install on test-2, publish blueprint, publish CK model, shared catalog, blueprint-libraries-build, construction-kit-libraries-build, octo-bpm, push to docker.mm.cloud, registry push, test-2 tenant, Register-OctoCliContext, RefreshCatalogs, blueprint not visible on test-2, ImagePullBackOff, ship the demo, make the app available.
---

# OctoMesh Deploy — local → test-2

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
the seed itself needs NO changes for test-2:

| Seed element | Why it ports |
|---|---|
| `${octo.tenantId}` in hostname/upstreamUrl | resolved at blueprint apply, per tenant |
| `{{domain.default}}` in hostname | resolved at DeployWorkload time: `127.0.0.1.nip.io` on kind, `test-2.mm.cloud` on test-2 |
| Pool/Adapter/HelmRepo rtIds `670…001/002/003` | seeded by System.Communication on every comm-enabled tenant |
| `ChartName` + empty `ChartVersion` | same dev-channel Helm repo on both clusters |
| Pipeline YAML | standard nodes, available on any Mesh Adapter |
| `image.repository`/`tag` in ValuesYaml | the operator injects `image.privateRegistry=docker.mm.cloud` on test-2 — never set it yourself |

Three things DO have to move to infrastructure the test-2 services can reach:

1. **CK model** → shared CK catalog (or direct ImportCk on the tenant — see below)
2. **Blueprint** → shared blueprint catalog (`meshmakers/blueprint-libraries-build`)
3. **App image** → `docker.mm.cloud` registry (kind-load is local-only)

## Two lanes

**CI lane (preferred, repeatable):** an Azure DevOps pipeline in the app repo
publishes on `main`: docker image push + `octo-ckc Publish` to
`PrivateGitHubCatalog` + `octo-bpm publish` to `PrivateGitHubBlueprintCatalog`.
Worked example with guard steps: `one-time-ticket/devops-build/azure-pipelines.yml`
(only `main` writes to shared catalogs; `dev/*`/`test/*` compile + validate only;
a guard verifies the pipeline's image tag matches the tag pinned in the seed).
Set this up once, then promotion = merge to main.

**Manual lane (first time / no CI yet):** run the publish commands yourself —
exact commands and one-time token setup in
[references/publishing.md](references/publishing.md). Network prerequisite:
`docker.mm.cloud` is reachable on office WiFi; off-site requires Tailscale first.

## The promotion sequence

Full command detail for each step lives in the two references. Run the steps in
this order; each has a checkable outcome.

### 1. Publish the artifacts (manual lane)

```powershell
# CK model -> shared CK catalog (one-time: octo-ckc -c Config -gt <github-token>)
octo-ckc -c Publish -f .\ck\out\ck-<name>.yaml -c PrivateGitHubCatalog -r

# Blueprint -> shared blueprint catalog (one-time: octo-bpm -c config -gt <github-token>)
octo-bpm -c publish -p .\blueprint\<Name>\<version> -c PrivateGitHubBlueprintCatalog -f

# App image -> internal registry (Tailscale if off-site!)
docker push docker.mm.cloud/meshmakers/<app>:<tag>
```

`octo-ckc`/`octo-bpm` are build outputs of `octo-construction-kit-engine`
(`bin/DebugL/net10.0/`), not on PATH. The pushed image tag must equal the tag
pinned in the seed's ValuesYaml — verify before pushing.

**CK catalog shortcut:** if publishing the CK model to the shared catalog is not
wanted yet, `octo-cli -c ImportCk -f <compiled> -w` directly on the test-2
tenant works too — `ckModelDependencies` resolution skips the catalog lookup
when a satisfying model version is already installed in the tenant
(source-verified short-circuit). The blueprint itself has no such shortcut: it
must be in a catalog the test-2 asset-repo reads.

### 2. Register the test-2 context + authenticate

```powershell
Register-OctoCliContext -Installation test-2 -TenantId <tenantId>   # octo-tools cmdlet
```

Creates context `test-2_<tenantId>` with all service URLs, switches to it, and
runs the interactive login. Flags, URL table, headless auth, and tenant
creation (if the tenant doesn't exist yet): see
[references/test-2-environment.md](references/test-2-environment.md).

From here on, every octo-cli command targets test-2 — **double-check
`octo-cli -c AuthStatus` before anything mutating**, and switch back to your
local context when done (`octo-cli -c UseContext -n <local-context>`).

### 3. Prepare the tenant (first time only)

```powershell
octo-cli -c EnableCommunication      # seeds Pool/Adapter/HelmRepo entities — deploys NOTHING yet
octo-cli -c GetPools -j              # pool 670…001 starts Undeployed
```

**Deploy the Pool first** (live-verified 2026-06-10, tenant `tickets`): nothing
rolls out while the pool is `Undeployed`, and workload deploy triggers fired in
that state are silently lost (the workload sits in `Pending` forever, no error).
octo-cli has **no DeployPool command** — it is REST-only:

```powershell
$ctx = Get-Content "$env:USERPROFILE\.octo-cli\contexts.json" | ConvertFrom-Json
$token = $ctx.Contexts.($ctx.ActiveContext).Authentication.AccessToken
Invoke-WebRequest -Method POST -Headers @{Authorization="Bearer $token"} `
  -Uri "https://communication.test-2.mm.cloud/<tenantId>/v1/Pool/deploy?poolRtId=670000000000000000000001"
# expect 204; GetPools -j -> CommunicationState Online, DeploymentState Deployed
```

Then bring up the Mesh Adapter and wait for it:

```powershell
octo-cli -c DeployWorkload -id 670000000000000000000002   # re-trigger AFTER the pool is deployed
octo-cli -c GetAdapters -j                                # poll until CommunicationState Online
```

### 4. Refresh the server-side catalog cache + install

```powershell
octo-cli -c RefreshCatalogs                       # CK MODEL catalogs only — does NOT touch blueprint catalogs!
octo-cli -c ListBlueprints                        # your blueprint must appear (CatalogName: PrivateGitHubBlueprintCatalog)
octo-cli -c InstallBlueprint -b <Name>-<Version>
```

**Blueprint catalogs have NO refresh API** (live-verified: the asset service
exposes refresh only via `CkModelCatalogController`; the blueprint manager's
refresh is never wired up). A **newly published** blueprint id/version stays
invisible to `ListBlueprints`/`InstallBlueprint` until the asset-repo pod
restarts:

```powershell
kubectl --context test-2 -n octo rollout restart deploy/octo-mesh-asset-rep-services
kubectl --context test-2 -n octo rollout status  deploy/octo-mesh-asset-rep-services
```

(kubeconfig: see test-2-environment.md). Only the catalog **index** is cached —
re-publishing new CONTENT under an already-listed id+version needs no restart;
`InstallBlueprint -b <id> -f` fetches the seed live from GitHub Pages.

Confirm: `Success: true`, your CK model in `LoadedCkModels`, no warnings.
`WasSkipped: true` means the `requires:` gate didn't match — see the
environment-gate note in
[references/test-2-environment.md](references/test-2-environment.md).

### 5. Deploy

```powershell
octo-cli -c DeployDataFlow -id <dataflowRtId>
octo-cli -c DeployWorkload -id <applicationRtId>
```

### 6. Verify

kubectl on test-2 IS available (Rancher kubeconfig download — see
test-2-environment.md), but the octo-cli signals below work without it:

| Signal | Command |
|---|---|
| Adapter online, pipelines deployed | `octo-cli -c GetAdapters -j`, `octo-cli -c GetDataFlowStatus -id <dataflowRtId> -j` |
| Workload state + failure detail | `octo-cli -c GetWorkloadsByChart -cn <chartName>`; the Application entity's `deploymentState` / `statusMessage` / `lastDeploymentError` attributes via rt_explorer or Studio |
| App reachable | `https://<app>-<tenantId>.test-2.mm.cloud` (from the `{{domain.default}}` hostname) |
| API reachable | adapter ingress host from `GetAdapters -j` (`publicUri`), then `curl https://<adapter-host>/<tenantId>/<path>` |

`lastDeploymentError` carries the Helm error plus pod diagnostics (waiting
reasons like ImagePullBackOff, exit codes, Warning events) collected by the
operator — it is the primary triage signal in place of `kubectl describe`.

End-to-end: run the same curl matrix used locally (create / list / error paths /
no leaked fields) against the test-2 hosts, then the browser flow.

## Pitfalls

| # | Symptom | Cause / fix |
|---|---|---|
| 1 | Blueprint missing from `ListBlueprints` on test-2 | Server-side blueprint catalog cache is stale and has **no refresh API** (`RefreshCatalogs` covers CK model catalogs only). Restart the asset-repo pod: `kubectl --context test-2 -n octo rollout restart deploy/octo-mesh-asset-rep-services`. Deleting local cache files does nothing for test-2. |
| 2 | `InstallBlueprint` fails resolving the CK model | Model not in a shared catalog and not imported in the tenant. Publish it (`octo-ckc … -c PrivateGitHubCatalog`) or `ImportCk` it directly, then retry. |
| 3 | Workload `lastDeploymentError` shows ImagePullBackOff | Image not in `docker.mm.cloud` under the exact `meshmakers/<app>:<tag>` from the seed. Push it (Tailscale if off-site), then `DeployWorkload` again. |
| 4 | `docker push` hangs/fails off-site | `docker.mm.cloud` is internal-network only — connect Tailscale first. Probe: `curl -skI https://docker.mm.cloud/v2/` → expect HTTP 200. |
| 5 | Install is a silent no-op (`WasSkipped: true`) | `requires: octo.environment` gate mismatch. Use `[dev, test]` (covers both readings of test-2's configuration) and re-check. |
| 6 | Mutating the wrong environment | Context confusion. `AuthStatus` before every mutating step; the context name (`test-2_<tenant>` vs `local_<tenant>`) is the tell. |
| 7 | Adapter stuck `Unregistered`/`Pending` forever, no pod, no error | The parent **pool is Undeployed** — workload deploy triggers fired before the pool is up are silently lost. Deploy the pool first (REST `POST …/v1/Pool/deploy?poolRtId=670…001`, no octo-cli command), then re-run `DeployWorkload -id 670…002`. |
| 8 | Wrong tag deployed after a new image push | Same-tag pushes don't restart pods. Either bump the tag (seed + push + `InstallBlueprint -f` + `DeployWorkload`) or undeploy/redeploy the workload. |

## References

- [references/test-2-environment.md](references/test-2-environment.md) — URLs,
  context registration, auth (interactive + headless), tenant creation, the
  environment-gate ambiguity, network access.
- [references/publishing.md](references/publishing.md) — shared catalogs
  (octo-ckc / octo-bpm, tokens, what gets written where), the ImportCk shortcut,
  registry push, image tag conventions, and the CI lane.
