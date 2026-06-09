# Communication Operator — Internals Reference

Exhaustive detail for `octo-communication-operator`. The SKILL.md overview points here for the full config table, Helm builder mechanics, CI shape, and test coverage. Verify against source before relying on any specific value: operator C# in `src/CommunicationOperator/`, charts in `octo-helm-core/src/`.

## Solution Layout

```
Octo.CommunicationOperator.sln
└── src/CommunicationOperator/                Operator host (ASP.NET Core, Microsoft.NET.Sdk.Web)
    ├── Common/        DictionaryExtensions, K8sNaming, OperatorLog (LoggerMessage source-gen)
    ├── Controller/    HTTP controllers (CommunicationPool, Diagnostics)
    ├── Diagnostics/   IWorkloadDiagnosticsCollector (pod/event scraping)
    ├── Entities/      V1CommunicationPoolEntity (CRD-mapped)
    ├── Finalizer/     CommunicationPoolFinalizer
    ├── Helm/          IHelmProcessInvoker/HelmProcessInvoker, IHelmRunner/HelmRunner, HelmException
    ├── Models/        Pool, K8Pool, PoolDescriptor (DTO-side models)
    ├── Options/       OperatorOptions (configuration binding)
    ├── Reconcilers/   WorkloadReconciler, WorkloadContextValuesBuilder,
    │                  WorkloadOverrideYamlBuilder, WorkloadDeployWatcher
    ├── Services/      CommunicationPoolManager, OperatorHubService, PoolService,
    │                  CommunicationPoolKubernetesGateway, OperatorHubClientFactory,
    │                  DiagnosticsService
    ├── Webhooks/      CommunicationPoolValidator, CommunicationPoolMutator (admission webhooks)
    └── scripts/       (src/scripts/) kind cluster bootstrap + sample CRs

tests/CommunicationOperator.Tests/         Unit tests (TUnit + NSubstitute)
```

The CRD ships from the `octo-helm-core` `octo-mesh-crds` chart, not from this repo's build.

## Custom Resource

`V1CommunicationPoolEntity` — `[KubernetesEntity(Group = "octo-mesh.meshmakers.io", ApiVersion = "v1alpha1", Kind = "CommunicationPool")]`. Spec carries tenant identity, controller endpoint, and broker connection params. `Spec.PoolRtId` is the canonical identity (24-char lowercase hex MongoDB ObjectId of the controller-side `RtPool`); every derived k8s name is built from it via `K8sNaming.DnsName`. `Spec.PoolName` is an optional display name.

## OperatorOptions — Full Configuration Table

Bound from the `Operator` configuration section; every key is also an env var prefixed `OPERATOR__`. Nested options use double underscores (`OPERATOR__CLUSTERDEPENDENCIES__MONGODBHOST`).

