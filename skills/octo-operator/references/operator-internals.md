# Communication Operator — Internals Reference

Exhaustive detail for `octo-communication-operator`. The SKILL.md overview points here for the full config table, Helm builder mechanics, CI shape, and test coverage. Verify against source before relying on any specific value: operator C# in `src/CommunicationOperator/`, charts in `octo-helm-core/src/`. The operator's agent docs (`CLAUDE.md` today, `AGENTS.md` + `docs/` once moved) explain the why; where they and the code disagree, the code wins.

## Solution Layout

```
Octo.CommunicationOperator.sln
└── src/CommunicationOperator/                Operator host (ASP.NET Core, Microsoft.NET.Sdk.Web)
    ├── Common/        DictionaryExtensions, K8sNaming, OperatorLog (LoggerMessage source-gen)
    ├── Controller/    DeploymentSiteController (KubeOps entity controller), DiagnosticsController (HTTP)
    ├── Diagnostics/   IWorkloadDiagnosticsCollector (pod/event scraping)
    ├── Entities/      V1DeploymentSiteEntity (CRD-mapped)
    ├── Finalizer/     DeploymentSiteFinalizer
    ├── Helm/          IHelmProcessInvoker/HelmProcessInvoker, IHelmRunner/HelmRunner, HelmException,
    │                  HelmFieldOwnershipConflict
    ├── Models/        DeploymentSite, K8Pool (DTO-side models)
    ├── Options/       OperatorOptions (configuration binding)
    ├── Reconcilers/   WorkloadReconciler, WorkloadContextValuesBuilder,
    │                  WorkloadOverrideYamlBuilder, WorkloadDeployWatcher
    ├── Services/      DeploymentSiteManager, DeploymentSiteService, OperatorHubService,
    │                  DeploymentSiteKubernetesGateway, OperatorHubClientFactory,
    │                  OperatorAccessTokenService, ConfigureOperatorAuthenticatorOptions,
    │                  DiagnosticsService
    ├── Watching/      WatchFallbackKubernetesClient, WatchModeState, WatchRefusal
    ├── Webhooks/      DeploymentSiteValidator, DeploymentSiteMutator (admission webhooks)
    └── sample/        sample DeploymentSite CRs and secrets
src/scripts/                                  kind cluster bootstrap + local test CR

tests/CommunicationOperator.Tests/         Unit tests (TUnit + NSubstitute) + kind E2E suites
```

The CRD ships from the `octo-helm-core` `octo-mesh-crds` chart, not from this repo's build.

## Custom Resource

`V1DeploymentSiteEntity` — `[KubernetesEntity(Group = "octo-mesh.meshmakers.io", ApiVersion = "v1", Kind = "DeploymentSite")]`, plural `deploymentsites`. Before AB#4924 the kind was `CommunicationPool` (version `v1alpha1`); the chart ships only `v1` now. The spec records only the operator's intent: `TenantId` and `DeploymentSiteRtId` (24-char lowercase hex MongoDB ObjectId of the controller-side deployment site). Every derived k8s name (CR name, broker secret, identity labels) is built from the rtId; the display name lives on the controller entity, not on the CR. Controller URI, broker settings and certificate toggles come from `OperatorOptions`, not from the CR. Status: `CommunicationStatus`.

## OperatorOptions — Full Configuration Table

Bound from the `Operator` configuration section; every key is also an env var prefixed `OPERATOR__`. Nested options use double underscores (`OPERATOR__CLUSTERDEPENDENCIES__MONGODBHOST`). The env names below are the ones the `octo-mesh-communication-operator` chart renders. Exception: the bootstrap read of `DevWebhookHost`/`DevWebhookPort` (dev builds) uses the `OCTO_` prefix (`OCTO_OPERATOR__DEVWEBHOOKHOST`).

