# Web app as an operator-deployed Application workload

> **Hostnames are placeholders.** The concrete domains of the shared environments (`<test-2-domain>`, `<staging-domain>`, `<prod-1-domain>`, `<prod-2-domain>`, `<legacy-domain>`, `<registry>`, `<rancher-url>`) are internal. If the plugin `octo-claude-pm` is installed, see its `agent-operating-rules/references/environments.md`; otherwise ask a colleague.

How to ship a web UI for a mesh app so that the **platform itself deploys it**:
an `System.Communication/Application` entity in the blueprint seed, helm-installed
by the Communication Operator on `DeployWorkload`. Verified 2026-06-09 on local
kind (one-time-ticket demo). Operator/chart internals → octo-operator skill.

## Why a workload (and not the adapter)

The Mesh Adapter serves `application/json` only — it cannot serve HTML. The
platform-native way to deliver a UI is an Application workload: Helm release,
ingress with per-tenant hostname, lifecycle via octo-cli/Studio.

## The fast path: fulfil the property-walker chart contract

`property-walker` (meshmakers Helm repo, dev channel) is a generic
"Node proxy + static SPA" chart. Any image that fulfils its contract can reuse it
via image override — no chart authoring, no CI:

| Contract item | Requirement |
|---|---|
| `PORT` env | HTTP server listens on it (chart sets it from `service.port`, default 5055) |
| `UPSTREAM_URL` env | tenant-scoped Mesh Adapter base the app proxies to |
| `GET /` | returns 200 + the SPA (liveness/readiness probes hit `/`) |
| container port | 5055 |

App shape that fits (zero npm dependencies, see `one-time-ticket/app/` for a
complete implementation):

- `server/server.js` — node:http server. `GET /` → serve `client/index.html`;
  `/api/<rest>` (any method) → proxy to `UPSTREAM_URL/<rest>` preserving query +
  JSON body, TLS verification off for https upstreams; answer `/favicon.ico`
  with 204; 502 `{"error":"upstream_unreachable"}` on connect failure.
- `client/index.html` — single self-contained SPA calling `api/...` (same origin
  → no CORS, no cert issues in the browser).
- `Dockerfile`: `FROM node:22-alpine`, copy server+client, `ENV PORT=5055`,
  `EXPOSE 5055`, `CMD ["node","server/server.js"]`.

The proxy indirection is what makes the browser story work: browser → app
(same origin, trusted ingress cert) → in-cluster adapter (plain HTTP).

## Image build + registry rules

The communication controller injects `image.privateRegistry=<registry>` at
deploy time, so the final image reference is `<registry>/<repository>:<tag>`.

Local kind (no registry needed — `pullPolicy: IfNotPresent` finds node-local images):

```powershell
docker build -t meshmakers/<app>:0.1.0 .\app
docker tag meshmakers/<app>:0.1.0 <registry>/meshmakers/<app>:0.1.0
kind load docker-image meshmakers/<app>:0.1.0 <registry>/meshmakers/<app>:0.1.0
```

Tag and load **both** names so the image resolves regardless of registry-prefix
injection. Shared clusters (test-2 etc.): push to `<registry>` instead.

## The Application seed entity

```yaml
- rtId: '077100000000000000000005'
  ckTypeId: System.Communication/Application-1
  associations:
    - roleId: System.Communication/Manages-1            # deploy target pool
      targetRtId: '670000000000000000000001'
      targetCkTypeId: System.Communication/Pool-1
    - roleId: System.Communication/HelmRepository-1     # chart source
      targetRtId: '670000000000000000000003'
      targetCkTypeId: System.Communication/HelmRepositoryConfiguration-1
  attributes:
    - id: System/Name-1
      value: My App UI
    - id: System.Communication/ChartName-1
      value: property-walker          # reused chart (see contract above)
    - id: System.Communication/ChartVersion-1
      value: ""                       # empty = always newest chart from the repo
    - id: System.Communication/DeploymentState-1
      value: 0
    - id: System.Communication/ReceivesClusterSecrets-1
      value: false                    # app only talks HTTP to the adapter
    - id: System.Communication/IngressEnabled-1
      value: true
    - id: System.Communication/Hostname-1
      value: 'my-app-${octo.tenantId}.{{domain.default}}'
    - id: System.Communication/ValuesYaml-1
      value: |
        upstreamUrl: http://${octo.tenantId}-670000000000000000000002.octo.svc.cluster.local:80/${octo.tenantId}
        image:
          repository: meshmakers/<app>
          tag: "0.1.0"
```

