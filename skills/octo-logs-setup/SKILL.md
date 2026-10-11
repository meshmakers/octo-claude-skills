---
name: octo-logs-setup
description: "One-time setup and health check of the Dash0 MCP connection that /octo-logs relies on to read OctoMesh cluster logs. Walks through registering the Dash0 MCP server in Claude Code, the browser OAuth login via /mcp, and verifies access with listDatasets. Replaces the former Loki credential setup (LOKI_USERNAME / LOKI_PASSWORD) — Loki no longer exists; old LOKI_* variables can be deleted from the private profile. Run this when the mcp__dash0__* tools are missing or return auth errors. Trigger on: set up log access, configure log access, octo-logs setup, Dash0 MCP, dash0 tools missing, mcp__dash0 not available, Dash0 login, Dash0 auth, log credentials missing, LOKI_USERNAME, LOKI_PASSWORD, logcli auth."
---

# OctoMesh Log Access — Dash0 MCP Setup

## Overview

`/octo-logs` reads logs exclusively through the **Dash0 MCP server**
(`mcp__dash0__*` tools). There are no log credentials to store: the MCP
connection authenticates with Dash0 via OAuth in the browser, and Claude Code
keeps the token. Loki/logcli and the `LOKI_USERNAME` / `LOKI_PASSWORD` variables
are obsolete.

**Internal details** — the MCP endpoint URL of the organization, the Dash0
organization to log in to, the datasets: if the plugin `octo-claude-pm` is
installed, its internal reference `agent-operating-rules/references/dash0.md`
holds them. This public plugin deliberately contains none. Without that plugin,
ask a colleague or your Dash0 administrator for the MCP endpoint.

## Step 1 — check whether the tools are already there

Call `mcp__dash0__listDatasets`.

- Works and returns datasets → setup is done, go back to `/octo-logs`.
- Tool unknown / not listed → Step 2.
- Auth error → Step 3.

## Step 2 — register the Dash0 MCP server (user runs this)

Register the MCP server for the workspace (or with `--scope user` for all
projects). `<mcp-endpoint>` is the HTTP MCP URL of your organization's Dash0
region (see the internal reference):

```bash
claude mcp add --transport http --scope local dash0 <mcp-endpoint>
```

Then restart the Claude Code session so the tools load.

## Step 3 — log in

In Claude Code run `/mcp`, select **dash0** and choose *Authenticate*. The browser
opens the Dash0 login of your organization. After the redirect the server shows
as connected. The assistant cannot do this step — ask the user.

## Step 4 — verify

`mcp__dash0__listDatasets`, then a minimal query against one of the returned
datasets:

```json
mcp__dash0__getLogRecords {
  "dataset": "<dataset>",
  "timeRange": {"from": "now-15m", "to": "now"},
  "filters": [{"key": "k8s.namespace.name", "value": "octo"}],
  "pagination": {"limit": 3}
}
```

Lines come back → `/octo-logs` is ready.

## Cleanup of the old Loki setup (optional)

Earlier versions of this skill wrote `LOKI_USERNAME` / `LOKI_PASSWORD` (and
per-cluster `LOKI_*_<CLUSTER>` variants) into a private PowerShell profile. They
are no longer read by anything. The user can remove those lines; the assistant
must not print the profile (it holds other secrets).