| Option | Env var | Default | Purpose |
|--------|---------|---------|---------|
| `AutoManageDeploymentSites` | `OPERATOR__AUTOMANAGEDEPLOYMENTSITES` | `false` | Gates auto-creating/-deleting `DeploymentSite` CRs (and broker secrets) on `DeploymentSiteDeployedAsync`/`DeploymentSiteUndeployedAsync`, plus the reconnect fan-out. Central only. **Does not** gate the SignalR connection. |
| `WatchNamespace` | `OPERATOR__WATCHNAMESPACE` | empty (all namespaces) | Restricts the CR watcher to one namespace. Required when multiple operators share a cluster. Wired via `OperatorSettingsBuilder.WithNamespace()`. |
| `CommunicationControllerUri` | `OPERATOR__COMMUNICATIONCONTROLLERURI` | empty | SignalR endpoint. Required in **both** modes for `OperatorHubService` to start; empty → hub service exits, `RegisterDeploymentSiteAsync` no-ops. |
| `WorkloadCommunicationControllerUri` | `OPERATOR__WORKLOADCOMMUNICATIONCONTROLLERURI` | empty (= `CommunicationControllerUri`) | Controller address projected into workloads, when it differs from the operator's own (local kind with a host-run controller, AB#4967). |
| `DeploymentSiteNamespace` | `OPERATOR__DEPLOYMENTSITENAMESPACE` | `octo` | Namespace for auto-created CRs + broker secrets. Helm releases go here unless the chart overrides. |
| `PlatformNamespace` | — (not in the chart) | empty (= `DeploymentSiteNamespace`) | Namespace for adapter-pool releases (AB#4924). A distinct value disables the pool owner reference (cross-namespace owner references are forbidden). |
| `DeploymentSiteRegistrationRetrySeconds` | — (not in the chart) | `30` | Cadence of the registration retry loop (AB#4371); fractional allowed; `<= 0` disables. |
| `BrokerHost` / `BrokerVirtualHost` / `BrokerPort` | `OPERATOR__BROKERHOST` / `…VIRTUALHOST` / `…PORT` | empty / `/` / `5672` | RabbitMQ endpoint for workload pods. |
| `BrokerUser` | `OPERATOR__BROKERUSER` | none | RabbitMQ user baked into the per-site `…-octo-mesh-connection` secret. |
| `BrokerPassword` | `OPERATOR__BROKERPASSWORD` | none | RabbitMQ password. **Injected unconditionally** as `secrets.rabbitmq` whenever set. |
| `RootCaCertificate` | `OPERATOR__ROOTCACERTIFICATE` | none | PEM root CA from the chart's `secrets.rootCa`; injected unconditionally as plain `secrets.rootCa` (AB#4417). |
| `InstancePrefix` | `OPERATOR__INSTANCEPREFIX` | none | Forwarded to workload pods via Helm values. |
| `AdapterIgnoreCertificateValidation` | `OPERATOR__ADAPTERIGNORECERTIFICATEVALIDATION` | `false` | Dev-only; forwarded to workload pods. |
| `ImagePullSecretName` | `OPERATOR__IMAGEPULLSECRETNAME` | none | Image-pull secret name injected into workload pod specs when set. |
| `ImageRegistry` | `OPERATOR__IMAGEREGISTRY` | none | Private registry host projected into each workload's Helm values as `image.privateRegistry`. |
| `ReportingServiceUri` | `OPERATOR__REPORTINGSERVICEURI` | none | Cluster-internal reporting service URI → workload value `reportingServiceUri`. |
| `AuthUri` | `OPERATOR__AUTHURI` | none | Public identity issuer → workload value `authUri` (expected token issuer of secured trigger nodes). Not emitted when empty. |
| `AdditionalValidIssuers` | `OPERATOR__ADDITIONALVALIDISSUERS__<n>` | `[]` | Extra accepted issuer strings → `additionalValidIssuers` (split-horizon setups, AB#5232). |
| `ClusterDependencies.MongodbHost` / `MongodbReplicaSet` / `RabbitMqHost` / `RabbitMqUser` / `StreamDataHost` / `StreamDataUser` | `OPERATOR__CLUSTERDEPENDENCIES__<NAME>` | none | → `clusterDependencies.*` (context layer). |
| `ClusterDependencies.SystemDatabaseName` / `StreamDataSchemaInstancePrefix` / `TenantDatabasePrefix` | `OPERATOR__CLUSTERDEPENDENCIES__<NAME>` | none | Instance isolation; must mirror the core services of the same instance. Not emitted when empty. |
| `Ingress.ClassName` / `ClusterIssuer` / `Tls` / `Annotations` | `OPERATOR__INGRESS__<NAME>` (`…__ANNOTATIONS__<n>__NAME/__VALUE`) | none / unset | → `ingress.*`; `ClusterIssuer` becomes the `cert-manager.io/cluster-issuer` annotation. |
| `ClusterSecrets.MongodbUserPassword` / `MongodbAdminPassword` / `StreamDataPassword` | `OPERATOR__CLUSTERSECRETS__<NAME>` | none | Opt-in tier → `secrets.databaseUser` / `secrets.databaseAdmin` / `secrets.streamDataPassword` when `ReceivesClusterSecrets` is true. |
| `ClusterSecrets.SecretEncryptionKeys` / `SecretEncryptionActiveKeyId` / `SecretEncryptionLegacyV1Key` | `OPERATOR__CLUSTERSECRETS__SECRETENCRYPTION…` | none | Opt-in tier: SECRET-attribute key ring → `secrets.secretEncryption.*` (AB#5536). Never for adapter pools. |
| `IronOcrLicenseKey` | `OPERATOR__IRONOCRLICENSEKEY` | none | → `secrets.ironOcrLicenseKey`, only for charts in `ChartsReadingIronOcrLicense` (AB#5449). |
| `Dash0WebAuthToken` / `Dash0.Endpoint` / `Dash0.Dataset` / `Dash0.Environment` | `OPERATOR__DASH0…` | none | Browser telemetry for frontend charts: the token → `secrets.dash0WebAuthToken` only for charts in `ChartsReadingDash0WebAuthToken`; the non-secret context through `WorkloadContextValuesBuilder`. Unset = telemetry off. |
| `Authentication.IssuerUri` / `ClientId` / `ClientSecret` / `TenantId` | `OPERATOR__AUTHENTICATION__<NAME>` | none | The operator's own `/operatorHub` token (AB#5062). Without `ClientId` the connection stays anonymous. |
| `Helm.ForceConflicts` | `OPERATOR__HELM__FORCECONFLICTS` | `false` | Adds `--force-conflicts` to the real install (never to the dry run), AB#5325. Env only. |
| `ForceClassicWatch` | `OPERATOR__FORCECLASSICWATCH` | `false` | Start CR watches in classic mode (`resourceVersion=0`, no bookmarks), AB#6898. |
| `DevWebhookHost` / `DevWebhookPort` | `OCTO_OPERATOR__DEVWEBHOOKHOST` / `…PORT` | auto / `6001` | Dev webhook endpoint (DEBUG/DEBUGL builds). |

All `ClusterDependencies.*`, `ReportingServiceUri`, `AuthUri`, `AdditionalValidIssuers` and `Ingress.*` values are optional and become the **lowest** precedence (context) layer — the workload's own `ValuesYaml` and structured overrides win. Edge operators usually leave the cloud-side dependency hosts empty so per-workload values supply local equivalents.

The RabbitMQ password is **not** in `ClusterSecrets` — it stays on `BrokerPassword` and is injected unconditionally because every adapter needs the broker. Per-workload public-ingress opt-in (`ingress.enabled=true` + top-level `publicUri`) comes from the workload's typed `IngressEnabled`/`Hostname` attributes via `WorkloadDeployedDto`; the cluster-wide `Ingress.*` defaults here are not overridable per workload.

## Helm Layer Stack

| Layer | Type | Responsibility |
|-------|------|----------------|
| `Helm/HelmProcessInvoker` (`IHelmProcessInvoker`) | low-level | `System.Diagnostics.Process` wrapper around the `helm` binary on PATH. Captures stdout/stderr, masks `--username`/`--password` in the debug log line. On `OperationCanceledException` does `process.Kill(entireProcessTree: true)` (kubectl/registry helpers fork as children). |
| `Helm/HelmRunner` (`IHelmRunner`) | high-level | `EnsureRepoAsync` (idempotent `helm repo add --force-update` + `helm repo update`), `UpgradeInstallAsync` (`-f`, `--set`, `--rollback-on-failure`, optional `--force-conflicts`, optional `--description` = `octo-deploy:<fingerprint>` stamp), `UpgradeInstallDryRunAsync` (same minus `--rollback-on-failure` and `--force-conflicts`, plus `--dry-run=server`), `UninstallAsync` (`--ignore-not-found`), `GetLatestReleaseRevisionAsync` (`helm history … --max 1`), `GetInstalledChartVersionAsync` (`helm list --filter ^{release}$`). Non-zero exit → `HelmException` with full stderr. Omits `--version` when the value is blank/whitespace. |
| `Helm/HelmFieldOwnershipConflict` | parser | Recognises a server-side-apply field-ownership conflict in helm stderr (escaped and unescaped copies), names field paths and managers, distinguishes hand patches (`kubectl-*`) from the operator's own and `unknown` writers. |
| `Reconcilers/WorkloadContextValuesBuilder` | builder | `OperatorOptions` + workload identity (`tenantId`, `adapterRtId` from `WorkloadRtId`) → `values-context.yaml`. Only set fields are projected; empty options → null/no layer. **No secrets.** |
| `Reconcilers/WorkloadOverrideYamlBuilder` | builder | the workload's overrides (`ValueOverrideDto` list; `ValueOverride[]` on the CK entity) → `values-overrides.yaml`. Secret entries → `valueFrom: secretKeyRef` envelope on `{release}-octo-secrets`; non-secret → literals; dotted paths → nested maps. |
| `Reconcilers/WorkloadReconciler` | orchestrator | `DeployCoreAsync`: stamp check (reconciliation only) → `AppendClusterSecrets` → pool owner-reference lookup → `ReconcileSecretAsync` → `EnsureRepoAsync` (alias = short SHA-1 of repo URL) → write up to 3 values files (context → base → overrides) → `ResolveReplicaCountPinAsync` → `TryClearStaleHelmLockAsync` → `ResolveChartVersionAsync` → dry run → `helm upgrade --install {tenant}-{workload} {alias}/{chart}` → pool owner references on the Deployments → temp cleanup. `DeployAsync` wraps it with the single-flight logic. |

`WorkloadReconciler.ReleaseName` / `SecretName` / `RepoAlias` are deterministic helpers (`InternalsVisibleTo` for direct assertion). Release names: `{tenantId}-{workloadRtId}` (the 24-char hex runtime entity id, not `WorkloadName`), DNS-sanitised, ≤53 chars.

### Shared k8s naming (`Common/K8sNaming`)

- `K8sNaming.DnsName` — strict RFC-1123 subdomain segment (lowercase, `[a-z0-9-]`, collapsed dashes, ≤53 chars by default for Helm release-name parity).
- `K8sNaming.LabelValue` — laxer label alphabet (also `_` and `.`, `"unknown"` for empty, ≤63).

Both `WorkloadReconciler` and `DeploymentSiteManager` derive names from CK attributes that may contain whitespace/uppercase. The original CK name is preserved as `octo-mesh.meshmakers.io/pool-name` / `.../workload-name` annotations.

## Webhooks

- `DeploymentSiteValidator` — requires `spec.deploymentSiteRtId` to be a 24-char lowercase hex ObjectId (`^[a-f0-9]{24}$`). An empty/malformed id would otherwise surface only as a controller-side `FormatException` during registration, leaving the CR stuck `Unregistered`.
- `DeploymentSiteMutator` — currently a no-op (`NoChanges()`).

## Docker Image

`src/CommunicationOperator/Dockerfile` downloads the official `helm` tarball from `get.helm.sh`. Helm version pinned via `HELM_VERSION` build-arg (Helm 4; the reconciler relies on `--rollback-on-failure` and server-side apply); multi-arch via Buildx `TARGETARCH`. `HELM_CONFIG_HOME`/`HELM_CACHE_HOME`/`HELM_DATA_HOME` set under `/operator/` so the non-root `operator-user` can write the repo cache.

## CI Pipeline

`azure-pipelines.yml` at the repo root (templates from `octo-pipeline-templates`) runs explicit `Restore` → `Build` → `Test`, forwarding `OctoNugetPrivateServer` to **every** MSBuild step. Two non-obvious requirements:

1. Package versions come only from the pipeline: `Directory.Build.props` pins `999.0.0` for DebugL and `0.1.*` when `OctoNugetPrivateServer` is set; with neither, the `OctoVerifyVersionIsSet` target fails the build fast. A step without `OctoNugetPrivateServer` therefore breaks the build instead of falling back to public packages.
2. Test step is `command: 'custom'` + `custom: 'test'` + `--solution $(solutionFile) … -- --report-trx --report-trx-filename test-results.trx`. The standard `command: 'test'` + `projects:` form passes the project glob positionally, which Microsoft.Testing.Platform rejects on .NET 10. `--solution` enumerates every test project in the .sln, so adding a test project to the .sln is all that's needed to wire it into CI.

### Mandatory before commit (per repo conventions)

1. `dotnet build Octo.CommunicationOperator.sln -c DebugL` — zero warnings.
2. Test runner passes.
3. Docs (`README.md`, the agent docs, `docs/DEPLOYMENT-MANAGEMENT-CONCEPT.md`) updated for any behavior/structure change.

## Full Unit-Test Coverage Map

Paths relative to `tests/CommunicationOperator.Tests/`.

Pure-logic + callback surfaces:
- `Common/DictionaryExtensionsTests` — label-selector formatting.
- `Webhooks/DeploymentSiteValidatorTests` — rtId 24-char-hex rule (empty/too-short/uppercase/non-hex), enforced on update.
- `Webhooks/DeploymentSiteMutatorTests` — no-op invariant.
- `Finalizer/DeploymentSiteFinalizerTests` — success result + entity passthrough.
- `Controller/DeploymentSiteControllerTests` — `ReconcileAsync` happy/failure; `DeletedAsync` must **not** call `UpdateStatusAsync` (CR already gone → 404 → infinite KubeOps delete-retry).
- `Controller/DiagnosticsControllerTests` — loopback-only log-level endpoint (AB#5059).
- `Options/OperatorOptionsBindingTests` — env binding, incl. `Authentication` and `ForceClassicWatch`.

Helm, reconcilers and resource managers (mocked at the abstraction boundary):
- `Helm/HelmRunnerTests` — argument construction (`--description` only when set, `--force-conflicts` default off and never on the dry run, history and `helm list` parsing), repo-add (with/without auth), upgrade-install (files + `--set` escaping), dry-run (`--dry-run=server` present, `--rollback-on-failure` absent), uninstall; non-zero exit → `HelmException`.
- `Helm/HelmFieldOwnershipConflictTests` — verbatim helm stderr from real conflicts (AB#5325).
- `Diagnostics/WorkloadDiagnosticsCollectorTests` — `FormatPodStates`/`FormatWarningEvents`: ImagePullBackOff surfaced, benign waiting states suppressed, init-container failures tagged `initContainer`, terminated exit codes reported, unrelated events excluded, duplicates deduped.
- `Reconcilers/WorkloadDeployWatcherTests` — progress snapshots during the install.
- `Reconcilers/WorkloadReconcilerTests/DeployAsyncTests` — secret materialization, repo registration, upgrade call; dry-run **before** real install; dry-run failure skips the install; diagnostics merged into the rethrown `HelmException`; values-file order; hibernation pin.
- `…/DuplicateDispatchTests` (AB#6471), `…/ReconcileChartVersionTests` (AB#4955), `…/ReplicaCountPinTests` (AB#5350), `…/StaleHelmLockTests` (AB#4894), `…/ScaleAsyncTests` (AB#4917), `…/PlatformNamespaceTests` + `…/DeploymentSiteOwnerReferenceTests` (AB#4924), `…/AppendClusterSecretsTests` (all secret gates incl. pools).
- `…/UndeployAsyncTests` — `helm uninstall`, secret-cleanup branches.
- `…/WorkloadOverrideYamlBuilderTests` — plain values, secret references, deep nesting, plaintext never in output for secret entries.
- `…/WorkloadContextValuesBuilderTests` — empty options → null, partial → only set keys, full → complete YAML.
- `Services/DeploymentSiteManagerTests/` — auto-create/delete CR + broker secret, idempotency, CR/Secret content. Mocks `IDeploymentSiteKubernetesGateway`.
- `Services/DeploymentSiteServiceTests` — register/unregister, soft failure on `HubException`.
- `Services/OperatorHubServiceTests/` — `ExecuteAsyncTests` (early-return paths, client creation, on-connect registration), `DeploymentSiteDeployedAsyncTests` / `DeploymentSiteUndeployedAsyncTests`, `WorkloadDeployedAsyncTests`, `ScaleWorkloadTests`, `RegistrationRetryTests` (AB#4371, AB#8160), `ReverseSyncTests` (central sends, edge does not, empty skips, failure logged), `InactiveConnectionTests`, `RegisteredLogTests`. Mocks `IOperatorHubClientFactory`.
- `Services/OperatorAccessTokenServiceTests`, `Services/OperatorHubClientFactoryTests` — operator hub token (AB#5062).
- `Watching/WatchFallbackKubernetesClientTests`, `Watching/WatcherChainTests` — fake API server with the measured `RequestWatchProgress` matrix, real KubeOps `ResourceWatcher` (AB#6898).

**Kind E2E** (skip unless `OCTO_OPERATOR_E2E_KUBECONTEXT` is set): `E2E/AdapterPoolKindE2ETests` (helm substituted), `E2E/ScaledWorkloadRedeployKindE2ETests` and `E2E/ControllerRestartRedispatchKindE2ETests` (real helm ≥ 4); `OCTO_OPERATOR_E2E_LEGACY=1` only prints the redispatch outcome.

**Not unit-tested** (thin pass-through, covered by E2E): `DeploymentSiteKubernetesGateway` itself.

## Related Documentation

- The operator's agent docs (`CLAUDE.md`, later `AGENTS.md` + `docs/`) — one section per behaviour named in SKILL.md.
- `docs/E2E-SMOKE-TEST.md` — manual central-operator smoke-test runbook.
- `docs/DEPLOYMENT-MANAGEMENT-CONCEPT.md` — application deployment management, version lifecycle, reverse-sync contract.
- `octo-communication-controller-services/CLAUDE.md` — controller counterpart; the `/operatorHub` SignalR contract lives there.
- Monorepo root `CLAUDE.md` — global build configs, multi-tenancy, naming.
