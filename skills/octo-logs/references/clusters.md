# Clusters, Dash0 datasets, attributes, retention

## Where the logs come from

Each cluster runs the Dash0 operator (`dash0-system` namespace) with an
OpenTelemetry collector DaemonSet. Its filelog receiver tails every pod's log
under `/var/log/pods` and exports to Dash0 (EU ingress, org of meshmakers).
Configuration as code lives in `meshmakers-infrastructure`
(`roles/k8s-infrastructure/tasks/dash0.yml`, `dash0:` block in each cluster's
group_vars; docs: `docs/DASH0-OBSERVABILITY.md`).

Loki + Promtail are **gone** on all clusters (verified 2026-10-08) and were
removed from the IaC (AB#6116). The `monitoring.*` Grafana no longer has a Loki
datasource; the end-customer `grafana.*` never had one.

## Cluster → dataset

| Cluster | Dataset | Notes |
|---|---|---|
| test-2 | `test-2` | on-prem RKE2, first to receive every release |
| staging-1 | `staging-1` | Azure AKS |
| prod-1 | `prod-1` | Exoscale SKS — production |
| prod-2 | `prod-2` | Azure AKS — production |

`listDatasets` shows them (plus an empty `default`).

## Attributes (verified against test-2, 2026-10-08)

Filter keys for `getLogRecords` / `getAttributeValues`:

| Key | Content |
|---|---|
| `k8s.namespace.name` | namespace (`octo`, `mongodb`, `cratedb`, `ponton`, `dash0-system`, …) |
| `k8s.container.name` | container: `identity`, `assetrepository`, `communication`, `bot`, `mesh-adapter`, `platformservices`, `octo-mesh-ai`, `octo-mesh-mcp`, `octo-mesh-reporting`, `octo-mesh-office`, `octo-mesh-communication-operator`, app containers (`meshmakers-app`, `energy-community-app`, `fda-seen`, …) |
| `k8s.pod.name` | pod; middle segment = ReplicaSet hash (one rollout) |
| `service.name` | aligned with traces/metrics (AB#5478 §2.1); tenant adapters/apps appear as `<release>-<rtId>` |
| `otel.log.severity.range` | `ERROR`, `WARN`, `INFO`, `UNKNOWN` (unparsed lines) |
| `otel.log.body` | message body |
| `trace_id` / `span_id` | present on structured OctoMesh logs (AB#5478 §2.3) |

Use `getAttributeValues` with a filter (e.g. `k8s.namespace.name is octo`) to list
current values rather than relying on this table.

In **D0QL** (`mcp__dash0__sql`) the same data is addressed as
`resource_attributes['k8s.container.name']`, `severity`, `body`, `timestamp`.

## Severity caveat

Lines the collector could not parse arrive as `UNKNOWN`. Pods outside `octo`
(mongodb, cratedb, ponton) often have no real severity — search the body
(`otel.log.body matches "(?i)\\berror\\b"`) instead of filtering on severity.
A DEBUG spam filter (`Dash0SpamFilter`) drops noisy DEBUG lines before storage;
see "Cost control" in `docs/DASH0-OBSERVABILITY.md`.

## Retention

Set by the Dash0 dataset retention, not by the cluster: logs, spans and span events are kept
30 days (queries cannot span more than 30 days). prod-1 and prod-2 only have data since
2026-09-30, when they were connected to Dash0. Copy evidence you need longer into the work item.
