---
name: octo-app-builder
description: Build a complete OctoMesh-powered application end to end — a custom Construction Kit data model published to the CK catalog, an HTTP API made of dataflow pipelines on the tenant's Mesh Adapter, an optional containerized web app the Communication Operator rolls out to Kubernetes, and a blueprint that packages all of it so a single InstallBlueprint provisions any tenant. Encodes the verified build sequence (model → pipelines → app image → blueprint → install → deploy → verify) and the pitfalls that silently break it (blueprint catalog cache, pipeline registration rotation, HTTP response shaping, registry injection). Use this skill whenever someone wants to CREATE something new on OctoMesh — an app, a demo, an API, a workload, a blueprint — even if they only mention one piece of it. Trigger on - build an app on OctoMesh, create a workload, new OctoMesh application, OctoMesh demo, blueprint authoring, package as blueprint, seedDataPath, ckModelDependencies, InstallBlueprint, Application entity, DeployWorkload, operator-deployed app, HTTP API on the mesh adapter, FromHttpRequest API, octo-ckc publish, CK model catalog, local blueprint catalog, end-to-end OctoMesh app.
---

# OctoMesh App Builder

Build new OctoMesh-powered applications: data model + HTTP API + web app, packaged
as one installable blueprint. This skill owns the **end-to-end composition recipe**;
detail work routes to sibling skills.

## Routing

| For... | Use |
|---|---|
| Pipeline YAML node details, DataContext semantics, validation | `Skill("pipeline-expert", ...)` |
| octo-cli flag details, CK/RT exploration, deploy/status commands | `Skill("octo", ...)` |
| Operator/Helm-chart internals, CRDs, values layering | `Skill("octo-operator", ...)` |
| Build/start services, kind cluster setup, Docker infra | `Skill("octo-devtools", ...)` |
| Something is broken and needs investigation | `Skill("octo-agent", ...)` |

Stay in this skill for: designing the app, authoring CK models for it, authoring
the blueprint, the HTTP-API pipeline patterns, the Application workload, and the
overall sequencing.

## Anatomy of an OctoMesh app

```
blueprint (one InstallBlueprint provisions everything)
├── CK model            — the domain data model (via ckModelDependencies, from a CK catalog)
└── seed-data/entities.yaml
    ├── DataFlow + Pipelines  — the backend: HTTP API + logic on the Mesh Adapter (no service code!)
    └── Application           — the web app: Helm release deployed by the Communication Operator
```

Tickets/orders/whatever the domain needs are plain runtime entities of the custom
CK type — browsable in Studio, queryable via GraphQL, manipulated by pipelines.

A complete worked example lives in the workspace at `one-time-ticket/` (read its
README.md + CLAUDE.md): secret-redeemable-once app, 3 pipelines, operator-deployed
UI. The `ZenonDynprop.MainLatest` blueprint (meshmakers/blueprint-libraries-build,
`blueprints/v1/z/...`) is the same pattern with two adapters.

## Prerequisite checks (run before building)

```bash
octo-cli -c AuthStatus                      # valid token, correct environment
octo-cli -c GetAdapters --json              # Mesh Adapter Online? note its rtId
```

On every communication-enabled tenant the service-managed System.Communication
blueprint seeds fixed rtIds your seed will associate to:
Pool `670000000000000000000001`, Mesh Adapter `670000000000000000000002`,
dev Helm repo `670000000000000000000003`.

For an operator-deployed web app additionally: a cluster with the Communication
Operator running (`kubectl get pods -n octo-operator-system`) — on local dev this
is the kind cluster (see octo-devtools for setup).

## Build sequence

Work in a dedicated repo folder: `ck/ConstructionKit/`, `blueprint/<Name>/<version>/`,
`app/`, `test/`. The blueprint seed is the single source of truth; anything used
for iteration is scratch.

### 1. CK model → CK catalog

Author a minimal model (one folder, three files — full syntax in
[references/blueprint-authoring.md](references/blueprint-authoring.md) §CK model):
`ckModel.yaml` (modelId `<Name>-1.0.0`, dependency `System-[2.0,3.0)`),
`attributes/*.yaml`, `types/*.yaml` (derive from `${System}/Entity-1`, reference
attributes as `${this}/<AttrId>-1`).

