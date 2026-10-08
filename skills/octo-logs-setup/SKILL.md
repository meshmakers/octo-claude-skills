---
name: octo-logs-setup
description: "One-time setup and health check of the Dash0 MCP connection that /octo-logs relies on to read OctoMesh cluster logs (datasets test-2, staging-1, prod-1, prod-2). Registers the Dash0 MCP server in Claude Code, walks through the browser OAuth login via /mcp, and verifies access with listDatasets. Replaces the former Loki credential setup (LOKI_USERNAME / LOKI_PASSWORD) — Loki no longer exists; old LOKI_* variables can be deleted from the private profile. Run this when the mcp__dash0__* tools are missing or return auth errors. Trigger on: set up log access, configure log access, octo-logs setup, Dash0 MCP, dash0 tools missing, mcp__dash0 not available, Dash0 login, Dash0 auth, log credentials missing, LOKI_USERNAME, LOKI_PASSWORD, logcli auth."
---

# OctoMesh Log Access — Dash0 MCP Setup

## Overview

`/octo-logs` reads cluster logs exclusively through the **Dash0 MCP server**
(`mcp__dash0__*` tools). There are no log credentials to store any more: the MCP
connection authenticates with Dash0 via OAuth in the browser, and Claude Code
keeps the token. Loki/logcli and the `LOKI_USERNAME` / `LOKI_PASSWORD` variables
are obsolete (Loki was removed from all clusters, AB#6116).

## Step 1 — check whether the tools are already there

Call `mcp__dash0__listDatasets`. Expected datasets: `test-2`, `staging-1`,
`prod-1`, `prod-2` (plus an empty `default`).

- Works → setup is done, go back to `/octo-logs`.
- Tool unknown / not listed → Step 2.
- Auth error → Step 3.

## Step 2 — register the Dash0 MCP server (user runs this)

The OctoMesh org uses the EU endpoint. Register it for the monorepo workspace
(or with `--scope user` for all projects):

```bash
claude mcp add --transport http --scope local dash0 https://api.europe-west4.gcp.dash0.com/mcp
```

Then restart the Claude Code session so the tools load.

## Step 3 — log in

In Claude Code run `/mcp`, select **dash0** and choose *Authenticate*. The browser
opens the Dash0 login (meshmakers org). After the redirect the server shows as
connected. The assistant cannot do this step — ask the user.

## Step 4 — verify

`mcp__dash0__listDatasets`, then a minimal query:

```json
mcp__dash0__getLogRecords {
  "dataset": "test-2",
  "timeRange": {"from": "now-15m", "to": "now"},
  "filters": [{"key": "k8s.namespace.name", "value": "octo"}],
  "pagination": {"limit": 3}
}
```

Lines come back → `/octo-logs` is ready.

## Cleanup of the old Loki setup (optional)

Earlier versions of this skill wrote `LOKI_USERNAME` / `LOKI_PASSWORD` (and
per-cluster `LOKI_*_<CLUSTER>` variants) into the private PowerShell profile
(`~/.config/powershell/Microsoft.PowerShell_profile_private.ps1` on macOS,
`~/.pwsh/profile.ps1` elsewhere). They are no longer read by anything. The user
can remove those lines; the assistant must not print the file (it holds other
secrets) — at most list matching variable **names**:

```bash
grep -o '\$env:LOKI_[A-Z0-9_]*' ~/.config/powershell/Microsoft.PowerShell_profile_private.ps1 | sort -u
```
