# test-2 environment — contexts, auth, tenants, network

> **Hostnames are placeholders.** The concrete domains of the shared environments (`<test-2-domain>`, `<staging-domain>`, `<prod-1-domain>`, `<prod-2-domain>`, `<legacy-domain>`, `<registry>`, `<rancher-url>`) are internal. If the plugin `octo-claude-pm` is installed, see its `agent-operating-rules/references/environments.md`; otherwise ask a colleague.

Verified 2026-06-10 against `octo-tools` cmdlet sources, the octo skill's
environments reference, and `meshmakers_staging` cluster values. Staging/prod
are out of scope.

## Service URLs

| Service | URL | AddContext flag |
|---|---|---|
| Identity | `https://connect.<test-2-domain>/` | `-isu` |
| Asset | `https://assets.<test-2-domain>/` | `-asu` |
| Bot | `https://bots.<test-2-domain>/` | `-bsu` |
| Communication | `https://communication.<test-2-domain>/` | `-csu` |
| Reporting | `https://reporting.<test-2-domain>/` | `-rsu` |
| AI | `https://ai.<test-2-domain>/` | `-aisu` |
| Admin Panel | `https://adminpanel.<test-2-domain>` | — |
| Studio | `https://studio.<test-2-domain>` | — |

PR sub-environments exist via URI suffix: `-UriSuffix pr123` →
`assets-pr123.<test-2-domain>`, context `test-2_pr123_<tenantId>`.

## Context registration

Preferred (octo-tools cmdlet, source: `Register-OctoCliContext.psm1`):

```powershell
Register-OctoCliContext -Installation test-2 -TenantId <tenantId>
# optional: -IncludeReporting -IncludeAi   (NOT included by default)
#           -UriSuffix pr123              (PR sub-environment)
#           -TenantId a,b,c               (one context per tenant, never activates; AB#6840)
#           -NoSwitch                     (register without activating)
#           -NoLogin                      (skip the interactive login)
```

Creates/updates context `test-2_<tenantId>`, activates it, runs `Login -i`.

Raw octo-cli equivalent:

```powershell
octo-cli -c AddContext -n test-2_<tenantId> `
  -isu "https://connect.<test-2-domain>/" -asu "https://assets.<test-2-domain>/" `
  -bsu "https://bots.<test-2-domain>/" -csu "https://communication.<test-2-domain>/" `
  -tid <tenantId>
