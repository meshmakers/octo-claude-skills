# Temporary Tenants — Fully Non-Interactive Lifecycle

An agent can create a throwaway tenant, work in it, and delete it **without any user interaction**. The old assumption that `octo-cli` first needs a one-time interactive login (`LogIn -i`) no longer holds — the combination of OAuth2 `client_credentials` login and client mirroring covers the whole lifecycle.

Verified end-to-end on a local environment on 2026-06-10 (create → mirror login → GraphQL read → identity write → delete, all with a machine token).

## How It Works

Two platform features make this possible:

1. **`LogInClientCredentials`** — headless OAuth2 `client_credentials` login. Reads `-id`/`-s` arguments or the `OCTO_CLI_CLIENT_ID` / `OCTO_CLI_CLIENT_SECRET` environment variables. The resulting token carries the `octo_api` scope claim and **no user identity** (no `sub` of a user, no role claims).
2. **Client mirroring** — a client created in the system tenant (`octosystem`) with `-apic` (`AutoProvisionInChildTenants`) is automatically copied (same ClientId, same secret, same scopes) into **every newly created tenant** as part of tenant setup. Provisioning is synchronous: the mirrored client can log in against the new tenant immediately after `Create` returns.

Authorization for tenant create/delete is **scope-based, not role-based**: the asset-service endpoints require only the `octo_api.full_access` scope claim (`TenantAssetApiReadWritePolicy`). A machine token qualifies; no user subject is needed anywhere in the tenant create/delete path.

## One-Time Setup (operator, once per environment)

Requires an existing authenticated session in the **octosystem** context (this is the only step that may ever need a human):

```bash
octo-cli -c AddClientCredentialsClient -id claude-agent -n "Claude Agent (non-interactive automation)" -s "<generated-secret>" -apic --context local_octosystem
```

- The client gets `octo_api.full_access` scope automatically.
- Convention: store the secret at `~/.octo-cli/<clientId>.secret` (same sensitivity class as the tokens already in `~/.octo-cli/contexts.json`). On the local dev environment the client `claude-agent` already exists and its secret is at `~/.octo-cli/claude-agent.secret`.
- `-apic` only works from the system tenant — the mirroring parent is hard-wired to `octosystem`.
- Tenants that existed **before** the client was created don't have the mirror; backfill with `octo-cli -c ProvisionClientInExistingTenants -id claude-agent` or per-tenant `ProvisionClientInTenant -id claude-agent -ctid <tenantId>`.

## Agent Workflow

All steps below run without user interaction, and **every command uses `--context` so the active context is never changed** — a parallel session keeps working undisturbed. Export the credentials once; while they stay exported, octo-cli automatically re-acquires the token on expiry (no refresh token exists for `client_credentials`).

```bash
export OCTO_CLI_CLIENT_ID=claude-agent
export OCTO_CLI_CLIENT_SECRET=$(cat ~/.octo-cli/claude-agent.secret)

# 1. Authenticate against the system tenant (token stored in local_octosystem)
octo-cli -c LogInClientCredentials --context local_octosystem

# 2. Create the temp tenant — ALWAYS with -np
octo-cli -c Create -tid tmp-<purpose> -db tmp-<purpose> -np --context local_octosystem

# 3. Context for the temp tenant + mirror login (same credentials, token stored in the new context)
octo-cli -c AddContext -n local_tmp-<purpose> \
  -isu https://localhost:5003/ -asu https://localhost:5001/ \
  -bsu https://localhost:5009/ -csu https://localhost:5015/ \
  -rsu https://localhost:5008/ -apu https://localhost:5005/ \
  -tid tmp-<purpose>
octo-cli -c LogInClientCredentials --context local_tmp-<purpose>

# 4. Work in the tenant — full octo-cli + GraphQL access, all with --context
#    octo-cli -c ImportCk ... -w --context local_tmp-<purpose>
#    For the ck_explorer/rt_explorer scripts: export OCTO_CLI_CONTEXT=local_tmp-<purpose>

# 5. Tear down
octo-cli -c Delete -tid tmp-<purpose> -y --context local_octosystem
octo-cli -c RemoveContext -n local_tmp-<purpose>
```

For non-local environments substitute the service URLs from `references/environments.md`. Alternatively, `export OCTO_CLI_CONTEXT=local_tmp-<purpose>` once for step 4 instead of repeating `--context` on every command.

## Rules & Pitfalls

- **`-np` (no-provision) is mandatory on `Create`.** The default behavior provisions "the current user" as tenant admin — a machine token has no user, so admin provisioning would fail. Access to the new tenant comes from the mirror instead.
- **Tenant IDs are lowercased** by the CLI; use lowercase, and prefix temp tenants with `tmp-` so they're recognizable and safe to clean up.
- **The client is per-tenant.** A token is only valid for the tenant of the context it was acquired in — run `LogInClientCredentials --context <ctx>` **once per context** to populate each one's token (cheap and idempotent). With `--context` there is no switching, so there is nothing to re-run on a switch.
- **No refresh token** is issued. Keep `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET` exported; octo-cli then re-acquires expired tokens automatically mid-script.
- **No user roles in the token.** Scope-gated endpoints (asset repo, runtime GraphQL, identity tenant API — verified) work fine. Anything that filters by *user* role claims or needs a user subject behaves as "no user": e.g. `AuthStatus` shows no User-Info section, `ProvisionCurrentUser` is meaningless.
- **The GraphQL explorer scripts follow the same context selection** — they read `OCTO_CLI_CONTEXT` (falling back to the active context) from `~/.octo-cli/contexts.json`, which `LogInClientCredentials --context <ctx>` populates exactly like a device-code login. `export OCTO_CLI_CONTEXT=<tmp-ctx>` so the scripts and octo-cli agree on the temp tenant without touching the active context.
- **Cleanup confirmation:** `Delete` prompts interactively; pass `-y` in agent runs. Only auto-delete tenants the agent itself created in the same session (recognizable via the `tmp-` prefix) — never auto-delete anything else.