```powershell
# octo-ckc = build output of octo-construction-kit-engine (bin/DebugL/net10.0/octo-ckc.exe), not on PATH
octo-ckc -c Compile -p .\ck\ConstructionKit -o .\ck\out
octo-ckc -c Publish -f .\ck\out\ck-<name>.yaml -r     # → ~/.octo/local-catalog (LocalFileSystemCatalog)
```

Publishing to the catalog is what lets the blueprint auto-import the model via
`ckModelDependencies`. For pipeline iteration also import it into the tenant now:
`octo-cli -c ImportCk -f .\ck\out\ck-<name>.yaml -w`, then verify the exact
attribute IDs with the octo skill's
`ck_explorer.py preflight <Model>/<Type> --for-import`.

### 2. HTTP-API pipelines (iterate on a scratch dataflow)

Author the API as `FromHttpRequest@1` pipelines executed by the Mesh Adapter.
The proven patterns — create entity, list without sensitive fields, conditional
read-and-update — are in
[references/http-api-pipelines.md](references/http-api-pipelines.md) with verbatim
YAML. Three rules that are not obvious and break things silently:

1. **The HTTP response is the entire final DataContext.** End every pipeline with
   `Project@1` + `clear: true` listing only the response fields — otherwise the
   raw request body and lookup results (including any secrets) leak into the response.
2. **`SetPrimitiveValue@1` fails the whole pipeline on a missing source path** —
   guard copies of optional attributes with `If@1` on a discriminator field.
3. **Result sets are PascalCase** (`$.lookup.TotalCount`, `$.lookup.Items[0].Attributes.X`);
   `attributeName` in `CreateUpdateInfo@1` is the CK attribute name as declared.

