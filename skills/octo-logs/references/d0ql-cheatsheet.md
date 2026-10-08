# D0QL recipes for OctoMesh logs (`mcp__dash0__sql`)

D0QL is a ClickHouse SQL subset. Table `logs`. Columns used here:
`timestamp`, `severity` (UNKNOWN/TRACE/DEBUG/INFO/WARN/ERROR/FATAL), `body`,
`resource_attributes` (map — **bracket notation only**). Without `LIMIT` the
server forces 1000 rows. All recipes below were run against `test-2` on 2026-10-08. The time window comes from the tool's `timeRange`,
not from a `WHERE timestamp` clause.

```sql
-- Errors per container
SELECT resource_attributes['k8s.container.name'] AS container, count() AS errors
FROM logs
WHERE resource_attributes['k8s.namespace.name'] = 'octo' AND severity = 'ERROR'
GROUP BY container ORDER BY errors DESC LIMIT 20

-- Errors per tenant adapter / app (service.name = <release>-<rtId>)
SELECT resource_attributes['service.name'] AS service, count() AS errors
FROM logs
WHERE resource_attributes['k8s.container.name'] = 'mesh-adapter' AND severity = 'ERROR'
GROUP BY service ORDER BY errors DESC LIMIT 20

-- Top error messages of one service (first 160 chars)
SELECT substring(body, 1, 160) AS msg, count() AS n
FROM logs
WHERE resource_attributes['k8s.container.name'] = 'identity' AND severity = 'ERROR'
GROUP BY msg ORDER BY n DESC LIMIT 20

-- Error rate per 5 minutes (INTERVAL / toStartOf* are NOT supported;
-- toUInt64(timestamp) = unix seconds, bucket it yourself)
SELECT floor(toUInt64(timestamp) / 300) * 300 AS bucket_unix_s, count() AS errors
FROM logs
WHERE resource_attributes['k8s.namespace.name'] = 'octo' AND severity = 'ERROR'
GROUP BY bucket_unix_s ORDER BY bucket_unix_s LIMIT 300

-- One error across rollouts (pod hash = rollout)
SELECT resource_attributes['k8s.pod.name'] AS pod, count() AS n,
       min(timestamp) AS first_seen, max(timestamp) AS last_seen
FROM logs
WHERE resource_attributes['k8s.container.name'] = 'communication'
  AND body LIKE '%ObjectDisposedException%'
GROUP BY pod ORDER BY first_seen LIMIT 20

-- Case-insensitive body search outside octo (no severity there)
SELECT timestamp, resource_attributes['k8s.pod.name'] AS pod, substring(body, 1, 200) AS msg
FROM logs
WHERE resource_attributes['k8s.namespace.name'] = 'ponton' AND body ILIKE '%error%'
ORDER BY timestamp DESC LIMIT 50
```

If a query is rejected, the error message names the fix (e.g. dot notation →
bracket notation); apply it and retry.

## LogQL → Dash0 translation (for old notes/runbooks)

| LogQL (Loki, gone) | Dash0 |
|---|---|
| `{namespace="octo", container="identity"}` | filters `k8s.namespace.name is octo`, `k8s.container.name is identity` |
| `level="ERROR"` | `otel.log.severity.range is ERROR` / SQL `severity = 'ERROR'` |
| `\|= "text"` / `!= "text"` | `otel.log.body contains` / `does_not_contain` |
| `\|~ "(?i)re"` | `otel.log.body matches "(?i)re"` / SQL `match(body, '(?i)re')` |
| `pod="..."` | `k8s.pod.name is ...` |
| `source=~"Octo.Identity.*"` | body search (`contains`) — NLog source is part of the body |
| `count_over_time(...[24h])` by container | SQL `count()` … `GROUP BY` with `timeRange` 24h |
| `logcli query --forward --limit=1` | SQL `min(timestamp)` or `getLogRecords` with a tight window |
