# Repair tenants after a System bump (AB#7567, AB#7562)

A release that embeds a newer `System` CK model (for example System 2.5.0 to 2.7.0) replaces it in every tenant at the
next service start. Classic (`ck-models/v2`) catalog models that pin `System` exactly are then re-validated and marked
`ResolveFailed`; range-retaining models (`ck-models/v3`, `dependencyRanges`) keep resolving. The catalog usually holds a
range-retaining successor for each failed model. **`FixAll` imports that successor** — no `CheckUpgrade` and no manual
`ImportFromCatalog` per model is needed.

## What `FixAll` does and does not do

- Imports every row of `LibraryStatus` with `NeedsAction` and `IsCompatible` (a `ResolveFailed` model with a resolving
  catalog successor qualifies). Compatibility is judged by the catalog model's `dependencyRanges` (inside the range and at
  or above the floor); classic models stay exact-pinned.
- Models that pin each other exactly are imported together in one guarded set, in dependency order.
- Never forces: an update that would break an installed model (tenant upgrade guard) is skipped and listed with its blocker.
- Models without a resolving successor stay `ResolveFailed` and are listed by `LibraryStatus` with their reason
  (`IncompatibilityReason`, `ResolveFailedReason`). Typical: a customer model with an exact pin of its own
  (for example `Maco-1.0.0` pinned to `Industry.Basic-1.0.0`) — publish a successor, then run `FixAll` again.
- Needs octo-cli and services from 3.5.43 or newer (AB#7376 joint import, AB#7408 range-aware check).

## One tenant

```
octo-cli -c LibraryStatus -io --context <ctx>          # before: which rows are ResolveFailed / NeedsAction
octo-cli -c FixAll -w -y --context <ctx>
octo-cli -c LibraryStatus -io --context <ctx>          # after: all Available, remaining rows listed with a reason
```

## All tenants of an installation (one sweep, no interactive login per tenant)

Needs the OctoMesh developer shell (route via `octo-devtools`) and a provisioned operator in each child tenant
(`ProvisionCurrentUser -ttid <child>`, once per tenant; see `tenant-tokens.md`).

```powershell
Register-OctoCliContext -Installation <i> -TenantId a,b,c -NoSwitch          # one context per tenant
Invoke-OctoTenantSweep -Installation <i> -Tenant a,b,c -CliArguments '-c','LibraryStatus','-io' -IncludeOutput   # before (read-only)
Invoke-OctoTenantSweep -Installation <i> -Tenant a,b,c -CliArguments '-c','FixAll','-w','-y' -WhatIf              # dry run
Invoke-OctoTenantSweep -Installation <i> -Tenant a,b,c -CliArguments '-c','FixAll','-w','-y'                      # repair
Invoke-OctoTenantSweep -Installation <i> -Tenant a,b,c -CliArguments '-c','LibraryStatus','-io' -IncludeOutput   # after
```

The sweep prints one row per tenant (Ok / Denied + cause / Failed) and continues after a denial. A tenant that shows
`Denied` is not provisioned: run `ProvisionCurrentUser` for it, then repeat only that tenant.

## Rules

- `FixAll` on staging-1, prod-1, prod-2 and customer clusters is a write: only with the developer's explicit go for that
  cluster in the current session (agent-operating-rules §5.1).
- Do not use `ImportFromCatalog --force` to get past a skipped row; a skipped row means the guard found a real break.
- After the sweep, check the models `FixAll` could not repair (no successor) and give them to the owner of the model.