Iterate with a **scratch dataflow**: temp rtIds and temp paths (e.g. `/myapp-test-*`)
in a throwaway ImportRt file, `ImportRt -f ... -w` + `DeployDataFlow`, curl, fix,
re-import with `-r`. Expect the deploy-rotation quirk (pitfall #2 below) during
iteration — it does not affect the final fresh install. When the endpoints behave,
copy the pipeline YAML verbatim into the blueprint seed, then undeploy and delete
the scratch entities (GraphQL `runtime.runtimeEntities.delete`, unversioned ckTypeIds).

Reach the adapter for curl tests: in-cluster it serves plain HTTP on `:80`; from the
host use `kubectl port-forward -n octo svc/<tenant>-<adapterRtId> 5020:80`, routes
are `http://localhost:5020/{tenantId}{path}`.

### 3. Web app workload (optional)

The platform deploys web apps as `System.Communication/Application` entities —
the operator helm-installs them. The fastest path is fulfilling the existing
**property-walker chart contract** (env `PORT` + `UPSTREAM_URL`, probe on `GET /`,
container port 5055): a zero-dependency Node proxy that serves a static SPA at `/`
and forwards `/api/*` to the tenant-scoped adapter URL. Full recipe, Dockerfile,
and the Application entity YAML: [references/app-workload.md](references/app-workload.md).

Image handling on local kind (no registry needed):

```powershell
docker build -t meshmakers/<app>:0.1.0 .\app
docker tag meshmakers/<app>:0.1.0 docker.mm.cloud/meshmakers/<app>:0.1.0
kind load docker-image meshmakers/<app>:0.1.0 docker.mm.cloud/meshmakers/<app>:0.1.0
```

Tag **both** names: the communication controller injects
`image.privateRegistry=docker.mm.cloud` at deploy time, so the final image
reference gets that prefix. On shared clusters push to `docker.mm.cloud` instead.

### 4. Blueprint

Author `blueprint/<Name>/<version>/blueprint.yaml` + `seed-data/entities.yaml` —
full format in [references/blueprint-authoring.md](references/blueprint-authoring.md).
Key decisions:

- `ckModelDependencies: [<Model>-[1.0.0,2.0.0)]` — pulls the model from the CK
  catalog at install; no manual ImportCk for consumers.
- Seed entities use **hand-assigned stable 24-hex rtIds** (pick a recognizable
  prefix, e.g. `0771…01`) so re-applies are idempotent and entities are identifiable.
- Pipelines associate `System/ParentChild-1` → your DataFlow and
  `System.Communication/Executes-1` → Mesh Adapter `670…002`.
- The Application associates `Manages-1` → Pool `670…001` and `HelmRepository-1`
  → `670…003`; hostname template `<app>-${octo.tenantId}.{{domain.default}}`
  works on every cluster (`127.0.0.1.nip.io` on kind).
- Gate with `requires: {octo.environment: [dev, test]}` if the rollout depends on
  the operator (staging/prod may not run it).

Install into the local blueprint catalog:

```powershell
# layout: ~/.octo/local-blueprint-catalog/blueprints/v1/<Name>/<version>/{blueprint.yaml,seed-data/}
Copy-Item ... # copy both files preserving layout
Remove-Item "$HOME\.octo\blueprint-catalog\cache\local-blueprint-catalog-cache.json" -Force
octo-cli -c ListBlueprints     # must now show <Name>-<version>
```

Deleting the cache file is mandatory — it only rebuilds when missing (pitfall #1).

### 5. Install + deploy

```powershell
octo-cli -c InstallBlueprint -b <Name>-<Version>       # -f to force re-apply after seed edits
octo-cli -c DeployDataFlow --identifier <dataflowRtId>
octo-cli -c DeployWorkload -id <applicationRtId>       # only if there is an app
```

Confirm the install output: `Success: true`, `ApplicationMode: Initial`, your model
under `LoadedCkModels`, no warnings. A silent no-op with `WasSkipped` means the
`requires:` gate did not match the environment.

### 6. Verify

- Curl matrix against every endpoint: happy path, conditional/error paths, and
  that no response leaks fields it shouldn't (grep the raw JSON).
- App: pod Running (`kubectl get pods -n octo`), ingress host answers, then drive
  the real UI flow in a browser (Playwright) — not just the API.
- On any silent failure read the adapter log first:
  `kubectl logs -n octo deploy/<tenant>-<adapterRtId>` — pipeline exceptions,
  route registrations (`Removing pipeline` / `Registering pipeline`), request traces.
- Clean up test entities afterwards so the consumer starts fresh.

## Pitfalls (each cost real debugging time)

| # | Symptom | Cause / fix |
|---|---|---|
| 1 | New blueprint missing from `ListBlueprints` | Local blueprint catalog cache only rebuilds when the cache file is **missing**. Delete `~/.octo/blueprint-catalog/cache/local-blueprint-catalog-cache.json`. |
| 2 | Endpoint answers 200 with empty body in ~0.1 ms | Route's method not registered (path-only fallback). After `ImportRt -r` on a live dataflow, each `DeployDataFlow` can remove an unchanged pipeline while re-registering a changed one. Re-run `DeployDataFlow` and re-test ALL routes; fresh install + single deploy is reliable. |
| 3 | Pipeline 500s only for some entities | `SetPrimitiveValue@1` on an optional attribute that is unset. Guard with `If@1`. |
| 4 | Response contains request body / secrets / lookup internals | No `Project@1 clear: true` at the end. The response is the whole final DataContext. |
| 5 | App pod `ImagePullBackOff` | Controller injected `docker.mm.cloud` prefix and the image only exists under the plain name. Tag + `kind load` both names (or push to the registry). |
| 6 | Install is a silent no-op | `requires:` gate mismatch (`WasSkipped: true`). Check `octo.environment`. |
| 7 | `ImportRt` fails on re-run | Default mode is InsertOnly. Use `-r` for scratch iteration; blueprint re-apply (`InstallBlueprint -f`) upserts by itself. |
| 8 | Errors return HTTP 200 | By design — `FromHttpRequest@1` pipelines cannot set status codes. Return `{ "error": ... }` payloads and make clients check for them. |

## Design constraints to set expectations early

- Pipeline check-then-update is **not atomic** — concurrent requests can race.
  Fine for demos; call it out for production designs.
- No auth on adapter HTTP routes — anyone with the URL can call them.
- Content type is always `application/json`; the adapter cannot serve HTML.
  That's exactly why the UI ships as an Application workload instead.

## References

- [references/blueprint-authoring.md](references/blueprint-authoring.md) — CK model
  source syntax, blueprint manifest + seed format, variables, catalogs, lifecycle.
- [references/http-api-pipelines.md](references/http-api-pipelines.md) — verbatim
  pipeline YAML for create/list/conditional-update APIs, response shaping, debugging.
- [references/app-workload.md](references/app-workload.md) — Application entity,
  property-walker chart contract, proxy server pattern, image + deploy loop.