| Option | Env var | Default | Purpose |
|--------|---------|---------|---------|
| `AutoManagePools` | `OPERATOR__AUTOMANAGEPOOLS` | `false` | Gates auto-creating/-deleting `CommunicationPool` CRs on `PoolDeployedAsync`/`PoolUndeployedAsync`. Central only. **Does not** gate the SignalR connection. |
| `WatchNamespace` | `OPERATOR__WATCHNAMESPACE` | empty (all namespaces) | Restricts the CR watcher to one namespace. Required when multiple operators share a cluster. Wired via `OperatorSettingsBuilder.WithNamespace()`. |
| `CommunicationControllerUri` | `OPERATOR__COMMUNICATIONCONTROLLERURI` | required when central | SignalR endpoint. Required in **both** modes for `OperatorHubService` to start; empty → hub service exits, `RegisterPoolAsync` no-ops. |
| `PoolNamespace` | `OPERATOR__POOLNAMESPACE` | `octo` | Namespace for auto-created CRs + broker secrets. Helm releases default here unless the chart overrides. |
| `BrokerHost` | `OPERATOR__BROKERHOST` | required when central | RabbitMQ host for workload pods. |
| `BrokerVirtualHost` | `OPERATOR__BROKERVIRTUALHOST` | `/` | RabbitMQ vhost. |
| `BrokerPort` | `OPERATOR__BROKERPORT` | `5672` | RabbitMQ port. |
| `BrokerUser` | `OPERATOR__BROKERUSER` | required when central | RabbitMQ user baked into `<tenantId>-<poolName>-octo-mesh-connection` secret. |
| `BrokerPassword` | `OPERATOR__BROKERPASSWORD` | required when central | RabbitMQ password. **Injected unconditionally** as `secrets.rabbitmq` whenever set (Tier-1 secret). |
| `InstancePrefix` | `OPERATOR__INSTANCEPREFIX` | none | Forwarded to workload pods via Helm values. |
| `AdapterIgnoreCertificateValidation` | `OPERATOR__ADAPTERIGNORECERTIFICATEVALIDATION` | `false` | Dev-only; forwarded to workload pods. |
| `ImagePullSecretName` | `OPERATOR__IMAGEPULLSECRETNAME` | none | Image-pull secret name injected into adapter pod specs when set. |
| `ImageRegistry` | `OPERATOR__IMAGEREGISTRY` | none | Private registry host projected into each workload's Helm values as `image.privateRegistry`. |
| `ReportingServiceUri` | `OPERATOR__REPORTINGSERVICEURI` | none | Cluster-internal reporting service URI → workload value `reportingServiceUri`. |
| `ClusterDependencies.MongodbHost` | `OPERATOR__CLUSTERDEPENDENCIES__MONGODBHOST` | none | → `clusterDependencies.mongodbHost`. |
| `ClusterDependencies.MongodbReplicaSet` | `OPERATOR__CLUSTERDEPENDENCIES__MONGODBREPLICASET` | none | → `clusterDependencies.mongodbReplicaSet`. |
| `ClusterDependencies.RabbitMqHost` | `OPERATOR__CLUSTERDEPENDENCIES__RABBITMQHOST` | none | → `clusterDependencies.rabbitMqHost`. |
| `ClusterDependencies.RabbitMqUser` | `OPERATOR__CLUSTERDEPENDENCIES__RABBITMQUSER` | none | → `clusterDependencies.rabbitMqUser`. |
| `ClusterDependencies.StreamDataHost` | `OPERATOR__CLUSTERDEPENDENCIES__STREAMDATAHOST` | none | CrateDB host → `clusterDependencies.streamDataHost`. |
| `ClusterDependencies.StreamDataUser` | `OPERATOR__CLUSTERDEPENDENCIES__STREAMDATAUSER` | none | CrateDB user → `clusterDependencies.streamDataUser`. |
| `Ingress.ClassName` | `OPERATOR__INGRESS__CLASSNAME` | none | → `ingress.className`. |
| `Ingress.ClusterIssuer` | `OPERATOR__INGRESS__CLUSTERISSUER` | none | cert-manager ClusterIssuer → `ingress.annotations["cert-manager.io/cluster-issuer"]`. |
| `Ingress.Tls` | `OPERATOR__INGRESS__TLS` | unset (chart default) | → `ingress.tls`. |
| `ClusterSecrets.MongodbUserPassword` | `OPERATOR__CLUSTERSECRETS__MONGODBUSERPASSWORD` | none | Tier-2 secret → `secrets.databaseUser` when `ReceivesClusterSecrets` true. |
| `ClusterSecrets.MongodbAdminPassword` | `OPERATOR__CLUSTERSECRETS__MONGODBADMINPASSWORD` | none | Tier-2 → `secrets.databaseAdmin` when flag true. |
| `ClusterSecrets.StreamDataPassword` | `OPERATOR__CLUSTERSECRETS__STREAMDATAPASSWORD` | none | Tier-2 → `secrets.streamDataPassword` when flag true. |

All `ClusterDependencies.*`, `ReportingServiceUri`, and `Ingress.*` values are optional and become the **lowest** precedence (context) layer — the workload's own `ValuesYaml` and structured overrides win. Edge operators usually leave the cloud-side dependency hosts empty so per-workload values supply local equivalents.

The RabbitMQ password is **not** in `ClusterSecrets` — it stays on `BrokerPassword` and is injected unconditionally because every adapter needs the broker. Per-workload public-ingress opt-in (`ingress.enabled=true` + top-level `publicUri`) comes from the workload's typed `IngressEnabled`/`Hostname` attributes via `WorkloadDeployedDto`; the cluster-wide `Ingress.*` defaults here are not overridable per workload.

For central deployment, the operator also needs RabbitMQ connectivity to receive tenant lifecycle events via the DistributedEventHub (configured via `Meshmakers.Octo.Services.Infrastructure`).

## Helm Layer Stack

