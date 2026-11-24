# Publishing artifacts — catalogs, registry, CI lane

> **Hostnames are placeholders.** The concrete domains of the shared environments (`<test-2-domain>`, `<staging-domain>`, `<prod-1-domain>`, `<prod-2-domain>`, `<legacy-domain>`, `<registry>`, `<rancher-url>`) are internal. If the plugin `octo-claude-pm` is installed, see its `agent-operating-rules/references/environments.md`; otherwise ask a colleague.

How the three promotable artifacts (CK model, blueprint, app image) reach
infrastructure the target cluster's services can read. Verified 2026-06-10 against
octo-ckc/octo-bpm help + engine source (`GitHubCatalog.cs`,
`GitHubBlueprintCatalog.cs`), the commit history of a GitHub blueprint catalog,
and a live registry probe.

Tooling: `octo-ckc` and `octo-bpm` are the CK and blueprint CLIs of
`octo-construction-kit-engine`, not on PATH by default. <!-- developer-machine -->(on a developer machine: the build output `bin/DebugL/net10.0/` of that repository)<!-- /developer-machine -->
octo-cli has NO publish commands — publishing always goes through these tools.

## CK model → shared CK catalog

Catalog: `PrivateGitHubCatalog` = a GitHub repository configured in the asset
repository, read via its GitHub Pages site, written via the GitHub API.

```bash
# one-time: GitHub token in ~/.octo-ckc/settings.json ("PrivateOctoGitHub": {"GitHubApiToken": "…"}),
# written with an editor; `octo-ckc -c Config -gt <token>` would put it on the command line and in the history
octo-ckc -c Compile -p ./ck/ConstructionKit -o ./ck/out
octo-ckc -c Publish -f ./ck/out/ck-<name>.yaml -c PrivateGitHubCatalog -r   # -r replaces existing version
```

Publish commits the compiled model to
`ck-models/<root>/<letter>/<Name>/<major>/ck-<name>-<version>.json` on `main` and
upserts the three catalog.json index levels of that root — one API commit per file.

### Two catalog roots: `ck-models/v2/` and `ck-models/v3/`

`octo-ckc` picks the root from the compiled model; there is no flag for it:

| Model | Root |
|---|---|
| classic model (`ckLanguage` 1, exact dependency pins) | `ck-models/v2/` |
| `ckLanguage: 2`, range-retaining dependencies, or any model whose compiled output carries `minEngineVersion` (also a classic model on such a dependency) | `ck-models/v3/` |

Engines before CK v2 read only `v2`; engines from CK v2 on read both. An engine below a
model's `minEngineVersion` refuses it (message 126, `CkModelRequiresNewerEngine`).
A published version lives in one root only. The rules, the
`minEngineVersion` values and their history are in the engine repository
(`octo-construction-kit-engine`), `docs/ck-publishing.md` (*Two catalog roots*) and
`docs/system-ck-models.md`.

**Shared-environment gate.** Never publish a `ck-models/v3/` model into a catalog test-2
reads, and never `ImportCk` it on a test-2 tenant, before **every** service of test-2 runs
an engine at or above the model's `minEngineVersion` (the CK v2 engine). Check
`minEngineVersion` in the compiled output (`./ck/out/ck-<name>.yaml`) before you publish;
when you cannot confirm the engine version of test-2's services, ask the environment's
owner instead of publishing. Never bump or republish a model to get past a refusal.

### Shortcut: skip the catalog entirely

`ckModelDependencies` resolution short-circuits when the tenant already has a
satisfying model version installed (source-verified:
`EnsureCkModelInstalledAsync` returns before any catalog lookup when
installed ≥ requested). So this works without any catalog publish:

The shared-environment gate above applies here too.

```bash
# on the target tenant's context
octo-cli -c ImportCk -f ./ck/out/ck-<name>.yaml -w
octo-cli -c InstallBlueprint -b <Name>-<Version>
```

Good for first experiments; publish to the shared catalog once others or other
tenants need the model.

## Blueprint → shared blueprint catalog

