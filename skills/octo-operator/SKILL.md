---
name: octo-operator
description: Use this skill for developing and operating the OctoMesh Communication Operator — the .NET 10 KubeOps Kubernetes operator that watches CommunicationPool CRDs, connects to the Communication Controller over SignalR (/operatorHub), and runs helm upgrade/uninstall for Adapter and Application workloads. Covers edge vs central deployment modes, the Helm values layering model (context < base < overrides), secret injection tiers, CRD generation, the TUnit + Microsoft.Testing.Platform test workflow on .NET 10, and the local kind cluster developer loop. Also covers the octo-helm-core chart repository (octo-mesh, octo-mesh-crds, octo-mesh-communication-operator, octo-mesh-schema-provider, octo-mesh-demo-app). Trigger on communication operator, KubeOps, CommunicationPool, CRD, CRD generation, helm chart, helm upgrade, WorkloadReconciler, operatorHub, edge deployment, central deployment, octo-helm-core, kind cluster, workload deployment, ICommunicationPoolKubernetesGateway, IOperatorHubClientFactory.
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/octo-operator/references/*)"
---

# OctoMesh Communication Operator

## Purpose

Developer-facing skill for the **Octo Communication Operator** (`octo-communication-operator`) and its companion chart repo (`octo-helm-core`). It provides the architecture map, key testing seams, the Helm values model, the CRD-generation workflow, and the local kind developer loop so you can extend or debug the operator without reading the full repo CLAUDE.md cold.

**Repos:**
- `C:\dev\meshmakers\octo-communication-operator` — the operator (.NET 10, KubeOps).
- `C:\dev\meshmakers\octo-helm-core` — the official Helm charts (CRDs, operator, core services, demo app).

**Cross-references:**
- `octo-devtools` skill — owns the local kind bring-up cmdlets (`Install-OctoKubernetes`, `Deploy-OctoOperator`, `Get-OctoKubernetesStatus`, `Uninstall-OctoKubernetes`). Do **not** duplicate them here; route there.
- `octo-agent` skill — debugging/build-chain investigation (DebugL NuGet, service health).

**Verify-before-claim:** confirm CLI/cmdlet behavior against source before asserting it — operator C# in `src/CommunicationOperator/`, chart YAML in `octo-helm-core/src/`, cmdlets in `octo-tools/modules/*.psm1`.

## What the Operator Is

A Kubernetes operator built on the **KubeOps** framework (`dotnet-operator-sdk`). It:

1. Watches `CommunicationPool` custom resources (CRD group `octo-mesh.meshmakers.io`, version `v1alpha1`, kind `CommunicationPool`; the C# entity is `V1CommunicationPoolEntity`).
2. Connects to the Communication Controller's `/operatorHub` SignalR hub (always, when a controller URI is configured — see modes below).
3. On `WorkloadDeployedAsync` events, runs `helm upgrade --install` per **Adapter** and **Application** workload; on `WorkloadUndeployedAsync`, runs `helm uninstall`.

There is **no raw-K8s `AdapterReconciler` path anymore** — every Adapter and Application is deployed exclusively as a Helm release via `WorkloadReconciler`.

The CRD itself is **not** generated in this repo's output by default; it ships from the `octo-mesh-crds` chart in `octo-helm-core`. See [CRD Generation](#crd-generation-workflow).

## Deployment Modes

The operator runs in two modes, distinguished by `OPERATOR__AUTOMANAGEPOOLS` and where it runs.

| | **Edge** (`AutoManagePools=false`) | **Central** (`AutoManagePools=true`) |
|---|---|---|
| Runs | On a remote edge cluster | Alongside the Controller in the same cluster |
| `CommunicationPool` CRs | Managed manually / by an external system | Auto-created/-deleted on `TenantCreated` / `TenantDeleted` |
| SignalR `/operatorHub` connection | **Still runs** (gated by `CommunicationControllerUri`, not by this flag) | Runs |
| `WatchNamespace` | Required when several operators share one cluster (one per target controller) so they don't race on CRs | Usually cluster-wide |
| Reverse-sync on reconnect | Skipped (controller rejects edge with `HubException`) | Sends `ReportDeployedStateAsync` for owned pools |

**CRITICAL — the flag is narrow:** `AutoManagePools` gates **only** the side effect of auto-creating/-deleting `CommunicationPool` CRs and broker secrets. The SignalR connection, pool register/unregister round-trip, and the `WorkloadDeployedAsync` → `helm` path run in **both** modes whenever `OPERATOR__COMMUNICATIONCONTROLLERURI` is set. A previous early-return on `!AutoManagePools` caused edge pools to show as `Unregistered` forever. When `CommunicationControllerUri` is empty, `OperatorHubService` logs a warning and exits, and `RegisterPoolAsync` becomes a no-op — the CR reconciles locally but the controller never sees the pool.

For multiple edge operators on one cluster, each must set `OPERATOR__WATCHNAMESPACE`.

## Reconciliation Flow

1. A `CommunicationPool` CR is created (manually, or by `OperatorHubService` when central).
2. `PoolService` registers the pool with the Controller via the `PoolHub` SignalR client.
3. The Controller fans out `WorkloadDeployedAsync` on `/operatorHub` per Adapter/Application.
4. `WorkloadReconciler` materializes secret-flagged values into an operator-owned `Secret`, ensures the chart repo, then runs `helm upgrade --install` (preceded by a dry-run pre-flight — see below).
5. On pool deletion, matching `WorkloadUndeployedAsync` events trigger `helm uninstall` per release.

**Soft-failure on unregister:** `PoolService.UnRegisterPoolAsync` (from `CommunicationPoolController.DeletedAsync`) treats any `HubException` from the controller as a soft failure — logs only. The CR is already gone when `DeletedAsync` fires and the tenant may no longer exist controller-side; re-throwing would trap the entity in the KubeOps retry queue forever. The local connection is stopped and the pool removed regardless.

## Helm Values Layering Model

`WorkloadReconciler` writes up to **three** values files to a temp dir and passes them via `-f` in this order (Helm's later `-f` wins, so order = precedence, lowest → highest):

| File | Source builder | Precedence |
|------|----------------|------------|
| `values-context.yaml` | `WorkloadContextValuesBuilder` — operator's own `OperatorOptions` (cluster Mongo/RabbitMQ/CrateDB hosts, reporting URI, instance prefix, ingress defaults) + workload identity (`tenantId`, `adapterRtId`) | lowest |
| `values-base.yaml` | the workload's own `ValuesYaml` from the CK entity | middle |
| `values-overrides.yaml` | `WorkloadOverrideYamlBuilder` — structured `ValueOverride[]` from the Studio form | highest |

`WorkloadContextValuesBuilder` projects **only** the fields that are set — an edge operator with an empty DTO context passes no context layer at all. **Secrets are deliberately not handled in the context builder**; they flow through `WorkloadOverrideYamlBuilder` and the per-release Secret. Secret-flagged override entries become a `valueFrom: secretKeyRef` envelope pointing at the operator-owned `{release}-octo-secrets` Secret; non-secret entries are literal values; dotted paths (e.g. `oauth.clientSecret`) become nested maps.

**Release name:** `{tenantId}-{workloadRtId}`, DNS-sanitised via `K8sNaming.DnsName` and truncated to Helm's 53-char limit. The runtime entity id (24-char lowercase hex) is used — not the user-facing `WorkloadName` — so renaming the workload in Studio does not orphan the helm release. `WorkloadReconciler.ReleaseName` / `SecretName` / `RepoAlias` are the deterministic helpers (exposed to tests via `InternalsVisibleTo`).

**Empty `version`:** `UpgradeInstallAsync` omits `--version` when blank so helm picks the newest tag — the contract for `System.Communication.MainLatest` on dev/test clusters. Pass a non-blank value to pin a chart.

Full builder mechanics and the `IHelmRunner` / `IHelmProcessInvoker` argument contracts are in `references/operator-internals.md`.

## Secret Injection Tiers

Before the override builder runs, `WorkloadReconciler` calls `AppendClusterSecrets` with **two distinct tiers** — this is a foot-gun, get it right:

1. **`secrets.rabbitmq`** (from `OperatorOptions.BrokerPassword`) — injected **UNCONDITIONALLY** whenever `BrokerPassword` is set. RabbitMQ is the controller↔adapter command bus; every adapter needs it. Gating this behind the cluster-secrets opt-in previously broke pure edge adapters (Modbus/Loxone) that failed the chart's mandatory `secrets.rabbitmq` check.
2. **Data-store secrets** (`secrets.databaseUser`, `secrets.databaseAdmin`, `secrets.streamDataPassword`, from `OperatorOptions.ClusterSecrets.*`) — injected **only** when the workload's `WorkloadDeployedDto.ReceivesClusterSecrets` flag is true (set by the controller from the Adapter CK entity's `ReceivesClusterSecrets` attribute). Pure edge adapters leave this false; the chart's `features.mongo` / `features.streamData` gates then skip the matching env blocks.

Injected entries are **prepended** so any entity-supplied override on the same path still wins, then flow through the normal secret pipeline into `{release}-octo-secrets`. Each adapter chart's `secrets.*` block must accept both plaintext strings (legacy) and `valueFrom` maps — see the `octo-mesh.secretEnv` helper in `octo-mesh-adapter` / `octo-eda-adapter` templates.

## Pre-flight, Watcher, Cancellation

Three mechanisms surface the real failure reason behind `helm upgrade --install --atomic` (which otherwise collapses everything into one opaque `context deadline exceeded` stderr line):

- **Pre-flight dry-run** (`UpgradeInstallDryRunAsync`, `--dry-run=server`, no `--atomic`) runs before the real install in `WorkloadReconciler.DeployAsync`. Admission webhooks, OpenAPI schema validation, and RBAC run server-side without creating resources, catching schema/Gatekeeper/RBAC errors in <2s. On failure it throws `HelmException` and the real install is skipped.
- **Live Deploy Watcher** (`WorkloadDeployWatcher`) polls `IWorkloadDiagnosticsCollector.CollectAsync` every ~3s during the real install and pushes non-empty, changed snapshots to the controller via `ReportWorkloadDeploymentProgressAsync` (state stays `Pending` — helm may still recover). Closes the 5-minute gap before the post-failure collector runs. Older controllers reject the new hub method with `HubException`; the service logs one warning and degrades silently.
- **Post-failure diagnostics** (`IWorkloadDiagnosticsCollector`) scrapes pod container statuses and namespace `Warning` events on `HelmException`, merging the result into the rethrown exception's stderr. Events outlive pods, so `ImagePullBackOff` / `FailedScheduling` / `FailedMount` are caught even after atomic rollback.

**Cancellable deploys:** `WorkloadReconciler._inFlightDeploys` tracks running deploys by release. `UndeployAsync` cancels an in-flight deploy's CTS, waits a 2s grace for atomic rollback, then `helm uninstall --ignore-not-found`. Cancellation works end-to-end only because `HelmProcessInvoker.InvokeAsync` does `process.Kill(entireProcessTree: true)` on cancel — `WaitForExitAsync(ct)` alone leaves helm holding the release lock.

Reconciler exceptions are **logged but not propagated** to the hub — one bad workload must not crash the SignalR connection.

## Reverse-Sync on Reconnect

After re-registering owned CRs on reconnect, a **central** operator (`AutoManagePools=true`) calls `IOperatorHub.ReportDeployedStateAsync(reports)` to restore `DeploymentState=Deployed` on pools whose state drifted while offline. Two coupled paths run it: **bulk on reconnect** (`OperatorHubService.onReconnect`, covers controller-restart) and **per-pool on register** (`PoolService.RegisterPoolAsync`, covers operator-restart race where KubeOps repopulates `_pools` after the bulk snapshot). Per-pool is idempotent (restore-only-when-changed). Edge operators skip it (controller rejects them); empty owned-pool list skips it; call failure is logged, not propagated. Workloads are **not yet** reverse-synced (no persistent helm-release→workload-rtId map survives a pod restart). See `docs/DEPLOYMENT-MANAGEMENT-CONCEPT.md` for the contract.

## Key Testing Seams

The operator is built to be testable at abstraction boundaries, not against the k8s SDK. Mock these:

| Seam (interface) | Replaces | What it abstracts |
|------------------|----------|-------------------|
| `ICommunicationPoolKubernetesGateway` | direct `IKubernetes` calls in `CommunicationPoolManager` | Six methods: `CommunicationPoolExistsAsync`, `CreateCommunicationPoolAsync`, `DeleteCommunicationPoolAsync`, `SecretExistsAsync`, `CreateSecretAsync`, `DeleteSecretAsync`. All k8s-SDK quirks (404→false, CRD group/version/plural constants) live in `CommunicationPoolKubernetesGateway`. **Add new k8s calls here — never reach back into `IKubernetes` from elsewhere.** |
| `IOperatorHubClientFactory` | `new OperatorHubClient(...)` in `OperatorHubService.ExecuteAsync` | Produces an `IOperatorHubClient` (SDK type). Mock it to substitute the SignalR client. Prod wiring in `OperatorHubClientFactory` (singleton). |
| `IHelmRunner` / `IHelmProcessInvoker` | the `helm` binary | High-level operations / low-level process wrapper. |
| `IWorkloadDiagnosticsCollector` | k8s pod/event scraping | Pure formatters `FormatPodStates` / `FormatWarningEvents` exposed via `InternalsVisibleTo`. |

**Test sync point for `OperatorHubService`:** use `client.When(c => c.EnableReconnect(...)).Do(_ => tcs.TrySetResult())` — once `EnableReconnect` ran, the connect callback finished and the service is parked in `Task.Delay(Infinite, ...)`. Asserting earlier races.

`CommunicationPoolKubernetesGateway` itself and `OperatorHubClientFactory` are **not** unit-tested (thin pass-throughs, covered by E2E).

## Test Conventions (.NET 10 / TUnit / MTP)

**Framework:** TUnit (`[Test]` attribute, `Assert.That(...).IsXxx(...)` fluent API) + NSubstitute. Tests mirror the source folder structure; namespaces `Meshmakers.Octo.Communication.Operator.Tests.<Area>`.

**CRITICAL — .NET 10 uses Microsoft.Testing.Platform, not VSTest.** The legacy VSTest path is rejected. Two pieces opt in: `global.json` at the repo root sets `"test": { "runner": "Microsoft.Testing.Platform" }`, and the test csproj references `Microsoft.Testing.Extensions.TrxReport`. Under MTP, the project/solution is a **flag** (`--project`/`--solution`, not positional), and reporter/filter args go **after `--`**.

Verified commands (run from the repo root; build only ever in **DebugL**):

| Command | Use |
|---------|-----|
| `dotnet build Octo.CommunicationOperator.sln -c DebugL` | Build (zero warnings — `TreatWarningsAsErrors=true`) |
| `dotnet test --solution Octo.CommunicationOperator.sln -c DebugL -- --report-trx --report-trx-filename test-results.trx` | **Canonical** — same form the Azure Pipeline runs |
| `dotnet run --project tests/CommunicationOperator.Tests/CommunicationOperator.Tests.csproj -c DebugL --no-build` | Quick dev form (no TRX, no rebuild) |
| `dotnet run --project tests/CommunicationOperator.Tests/CommunicationOperator.Tests.csproj -c DebugL --no-build -- --treenode-filter "/*/*/CommunicationPoolValidatorTests/*"` | Run one test class |

Test-project gotchas: `ThrowsAsync(...)` (not `Throws(...)`) for `Task`-returning substitutes (`NS5003` is an error); implement `IDisposable` + dispose any disposable SUT (`TUnit0023`); inject options with fully-qualified `Microsoft.Extensions.Options.Options.Create(new OperatorOptions { ... })`; set `<EnablePreviewFeatures>true</EnablePreviewFeatures>` (KubeOps APIs are `[RequiresPreviewFeatures]`). Target framework `net10.0`, three configs `Debug`/`Release`/`DebugL`.

## CRD Generation Workflow

The CRD is shipped from `octo-helm-core` (`octo-mesh-crds` chart), not from this repo's build output. To regenerate operator + CRD YAML into `config/` (run from **`src/CommunicationOperator/`**, where `install.ps1` lives):

```bash
# Read-only generation — writes YAML manifests to ./config, clears stale output.
dotnet kubeops g op meshmakers-octo-communication-operator ./CommunicationOperator.csproj --out config --clear-out
```

This is a **codegen** command (writes files under `config/`), not a cluster mutation. Apply with `kubectl apply -k config/install` only deliberately on a dev cluster. When the CRD schema changes, propagate the generated CRD into the `octo-mesh-crds` chart in `octo-helm-core`.

## Local Kind Developer Loop

The full kind bring-up is owned by **octo-tools** cmdlets — route to the `octo-devtools` skill for these; do not re-implement. Verified entry points (from `octo-tools/modules/*.psm1`):

| Cmdlet | Effect | Safety |
|--------|--------|--------|
| `Install-OctoKubernetes` | Creates kind cluster + `octo-mesh-crds` chart + namespaces + in-cluster infra + ingress-nginx/cert-manager, then deploys the operator. Idempotent; refuses while docker-compose infra is up (port clash). | **Mutating** (creates a cluster) |
| `Deploy-OctoOperator` | (Re)deploys the operator standalone from the dev registry (`:main-latest` by default) via the `octo-mesh-communication-operator` chart, generating self-signed webhook certs. | **Mutating** |
| `Get-OctoKubernetesStatus` | Shows pods, Helm releases, host-port reachability. | Read-only |
| `Uninstall-OctoKubernetes` | Deletes the kind cluster and its data. | **Destructive** |

In-repo helpers (run via PowerShell): `src/scripts/Create-KindTestCluster.ps1` (+ `Remove-KindTestCluster.ps1`), and `start-operator.ps1` at the repo root runs a locally-built operator in **central mode** on ports 5022/5023 (`ASPNETCORE_ENVIRONMENT=Development`). It is intentionally **not** named `octo-start.ps1` so `Start-Octo` does not auto-launch it.

In DEBUG/DEBUGL builds the operator auto-picks the first non-loopback IPv4 for its dev webhook endpoint and logs it (`Dev webhook endpoint: https://192.168.x.y:6001`). Override with `Operator:DevWebhookHost`/`Port` in `appsettings.Development.json` or `OCTO_OPERATOR__DEVWEBHOOKHOST`/`PORT`.

Manual E2E runbook: `docs/E2E-SMOKE-TEST.md` (uses `Install-OctoKubernetes`, `Start-Octo`, `start-operator.ps1`).

## octo-helm-core Charts

`octo-helm-core` is the official Helm chart repo, **published to `https://meshmakers.github.io/charts`** (GitHub Pages). Add it with `helm repo add meshmakers https://meshmakers.github.io/charts`.

Charts live under `src/<chart>/` (each has its own `Chart.yaml` and `values.yaml`):

| Chart | Purpose |
|-------|---------|
| `octo-mesh` | Core services (identity, asset-repo, bot, comm-controller, report, admin panel, AI services). Installed centrally, multi-tenant. **Main values.yaml a developer edits: `src/octo-mesh/values.yaml`.** |
| `octo-mesh-crds` | CRDs required by the Communication Operator (the `CommunicationPool` CRD). |
| `octo-mesh-communication-operator` | The operator deployment (the chart `Deploy-OctoOperator` installs). |
| `octo-mesh-schema-provider` | Schema-provider application chart (`type: application`). |
| `octo-mesh-demo-app` | Demo application chart. |

Adapter charts (`octo-mesh-adapter`, `octo-eda-adapter`) now live in their **own** adapter repos and publish from there, not from `octo-helm-core`.

## References

- `references/operator-internals.md` — `OperatorOptions` full config table (env-var keys, central vs edge requirements), Helm builder mechanics, `IHelmRunner`/`IHelmProcessInvoker` argument contracts, CI pipeline shape, solution layout, and the full unit-test coverage map.
