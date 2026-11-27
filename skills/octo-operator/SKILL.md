---
name: octo-operator
description: "Use this skill for developing and operating the OctoMesh Communication Operator — the .NET 10 KubeOps Kubernetes operator that watches DeploymentSite custom resources, connects to the Communication Controller over SignalR (/operatorHub), and runs helm upgrade/uninstall/scale for Adapter, Application and adapter-pool workloads. Covers edge vs central modes, the Helm values layering (context < base < overrides), secret injection tiers, deploy recovery (chart-version keep, replica pin, field-ownership conflicts, stale Helm locks, idempotent dispatch), watch fallback, operator hub authentication, CRD generation, TUnit + Microsoft.Testing.Platform tests and the local kind loop. Also covers the octo-helm-core charts. Trigger on communication operator, KubeOps, DeploymentSite, CommunicationPool (old name), CRD, helm chart, helm upgrade, WorkloadReconciler, operatorHub, edge deployment, central deployment, adapter pool, octo-helm-core, kind cluster, workload deployment, IDeploymentSiteKubernetesGateway, IOperatorHubClientFactory."
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/octo-operator/references/*)"
---

# OctoMesh Communication Operator

## Purpose

Developer-facing skill for the **Octo Communication Operator** (`octo-communication-operator`) and its companion chart repo (`octo-helm-core`). It provides the architecture map, the deploy-recovery behaviour, key testing seams, the Helm values model, the CRD-generation workflow, and the local kind developer loop so you can extend or debug the operator without reading the full repo docs cold.

**Repos** (siblings in the OctoMesh monorepo checkout):
- `octo-communication-operator` — the operator (.NET 10, KubeOps). Its agent docs are the source of truth for every section below: `CLAUDE.md` today, `AGENTS.md` + `docs/` once they move there. This skill names the section to read; it does not copy it.
- `octo-helm-core` — the official Helm charts (CRDs, operator, core services, demo app).

**Cross-references:**
- `octo-devtools` skill — owns the local kind bring-up cmdlets (`Install-OctoKubernetes`, `Deploy-OctoOperator`, `Get-OctoKubernetesStatus`, `Uninstall-OctoKubernetes`). Do **not** duplicate them here; route there.
- `octo-agent` skill — debugging/build-chain investigation (DebugL NuGet, service health).
- `octo-logs` skill — operator and workload logs of a deployed cluster.

**Verify-before-claim:** confirm behaviour against source before asserting it — operator C# in `src/CommunicationOperator/`, chart YAML in `octo-helm-core/src/`, cmdlets in `octo-tools/modules/*.psm1`. Where the operator's `CLAUDE.md` and the code disagree (it still says `v1alpha1` and `AutoManagePools` in places), the code wins.

## What the Operator Is

A Kubernetes operator built on the **KubeOps** framework (`dotnet-operator-sdk`). It:

1. Watches `DeploymentSite` custom resources (CRD `deploymentsites.octo-mesh.meshmakers.io`, group `octo-mesh.meshmakers.io`, version `v1`, kind `DeploymentSite`; the C# entity is `V1DeploymentSiteEntity` with spec `TenantId` + `DeploymentSiteRtId` and status `CommunicationStatus`). The kind was called `CommunicationPool` before AB#4924; that name survives only in comments of `src/CommunicationOperator/sample/inst.yaml` and `src/scripts/test-cluster-deployment-site-local.yaml`.
2. Connects to the Communication Controller's `/operatorHub` SignalR hub (always, when a controller URI is configured — see modes below).
3. On `WorkloadDeployedAsync` events, runs `helm upgrade --install` per **Adapter**, **Application** and **adapter pool** workload; on `WorkloadUndeployedAsync`, runs `helm uninstall`; on `ScaleWorkloadAsync`, patches the replica count without helm.

There is **no raw-K8s `AdapterReconciler` path anymore** — every workload is deployed exclusively as a Helm release via `WorkloadReconciler`.

The CRD itself is **not** generated in this repo's output by default; it ships from the `octo-mesh-crds` chart in `octo-helm-core`. See [CRD Generation](#crd-generation-workflow).

## Deployment Modes

The operator runs in two modes, distinguished by `OperatorOptions.AutoManageDeploymentSites` (`OPERATOR__AUTOMANAGEDEPLOYMENTSITES`) and where it runs.

| | **Edge** (`AutoManageDeploymentSites=false`) | **Central** (`AutoManageDeploymentSites=true`) |
|---|---|---|
| Runs | On a remote edge cluster | Alongside the Controller in the same cluster |
| `DeploymentSite` CRs | Managed manually / by an external system | Auto-created/-deleted on the controller's `DeploymentSiteDeployedAsync` / `DeploymentSiteUndeployedAsync` broadcasts (CR + broker secret, via `DeploymentSiteManager`) |
| SignalR `/operatorHub` connection | **Still runs** (gated by `CommunicationControllerUri`, not by this flag) | Runs |
| `WatchNamespace` | Required when several operators share one cluster (one per target controller) so they don't race on CRs | Usually cluster-wide |
| Reverse-sync on reconnect | Skipped (controller rejects edge with `HubException`) | Sends `ReportDeployedStateAsync` for owned sites |

**CRITICAL — the flag is narrow:** `AutoManageDeploymentSites` gates **only** the side effect of auto-creating/-deleting `DeploymentSite` CRs and broker secrets (and the reconnect fan-out of `RegisterOperatorAsync`). The SignalR connection, the site register/unregister round-trip, and the `WorkloadDeployedAsync` → `helm` path run in **both** modes whenever `OPERATOR__COMMUNICATIONCONTROLLERURI` is set. A previous early-return on the flag caused edge sites to show as `Unregistered` forever. When `CommunicationControllerUri` is empty, `OperatorHubService` logs a warning and exits, and `IOperatorHubInvoker.RegisterDeploymentSiteAsync` becomes a no-op — the CR reconciles locally but the controller never sees the site.

For multiple edge operators on one cluster, each must set `OPERATOR__WATCHNAMESPACE`.

## Reconciliation Flow

1. A `DeploymentSite` CR is created (manually, or by `OperatorHubService` when central).
2. `DeploymentSiteController.ReconcileAsync` → `DeploymentSiteService` registers the site with the Controller over the operator hub (`IOperatorHubInvoker.RegisterDeploymentSiteAsync`).
3. The Controller fans out `WorkloadDeployedAsync` on `/operatorHub` per workload.
4. `WorkloadReconciler` materializes secret-flagged values into an operator-owned `Secret`, ensures the chart repo, then runs `helm upgrade --install` (preceded by a dry-run pre-flight — see below).
5. On site deletion, matching `WorkloadUndeployedAsync` events trigger `helm uninstall` per release.

**Soft-failure on unregister:** `DeploymentSiteService.UnRegisterDeploymentSiteAsync` (from `DeploymentSiteController.DeletedAsync`) treats any `HubException` from the controller as a soft failure — logs only. The CR is already gone when `DeletedAsync` fires and the tenant may no longer exist controller-side; re-throwing would trap the entity in the KubeOps retry queue forever. The local connection is stopped and the site removed regardless.

## Helm Values Layering Model

`WorkloadReconciler` writes up to **three** values files to a temp dir and passes them via `-f` in this order (Helm's later `-f` wins, so order = precedence, lowest → highest):

| File | Source builder | Precedence |
|------|----------------|------------|
| `values-context.yaml` | `WorkloadContextValuesBuilder` — operator's own `OperatorOptions` (cluster Mongo/RabbitMQ/CrateDB hosts, reporting URI, instance prefix, ingress defaults) + workload identity (`tenantId`, `adapterRtId`) | lowest |
| `values-base.yaml` | the workload's own `ValuesYaml` from the CK entity | middle |
| `values-overrides.yaml` | `WorkloadOverrideYamlBuilder` — structured `ValueOverride[]` from the Studio form (`ValueOverrideDto` on the wire) | highest |

`WorkloadContextValuesBuilder` projects **only** the fields that are set — an edge operator with an empty DTO context passes no context layer at all. **Secrets are deliberately not handled in the context builder**; they flow through `WorkloadOverrideYamlBuilder` and the per-release Secret. Secret-flagged override entries become a `valueFrom: secretKeyRef` envelope pointing at the operator-owned `{release}-octo-secrets` Secret; non-secret entries are literal values; dotted paths (e.g. `oauth.clientSecret`) become nested maps.

**Typed CPU/memory settings sit inside these layers, they are not a fourth one.** `Adapter`, `Application` (and the inherited attributes of `AdapterPool`, which the controller rejects) carry `CpuRequest`, `CpuLimit`, `MemoryRequest`, `MemoryLimit` (System.Communication 4.10.0). The **controller** projects each non-blank value into one `resources.requests|limits.cpu|memory` entry of `ValueOverride[]` — and only if neither the `ValueOverride[]` (path match case-insensitive) nor the workload's `ValuesYaml` already sets that path. The operator is unchanged and sees ordinary overrides, so older edge operators work too. Resulting precedence, lowest → highest: **chart default < typed attributes < `ValuesYaml` (`values-base.yaml`) < explicit `ValueOverride[]` (`values-overrides.yaml`) < the `replicaCount` pin of a pool**. When an explicit value overrides a typed one the controller writes `LastDeploymentWarning` (`MemoryRequest 512Mi is overridden by an explicit Helm value (ValuesYaml resources.requests.memory)`), logs it and returns it from `POST deploymentsite/workloads/deploy` (`200 {"warning"}` instead of `204`); a conflict-free deploy clears it. Invalid typed values (not a Kubernetes quantity, request above limit) are rejected at deploy with the attribute named. Pools keep `PoolMemberCpuRequest` … `PoolMemberMemoryLimit`. Details: the controller's `CLAUDE.md` ("Typed sizing reaches Helm").

`--set` beats every `-f` layer: the only `--set` the operator adds is `replicaCount` (see [replica pin](#a-scaled-workload-fails-its-next-deploy-ab5350)).

**Release name:** `{tenantId}-{workloadRtId}`, DNS-sanitised via `K8sNaming.DnsName` and truncated to Helm's 53-char limit. The runtime entity id (24-char lowercase hex) is used — not the user-facing `WorkloadName` — so renaming the workload in Studio does not orphan the helm release. `WorkloadReconciler.ReleaseName` / `SecretName` / `RepoAlias` are the deterministic helpers (exposed to tests via `InternalsVisibleTo`).

**Empty `version`:** `UpgradeInstallAsync` omits `--version` when blank so helm picks the newest tag — the contract for `System.Communication.MainLatest` on dev/test clusters. Pass a non-blank value to pin a chart. A reconciliation keeps the installed version instead (see [below](#reconciliation-keeps-the-installed-chart-version-ab4955)).

Full builder mechanics and the `IHelmRunner` / `IHelmProcessInvoker` argument contracts are in `references/operator-internals.md`.

## Secret Injection Tiers

Before the override builder runs, `WorkloadReconciler.AppendClusterSecrets` injects cluster-level values in **three gates** — this is a foot-gun, get it right:

1. **Unconditional** (whenever the option is set):
   - `secrets.rabbitmq` (from `BrokerPassword`) — RabbitMQ is the controller↔adapter command bus; every adapter needs it. Gating it behind the cluster-secrets opt-in previously broke pure edge adapters (Modbus/Loxone) that failed the chart's mandatory `secrets.rabbitmq` check.
   - `secrets.rootCa` (from `RootCaCertificate`, AB#4417) — the TLS trust anchor for clusters whose controller endpoint uses a private CA. **Not** secret-flagged: the workload chart `b64enc`s it and needs a plain string.
2. **Per chart** (only for charts in a named list): `secrets.ironOcrLicenseKey` (`IronOcrLicenseKey`, list `ChartsReadingIronOcrLicense`) and `secrets.dash0WebAuthToken` (`Dash0WebAuthToken`, browser frontends, list `ChartsReadingDash0WebAuthToken`). A new chart that reads one of them must be added to the list **and** declare the value in its `secrets` block in the same change — Helm silently ignores an undeclared value.
3. **Opt-in** (only when `WorkloadDeployedDto.ReceivesClusterSecrets` is true, set by the controller from the CK attribute `ReceivesClusterSecrets`): the data-store secrets `secrets.databaseUser`, `secrets.databaseAdmin`, `secrets.streamDataPassword` (from `ClusterSecrets.*`) and the SECRET-attribute key ring `secrets.secretEncryption.*` (`ClusterSecrets.SecretEncryptionKeys` / `SecretEncryptionActiveKeyId` / `SecretEncryptionLegacyV1Key`; the active key id is a plain value). Pure edge adapters leave the flag false; the chart's `features.mongo` / `features.streamData` gates then skip the matching env blocks. An **adapter pool** never gets this tier: `AppendClusterSecrets` forces the flag to false for it (see [Adapter Pools](#adapter-pools--platform-namespace-owner-references-secret-tier-ab4924)).

Injected entries are **prepended** so any entity-supplied override on the same path still wins, then flow through the normal secret pipeline into `{release}-octo-secrets`. Each adapter chart's `secrets.*` block must accept both plaintext strings (legacy) and `valueFrom` maps — see the `octo-mesh.secretEnv` helper in `octo-mesh-adapter` / `octo-eda-adapter` templates. Tests: `Reconcilers/WorkloadReconcilerTests/AppendClusterSecretsTests`.

**Secret defaults are not a Helm tier.** An Application's `SecretDefaults` (System.Communication 4.15.0) never reach the operator: the controller leaves them out of `WorkloadDeployedDto` and projects them itself — on `DeployWorkload`, on every tenant load and on `POST {tenant}/v1/secretDefaults/reconcile` — into a platform-owned `System.Communication/SecretDefault` in the Application's tenant and its subtree; undeploying the Application withdraws them. No values file, no `{release}-octo-secrets` entry, no Helm release history, no pod env carries them, and no operator change is needed for them. If one ever shows up in a values file or the release Secret, that is a leak to report, not a tier to support. A secret the pod itself needs stays a secret-flagged `ValueOverride` (above); one only platform nodes need (e.g. a CAPTCHA secret for `VerifyCaptcha@1`) is a secret default — see `octo-app-builder` (`references/app-workload.md` §Secrets).

## Pre-flight, Watcher, Cancellation

The operator image ships **Helm 4** (`HELM_VERSION` build-arg in the Dockerfile). The real install is `helm upgrade --install --rollback-on-failure` (the Helm 4 replacement for `--atomic`), which collapses every failure into one opaque `context deadline exceeded` stderr line. Three mechanisms surface the real reason:

- **Pre-flight dry-run** (`UpgradeInstallDryRunAsync`, `--dry-run=server`, no `--rollback-on-failure`) runs before the real install in `WorkloadReconciler.DeployAsync`. Admission webhooks, OpenAPI schema validation, and RBAC run server-side without creating resources, catching schema/Gatekeeper/RBAC errors in <2s. On failure it throws `HelmException` and the real install is skipped. It **cannot** see a field-ownership conflict (see below).
- **Live Deploy Watcher** (`WorkloadDeployWatcher`) polls `IWorkloadDiagnosticsCollector.CollectAsync` every ~3s during the real install and pushes non-empty, changed snapshots to the controller via `ReportWorkloadDeploymentProgressAsync` (state stays `Pending` — helm may still recover). Closes the 5-minute gap before the post-failure collector runs. Older controllers reject the new hub method with `HubException`; the service logs one warning and degrades silently.
- **Post-failure diagnostics** (`IWorkloadDiagnosticsCollector`) scrapes pod container statuses and namespace `Warning` events on `HelmException`, merging the result into the rethrown exception's stderr. Events outlive pods, so `ImagePullBackOff` / `FailedScheduling` / `FailedMount` are caught even after the rollback.

**Cancellable deploys:** `WorkloadReconciler._inFlightDeploys` tracks running deploys by release. `UndeployAsync` cancels an in-flight deploy's CTS, waits a 2s grace (`CancelGracePeriod`) for the rollback, then `helm uninstall --ignore-not-found`. Cancellation works end-to-end only because `HelmProcessInvoker.InvokeAsync` does `process.Kill(entireProcessTree: true)` on cancel — `WaitForExitAsync(ct)` alone leaves helm holding the release lock.

The in-flight tracking for cancellation (`_inFlightDeploys`) is separate from the single-flight map (`_deployFlights`) that dedupes dispatches (see [Idempotent Dispatch](#idempotent-dispatch-after-a-controller-restart-ab6471)). The pre-flight dry-run and the watcher run only in the owner of a deploy — a joined request does neither.

Reconciler exceptions are **logged but not propagated** to the hub — one bad workload must not crash the SignalR connection.

## Deploy Recovery and Runtime Behaviour

Each subsection is a short map; the operator's agent docs hold the reasoning, measurements and incident history under the section of the same name (`octo-communication-operator/CLAUDE.md` today, `AGENTS.md`/`docs/` once moved). Read that section before changing the code.

### Reconciliation Keeps the Installed Chart Version (AB#4955)

`WorkloadDeployedDto.IsReconciliation` marks a re-dispatch ("restore what should run") as opposed to a user deploy. `WorkloadReconciler.ResolveChartVersionAsync`: a pinned `ChartVersion` is always used; an empty one means "newest in the repository" for a user deploy, but **the installed release's version** (`IHelmRunner.GetInstalledChartVersionAsync`, `helm list`) for a reconciliation — newest only when nothing is installed. The resolved version feeds the pre-flight and the real install; a failed lookup is logged and the deploy proceeds unpinned. Tests: `ReconcileChartVersionTests`.

### A Hand-Patched Workload Locks the Operator Out (AB#5325)

Helm 4 applies server-side, so a field another manager owns (left by `kubectl set image|env` or `kubectl patch`) makes `helm upgrade` — and its own rollback — fail with `conflict with "kubectl-…"`, leaving the release `failed`. A retry does not help. `Helm/HelmFieldOwnershipConflict` recognises the stderr and replaces it in `LastDeploymentError` with the cause and both remedies: delete the Deployment so the chart owns it again (usually right), or set `OPERATOR__HELM__FORCECONFLICTS=true` (`OperatorOptions.Helm.ForceConflicts`, default false, env only, never on the dry run), which overwrites hand-set values on every later deploy. Conflicts with helm's own manager or the operator are not reported as hand patches. Tests: `Helm/HelmFieldOwnershipConflictTests`.

### A Scaled Workload Fails Its Next Deploy (AB#5350)

The scale verb patches `spec.replicas` outside helm, which the chart also renders — so before AB#5350 every scaled workload hit the same server-side-apply conflict on its next deploy. `WorkloadReconciler.ResolveReplicaCountPinAsync` now adds `--set replicaCount=<n>` on the pre-flight and the real install: `0` when the DTO says `Hibernated`; otherwise the live count (`IDeploymentSiteKubernetesGateway.GetDeploymentReplicasByInstanceAsync`, the largest if Deployments disagree); no pin on first install, at live 0 without hibernation, or when the read fails. Consequence: once running, a helm deploy no longer decides the replica count. Tests: `ReplicaCountPinTests`, kind E2E `E2E/ScaledWorkloadRedeployKindE2ETests` (needs helm ≥ 4).

### Idempotent Dispatch After a Controller Restart (AB#6471)

After a controller restart or a site re-register, the controller re-dispatches every workload still `Pending` (`IsReconciliation=true`). It cannot tell a lost dispatch from a deploy the operator is still running or has finished with the report lost, so `WorkloadReconciler.DeployAsync` dedupes (`DeployCoreAsync` does the real work):

- **Single-flight per release:** an identical request (same `DesiredStateFingerprint`) joins the running deploy and shares its outcome (success or the same exception). A different request for the same release waits, then deploys. Other releases run in parallel.
- **Stamp:** every successful `helm upgrade` writes `--description octo-deploy:<fingerprint>` into the revision (visible in `helm history`; durable across operator restarts). The fingerprint is a truncated SHA-256 of the request DTO without `IsReconciliation`, plus the operator's context layer; secret values are hashed, never stored beside it.
- **Skip:** a reconciliation whose release's newest revision is `deployed` **and** carries the same stamp runs no helm and reports success. A missing or different stamp, status `failed`, or unreadable history all deploy as before. A user-triggered deploy never skips.
- Wire-compatible (no hub contract change); an older (edge) operator keeps the old behaviour until it is updated.

Tests: `DuplicateDispatchTests`, `Helm/HelmRunnerTests`, kind E2E `E2E/ControllerRestartRedispatchKindE2ETests`.

### Stale Helm-Lock Recovery (AB#4894)

A helm process killed mid-upgrade (operator pod replaced during a deploy) leaves the newest revision `pending-*`, which blocks every later upgrade with "another operation is in progress". Before the pre-flight (and before the chart version is resolved), `WorkloadReconciler.TryClearStaleHelmLockAsync` reads `GetLatestReleaseRevisionAsync`; only if it `IsPending` and its release secret `sh.helm.release.v1.{release}.v{rev}` is older than `StaleHelmLockThreshold` (10 min, above helm's 5-min wait) does it delete that secret and log a warning. Best effort throughout. Tests: `StaleHelmLockTests`.

### Pool-Registration Retry Loop (AB#4371)

A registration the controller **rejects while the connection stays alive** (e.g. its CK cache still loading after a joint restart) used to be forgotten. `OperatorHubService.RetryDeploymentSiteRegistrationLoopAsync` re-registers every owned site with `IsRegistered == false` while `client.IsAlive`, every `DeploymentSiteRegistrationRetrySeconds` (default 30, `<= 0` disables), and fires the per-site reverse-sync on success. The reconnect callback calls `DeploymentSiteService.ResetRegistrationState()` first. Since AB#8160 the loop backs off per site (`interval × 2^(n-1)`, capped by `RegistrationRetryMaxBackoffFactor` = 32), and `PreUpdateTenantAsync` keeps local entries so a deleted tenant's site does not come back as a zombie; the WARN names the failure count and suggests deleting the CR of a deleted tenant or site. Tests: `Services/OperatorHubServiceTests/RegistrationRetryTests`.

### Workload Scale Verb (AB#4917)

The controller's on-demand lifecycle scales via the hub callback `ScaleWorkloadAsync(ScaleWorkloadDto)` → `WorkloadReconciler.ScaleAsync` → `IDeploymentSiteKubernetesGateway.ScaleDeploymentsByInstanceAsync`: Deployments found by label `app.kubernetes.io/instance={release}` get a merge patch of `spec.replicas`, written as field manager `octo-communication-operator`. No helm run, no release history. The outcome goes back via `ReportWorkloadScaleStatusAsync` (older controllers: one warning, then silent). A redeploy never resurrects a hibernated workload (pin `0`, above). Tests: `ScaleAsyncTests`, `Services/OperatorHubServiceTests/ScaleWorkloadTests`.

### Adapter Pools — Platform Namespace, Owner References, Secret Tier (AB#4924)

An adapter pool (`WorkloadTypeDto.AdapterPool`) is one release whose members are leased to tenants; same deploy/undeploy/scale path. Three differences:

- **Namespace:** `WorkloadReconciler.ResolveNamespace` sends it to `PlatformNamespace`; empty (default) resolves to `DeploymentSiteNamespace`, which owner-reference garbage collection requires (Kubernetes forbids cross-namespace owner references). A distinct platform namespace works but the owner reference is then skipped with a warning.
- **Owner references:** the per-release Secret and, after install, the release's Deployments get a non-controller owner reference to the lending tenant's `DeploymentSite` CR (`DeploymentSiteManager.GetCrName`), so deleting the tenant removes the pool. Best effort.
- **Secret tier:** the opt-in tier is forced off — no shared data-store credentials and no key ring for a process that serves several tenants.

With `rbac.scope: namespace` in the operator chart a distinct platform namespace needs its own Role and RoleBinding. Tests: `PlatformNamespaceTests`, `DeploymentSiteOwnerReferenceTests`, `AppendClusterSecretsTests`, kind E2E `E2E/AdapterPoolKindE2ETests`.

### Watch Falls Back to Classic List+Watch (AB#6898)

KubeOps starts each watch without `resourceVersion` and with bookmarks, which needs the etcd feature `RequestWatchProgress`. Where the API server refuses it (HTTP 500 naming `RequestWatchProgress`), a fresh pod would never see its `DeploymentSite` CRs. `Watching/WatchFallbackKubernetesClient` (registered as `IKubernetesClient`) switches the process once to classic mode (`WatchModeState`, one WARN) and restarts at `resourceVersion=0` with `allowWatchBookmarks=false`; every reconnect then replays the current state as `ADDED`. `OPERATOR__FORCECLASSICWATCH=true` (`ForceClassicWatch`, env only, no chart value yet) starts in classic mode. Tests: `Watching/WatchFallbackKubernetesClientTests`, `Watching/WatcherChainTests`.

### The Operator's HTTP Surface Has No Authentication (AB#5059)

`Program.cs` wires no authentication or authorization middleware. `[Authorize]` therefore breaks an endpoint instead of gating it — bring an authority and a bearer scheme first. `Controller/DiagnosticsController` (`POST system/v1/diagnostics/reconfigureLogLevel`, process-wide log level) answers **403** to any non-loopback caller (missing address = not loopback; IPv4-mapped loopback is unmapped first); use `kubectl exec` or `kubectl port-forward`, which Kubernetes RBAC gates. Tests: `Controller/DiagnosticsControllerTests`.

### Operator Hub Authentication (AB#5062)

The operator can present its own client-credentials token on `/operatorHub`: `OperatorOptions.Authentication` (`IssuerUri`, `ClientId`, `ClientSecret`, `TenantId`; env `OPERATOR__AUTHENTICATION__*`) → `ConfigureOperatorAuthenticatorOptions` → `OperatorAccessTokenService` (scope `octo_api`, refresh 5 min before expiry, keeps the previous token on failure, first token before the hub starts) → the shared `IServiceClientAccessToken` that `OperatorHubClientFactory` hands to the client. **Unconfigured stays supported**: without `ClientId` the connection is anonymous as before. Register the client in the system tenant and name it in `TenantId`. Rollout order: operators with credentials first, check the controller's `LogOnly` inventory, only then switch the controller to `Enforce`. Tests: `OperatorAccessTokenServiceTests`, `OperatorHubClientFactoryTests`, `Options/OperatorOptionsBindingTests`.

## Reverse-Sync on Reconnect

After re-registering owned CRs on reconnect, a **central** operator (`AutoManageDeploymentSites=true`) calls `IOperatorHub.ReportDeployedStateAsync(reports)` to restore `DeploymentState=Deployed` on sites whose state drifted while offline. Two coupled paths run it: **bulk on reconnect** (`OperatorHubService` connect callback, covers controller-restart) and **per-site on register** (`DeploymentSiteService.RegisterDeploymentSiteAsync` → `IOperatorHubInvoker.ReportDeployedDeploymentSiteAsync`, covers the operator-restart race where KubeOps repopulates the registry after the bulk snapshot). Per-site is idempotent (restore-only-when-changed). Edge operators skip it (controller rejects them); empty owned-site list skips it; call failure is logged, not propagated. Workloads are **not yet** reverse-synced (no persistent helm-release→workload-rtId map survives a pod restart). Pending workloads are not part of this path: the controller re-dispatches them after the re-register, and the idempotent dispatch above keeps that from producing a second helm revision or an `Error` report. See `docs/DEPLOYMENT-MANAGEMENT-CONCEPT.md` for the contract.

## Key Testing Seams

The operator is built to be testable at abstraction boundaries, not against the k8s SDK. Mock these:

| Seam (interface) | Replaces | What it abstracts |
|------------------|----------|-------------------|
| `IDeploymentSiteKubernetesGateway` | direct `IKubernetes` calls in `DeploymentSiteManager` and `WorkloadReconciler` | CR and Secret existence/create/delete (`DeploymentSiteExistsAsync`, `CreateDeploymentSiteAsync`, `DeleteDeploymentSiteAsync`, `SecretExistsAsync`, `CreateSecretAsync`, `DeleteSecretAsync`), `GetSecretCreationTimestampAsync` (stale lock), `ScaleDeploymentsByInstanceAsync` / `GetDeploymentReplicasByInstanceAsync` (scale, replica pin), `TryGetDeploymentSiteOwnerReferenceAsync` / `SetDeploymentOwnerReferenceByInstanceAsync` (pools). All k8s-SDK quirks (404→false, CRD group/version/plural constants) live in `DeploymentSiteKubernetesGateway`. **Add new k8s calls here — never reach back into `IKubernetes` from elsewhere.** |
| `IOperatorHubClientFactory` | `new OperatorHubClient(...)` in `OperatorHubService.ExecuteAsync` | Produces an `IOperatorHubClient` (SDK type). Mock it to substitute the SignalR client. Prod wiring in `OperatorHubClientFactory` (singleton). |
| `IHelmRunner` / `IHelmProcessInvoker` | the `helm` binary | High-level operations / low-level process wrapper. `UpgradeInstallAsync` takes a `description` (stamp); `GetLatestReleaseRevisionAsync` returns `HelmReleaseRevision(Revision, Status, Description)` with `IsDeployed` / `IsPending`; `GetInstalledChartVersionAsync` reads the running chart version. |
| `IWorkloadDiagnosticsCollector` | k8s pod/event scraping | Pure formatters `FormatPodStates` / `FormatWarningEvents` exposed via `InternalsVisibleTo`. |

**Test sync point for `OperatorHubService`:** use `client.When(c => c.EnableReconnect(...)).Do(_ => tcs.TrySetResult())` — once `EnableReconnect` ran, the connect callback finished and the service is parked in `Task.Delay(Infinite, ...)`. Asserting earlier races.

**Kind E2E suites** (`E2E/AdapterPoolKindE2ETests`, `E2E/ScaledWorkloadRedeployKindE2ETests`, `E2E/ControllerRestartRedispatchKindE2ETests`) skip unless `OCTO_OPERATOR_E2E_KUBECONTEXT` is set (e.g. `kind-kind`); the two that run real helm also need helm ≥ 4 on PATH. `OCTO_OPERATOR_E2E_LEGACY=1` only prints the redispatch outcome as a counter-check against a build without the AB#6471 fix.

`DeploymentSiteKubernetesGateway` itself is **not** unit-tested (thin pass-through, covered by E2E).

## Test Conventions (.NET 10 / TUnit / MTP)

**Framework:** TUnit (`[Test]` attribute, `Assert.That(...).IsXxx(...)` fluent API) + NSubstitute. Tests mirror the source folder structure; namespaces `Meshmakers.Octo.Communication.Operator.Tests.<Area>`.

**CRITICAL — .NET 10 uses Microsoft.Testing.Platform, not VSTest.** The legacy VSTest path is rejected. Two pieces opt in: `global.json` at the repo root sets `"test": { "runner": "Microsoft.Testing.Platform" }`, and the test csproj references `Microsoft.Testing.Extensions.TrxReport`. Under MTP, the project/solution is a **flag** (`--project`/`--solution`, not positional), and reporter/filter args go **after `--`**.

Verified commands (run from the repo root; build only ever in **DebugL**):

| Command | Use |
|---------|-----|
| `dotnet build Octo.CommunicationOperator.sln -c DebugL` | Build (zero warnings — `TreatWarningsAsErrors=true`) |
| `dotnet test --solution Octo.CommunicationOperator.sln -c DebugL -- --report-trx --report-trx-filename test-results.trx` | **Canonical** — same form the Azure Pipeline runs |
| `dotnet run --project tests/CommunicationOperator.Tests/CommunicationOperator.Tests.csproj -c DebugL --no-build` | Quick dev form (no TRX, no rebuild) |
| `dotnet run --project tests/CommunicationOperator.Tests/CommunicationOperator.Tests.csproj -c DebugL --no-build -- --treenode-filter "/*/*/DeploymentSiteValidatorTests/*"` | Run one test class |

Test-project gotchas: `ThrowsAsync(...)` (not `Throws(...)`) for `Task`-returning substitutes (`NS5003` is an error); implement `IDisposable` + dispose any disposable SUT (`TUnit0023`); inject options with fully-qualified `Microsoft.Extensions.Options.Options.Create(new OperatorOptions { ... })`; set `<EnablePreviewFeatures>true</EnablePreviewFeatures>` (KubeOps APIs are `[RequiresPreviewFeatures]`). Target framework `net10.0`, three configs `Debug`/`Release`/`DebugL`.

## CRD Generation Workflow

The CRD is shipped from `octo-helm-core` (`octo-mesh-crds` chart, `templates/deploymentsites_octo-mesh_meshmakers_io.yaml`), not from this repo's build output. To regenerate operator + CRD YAML into `config/` (run from **`src/CommunicationOperator/`**, where `install.ps1` lives):

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

In-repo helpers (PowerShell scripts, not octo-tools cmdlets): the create and remove scripts for a bare kind test cluster in `src/scripts/` (with `kind-cluster.yaml`; `Install-OctoKubernetes` is the full dev setup), and `start-operator.ps1` at the repo root runs a locally-built operator in **central mode** on ports 5022/5023 (`ASPNETCORE_ENVIRONMENT=Development`). It is intentionally **not** named `octo-start.ps1` so `Start-Octo` does not auto-launch it.

In DEBUG/DEBUGL builds the operator auto-picks the first non-loopback IPv4 for its dev webhook endpoint and logs it (`Dev webhook endpoint: https://192.168.x.y:6001`). Override with `Operator:DevWebhookHost`/`Port` in `appsettings.Development.json` or `OCTO_OPERATOR__DEVWEBHOOKHOST`/`PORT` (this bootstrap read uses the `OCTO_` prefix; all other options bind from plain `OPERATOR__*`).

Manual E2E runbook: `docs/E2E-SMOKE-TEST.md` (uses `Install-OctoKubernetes`, `Start-Octo`, `start-operator.ps1`).

## Troubleshooting

- **Two helm revisions per workload, or an `Error` report ("A deploy for release ... is already in progress") after a controller restart or site re-register:** the operator is older than the AB#6471 fix (merge `a0fff62` of `octo-communication-operator`). Update the operator (edge operators separately). Revisions of the fixed operator carry the description `octo-deploy:<fingerprint>` in `helm history <release>`.
- **`UPGRADE FAILED: conflict occurred while applying object … conflict with "kubectl-…"`:** a hand patch owns the field ([AB#5325](#a-hand-patched-workload-locks-the-operator-out-ab5325)). Delete the Deployment, or set `OPERATOR__HELM__FORCECONFLICTS=true` knowingly. With `"octo-communication-operator"` on `.spec.replicas` the operator is older than AB#5350 — update it.
- **"another operation is in progress" on every deploy:** a stale `pending-*` revision; the operator clears it after 10 min ([AB#4894](#stale-helm-lock-recovery-ab4894)). Earlier, or on an older operator: `helm history` and a manual Undeploy → Deploy.
- **Site stays `Unregistered`, WARN with a growing failure count:** the controller rejects the registration ([AB#4371](#pool-registration-retry-loop-ab4371)). Read the controller log; for a deleted tenant or site delete the `DeploymentSite` CR.
- **`There was an error while watching the resource …V1DeploymentSiteEntity` every ~33 s with `RequestWatchProgress`:** the operator predates AB#6898 — update it, or set `OPERATOR__FORCECLASSICWATCH=true` ([watch fallback](#watch-falls-back-to-classic-listwatch-ab6898)).

## octo-helm-core Charts

`octo-helm-core` is the official Helm chart repo, **published to `https://meshmakers.github.io/charts`** (GitHub Pages). Add it with `helm repo add meshmakers https://meshmakers.github.io/charts`.

Charts live under `src/<chart>/` (each has its own `Chart.yaml` and `values.yaml`):

| Chart | Purpose |
|-------|---------|
| `octo-mesh` | Core services (identity, asset-repo, bot, comm-controller, report, admin panel, AI services). Installed centrally, multi-tenant. **Main values.yaml a developer edits: `src/octo-mesh/values.yaml`.** |
| `octo-mesh-crds` | CRDs required by the Communication Operator (the `DeploymentSite` CRD, `deploymentsites.octo-mesh.meshmakers.io`, version `v1`). |
| `octo-mesh-communication-operator` | The operator deployment (the chart `Deploy-OctoOperator` installs); renders the `OPERATOR__*` env vars and the operator's RBAC (`templates/operator-role.yaml`). |
| `octo-mesh-schema-provider` | Schema-provider application chart (`type: application`). |
| `octo-mesh-demo-app` | Demo application chart. |

Adapter charts (`octo-mesh-adapter`, `octo-eda-adapter`) now live in their **own** adapter repos and publish from there, not from `octo-helm-core`.

## References

- `references/operator-internals.md` — `OperatorOptions` full config table (env-var keys, central vs edge requirements), Helm builder mechanics, `IHelmRunner`/`IHelmProcessInvoker` argument contracts, CI pipeline shape, solution layout, and the full unit-test coverage map.
