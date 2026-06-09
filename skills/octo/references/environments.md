# OctoMesh Environment URL Mappings

These mappings mirror the `Register-OctoCliContext` cmdlet in the OctoMesh developer shell, which is the source of truth for the known installations: `local`, `test-2`, `staging-1`, `prod-1`, `prod-2`. The newer cluster installations use `*.octo-mesh.com` domains; the older `*.meshmakers.cloud` domains are still valid as legacy production/staging.

## Environment Service URLs

| Installation | Identity (`-isu`) | Asset (`-asu`) | Bot (`-bsu`) | Communication (`-csu`) | Reporting (`-rsu`) | AI (`-aisu`) |
|---|---|---|---|---|---|---|
| local | `https://localhost:5003/` | `https://localhost:5001/` | `https://localhost:5009/` | `https://localhost:5015/` | `https://localhost:5007/` | `https://localhost:5019/` |
| test-2 | `https://connect.test-2.mm.cloud/` | `https://assets.test-2.mm.cloud/` | `https://bots.test-2.mm.cloud/` | `https://communication.test-2.mm.cloud/` | `https://reporting.test-2.mm.cloud/` | `https://ai.test-2.mm.cloud/` |
| staging-1 | `https://connect.staging.octo-mesh.com/` | `https://assets.staging.octo-mesh.com/` | `https://bots.staging.octo-mesh.com/` | `https://communication.staging.octo-mesh.com/` | `https://reporting.staging.octo-mesh.com/` | `https://ai.staging.octo-mesh.com/` |
| prod-1 (Exoscale SKS Vienna) | `https://connect.prod-1.octo-mesh.com/` | `https://assets.prod-1.octo-mesh.com/` | `https://bots.prod-1.octo-mesh.com/` | `https://communication.prod-1.octo-mesh.com/` | `https://reporting.prod-1.octo-mesh.com/` | `https://ai.prod-1.octo-mesh.com/` |
| prod-2 (Azure AKS) | `https://connect.prod-2.octo-mesh.com/` | `https://assets.prod-2.octo-mesh.com/` | `https://bots.prod-2.octo-mesh.com/` | `https://communication.prod-2.octo-mesh.com/` | `https://reporting.prod-2.octo-mesh.com/` | `https://ai.prod-2.octo-mesh.com/` |

### Legacy domains (still valid)

| Installation | Identity | Asset | Communication |
|---|---|---|---|
| staging (legacy) | `https://connect.staging.meshmakers.cloud/` | `https://assets.staging.meshmakers.cloud/` | `https://communication.staging.meshmakers.cloud/` |
| production (legacy) | `https://connect.meshmakers.cloud` | `https://assets.meshmakers.cloud/` | `https://communication.meshmakers.cloud/` |

The `Invoke-OctoCliLoginProduction` / `Invoke-OctoCliLoginStaging` cmdlets still point at these legacy `*.meshmakers.cloud` domains; prefer `Register-OctoCliContext -Installation prod-1|prod-2|staging-1` for the current clusters.

## URI Suffix (test-2 and the *.octo-mesh.com clusters)

`Register-OctoCliContext -UriSuffix <suffix>` produces variant deployments by inserting `-<suffix>` into each service host (and `_<suffix>` into the context name). For test-2:
```
https://connect-<suffix>.test-2.mm.cloud/
https://assets-<suffix>.test-2.mm.cloud/
https://bots-<suffix>.test-2.mm.cloud/
https://communication-<suffix>.test-2.mm.cloud/
https://reporting-<suffix>.test-2.mm.cloud/
https://ai-<suffix>.test-2.mm.cloud/
```
The same `-<suffix>` insertion applies to `staging-1`, `prod-1`, and `prod-2` hosts.

## Switching Environment Procedure

Default tenant ID is `meshtest` unless the user specifies otherwise.
Context naming convention: `{installation}_{tenantId}` (e.g. `local_meshtest`, `staging-1_meshtest`, `prod-1_meshmakers`).

