---
name: octo-logs-setup
description: One-time, safe setup of the Loki / monitoring-Grafana credentials that the /octo-logs skill relies on. Stores LOKI_USERNAME / LOKI_PASSWORD in the gitignored private PowerShell profile that the octo-tools profile dot-sources — sourced from Keeper or Vault, with the password piped straight from the secret store into a writer that never prints it or takes it as a CLI argument. Supports per-cluster credentials. Run this when /octo-logs reports credentials are missing. Trigger on: set up Loki credentials, configure log access, LOKI_USERNAME, LOKI_PASSWORD, monitoring Grafana password, store Grafana credentials, logcli auth, log credentials missing, octo-logs setup, Keeper Grafana monitoring, Vault grafana admin_password, private profile credentials.
allowed-tools:
  - "Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/octo-logs-setup/scripts/setup_loki_creds.sh:*)"
---

# OctoMesh Log Access — Safe Credential Setup

## Overview

Configure the `mesh-admin` monitoring-Grafana credentials that **`/octo-logs`** uses, so that skill never has to handle them. "Safe" here means:

- Credentials live **only** in the machine-local **private PowerShell profile** (gitignored, outside any repo) that the octo-tools profile dot-sources — never committed, never in a tracked file.
- The password is **sourced from Keeper or Vault**, piped straight into the writer; it is **never passed as a CLI argument** (no shell-history / process-listing leak) and **never printed back**.
- The private profile is forced to perms **600**.

## How the credential flows

```
octo-tools/modules/profile.ps1  ──dot-sources──▶  private profile
                                                   $env:LOKI_USERNAME
                                                   $env:LOKI_PASSWORD
                                                          │
                                  /octo-logs ── run_logcli.sh loads the profile ──▶ logcli
```

Private profile path:
- **macOS**: `~/.config/powershell/Microsoft.PowerShell_profile_private.ps1`
- **Linux/Windows**: `~/.pwsh/profile.ps1`

Source of the password (shared `mesh-admin` login, per cluster):
- **Keeper** → entry "Grafana monitoring `<cluster>`"
- **Vault** → `meshmakers/<cluster>/grafana`, field `admin_password` (`VAULT_ADDR=https://vault.mm.cloud`)

## CRITICAL — never expose the password

**Do NOT write a command that contains the password** (the assistant must never type it). Only two safe paths:

1. **Vault pipe** — the secret stays inside the pipe, never in output. Safe for the assistant to run *if* `vault` is authenticated.
2. **User-pasted pipe via the `!` session prefix** — the user runs it themselves so the secret is in their input, not the assistant's.

## Step 1 — check current state (no secrets printed)

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs-setup/scripts/setup_loki_creds.sh" status
```

Reports the private-profile path, its perms, and which `LOKI_*` variable **names** are already defined. If `LOKI_USERNAME`/`LOKI_PASSWORD` are present, setup is likely already done — try `/octo-logs` directly.

## Step 2 — write the credentials safely

### Option A — from Vault (preferred; secret stays in the pipe)

If `vault` is authenticated, this can be run directly:

```bash
vault kv get -field=admin_password meshmakers/test-2/grafana \
  | bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs-setup/scripts/setup_loki_creds.sh" write
```

If Vault needs login first, ask the user to run it in-session (interactive auth):

> Please run: `! vault login -method=oidc` (or your usual Vault auth method)

If the KV mount differs from the default, the user adjusts with `-mount=<mount>`.

### Option B — from Keeper (user pastes; run via the `!` prefix)

Ask the user to copy the password from Keeper ("Grafana monitoring `<cluster>`") and run, **themselves**, in the session:

```
! printf %s 'PASTE_PASSWORD_HERE' | bash "<plugin>/skills/octo-logs-setup/scripts/setup_loki_creds.sh" write
```

(Provide the real expanded script path. The `!` prefix runs it in their session, keeping the secret out of the assistant's output.)

### Writer options

- `-u <username>` — default `mesh-admin`.
- `-c <cluster>` — write **per-cluster** vars `LOKI_USERNAME_<SUF>` / `LOKI_PASSWORD_<SUF>` (SUF = uppercase cluster, dashes removed, e.g. `prod-1` → `PROD1`). Use this only if clusters have **different** passwords; otherwise the generic pair (no `-c`) is used for all clusters.

The writer is idempotent — re-running replaces the same variables in place and leaves others untouched.

## Step 3 — activate and verify

The variables load on the next shell / profile load. `/octo-logs` loads the profile fresh per call, so verify immediately:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/octo-logs/scripts/run_logcli.sh" test-2 labels
```

A clean label list = credentials work. A `LOKI_USERNAME / LOKI_PASSWORD are not set` error = the write did not land in the profile this skill expects (re-check `status`).

## Per-cluster credentials

If `prod-1`/`prod-2` use a different password than `test-2`, write each with `-c`:

```bash
vault kv get -field=admin_password meshmakers/prod-1/grafana \
  | bash ".../setup_loki_creds.sh" write -c prod-1
```

`/octo-logs` prefers `LOKI_*_<CLUSTER>` and falls back to the generic pair, so a single generic pair is enough when the password is shared across the clusters you use.

## Safety rules

- Never echo, log, or paste `LOKI_PASSWORD` into the conversation or any tracked file.
- Never run a command that embeds the password literally — use the Vault pipe or the user's `!`-prefixed paste.
- Confirm the private profile is gitignored / outside any repo before writing (it is, by location).
- `status` is always safe to run; it prints names, never values.
