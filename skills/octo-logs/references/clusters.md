# Clusters, Grafana endpoints, retention

Source: OctoMesh wiki — "View application logs and set up alerts"
(`https://dev.azure.com/meshmakers/OctoMesh/_wiki/wikis/OctoMesh.wiki/238/Access-clusters-and-filter-logs`).

## Two Grafanas per cluster — do not confuse them

| Host | What it is | Logs? |
|---|---|---|
| `monitoring.<cluster-domain>` | **Prometheus-stack Grafana** (internal). Carries the **Loki** datasource. | **Yes — use this.** |
| `grafana.<cluster-domain>` | OctoMesh-Grafana, OAuth, end-customer-facing. | No Loki datasource. |

This skill always targets the `monitoring.*` host.

## Cluster → monitoring Grafana base URL

| Cluster | Monitoring URL |
|---|---|
| `test-2` (testing / pre-staging) | `https://monitoring.test-2.mm.cloud` |
| `staging-1` (staging) | `https://monitoring.staging.octo-mesh.com` |
| `prod-1` (production EU) | `https://monitoring.prod-1.octo-mesh.com` |
| `prod-2` (production AT) | `https://monitoring.prod-2.octo-mesh.com` |

These are baked into `scripts/_logcli.ps1` (`$baseMap`). Add a cluster there if a new one appears.

## Why logcli points at a datasource-proxy path (not the host root)

Loki is **not** exposed directly on the `monitoring.*` host — that host root is Grafana itself. The wiki's `LOKI_ADDR=https://monitoring.<domain>` points logcli at Grafana's root and returns HTML instead of logs.

Loki is reachable through Grafana's **datasource proxy**:

```
https://monitoring.<domain>/api/datasources/proxy/uid/<loki-datasource-uid>
```

`_logcli.ps1` discovers `<loki-datasource-uid>` at runtime by calling
`GET /api/datasources` (basic auth) and picking the entry with `type == "loki"` —
so no UID is hard-coded and it works across clusters. (For reference, test-2's
Loki UID has historically been `P8E80F9AEF21F6940`, but do not rely on that —
discovery is authoritative.)

## Login / credentials

- User `mesh-admin`, password from the team store (Keeper → "Grafana monitoring `<cluster>`", or Vault `meshmakers/<cluster>/grafana` → `admin_password`).
- Everyone shares this admin login.
- The skill reads `LOKI_USERNAME` / `LOKI_PASSWORD` from the private PowerShell profile. Set them via `/octo-logs-setup`.
- If clusters use distinct passwords, set per-cluster overrides `LOKI_USERNAME_<CLUSTER>` / `LOKI_PASSWORD_<CLUSTER>` (suffix = uppercase cluster with dashes removed, e.g. `LOKI_PASSWORD_PROD1`); the wrapper prefers those and falls back to the generic pair.

## Retention

- **~7 days per cluster** (Loki retention). Older lines are gone.
- A single query may span at most ~30 days of time range (a separate server limit), so `--since` beyond ~30d errors out regardless.
- For longer-lived history, dump before it ages out:
  ```bash
  bash run_logcli.sh test-2 query --since=24h --limit=10000 '{namespace="octo", level="ERROR"}' > errors.log
  ```

## logcli installation note

The wiki's `brew install grafana/tap/logcli` formula no longer exists. Use:

```bash
brew install logcli
```