| Layer | Type | Responsibility |
|-------|------|----------------|
| `Helm/HelmProcessInvoker` (`IHelmProcessInvoker`) | low-level | `System.Diagnostics.Process` wrapper around the `helm` binary on PATH. Captures stdout/stderr, masks `--username`/`--password` in the debug log line. On `OperationCanceledException` does `process.Kill(entireProcessTree: true)` (kubectl/registry helpers fork as children). |
| `Helm/HelmRunner` (`IHelmRunner`) | high-level | `EnsureRepoAsync` (idempotent `helm repo add --force-update` + `helm repo update`), `UpgradeInstallAsync` (`-f`, `--set`, `--atomic`), `UpgradeInstallDryRunAsync` (same minus `--atomic`, plus `--dry-run=server`), `UninstallAsync` (`--ignore-not-found`). Non-zero exit → `HelmException` with full stderr. Omits `--version` when the value is blank/whitespace. |
| `Reconcilers/WorkloadContextValuesBuilder` | builder | `OperatorOptions` + workload identity (`tenantId`, `adapterRtId` from `WorkloadRtId`) → `values-context.yaml`. Only set fields are projected; empty options → null/no layer. **No secrets.** |
| `Reconcilers/WorkloadOverrideYamlBuilder` | builder | `ValueOverride[]` → `values-overrides.yaml`. Secret entries → `valueFrom: secretKeyRef` envelope on `{release}-octo-secrets`; non-secret → literals; dotted paths → nested maps. |
| `Reconcilers/WorkloadReconciler` | orchestrator | `ReconcileSecretAsync` → `EnsureRepoAsync` (alias = short SHA-1 of repo URL, stable/idempotent) → write up to 3 values files (context → base → overrides) → `helm upgrade --install {tenant}-{workload} {alias}/{chart}` → temp cleanup. |

`WorkloadReconciler.ReleaseName` / `SecretName` / `RepoAlias` are deterministic helpers (`InternalsVisibleTo` for direct assertion). Release names: `{tenantId}-{workloadRtId}` (the 24-char hex runtime entity id, not `WorkloadName`), DNS-sanitised, ≤53 chars.

### Shared k8s naming (`Common/K8sNaming`)

- `K8sNaming.DnsName` — strict RFC-1123 subdomain segment (lowercase, `[a-z0-9-]`, collapsed dashes, ≤53 chars by default for Helm release-name parity).
- `K8sNaming.LabelValue` — laxer label alphabet (also `_` and `.`, `"unknown"` for empty, ≤63).

Both `WorkloadReconciler` and `CommunicationPoolManager` derive names from CK attributes (tenantId/poolName/workloadName) that may contain whitespace/uppercase. The original CK name is preserved as `octo-mesh.meshmakers.io/pool-name` / `.../workload-name` annotations.

## Webhooks

- `CommunicationPoolValidator` — requires `Spec.PoolRtId` to be 24-char lowercase hex (controller-side `RtPool` ObjectId). `PoolName` optional. An empty/malformed `PoolRtId` would otherwise surface only as a controller-side `FormatException` from `OperatorHub.RegisterPoolAsync`, leaving the CR stuck `Unregistered`.
- `CommunicationPoolMutator` — currently a no-op (`NoChanges()`).

## Docker Image

`src/CommunicationOperator/Dockerfile` downloads the official `helm` tarball from `get.helm.sh` (the baltocdn.com apt path was blocked on the CI pool). Helm version pinned via `HELM_VERSION` build-arg (default `v3.16.4`); multi-arch via Buildx `TARGETARCH`. `HELM_CONFIG_HOME`/`HELM_CACHE_HOME`/`HELM_DATA_HOME` set under `/operator/` so the non-root `operator-user` can write the repo cache.

## CI Pipeline

`devops-build/azure-pipelines.yml` runs explicit `Restore` → `Build` → `Test`, forwarding `OctoNugetPrivateServer` to **every** MSBuild step. Two non-obvious requirements:

1. `OctoNugetPrivateServer` must be on every MSBuild invocation. `Directory.Build.props` reads it to choose `OctoVersion` (`0.1.*` private feed when set, else `3.3.*` nuget.org) and `RestoreSources`. Missing it on build/test re-evaluates and falls back to nuget.org, dragging stale transitive packages (this is how a vulnerable RestSharp slipped in and tripped `NU1902` under `TreatWarningsAsErrors`).
2. Test step is `command: 'custom'` + `custom: 'test'` + `arguments: '--solution $(solutionFile) ... -- --report-trx --report-trx-filename test-results.trx'`. The standard `command: 'test'` + `projects:` form passes the project glob positionally, which Microsoft.Testing.Platform rejects on .NET 10. `--solution` enumerates every test project in the .sln, so adding a test project to the .sln is all that's needed to wire it into CI.

