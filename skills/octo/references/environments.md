# OctoMesh Environment URL Mappings

These mappings mirror the `Register-OctoCliContext` cmdlet in the OctoMesh developer shell, which is the source of truth for the known installations: `local`, `test-2`, `staging-1`, `prod-1`, `prod-2`.

> **Hostnames are placeholders.** The concrete domains of the shared environments (`<test-2-domain>`, `<staging-domain>`, `<prod-1-domain>`, `<prod-2-domain>`, `<legacy-domain>`, `<registry>`, `<rancher-url>`) are internal. If the plugin `octo-claude-pm` is installed, see its `agent-operating-rules/references/environments.md`; otherwise ask a colleague.

## Environment Service URLs

Every installation except `local` exposes the services as `https://<service>.<installation-domain>/`:

| Service | Host prefix | AddContext flag |
|---|---|---|
| Identity | `connect` | `-isu` |
| Asset | `assets` | `-asu` |
| Bot | `bots` | `-bsu` |
| Communication | `communication` | `-csu` |
| Reporting | `reporting` | `-rsu` |
| AI | `ai` | `-aisu` |

| Installation | Domain placeholder |
|---|---|
| local | `localhost` — Identity `https://localhost:5003/`, Asset `5001`, Bot `5009`, Communication `5015`, Reporting `5007`, AI `5019` |
| test-2 | `<test-2-domain>` |
| staging-1 | `<staging-domain>` |
| prod-1 | `<prod-1-domain>` |
| prod-2 | `<prod-2-domain>` |

Older installations on a legacy domain (`<legacy-domain>`) may still exist; the `Invoke-OctoCliLoginProduction` / `Invoke-OctoCliLoginStaging` cmdlets point at them. Prefer `Register-OctoCliContext -Installation prod-1|prod-2|staging-1` for the current clusters.

## URI Suffix (test-2 and the shared clusters)

`Register-OctoCliContext -UriSuffix <suffix>` produces variant deployments by inserting `-<suffix>` into each service host (and `_<suffix>` into the context name). For test-2:
```
https://connect-<suffix>.<test-2-domain>/
https://assets-<suffix>.<test-2-domain>/
https://bots-<suffix>.<test-2-domain>/
https://communication-<suffix>.<test-2-domain>/
https://reporting-<suffix>.<test-2-domain>/
https://ai-<suffix>.<test-2-domain>/
```
The same `-<suffix>` insertion applies to `staging-1`, `prod-1`, and `prod-2` hosts.

## Switching Environment Procedure

Default tenant ID is `meshtest` unless the user specifies otherwise.
Context naming convention: `{installation}_{tenantId}` (e.g. `local_meshtest`, `staging-1_meshtest`, `prod-1_meshmakers`).

**`--context` vs `UseContext`.** The blocks below create a context with `AddContext`, then authenticate it with `LogIn -i --context <ctx>` — the token lands in `<ctx>` and the **active context is left unchanged**, which is the parallel-safe default (a concurrent session pinned to another context won't be disturbed). Then work with `--context <ctx>` per command, or `export OCTO_CLI_CONTEXT=<ctx>` for the session. Use `UseContext -n <ctx>` only to change the persistent default for an interactive shell. If the context already exists with a valid token, skip `LogIn` — just `AuthStatus --context <ctx>` to verify.

### Switch to local
```bash
octo-cli -c AddContext -n local_meshtest -isu "https://localhost:5003/" -asu "https://localhost:5001/" -bsu "https://localhost:5009/" -csu "https://localhost:5015/" -tid meshtest
octo-cli -c LogIn -i --context local_meshtest
```

### Switch to test-2
```bash
octo-cli -c AddContext -n test-2_meshtest -isu "https://connect.<test-2-domain>/" -asu "https://assets.<test-2-domain>/" -bsu "https://bots.<test-2-domain>/" -csu "https://communication.<test-2-domain>/" -tid meshtest
octo-cli -c LogIn -i --context test-2_meshtest
```

### Switch to staging-1
```bash
octo-cli -c AddContext -n staging-1_meshtest -isu "https://connect.<staging-domain>/" -asu "https://assets.<staging-domain>/" -bsu "https://bots.<staging-domain>/" -csu "https://communication.<staging-domain>/" -tid meshtest
octo-cli -c LogIn -i --context staging-1_meshtest
```

### Switch to prod-1 / prod-2
```bash
# prod-1 (substitute prod-2 for the second production cluster)
octo-cli -c AddContext -n prod-1_meshmakers -isu "https://connect.<prod-1-domain>/" -asu "https://assets.<prod-1-domain>/" -bsu "https://bots.<prod-1-domain>/" -csu "https://communication.<prod-1-domain>/" -tid meshmakers
octo-cli -c LogIn -i --context prod-1_meshmakers
```

### Include reporting / AI services
Add `-rsu` and/or `-aisu` to the `AddContext` command:
```bash
# Example for test-2 with reporting + AI
octo-cli -c AddContext -n test-2_meshtest -isu "https://connect.<test-2-domain>/" -asu "https://assets.<test-2-domain>/" -bsu "https://bots.<test-2-domain>/" -csu "https://communication.<test-2-domain>/" -rsu "https://reporting.<test-2-domain>/" -aisu "https://ai.<test-2-domain>/" -tid meshtest
octo-cli -c LogIn -i --context test-2_meshtest
```

### Developer-shell shortcut
In the OctoMesh developer shell, the same registration is one command:
```powershell
Register-OctoCliContext -Installation staging-1 -TenantId meshtest
Register-OctoCliContext -Installation test-2 -TenantId voest -UriSuffix pr123 -IncludeReporting
Register-OctoCliContext -Installation prod-1 -TenantId meshmakers -NoLogin   # CI / client-credentials flow
Register-OctoCliContext -Installation local -TenantId meshtest -IncludeAi
```
Switches: `-IncludeReporting` (`-rsu`), `-IncludeAi` (`-aisu`), `-NoSwitch` (skip `UseContext`), `-NoLogin` (skip interactive login). `-TenantId` takes a list: `Register-OctoCliContext -Installation test-2 -TenantId tecob,lkv,wwc26 -NoSwitch` registers one context per tenant (never switches the active one; each new context is logged in by name unless `-NoLogin`). Use them with `Invoke-OctoTenantSweep`, see `tenant-tokens.md`.

### Work against a previously authenticated context
```bash
octo-cli -c AuthStatus --context local_meshtest   # verify the token is still valid, active context untouched
# then run commands with --context local_meshtest, or: export OCTO_CLI_CONTEXT=local_meshtest
# UseContext -n local_meshtest only if you want to change the persistent default
```

## Environment Detection from URLs

| URL Pattern | Installation |
|---|---|
| `localhost:500x` | local |
| `*.<test-2-domain>` | test-2 |
| `*.<staging-domain>` | staging-1 |
| `*.<prod-1-domain>` | prod-1 |
| `*.<prod-2-domain>` | prod-2 |
| `*.<legacy-domain>` | legacy staging / production domains |
