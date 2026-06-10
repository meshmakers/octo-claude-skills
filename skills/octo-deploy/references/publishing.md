# Publishing artifacts for test-2 — catalogs, registry, CI lane

How the three promotable artifacts (CK model, blueprint, app image) reach
infrastructure the test-2 services can read. Verified 2026-06-10 against
octo-ckc/octo-bpm help + engine source (`GitHubCatalog.cs`,
`GitHubBlueprintCatalog.cs`), the `blueprint-libraries-build` commit history,
and a live registry probe.

Tooling: `octo-ckc` and `octo-bpm` are build outputs of
`octo-construction-kit-engine` (`bin/DebugL/net10.0/`), not on PATH.
octo-cli has NO publish commands — publishing always goes through these tools.

## CK model → shared CK catalog

Catalog: `PrivateGitHubCatalog` = GitHub repo
`meshmakers/construction-kit-libraries-build` (public), read via GitHub Pages
(`https://meshmakers.github.io/construction-kit-libraries-build/`), written via
the GitHub API.

```powershell
octo-ckc -c Config -gt <github-api-token>     # one-time; stored in ~/.octo-ckc/settings.json
octo-ckc -c Compile -p .\ck\ConstructionKit -o .\ck\out
octo-ckc -c Publish -f .\ck\out\ck-<name>.yaml -c PrivateGitHubCatalog -r   # -r replaces existing version
```

Publish commits the compiled model to
`ck-models/v2/<letter>/<Name>/<major>/ck-<name>-<version>.json` on `main` and
upserts the three catalog.json index levels — one API commit per file.

### Shortcut: skip the catalog entirely

`ckModelDependencies` resolution short-circuits when the tenant already has a
satisfying model version installed (source-verified:
`EnsureCkModelInstalledAsync` returns before any catalog lookup when
installed ≥ requested). So this works without any catalog publish:

```powershell
# on the test-2 tenant context
octo-cli -c ImportCk -f .\ck\out\ck-<name>.yaml -w
octo-cli -c InstallBlueprint -b <Name>-<Version>
```

Good for first experiments; publish to the shared catalog once others or other
tenants need the model.

## Blueprint → shared blueprint catalog

Catalog: `PrivateGitHubBlueprintCatalog` = GitHub repo
`meshmakers/blueprint-libraries-build` (**private**), layout
`blueprints/v1/<letter>/<Name>/<major>/<Name>-<version>/{blueprint.yaml,seed-data/}`.

```powershell
octo-bpm -c config -gt <github-api-token>     # one-time; stored in ~/.octo-bpm/settings.json
octo-bpm -c publish -p .\blueprint\<Name>\<version> -c PrivateGitHubBlueprintCatalog -f   # -f = force/replace
octo-bpm -c list                              # confirm the catalog entry
```

There is NO ImportCk-style shortcut for blueprints — `InstallBlueprint` only
resolves from catalogs the asset-repo reads, so the blueprint must be published.

After publishing a **new blueprint id/version**, the server-side blueprint
catalog cache on test-2 must rebuild — and it has **NO refresh API at all**
(live-verified 2026-06-10: `RefreshCatalogs` refreshes CK MODEL catalogs only —
`CkModelCatalogController` REST `POST …/system/v1/ckmodelcatalog/refresh`; the
blueprint manager's `RefreshAllCatalogCachesAsync` is never exposed by any
controller or GraphQL mutation). The cache file inside the asset-repo pod only
rebuilds when missing, so restart the pod:

```powershell
kubectl --context test-2 -n octo rollout restart deploy/octo-mesh-asset-rep-services
```

Scope of the cache: the **index** (which blueprint ids/versions exist) only.
Re-publishing changed CONTENT under an already-listed id+version needs no
restart — `InstallBlueprint -b <id> -f` fetches blueprint.yaml/seed-data live
from GitHub Pages (≤1 min Pages deploy lag). The local cache-file-delete trick
from local development does not apply to test-2.

## App image → docker.mm.cloud

```powershell
# Tailscale first when off-site! Probe: curl -skI https://docker.mm.cloud/v2/  -> 200
docker build -t docker.mm.cloud/meshmakers/<app>:<tag> .\app
docker push docker.mm.cloud/meshmakers/<app>:<tag>
```

- `<tag>` must equal the tag pinned in the blueprint seed's ValuesYaml
  (`image.tag`). Static semver tags (`0.1.0`) for app workloads — the rolling
  `main-latest` + `pullPolicy: Always` pattern is for core services only.
- Repository path convention: `meshmakers/<app-name>`.
- Do NOT set `image.privateRegistry` in the seed — the operator injects
  `docker.mm.cloud` on test-2 (cluster values: `operator.imageRegistry`).
- Cluster nodes pull without per-pod imagePullSecrets (node-level containerd
  config / open internal registry). A locally built `linux/amd64` image is fine
  for test-2; CI builds multi-arch via buildx.
- Re-pushing the SAME tag does not restart running pods — bump the tag (and the
  seed) or undeploy/redeploy the workload.

## The CI lane (recommended once the app stabilizes)

Worked example: `one-time-ticket/devops-build/azure-pipelines.yml` (Azure
DevOps, modeled on the energy-community demo pipeline; templates:
`build-and-push-docker-image.yml`, `publish-ck-and-blueprint.yml`,
`install-octo-tools.yml`, `update-build-number.yml`).

Branch policy it encodes:

| Branch | Actions |
|---|---|
| any push | compile CK model (octo-ckc), validate blueprint (octo-bpm), docker build |
| `test/*` | + push image with the build-number tag (`0.1.YYMM.DDNNN-<branch>`) |
| `main` | + push image (build-number tag AND the blueprint-pinned static tag), publish CK model to `PrivateGitHubCatalog`, publish blueprint to `PrivateGitHubBlueprintCatalog` |

Guard worth copying: a verify step asserts the pipeline's `AppImageVersion`
variable equals the `image.tag` in `seed-data/entities.yaml`, so the published
blueprint can never reference an unpushed image tag. Only `main` writes to the
shared catalogs — dev/test branches never publish.

CI-agent gotchas (cost a red build each, 2026-06-10):

- **Never use `octo-ckc … -lce false`** to keep the local catalog out of
  dependency resolution: in the released 3.3.x tools the flag disables the
  catalog only AFTER construction, which crashes `Compile` with "Model catalog
  'LocalFileSystemCatalog' is not enabled for read operations" on any agent
  without a warm catalog cache (dev machines have one, so it never reproduces
  locally). Configure via the settings file instead — both tools always read
  `~/.octo-ckc/settings.json` / `~/.octo-bpm/settings.json`:
  `{ "PrivateOctoGitHub": { "GitHubApiToken": "…" }, "LocalFileSystemCatalog": { "IsEnabled": false } }`
  (construction-time disable → catalog is skipped correctly). Wipe
  `~/.octo/ck-catalog/cache` + `~/.octo/blueprint-catalog/cache` before
  publishing, and delete the PAT-bearing settings files in an `always()` step.
- **`octo-bpm -c publish` can soft-fail with exit 0** (logs the error and
  returns) — grep the output for `published successfully to catalog` and fail
  the step if absent.

With CI in place, the manual lane reduces to: merge to main, wait for the
pipeline, then on the tenant `RefreshCatalogs` (CK models) → restart the
asset-repo pod if the blueprint id/version is NEW → `InstallBlueprint` →
`DeployDataFlow` → `DeployWorkload`.