If the context already exists with a valid token, skip `LogIn` — just `UseContext` and check `AuthStatus`.

### Switch to local
```bash
octo-cli -c AddContext -n local_meshtest -isu "https://localhost:5003/" -asu "https://localhost:5001/" -bsu "https://localhost:5009/" -csu "https://localhost:5015/" -tid meshtest
octo-cli -c UseContext -n local_meshtest
octo-cli -c LogIn -i
```

### Switch to test-2
```bash
octo-cli -c AddContext -n test-2_meshtest -isu "https://connect.test-2.mm.cloud/" -asu "https://assets.test-2.mm.cloud/" -bsu "https://bots.test-2.mm.cloud/" -csu "https://communication.test-2.mm.cloud/" -tid meshtest
octo-cli -c UseContext -n test-2_meshtest
octo-cli -c LogIn -i
```

### Switch to staging-1
```bash
octo-cli -c AddContext -n staging-1_meshtest -isu "https://connect.staging.octo-mesh.com/" -asu "https://assets.staging.octo-mesh.com/" -bsu "https://bots.staging.octo-mesh.com/" -csu "https://communication.staging.octo-mesh.com/" -tid meshtest
octo-cli -c UseContext -n staging-1_meshtest
octo-cli -c LogIn -i
```

### Switch to prod-1 / prod-2
```bash
# prod-1 (substitute prod-2 for the Azure AKS cluster)
octo-cli -c AddContext -n prod-1_meshmakers -isu "https://connect.prod-1.octo-mesh.com/" -asu "https://assets.prod-1.octo-mesh.com/" -bsu "https://bots.prod-1.octo-mesh.com/" -csu "https://communication.prod-1.octo-mesh.com/" -tid meshmakers
octo-cli -c UseContext -n prod-1_meshmakers
octo-cli -c LogIn -i
```

### Include reporting / AI services
Add `-rsu` and/or `-aisu` to the `AddContext` command:
```bash
# Example for test-2 with reporting + AI
octo-cli -c AddContext -n test-2_meshtest -isu "https://connect.test-2.mm.cloud/" -asu "https://assets.test-2.mm.cloud/" -bsu "https://bots.test-2.mm.cloud/" -csu "https://communication.test-2.mm.cloud/" -rsu "https://reporting.test-2.mm.cloud/" -aisu "https://ai.test-2.mm.cloud/" -tid meshtest
octo-cli -c UseContext -n test-2_meshtest
```

### Developer-shell shortcut
In the OctoMesh developer shell, the same registration is one command:
```powershell
Register-OctoCliContext -Installation staging-1 -TenantId meshtest
Register-OctoCliContext -Installation test-2 -TenantId voest -UriSuffix pr123 -IncludeReporting
Register-OctoCliContext -Installation prod-1 -TenantId meshmakers -NoLogin   # CI / client-credentials flow
Register-OctoCliContext -Installation local -TenantId meshtest -IncludeAi
```
Switches: `-IncludeReporting` (`-rsu`), `-IncludeAi` (`-aisu`), `-NoSwitch` (skip `UseContext`), `-NoLogin` (skip interactive login).

### Switch back to a previously authenticated context
```bash
octo-cli -c UseContext -n local_meshtest
octo-cli -c AuthStatus   # verify the token is still valid
```

## Environment Detection from URLs

| URL Pattern | Installation |
|---|---|
| `localhost:500x` | local |
| `*.test-2.mm.cloud` | test-2 |
| `*.staging.octo-mesh.com` | staging-1 |
| `*.prod-1.octo-mesh.com` | prod-1 (Exoscale SKS Vienna) |
| `*.prod-2.octo-mesh.com` | prod-2 (Azure AKS) |
| `*.staging.meshmakers.cloud` | staging (legacy domain) |
| `*.meshmakers.cloud` (no staging/test prefix) | production (legacy domain) |
