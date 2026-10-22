# Temporary Tenants — Fully Non-Interactive Lifecycle

An agent can create a throwaway **scratch tenant**, work in it as its administrator, and delete it **without any user interaction** — no `LogIn -i`, no device-code login per tenant. The pieces are OAuth2 `client_credentials` login, client mirroring, and the opt-in `--scratch` flag of `Create` (AB#7192) that makes the creating client administrator of the tenant it creates.

## How It Works

1. **`LogInClientCredentials`** — headless OAuth2 `client_credentials` login. Reads `-id`/`-s` arguments or the `OCTO_CLI_CLIENT_ID` / `OCTO_CLI_CLIENT_SECRET` environment variables. The token has **no user identity**; it carries the roles the client holds in the tenant it was issued for.
2. **Client mirroring** — a client created in the system tenant (`octosystem`) with `-apic` (`AutoProvisionInChildTenants`) is copied (same ClientId, same secret, same scopes) into the tenants below it. A mirror has **no roles** in a child on its own.
3. **`Create --scratch`** — records the creating client as the creator of the new tenant, and identity gives **that client's mirror** the `TenantOwners` group in the new tenant (all roles; only that client, only that tenant). The grant is re-applied on every identity restart and mirror provisioning; removing the client from `TenantOwners` revokes it for good (`GetTenants` shows `scratchAccessRevoked`).
4. **`Delete --disable-features -y`** — switches off every capability the tenant has enabled (AI Services, Communication, Reporting, Stream Data) with the caller's token for that tenant, then deletes it.

Authorization is **role-based**: creating and deleting a tenant needs the role `TenantManagement` of the caller in the parent tenant, and `--scratch` is accepted **only** for a client-credentials token of the direct parent (a user token or another tenant's token gets HTTP 403). The capability endpoints of a tenant belong to the tenant's own administrator — a token of the parent tenant is refused there (the capability toggles check the role from AB#7319 on), which is why the creator needs the `TenantOwners` grant and why `Delete --disable-features` uses the child token.

## One-Time Setup (operator, once per environment)

Requires an authenticated **octosystem** session (the only step that may ever need a human):

```bash
octo-cli -c AddClientCredentialsClient -id claude-agent -n "Claude Agent (non-interactive automation)" -s "<generated-secret>" -apic --context local_octosystem
octo-cli -c AddClientToRole -id claude-agent -r TenantManagement --context local_octosystem
```

- The client needs `-apic` (otherwise it has no mirror in the child and `--scratch` grants nothing) **and** the role `TenantManagement` in `octosystem` (create and delete need it).
- Convention: store the secret at `~/.octo-cli/<clientId>.secret` (same sensitivity class as the tokens in `~/.octo-cli/contexts.json`). On the local dev environment the client `claude-agent` may already exist and its secret is at `~/.octo-cli/claude-agent.secret` — check its roles with `GetClients` before relying on it.
- `-apic` mirrors into tenants below the creating tenant; the mirror of a client of `octosystem` is provisioned when identity sets a tenant up. Tenants that existed **before** the client was created get the mirror with `ProvisionClientInExistingTenants -id claude-agent` or `ProvisionClientInTenant -id claude-agent -ctid <tenantId>`.

## Agent Workflow

All steps run without user interaction, and **every command uses `--context` so the active context is never changed**. Export the credentials once; while they stay exported, octo-cli re-acquires the token on expiry (no refresh token exists for `client_credentials`).

```bash
export OCTO_CLI_CLIENT_ID=claude-agent
export OCTO_CLI_CLIENT_SECRET=$(cat ~/.octo-cli/claude-agent.secret)

# 1. Authenticate against the system tenant (token stored in local_octosystem)
octo-cli -c LogInClientCredentials --context local_octosystem

# 2. Create the scratch tenant — the client becomes its administrator (no -np needed: --scratch provisions no user)
octo-cli -c Create -tid tmp-<purpose> -db tmp-<purpose> --scratch --context local_octosystem
#    wait until GetTenantLifecycle -tid tmp-<purpose> reports Active (about a minute)

# 3. Context for the scratch tenant + login as the mirror (same credentials)
octo-cli -c AddContext -n local_tmp-<purpose> \
  -isu https://localhost:5003/ -asu https://localhost:5001/ \
  -bsu https://localhost:5009/ -csu https://localhost:5015/ \
  -rsu https://localhost:5007/ -aisu https://localhost:5019/ \
  -tid tmp-<purpose>
octo-cli -c LogInClientCredentials --context local_tmp-<purpose>

# 4. Work in the tenant as its administrator — all octo-cli verbs, GraphQL, the Enable*/Disable* capability verbs
#    octo-cli -c EnableStreamData --context local_tmp-<purpose>
#    For the ck_explorer/rt_explorer scripts: export OCTO_CLI_CONTEXT=local_tmp-<purpose>

# 5. Tear down: disables whatever is still enabled, then deletes
octo-cli -c Delete -tid tmp-<purpose> --disable-features -y --context local_octosystem
octo-cli -c RemoveContext -n local_tmp-<purpose>
```

For non-local environments substitute the service URLs from `references/environments.md`.

## Rules & Pitfalls

- **Use `Create --scratch` for agents.** Without it the mirror has no roles in the child and the agent cannot work there or clean up. `--scratch` skips the provisioning of the current user (a service token has none), so `-np` is not needed with it.
- **`--scratch` refuses user tokens by design** (HTTP 403). A user session creates a plain tenant, provisions itself (`ProvisionCurrentUser -ttid <tenant>`) and cleans up with `Delete --disable-features -y` as the tenant's administrator.
- **Child secret.** The mirror authenticates in the child with the inherited parent secret today. `Delete --disable-features` takes `OCTO_CLI_CHILD_CLIENT_SECRET` (the secret of the mirror in the child) when set and falls back to `OCTO_CLI_CLIENT_SECRET` only without it.
- **Which secret where.** In a child context (direct work: `Restore`, `Dump`, feature switches) the mirror secret goes into `OCTO_CLI_CLIENT_SECRET` (with `OCTO_CLI_CLIENT_ID`). `OCTO_CLI_CHILD_CLIENT_SECRET` is read only by parent-context commands that fetch the child token themselves (`Delete --disable-features`). The mirror's own secret comes from `POST …/clients/<clientId>/mirrors/<childTenantId>/secret` on the identity service (returned once, no CLI verb yet); the inherited parent secret keeps working until AB#5061 closes it.
- **Activated archives are never deleted.** If Stream Data stays enabled because archives are activated, `Delete --disable-features` lists them, does **not** delete the tenant and fails: `DisableArchive` (data kept) or `DeleteArchive`, then repeat.
- **Restore into a scratch tenant:** there is no `Restore --scratch`. Create the tenant with `Create --scratch`, then restore into it with the child (mirror) token (`--context local_tmp-<purpose>`); the scratch record survives the restore, so the creator stays administrator.
- **Tenant IDs are lowercased** by the CLI; prefix temp tenants with `tmp-` so they are recognizable and safe to clean up.
- **The client is per-tenant.** A token is only valid for the tenant of the context it was acquired in — run `LogInClientCredentials --context <ctx>` once per context.
- **No refresh token** is issued. Keep `OCTO_CLI_CLIENT_ID`/`OCTO_CLI_CLIENT_SECRET` exported; octo-cli then re-acquires expired tokens automatically.
- **Roles, not scope.** The token has no user, but the mirror's `TenantOwners` membership gives it all tenant roles; a client without `TenantManagement` in the parent gets 403 on create and delete. Do not rely on an old behaviour where a scope-only token could toggle capabilities (AB#7319 removes it).
- **The GraphQL explorer scripts follow the same context selection** — they read `OCTO_CLI_CONTEXT` (falling back to the active context) from `~/.octo-cli/contexts.json`.
- **Cleanup:** only auto-delete tenants the agent itself created in the same session (the `tmp-` prefix); never auto-delete anything else. `-y` is required with `--disable-features`.
- MCP: `delete_tenant` with `disableFeatures` works for a **user** MCP session only (the child token comes from a token exchange); a client-credentials agent uses the CLI.
