# Web app as an operator-deployed Application workload

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

The communication controller injects `image.privateRegistry=docker.mm.cloud` at
deploy time, so the final image reference is `docker.mm.cloud/<repository>:<tag>`.

Local kind (no registry needed — `pullPolicy: IfNotPresent` finds node-local images):

```powershell
docker build -t meshmakers/<app>:0.1.0 .\app
docker tag meshmakers/<app>:0.1.0 docker.mm.cloud/meshmakers/<app>:0.1.0
kind load docker-image meshmakers/<app>:0.1.0 docker.mm.cloud/meshmakers/<app>:0.1.0
```

Tag and load **both** names so the image resolves regardless of registry-prefix
injection. Shared clusters (test-2 etc.): push to `docker.mm.cloud` instead.

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
