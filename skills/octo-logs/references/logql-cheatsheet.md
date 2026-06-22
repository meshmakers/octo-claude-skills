# LogQL cheat sheet (OctoMesh)

A LogQL query has two parts: a **label selector** `{...}` (required) and optional
**line filters** / parsers. All examples below are the quoted argument you pass to
`run_logcli.sh <cluster> query '<here>'` (or `instant-query` for the metric forms).

## How OctoMesh logs are labeled

Promtail parses the OctoMesh log format and attaches these labels:

| Label | Always set? | Example | Notes |
|---|---|---|---|
| `namespace` | yes | `octo`, `ponton`, `mongodb` | Kubernetes namespace |
| `container` | yes | `identity`, `assetrepository`, `communication`, `bot` | Service name; STABLE across redeploys |
| `pod` | yes | `octo-mesh-identity-services-574cc9cd4c-6tc5x` | Specific replica; middle segment = ReplicaSet hash = one deployment rollout |
| `level` | yes (octo app logs) | `INFO`, `WARN`, `ERROR`, `DEBUG` | NLog/MEL severity |
| `source` | only app logs | `Octo.Identity.UserManager` | NLog source = `Class.Method` |

Two log shapes are emitted; both set `level`, only the first sets `source`:

```
2026-04-30 00:00:02.2698| INFO|Octo.Identity.UserManager|User 'alice' created   # app (NLog) — has source
2026-06-03 13:26:04.7751|DEBUG|Connection id "0H..." sending FIN                 # framework (Kestrel/MEL) — no source
```

Pods OUTSIDE `octo` (ponton, mongodb, cratedb) are not parsed → only
`namespace`/`container`/`pod`. Use inline filters for those.

## Pick the service

```logql
{namespace="octo"}
{namespace="octo", container="identity"}
{namespace="octo", container="assetrepository"}
{namespace="octo", container="communication"}
{namespace="octo", container="bot"}
```

## Filter by level

```logql
{namespace="octo", level="ERROR"}
{namespace="octo", container="identity", level=~"ERROR|WARN"}
{namespace="octo", level="ERROR", source=~"Octo.Identity.*"}
```

## Search the message body

```logql
{namespace="octo"} |= "Exception"            # substring (fast)
{namespace="octo"} |~ "(?i)timeout"          # regex, case-insensitive
{namespace="octo", level="ERROR"} != "/healthz"     # negative filter
{namespace="octo", level="ERROR"} |= "TenantId=42" != "expected"   # chained
```

## Rates and counts (use `instant-query`)

```logql
sum by (container) (count_over_time({namespace="octo", level="ERROR"}[24h]))
sort_desc(sum by (source) (count_over_time({namespace="octo", container="identity", level="ERROR"}[24h])))
sum by (container) (rate({namespace="octo", level="ERROR"}[1m]))
topk(5, sum by (source) (count_over_time({namespace="octo", level="ERROR"}[1h])))
```

## Non-octo namespaces (no `level` label)

```logql
{namespace="ponton"} |~ "(?i)\\bERROR\\b"
{namespace="mongodb"} |~ "\"s\":\"W\""        # Mongo JSON: "s" = severity (W = warning)
```

## Tracing an error across deployments

Each `pod` hash = one rollout; `container` is stable. Keep `container`, drop `pod`:

```logql
# which deployments carry the error (group by pod = by rollout)
sort_desc(sum by (pod) (count_over_time({namespace="octo", container="identity"} |= "ObjectDisposedException" [168h])))
```

Then pin first/last occurrence per deployment with the log form:

```bash
# first occurrence in a given rollout (--forward = oldest first)
run_logcli.sh test-2 query --since=168h --limit=1 --forward \
  '{namespace="octo", container="identity", pod="<pod>"} |= "ObjectDisposedException"'
# last occurrence (default newest first)
run_logcli.sh test-2 query --since=168h --limit=1 \
  '{namespace="octo", container="identity", pod="<pod>"} |= "ObjectDisposedException"'
```

A gap between one rollout's last hit and the next rollout's first hit, with the
same error resuming, means the error survived the redeploy (a real recurring bug,
not a one-deployment fluke).

### `|=` vs `source=` when tracing

Prefer a **line filter (`|=` / `|~`)** over the `source=` label for cross-deployment
hunts. `source` and `level` are only attached to lines the parser recognized, so a
`source=` filter silently misses some lines that `|=` catches.

## Gotchas

- **Single-quote the whole query** in bash — `{`, `}`, `|`, `"` are shell-special.
- `--forward` for first-occurrence; default order is newest-first.
- `instant-query` returns a single value per series — use it for counts/rates;
  use `query` for log lines.
- `detected_level` (vs `level`) appearing means Grafana's heuristic kicked in because
  the parser did not set a label — file the sample line with #devops to extend the parser.