Catalog: `PrivateGitHubBlueprintCatalog` = a GitHub repository configured in the
asset repository, layout
`blueprints/v1/<letter>/<Name>/<major>/<Name>-<version>/{blueprint.yaml,seed-data/}`.

```bash
# one-time: GitHub token in ~/.octo-bpm/settings.json, same shape as for octo-ckc (not via -gt)
octo-bpm -c validateVersion -p ./blueprint/<Name>/<version> -cn PrivateGitHubBlueprintCatalog   # version honest?
octo-bpm -c publish -p ./blueprint/<Name>/<version> -c PrivateGitHubBlueprintCatalog
octo-bpm -c list                              # confirm the catalog entry
```

**Published blueprint versions are immutable.** Every content change — seed data,
`ValuesYaml`, `blueprint.yaml` — gets a new blueprint version; `validateVersion`
fails with `OCTO-BP100` when the content under an already-published version differs.
It cannot see a file that was deleted locally (a file that exists only in the published
version), so removing a file needs the version bump by your own discipline; a renamed
file shows up under its new name and is detected.
`publish` does not overwrite an existing version (it logs an error, see the
soft-fail note below); its `-f` (force/replace) is only for a local developer
catalog, never for a shared catalog that tenants install from.

There is NO ImportCk-style shortcut for blueprints — `InstallBlueprint` only
resolves from catalogs the asset-repo reads, so the blueprint must be published.

After publishing a **new blueprint id/version**, refresh the server-side blueprint
catalog index of the target asset repository. The index is read from GitHub Pages, so
wait until the Pages deployment of the publish has finished (about a minute) — a refresh
before that caches the old index. If `ListBlueprints` still lacks the new version,
refresh again:

```bash
octo-cli -c RefreshBlueprintCatalogs -cn PrivateGitHubBlueprintCatalog   # omit -cn for all catalogs
```

The refresh is always forced and needs no service restart (tenant role
`DataModelManagement`). `RefreshCatalogs` refreshes CK MODEL catalogs only. Never restart the asset
repository with kubectl on a shared cluster.

Scope of the cache: the **index** (which blueprint ids/versions exist) only;
`InstallBlueprint`/`UpdateBlueprint` fetch blueprint.yaml and seed data live from
GitHub Pages (≤1 min Pages deploy lag). A content change is a new version, so it
always needs the refresh before `UpdateBlueprint -tv <Name>-<NewVersion>`.

## App image → <registry>

```bash
# Registry reachable? Probe (registry CA trusted): curl -sI https://<registry>/v2/  -> 200 or 401
docker build -t <registry>/meshmakers/<app>:<tag> ./app
docker push <registry>/meshmakers/<app>:<tag>
```

- `<tag>` must equal the tag pinned in the blueprint seed's ValuesYaml
  (`image.tag`). Static semver tags (`0.1.0`) for app workloads — the rolling
  `main-latest` + `pullPolicy: Always` pattern is for core services only.
- Repository path convention: `meshmakers/<app-name>`.
- Do NOT set `image.privateRegistry` in the seed — the operator injects
  `<registry>` on the shared cluster (cluster values: `operator.imageRegistry`).
- Cluster nodes pull without per-pod imagePullSecrets (node-level containerd
  config / open internal registry). A locally built `linux/amd64` image is fine
  for an amd64 cluster; CI builds multi-arch via buildx.
- Re-pushing the SAME tag does not restart running pods — bump the tag (and the
  seed) or undeploy/redeploy the workload.

## The CI lane (recommended once the app stabilizes)

A CI pipeline in the app repository (for example Azure DevOps or GitHub Actions)
with steps for the image build and push, the CK and blueprint publish, the tool
installation and the build number.

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
pipeline, then on the tenant `RefreshCatalogs` (CK models) →
`RefreshBlueprintCatalogs` (every content change is a new blueprint version) →
`InstallBlueprint` (first install) or `UpdateBlueprint -tv <Name>-<NewVersion>`
(existing install) → `DeployDataFlow` → `DeployWorkload`.
