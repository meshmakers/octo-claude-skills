# test-2 environment — contexts, auth, tenants, network

Verified 2026-06-10 against `octo-tools` cmdlet sources, the octo skill's
environments reference, and `meshmakers_staging` cluster values. Staging/prod
are out of scope.

## Service URLs

| Service | URL | AddContext flag |
|---|---|---|
| Identity | `https://connect.test-2.mm.cloud/` | `-isu` |
| Asset | `https://assets.test-2.mm.cloud/` | `-asu` |
| Bot | `https://bots.test-2.mm.cloud/` | `-bsu` |
| Communication | `https://communication.test-2.mm.cloud/` | `-csu` |
| Reporting | `https://reporting.test-2.mm.cloud/` | `-rsu` |
| AI | `https://ai.test-2.mm.cloud/` | `-aisu` |
| Admin Panel | `https://adminpanel.test-2.mm.cloud` | — |
| Studio | `https://studio.test-2.mm.cloud` | — |

PR sub-environments exist via URI suffix: `-UriSuffix pr123` →
`assets-pr123.test-2.mm.cloud`, context `test-2_pr123_<tenantId>`.

## Context registration

Preferred (octo-tools cmdlet, source: `Register-OctoCliContext.psm1`):

```powershell
Register-OctoCliContext -Installation test-2 -TenantId <tenantId>
# optional: -IncludeReporting -IncludeAi   (NOT included by default)
#           -UriSuffix pr123              (PR sub-environment)
#           -NoSwitch                     (register without activating)
#           -NoLogin                      (skip the interactive login)
```

Creates/updates context `test-2_<tenantId>`, activates it, runs `Login -i`.

Raw octo-cli equivalent:

```powershell
octo-cli -c AddContext -n test-2_<tenantId> `
  -isu "https://connect.test-2.mm.cloud/" -asu "https://assets.test-2.mm.cloud/" `
  -bsu "https://bots.test-2.mm.cloud/" -csu "https://communication.test-2.mm.cloud/" `
  -tid <tenantId>
octo-cli -c Login -i --context test-2_<tenantId>
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

- **Interactive (human):** `octo-cli -c Login -i` — browser/device-code flow.
- **Headless (agent/CI):** `octo-cli -c LogInClientCredentials` with
  `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET` (or `-id`/`-s`). Requires a
  client-credentials client provisioned for the target tenant (the octo skill's
  `references/temp-tenants.md` documents the pattern for local; whether the
  `claude-agent` client exists on test-2's `octosystem` is NOT verified — check
  with `GetClients` on a test-2 octosystem context before relying on it).

## Creating a tenant on test-2

1. Ensure an **octosystem** context on test-2 exists (`Register-OctoCliContext
   -Installation test-2 -TenantId octosystem`); target it below with `--context
   test-2_octosystem`.
2. `octo-cli -c Create -tid <tenantId> -db <tenantId> --context test-2_octosystem`
   — interactive sessions provision the current user as tenant admin. Headless
   sessions MUST add `-np` (machine tokens carry no user to provision). Tenant
   IDs are lowercased.
3. `octo-cli -c EnableCommunication --context test-2_<tenantId>` — must run
   against the TARGET tenant context, not octosystem (pass its `--context`, no
   switching needed). This only
   SEEDS the Pool/Adapter/HelmRepo entities (`670…001/002/003`) — it deploys
   nothing. `GetAdapters` may return 500 until communication is enabled.
4. **Deploy the Pool** (live-verified 2026-06-10: nothing rolls out while the
   pool is `Undeployed`, and deploy triggers fired in that state are silently
   lost). No octo-cli command exists — REST only:
   `POST https://communication.test-2.mm.cloud/<tenantId>/v1/Pool/deploy?poolRtId=670000000000000000000001`
   with the bearer token from `~/.octo-cli/contexts.json` → 204.
   `GetPools -j` → `Online`/`Deployed`.
5. `octo-cli -c DeployWorkload -id 670000000000000000000002` (re-trigger after
   the pool is up), then `octo-cli -c GetAdapters -j` until the Mesh Adapter
   shows Online (~1 min: operator provisions the CommunicationPool CR, then
   Helm-installs the adapter pod `<tenantId>-670…002-…`).

## The environment gate (`requires: octo.environment`)

`${octo.environment}` on test-2 comes from `OCTO_BLUEPRINTS__ENVIRONMENT` on
the asset-repo deployment. Two sources disagree about its value:
- the helm values chain (`octo-mesh` chart default `dev`, not overridden in
  `test-2-values.yaml`) ⇒ `dev`
- blueprint comments (ZenonDynprop) treat test-2 as the `test` channel ⇒ `test`

The runtime value was NOT verified. Consequence for authors: gate test-2-bound
blueprints with **both** values —

```yaml
requires:
  octo.environment: [dev, test]
```

Probe on first use: `InstallBlueprint` and check the response — a successful
no-op with `WasSkipped: true` means the gate didn't match the actual value.

## Network access

- `*.test-2.mm.cloud` services: publicly reachable (TLS via mm-cloud certs).
- `docker.mm.cloud` (image registry): internal network only — office WiFi
  direct, otherwise Tailscale first. Reachability probe:
  `curl -skI https://docker.mm.cloud/v2/` → `HTTP/1.1 200 OK` with
  `Docker-Distribution-Api-Version: registry/2.0`.
- kubectl access to test-2 EXISTS via a Rancher kubeconfig download
  (`https://rancher.mm.cloud`, publicly reachable — no VPN). Caveats:
  - The downloaded yaml is NOT auto-integrated — merge it:
    `$env:KUBECONFIG="$env:USERPROFILE\.kube\config;<downloaded.yaml>";
    kubectl config view --flatten > merged; mv merged ~/.kube/config`
    (context name `test-2`).
  - Older `k3s-test-2` contexts route via `rancher.srv.mm.local` (internal,
    needs VPN) — connection refused off-VPN; prefer the `rancher.mm.cloud` one.
  - Asset-repo deployment (for the blueprint-catalog cache restart):
    `octo/octo-mesh-asset-rep-services`.
- Without kubectl, observability runs through octo-cli status commands and the
  workload entities' `deploymentState`/`statusMessage`/`lastDeploymentError`
  attributes (rt_explorer / Studio).