octo-cli -c LogIn -i --context test-2_<tenantId>
octo-cli -c AuthStatus --context test-2_<tenantId>
```

Notes:
- The legacy `Invoke-OctoCliLoginTest2` cmdlet names contexts `test2_…` (no
  hyphen) — a DIFFERENT name than `Register-OctoCliContext`'s `test-2_…`. Don't
  mix; prefer `Register-OctoCliContext`.
- Context discipline: prefer `--context test-2_<tenantId>` (or `export
  OCTO_CLI_CONTEXT=test-2_<tenantId>`) on every call so you don't depend on — or
  mutate — the global active context, which a parallel session could flip.
  `Register-OctoCliContext` still switches the active context; `--context` on the
  commands afterward overrides it per-invocation. Run `AuthStatus` before
  mutating commands. Only `UseContext` if you want a persistent default.

## Authentication

- **Interactive (human):** `octo-cli -c LogIn -i` — browser/device-code flow.
- **Headless (agent/CI):** `octo-cli -c LogInClientCredentials` with
  `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET` (or `-id` plus `--secret-stdin`; never the deprecated `-s`). Requires a
  client-credentials client provisioned for the target tenant (the octo skill's
  `references/temp-tenants.md` documents the pattern for local). Log the client
  into a context of the agent's own (e.g. `agent_<lane>_test-2_octosystem`), never
  into a human's `test-2_*` context: octo-cli refuses to replace an interactive
  login there (AB#9063).
- **Agent client per workstation (test-2):** every workstation that runs agents
  against test-2 has its own client in `octosystem`, so one machine can be
  revoked on its own: id `claude-agent-<user>-<workstation>` (e.g.
  `claude-agent-gerald-wks-1`; `claude-agent` is the legacy shared client).
  Grant `client_credentials` only, scopes `openid profile email role octo_api`,
  role `TenantManagement` only (create/delete scratch tenants). Created with
  `-apic`, so it is mirrored into **new** sub-tenants only — not into existing
  child tenants (no `ProvisionClientInExistingTenants`).
  - Create the secret file **first**:
    `(umask 077; set -C; openssl rand -base64 48 | tr -d '\n' > ~/.octo-cli/<client>.secret)`
    (`set -C` fails instead of overwriting an existing file),
    then `AddClientCredentialsClient … --secret-stdin < ~/.octo-cli/<client>.secret`.
    A client created with an unknown secret must be deleted and recreated —
    adding a second secret leaves the unknown one valid.
  - The human stores the secret in the team's secret store (path: see
    `agent-operating-rules` `references/environments.md` if `octo-claude-pm` is
    installed); agents never write it there.
  - Verify with a temporary context: pipe the secret into
    `LogInClientCredentials -id <client> --secret-stdin`, then `AuthStatus` shows
    role `TenantManagement`, `client_id <client>` and the audiences `octoAPI`
    plus the MCP audience.

## Creating a tenant

1. Ensure an **octosystem** context on the target installation exists<!-- developer-machine --> (`Register-OctoCliContext
   -Installation <installation> -TenantId octosystem`)<!-- /developer-machine -->; target it below with `--context
   <octosystem-context>`.
2. `octo-cli -c Create -tid <tenantId> -db <tenantId> --context <octosystem-context>`
   — interactive sessions provision the current user as tenant admin. Headless
   (client-credentials) sessions add `--scratch` (the client becomes administrator
   of the tenant it creates, no user provisioning; the client needs `-apic` and
   the role `TenantManagement`; clean up with `Delete --disable-features -y`, see
   the octo skill's `references/temp-tenants.md`) or, for a tenant that is not
   a scratch tenant, `-np` (machine tokens carry no user to provision). Tenant
   IDs are lowercased. If the tenant was created without provisioning (`-np`) or
   by someone else, run `octo-cli -c ProvisionCurrentUser -ttid <tenantId>
   --context <octosystem-context>` before using the root operator's token in it: a
   root-tenant user has no implicit rights in a child tenant (AB#6836).
3. `octo-cli -c EnableCommunication --context <tenant-context>` — must run
   against the TARGET tenant context, not octosystem (pass its `--context`, no
   switching needed). This only
   SEEDS the deployment site/Adapter/HelmRepo entities (`670…001/002/003`) — it deploys
   nothing. `GetAdapters` may return 500 until communication is enabled.
4. **Deploy the deployment site** (live-verified 2026-06-10: nothing rolls out
   while it is `Undeployed`, and deploy triggers fired in that state are silently
   lost): `octo-cli -c DeployDeploymentSite -id 670000000000000000000001 --context
   <tenant-context>`, then `GetDeploymentSites -j --context <tenant-context>` →
   `Online`/`Deployed`.
5. `octo-cli -c DeployWorkload -id 670000000000000000000002 --context
   <tenant-context>` (re-trigger after the deployment site is up), then
   `octo-cli -c GetAdapters -j --context <tenant-context>` until the Mesh Adapter
   shows Online (~1 min: operator provisions the DeploymentSite resource, then
   Helm-installs the adapter pod `<tenantId>-670…002-…`).

## The environment gate (`requires: octo.environment`)

`${octo.environment}` comes from the asset repository's configuration
(`OCTO_BLUEPRINTS__ENVIRONMENT`; chart default `dev`), and a test cluster may be
read as either the `dev` or the `test` channel. Gate blueprints meant for a test
cluster with **both** values —

```yaml
requires:
  octo.environment: [dev, test]
```

Probe on first use: `InstallBlueprint` and check the response — a successful
no-op with `WasSkipped: true` means the gate didn't match the actual value.

## Network access

- `*.<test-2-domain>` services: publicly reachable (TLS).
- `<registry>` (image registry): internal network only — office WiFi
  direct, otherwise Tailscale first. Reachability probe:
  `curl -sI https://<registry>/v2/` (registry CA trusted) → `HTTP/1.1 200 OK` (or `401` when the registry requires a login; both mean reachable) with
  `Docker-Distribution-Api-Version: registry/2.0`.
- kubectl access to test-2 EXISTS via a Rancher kubeconfig download
  (`<rancher-url>`, publicly reachable — no VPN). Caveats:
  - The downloaded yaml is NOT auto-integrated — merge it:
    `KUBECONFIG=~/.kube/config:<downloaded.yaml> kubectl config view --flatten > merged && mv merged ~/.kube/config`
    (PowerShell: `$env:KUBECONFIG="$HOME\.kube\config;<downloaded.yaml>"`, then the same `kubectl config view`)
    (context name `test-2`).
  - Older `k3s-test-2` contexts route via `<internal-rancher-host>` (internal,
    needs VPN) — connection refused off-VPN; prefer the `<rancher-url>` one.
  - Use it to read (pods, logs, events). Never restart or change workloads with
    kubectl: blueprint catalogs refresh with `RefreshBlueprintCatalogs`, workloads
    redeploy with `DeployWorkload`.
- Without kubectl, observability runs through octo-cli status commands and the
  workload entities' `deploymentState`/`statusMessage`/`lastDeploymentError`
  attributes (rt_explorer / Studio).