- `${octo.tenantId}` resolves at blueprint apply; `{{domain.default}}` resolves at
  **deploy** time against the controller's domain config (`127.0.0.1.nip.io` on
  kind → ingress works directly at `https://my-app-<tenant>.127.0.0.1.nip.io`).
- `upstreamUrl`: the Mesh Adapter's in-cluster service is named
  `{tenantId}-{adapterRtId}` in namespace `octo`, plain HTTP on `:80`, routes
  prefixed with `/{tenantId}`.
- `ValuesYaml` overrides chart defaults; the controller merges its own values
  (registry, ingress, publicUri) on top.
- For a dedicated chart later: publish `<app>` chart via the standard CI to the
  Helm repo and set `ChartName` accordingly — the rest stays identical.

## Secrets: secret defaults vs. secret ValueOverrides

Decide by **who uses the secret**:

| The secret is used by | Declare it as | Where the value ends up |
|---|---|---|
| the app's own pod (its database password, an API key the server calls with) | a `Values` entry with `IsSecret: true` and the value in `SecretValue` | the release's Kubernetes Secret, referenced from the Helm values |
| platform nodes in every tenant the app serves (e.g. a CAPTCHA secret `VerifyCaptcha@1` checks with) | an entry of the Application's `SecretDefaults` (System.Communication 4.15.0 or newer) | a platform-owned `System.Communication/SecretDefault` in the Application's tenant and its whole subtree; never Helm values, the pod or a Kubernetes Secret |

**Never a secret ValueOverride when the pod does not need the value**: it would land in the pod and its Kubernetes
Secret for nothing. A static frontend that shows a CAPTCHA needs only the public **site key** — an ordinary
`Values` entry — while the **secret** is a secret default.

The seed declares **no** `SecretDefaults` entry. An entry without `SecretValue` makes `DeployWorkload` refuse the
Application ("the SecretDefaults entry '<key>' has no SecretValue"), and the secret seed lint (`octo-bpm validate`,
blueprint build) refuses a value, a `<...>` / `TODO_SET_*` placeholder and a `${...}` variable in a Secret slot, so a
Secret attribute in a seed is only ever empty or omitted; blueprints have no install-time parameters either.

- **The operator adds the entry after the install** — key and value together — and deploys the Application:
  - **Refinery Studio:** Application -> **Further attributes** -> `SecretDefaults` -> add a row: `Key`, `SecretValue`
    (write-only; empty on a later edit keeps the stored value), optionally `AllowedTenantIds` and `Description` ->
    **Save** -> **Deploy**.
  - **GraphQL:** `systemCommunicationApplications.update` with the whole `secretDefaults` list (it replaces the list:
    use it while the Application carries no other entry, otherwise the Studio form). The secret is a **GraphQL
    variable**, never inline in the document, never on a command line — e.g. the variables JSON on stdin with
    `octo-cli -c GraphQl -tid <tenant> -f write-secret-default.graphql -vars @/dev/stdin`:

    ```graphql
    mutation writeSecretDefault($secretValue: String!) {
      runtime { systemCommunicationApplications { update(entities: [{ rtId: "<application rtId>", item: {
        secretDefaults: [{ key: "my-app-captcha-secret", secretValue: $secretValue,
                           description: "Turnstile secret of the registration form" }] } }]) {
        rtId secretDefaults { key allowedTenantIds secretValue { isSet } } } } }
    }
    ```
  - **A CD from a secret store**, as the Energy Community app on test-2 (Vault -> `SecretDefaults` before the
    deploy). The store is then the source of truth; a Studio edit is overwritten by the next run.

  Re-apply and blueprint updates keep the entry (TenantOwned, carried over by record key). Rotate by writing the new
  value and deploying again.
- **Scope.** The Application's own tenant plus its whole subtree, never siblings. `AllowedTenantIds` absent or empty
  means exactly that set; a non-empty list narrows it to the listed tenants and never widens it (a listed tenant
  outside the subtree is ignored). A tenant added below the Application later is covered automatically only while
  the list is empty; with a non-empty list add its id to the list and deploy again.
