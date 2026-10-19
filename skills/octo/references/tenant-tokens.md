# Tenant tokens, child tenants and sweeps (AB#6836, AB#6840)

A command addresses **one tenant: the tenant of its context**. octo-cli (3.5.27 and newer) never sends a token that was issued for another tenant: a token of a different tenant (for example the root tenant's token in a context for a child tenant) is exchanged per tenant (RFC 8693, cached, renewed silently), and if that is not possible the command stops. There is no fallback to the other token.

- **Authority in a child tenant comes only from explicit provisioning.** A root-tenant operator has no implicit rights in a child tenant. Once per child tenant, **also for every new tenant**: `octo-cli -c ProvisionCurrentUser -ttid <child> --context <root-ctx>` (flags in `references/command-reference.md`).
- **Denial message.** The command exits with code `-4` and a message that names the tenant and the cause: not provisioned (run `ProvisionCurrentUser -ttid <tenant>`), access to the tenant denied (not a descendant, not provisioned), client not allowed to exchange (use a context for the tenant), sign-in rejected (`LogIn`), tenant unknown, identity unreachable. An HTTP 403 of a service is mapped to the same provisioning hint. Do not retry with another context's token.
- **Per-tenant contexts stay valid** for CI and machines (`LogInClientCredentials --context <tenant-ctx>`, the CD pipeline): their token is issued for the context's tenant, so nothing is exchanged.
- **Many tenants: use the helper, not a script.** With the OctoMesh developer shell loaded (route via `octo-devtools`): `Register-OctoCliContext -Installation <i> -TenantId a,b,c -NoSwitch` creates one context per tenant, then `Invoke-OctoTenantSweep -Installation <i> -Tenant a,b,c -CliArguments '-c','LibraryStatus','-io' [-WhatIf] [-Json]` runs the command per tenant through `octo-cli --context <i>_<tenant>`, prints one row per tenant (`Ok` / `Denied` + cause / `Failed`) and continues after a denial. Commands with their own tenant argument use `-Context <ctx> -CliArguments '-c','ClearCache','-tid','{tenant}'`; `-AllTenants` takes the list from `GetTenants --all`. `-WhatIf` lists the calls without running them. The helper never reads, prints or writes a token.
- **No token scraping.** Do not write scripts (curl, Python, PowerShell) that read an access token out of the context file and call a child tenant's route with it: after the gate is enforced such calls are denied. Use an octo-cli command, or the helper around one. GraphQL against a tenant is the command `octo-cli -c GraphQl -tid <tenant> -q|-f|-si` (AB#7027). Impersonation loops use `SwitchServiceAccountsToImpersonation`, not curl. The Python explorers in `scripts/` use the selected context's token for that context's **own** tenant and keep working.
- Tenant status/capability routes of the finished files migration have no CLI command and get none; do not script them.
- Pool deploy (`POST .../v1/Pool/deploy`) has no CLI command yet (known gap): see the REST note in `SKILL.md`; its token must be issued for that tenant.

## Worked example

```powershell
# one context per tenant, nothing switched, no login yet
Register-OctoCliContext -Installation test-2 -TenantId tecob,lkv,wwc26 -NoSwitch -NoLogin

# dry run: which calls would run?
Invoke-OctoTenantSweep -Installation test-2 -Tenant tecob,lkv,wwc26 -CliArguments '-c','LibraryStatus','-io' -WhatIf

# run; a tenant without provisioning shows Outcome=Denied with the ProvisionCurrentUser hint, the others continue
Invoke-OctoTenantSweep -Installation test-2 -Tenant tecob,lkv,wwc26 -CliArguments '-c','LibraryStatus','-io'

# provision the operator in every child tenant (once, also for new tenants)
Invoke-OctoTenantSweep -Context test-2_octosystem -AllTenants -Exclude octosystem `
    -CliArguments '-c','ProvisionCurrentUser','-ttid','{tenant}'

# GraphQL query over many tenants, the answer per tenant (read-only; clean JSON in .Stdout)
$q = '{ constructionKit { models(first:1) { totalCount } } }'
Invoke-OctoTenantSweep -Context test-2_octosystem -Tenant tecob,lkv,wwc26 -IncludeOutput `
    -CliArguments '-c','GraphQl','-tid','{tenant}','-q',$q |
  ForEach-Object { [pscustomobject]@{ Tenant = $_.Tenant; Outcome = $_.Outcome
      Total = if ($_.Outcome -eq 'Ok') { ($_.Stdout | ConvertFrom-Json).data.constructionKit.models.totalCount } } }
```

Reference: octo-tools `docs/tenant-sweep.md`. octo-cli behaviour: octo-cli `CLAUDE.md`, "Tokens per tenant".
