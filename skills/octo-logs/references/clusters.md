# Dash0 datasets and attributes

## Where the logs come from

Each cluster runs the Dash0 operator with an OpenTelemetry collector DaemonSet
that tails every pod's log and exports to Dash0. Environments are separated by
**dataset** (typically one per cluster); `mcp__dash0__listDatasets` shows the
ones your login can read. Which datasets exist, how the infrastructure is
configured and how to reach Dash0 outside the MCP server are internal facts: if
`octo-claude-pm` is installed, see its `agent-operating-rules/references/dash0.md`.

## Attributes

Filter keys for `getLogRecords` / `getAttributeValues`:

| Key | Content |
|---|---|
| `k8s.namespace.name` | namespace (`octo`, `mongodb`, `cratedb`, …) |
| `k8s.container.name` | container: `identity`, `assetrepository`, `communication`, `bot`, `mesh-adapter`, `platformservices`, `octo-mesh-ai`, `octo-mesh-mcp`, `octo-mesh-reporting`, `octo-mesh-office`, `octo-mesh-communication-operator`, plus the containers of deployed apps |
| `k8s.pod.name` | pod; middle segment = ReplicaSet hash (one rollout) |
| `service.name` | aligned with traces/metrics; tenant adapters/apps appear as `<release>-<rtId>` |
| `otel.log.severity.range` | `ERROR`, `WARN`, `INFO`, `UNKNOWN` (unparsed lines) |
| `otel.log.body` | message body |
| `trace_id` / `span_id` | present on structured OctoMesh logs |

Use `getAttributeValues` with a filter (e.g. `k8s.namespace.name is octo`) to list
current values rather than relying on this table.

In **D0QL** (`mcp__dash0__sql`) the same data is addressed as
`resource_attributes['k8s.container.name']`, `severity`, `body`, `timestamp`.

## Severity caveat

Lines the collector could not parse arrive as `UNKNOWN`. Pods outside `octo`
(databases, third-party charts) often have no real severity — search the body
(`otel.log.body matches "(?i)\\berror\\b"`) instead of filtering on severity.
A spam filter may drop noisy DEBUG lines before storage.

## Retention

Set by the Dash0 dataset retention, not by the cluster; queries cannot reach
further back. Copy evidence you need longer into the work item.