- **Projection.** A Pending or Deployed Application is a source. The controller
  projects on `DeployWorkload`, on every tenant load (service start, Enable, tenant update — so a tenant created or
  loaded after the deploy receives the default without a redeploy) and on `POST {tenant}/v1/secretDefaults/reconcile`
  (that tenant and its subtree; use it e.g. after deleting an Application, which no hook sees). **Undeploying the
  Application withdraws its defaults** from every tenant. A redeploy the deploy guard refuses (state Error) does not:
  the previous release keeps running, so the Application holds the defaults it already projected and offers nothing
  to a tenant it did not serve before. Revocation wins: removing the entry or narrowing `AllowedTenantIds` removes
  the default from every tenant it no longer reaches. The projection is best effort per tenant: a skipped tenant (no
  System.Communication 4.15.0, not resolvable) or a failed write is a Warning/Error event, and the deploy still
  succeeds. Events about an Application's defaults are **linked to the Application** (`relatesFrom` of
  `System.Notification/Event`) when stored in its own tenant. After every deploy read those events; for a skipped or
  failed tenant fix the cause and deploy again, and revoke an old secret at the provider only once no such event is
  left. A failed event write is only logged, so no event is no proof: the controller log has one line per deploy,
  `Secret defaults of application '<name>' (<rtId>) projected: <n> written, <n> removed, <n> skipped, <n> failed` —
  revoke only after a line with 0 skipped and 0 failed.
- **Is it set in a tenant?** `SecretDefault.Value` is `Hidden` (System.Communication 4.16.0 and later, so 4.18.0 too):
  GraphQL, REST, MCP, import and export can neither read nor write it, not even `isSet`. The projected entity is the
  signal — query `systemCommunicationSecretDefault` by `rtWellKnownName` = key and read `sourceTenantId`,
  `sourceWorkloadRtId`, `lastProjectedAt`.
- **Nobody in a served tenant can read it**: `RevealSecret@1` refuses `System.Communication/SecretDefault` for every
  identity, and GraphQL, MCP and export cannot read the Hidden value. Only platform nodes use it — today
  `VerifyCaptcha@1` (`defaultKey` = the Key), which uses the tenant's own secret when it is set and the default
  otherwise. A tenant that wants its own value keeps it in its own Secret attribute (`tenantSecret` of the node); the
  projection never touches that.
- Key: `^[A-Za-z0-9][A-Za-z0-9._-]*$`, at most 128 characters, unique per Application. The key is the well-known
  name of the `SecretDefault` in every target tenant, one per key and tenant: Applications whose scopes overlap (two
  in one tenant, or one in an ancestor of the other) need distinct keys. With the same key the source closer to the
  root wins (a Warning event names the refused one), otherwise the last deploy overwrites the other's value.

Worked sample with the Application, a tenant override type, the `VerifyCaptcha@1` route and the verify commands:
`octo-communication-controller-services/samples/Blueprints/SecretDefaultDemo/` (controller PR #96). Pipeline side:
`pipeline-expert`, `VerifyCaptcha@1`.

## Deploy + operate

```powershell
octo-cli -c DeployWorkload -id <applicationRtId>      # operator helm-installs
kubectl get pods -n octo                              # <tenant>-<appRtId>-<chart>-… Running
kubectl get ingress -n octo                           # host shows the resolved domain
octo-cli -c UndeployWorkload -id <applicationRtId> -y # helm-uninstall (destructive)
octo-cli -c UpdateWorkloadChartVersion -id <rtId> -cv <semver>  # set version, then DeployWorkload
```

Iteration loop after app changes: rebuild image → `kind load` both tags →
`kubectl rollout restart deploy/<release-name> -n octo` (release name =
`{tenantId}-{applicationRtId}-<chartname>` as shown by `kubectl get deploy -n octo`).

Failure triage:
- `ImagePullBackOff` → registry-prefix mismatch; check the pod's image reference
  (`kubectl get pod … -o jsonpath='{.items[0].spec.containers[0].image}'`) and
  make sure exactly that name was kind-loaded/pushed.
- Pod restarts / not Ready → probes failing: `GET /` must return 200 on `PORT`.
- Helm install error → `kubectl logs -n octo-operator-system deploy/communication-operator`
  and the workload's `lastDeploymentError` attribute (rt_explorer/Studio).
- Uninstalling the blueprint? `UndeployWorkload` FIRST, then `UninstallBlueprint`.
