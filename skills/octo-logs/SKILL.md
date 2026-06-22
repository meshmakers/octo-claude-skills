---
name: octo-logs
description: Query and trace OctoMesh cluster logs from your machine via Loki + logcli, without handling credentials — the octo-tools PowerShell profile supplies them automatically. Reads service logs from each cluster's monitoring Grafana Loki datasource (test-2, staging-1, prod-1, prod-2): filter by namespace/container/level/source, search message bodies, count error rates, and trace an error across pod redeployments. Run /octo-logs-setup once first to store credentials safely. Trigger on: logs, Loki, logcli, LogQL, cluster logs, view logs, service logs, error logs, grep logs, tail logs, monitoring Grafana, trace error, error over deployments, log retention, namespace octo, level ERROR, identity/asset-rep/communication logs, log query, what broke in the cluster.
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/references/*)"
  - "Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh:*)"
---

# OctoMesh Cluster Logs — Loki / logcli Interface

## Overview

Read and trace service logs from any OctoMesh cluster's **monitoring Grafana** (the internal Prometheus-stack Grafana, which carries the Loki log datasource) using `logcli`.

Credentials are **never handled by this skill**. The wrapper loads the octo-tools PowerShell profile, which dot-sources the private profile holding `LOKI_USERNAME` / `LOKI_PASSWORD`, then resolves the cluster's Loki datasource-proxy URL and runs `logcli`. If credentials are missing, direct the user to **`/octo-logs-setup`**.

## Prerequisites

- `logcli` on PATH — install with `brew install logcli` (the formula is plain `logcli`, NOT `grafana/tap/logcli`).
- `pwsh` on PATH and the OctoMesh monorepo workspace (provides `octo-tools/modules/profile.ps1`).
- `LOKI_USERNAME` / `LOKI_PASSWORD` set by the private profile — see `/octo-logs-setup`.
- Network reachability to the cluster (VPN / Tailscale).

## Invocation Pattern

All queries go through the wrapper. Pass the cluster first, then a normal `logcli` sub-command:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" <cluster> <logcli-subcommand> [args...]
```

- `<cluster>` is one of: `test-2`, `staging-1`, `prod-1`, `prod-2`.
- **Always single-quote the LogQL query** so bash does not eat the `{`, `}`, `|`, `"` characters.
- logcli writes results to stdout; its info line goes to stderr (append `2>/dev/null` to silence it).

Examples:

```bash
# List available labels (connectivity check)
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 labels

# Last hour of errors from one service
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 \
  query --since=1h --limit=200 '{namespace="octo", container="identity", level="ERROR"}'

# Dump 10k error lines to a file for offline analysis
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 \
  query --since=24h --limit=10000 '{namespace="octo", level="ERROR"}' > errors.log
```

## Key logcli flags

| Flag | Use |
|---|---|
| `--since=1h` / `--since=24h` | Relative window back from now |
| `--from`/`--to` (RFC3339) | Absolute window (max 30-day span) |
| `--limit=N` | Cap lines (default 30); raise for dumps |
| `--forward` | Oldest-first (default is newest-first) — use to find the FIRST occurrence |
| `--quiet` | Suppress logcli's own stderr info line |
| `-o raw` | Just the log line, no labels |
| `instant-query '<metric>'` | Single-value metric (counts/rates) instead of a log stream |

## LogQL essentials

A query is a **label selector** `{...}` (required) plus optional **line filters** (`|=`, `|~`, `!=`).

```logql
{namespace="octo"}                                        # whole namespace
{namespace="octo", container="identity"}                  # one service
{namespace="octo", level="ERROR"}                         # all errors
{namespace="octo", container="identity", level=~"ERROR|WARN"}
{namespace="octo", level="ERROR", source=~"Octo.Identity.*"}   # by NLog source class
{namespace="octo"} |= "Exception"                         # substring (fast)
{namespace="octo"} |~ "(?i)timeout"                       # regex, case-insensitive
{namespace="octo", level="ERROR"} != "/healthz"           # exclude noise
```

Labels: `namespace`, `container`, `pod`, and (for `octo`-namespace app logs only) `level` and `source`. Pods **outside** `octo` (ponton, mongodb, cratedb) have **no `level` label** — filter inline, e.g. `{namespace="ponton"} |~ "(?i)\\bERROR\\b"`.

Full reference: `references/logql-cheatsheet.md`. Cluster URLs, retention and the two-Grafana gotcha: `references/clusters.md`.

## Counting / rates (instant-query)

```bash
# Errors per container in the last 24h
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 \
  instant-query 'sort_desc(sum by (container) (count_over_time({namespace="octo", level="ERROR"}[24h])))'

# Error sources within one container
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 \
  instant-query 'sort_desc(sum by (source) (count_over_time({namespace="octo", container="identity", level="ERROR"}[24h])))'
```

## Tracing an error across deployments

The `pod` name's middle segment is the **ReplicaSet hash** — a new hash = a new deployment rollout. The `container` label is stable across rollouts. To follow an error across redeploys, **keep `container`, drop `pod`**, then group by `pod`:

```bash
# Which deployments carry this error (each pod hash = one rollout)
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 \
  instant-query 'sort_desc(sum by (pod) (count_over_time({namespace="octo", container="identity"} |= "ObjectDisposedException" [168h])))'

# First occurrence in a specific deployment (--forward = oldest first)
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 \
  query --since=168h --limit=1 --forward '{namespace="octo", container="identity", pod="<pod-name>"} |= "ObjectDisposedException"'
```

Note: for cross-deployment hunting prefer a **line filter (`|=`)** over the `source` label — `source`/`level` are only attached to lines the log parser recognized, so some lines are missed by a `source=` filter but caught by `|=`.

## Retention

**~7 days per cluster.** Queries older than that return nothing; a single query may also span at most ~30 days. For longer history, dump to a file before it ages out (`query --since=24h --limit=10000 ... > file.log`).

## Safety

- All operations here are **read-only** (queries only — never writes).
- **Be deliberate on `prod-1` / `prod-2`.** Confirm the cluster with the user before running prod queries, prefer tight `--since` windows, and never paste customer PII from prod logs into shared channels.
- Never echo `LOKI_PASSWORD`. The wrapper keeps it inside the PowerShell session; do not add commands that print it.

## Execution Flow

1. **Pick the cluster** — default `test-2` unless the user names another; confirm before prod.
2. **Build the LogQL** — start from the recipes above / `references/logql-cheatsheet.md`; single-quote it.
3. **Run via the wrapper** — logs → `query`; counts/rates → `instant-query`.
4. **If credentials are missing** (`LOKI_USERNAME / LOKI_PASSWORD are not set`) → tell the user to run `/octo-logs-setup`.
5. **Summarize** — surface the lines/counts that matter; for "what broke" start broad (`level="ERROR"` per container), then drill into the top source/pod.