### Mandatory before commit (per repo conventions)

1. `dotnet build Octo.CommunicationOperator.sln -c DebugL` — zero warnings.
2. Test runner passes.
3. Docs (`README.md`, `CLAUDE.md`, `docs/DEPLOYMENT-MANAGEMENT-CONCEPT.md`) updated for any behavior/structure change.

## Full Unit-Test Coverage Map

Pure-logic + callback surfaces:
- `Common/DictionaryExtensionsTests` — label-selector formatting.
- `Webhooks/CommunicationPoolValidatorTests` — pool-rtId 24-char-hex rule (empty/too-short/uppercase/non-hex), poolName optional, enforced on update.
- `Webhooks/CommunicationPoolMutatorTests` — no-op invariant.
- `Finalizer/CommunicationPoolFinalizerTests` — success result + entity passthrough.
- `Controller/CommunicationPoolControllerTests` — `ReconcileAsync` happy/failure; `DeletedAsync` must **not** call `UpdateStatusAsync` (CR already gone → 404 → infinite KubeOps delete-retry).
- `Services/OperatorHubServiceTests` — `TenantCreatedAsync`/`TenantDeletedAsync` delegate to `ICommunicationPoolManager` and swallow exceptions.

Reconcilers + resource managers (mocked at the abstraction boundary):
- `Helm/HelmRunnerTests` — argument construction for repo-add (with/without auth), upgrade-install (files + `--set` escaping), dry-run (`--dry-run=server` present, `--atomic` absent, operation tag flags pre-flight failures), uninstall; non-zero exit → `HelmException`.
- `Diagnostics/WorkloadDiagnosticsCollectorTests` — `FormatPodStates`/`FormatWarningEvents`: ImagePullBackOff surfaced, benign waiting states (`ContainerCreating`/`PodInitializing`) suppressed, init-container failures tagged `initContainer`, terminated exit codes reported, unrelated events excluded, duplicates deduped.
- `Reconcilers/WorkloadReconcilerTests/DeployAsyncTests` — secret materialization (create/replace/cleanup-on-empty), repo registration with optional auth, upgrade with correct release/chart-ref/values-file count; dry-run **before** real install (`Received.InOrder`); dry-run failure skips real install; real-install failure invokes diagnostics; collector output merged into rethrown `HelmException.StdErr`; empty diagnostics → original rethrown; file ordering (context → base → overrides) when operator context set.
- `Reconcilers/WorkloadReconcilerTests/UndeployAsyncTests` — `helm uninstall`, secret-cleanup branches.
- `Reconcilers/WorkloadReconcilerTests/WorkloadOverrideYamlBuilderTests` — plain values, secret references, deep nesting, plaintext never in output for secret entries.
- `Reconcilers/WorkloadReconcilerTests/WorkloadContextValuesBuilderTests` — empty options → null, partial → only set keys, full → complete YAML with cluster deps + ingress annotations.
- `Services/CommunicationPoolManagerTests/` — auto-create/delete CR + broker secret, idempotency, CR/Secret content. Mocks `ICommunicationPoolKubernetesGateway`.
- `Services/OperatorHubServiceTests/ExecuteAsyncTests` — early-return paths, client creation, on-connect registration + per-tenant pool creation, clean shutdown. Mocks `IOperatorHubClientFactory`.
- `Services/OperatorHubServiceTests/ReverseSyncTests` — Cloud with owned pools sends report; edge does NOT; empty owned-pool list skips; `ReportDeployedStateAsync` failure logged not crashing.

**Not unit-tested** (thin pass-throughs, covered by E2E): `CommunicationPoolKubernetesGateway` itself, `OperatorHubClientFactory`.

## Related Documentation

- `docs/E2E-SMOKE-TEST.md` — manual central-operator smoke-test runbook.
- `docs/DEPLOYMENT-MANAGEMENT-CONCEPT.md` — application deployment management, version lifecycle, `ManuallyDeployed` state, reverse-sync contract.
- `octo-communication-controller-services/CLAUDE.md` — controller counterpart; the `/operatorHub` SignalR contract lives there.
- Monorepo root `CLAUDE.md` — global build configs, multi-tenancy, naming.
