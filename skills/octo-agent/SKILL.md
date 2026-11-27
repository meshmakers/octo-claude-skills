---
name: octo-agent
description: "Debugging and investigation agent for OctoMesh — diagnoses CK model failures (ResolveFailed, modelState 2, broken dependencies, version-bump cascades), blueprint install failures, and CK migration problems; inspects MongoDB tenant databases directly; runs selective DebugL builds and targeted tests to isolate a regression; and manages Docker volume backups for safe rollback. Use it when something broke after a build, version bump, merge, or upgrade and you need to find the root cause safely. Trigger on: help me fix, investigate this bug, what broke, isolate the issue, why is the model broken, ResolveFailed, modelState 2, multi-version conflict, error code 66, CK migration failed, blueprint failed, BlueprintInstallation, LibraryStatus, FixAll, check database state, query MongoDB, tenant DB, NuGet dependency chain, package not found, selective build, build fails, service won't start, health check failing, error in logs, cascade failure, version bump broke, something broke after upgrade, data corruption, tenant broken, backup before testing, restore database, safe rollback, test isolation, token refresh failing, Hangfire cron not firing."
allowed-tools:
  - "Read(${CLAUDE_PLUGIN_ROOT}/skills/octo-agent/references/*)"
  - "Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/octo-devtools/scripts/run_pwsh.sh:*)"
  - "mcp__mongodb__find"
  - "mcp__mongodb__aggregate"
  - "mcp__mongodb__count"
  - "mcp__mongodb__list-collections"
  - "mcp__mongodb__list-databases"
  - "mcp__mongodb__collection-schema"
---

# OctoMesh Developer Agent

## Purpose

Developer-facing debugging and investigation agent for OctoMesh. This skill provides deep platform knowledge for safely investigating bugs, performing selective builds, inspecting database state, and rolling back when things go wrong.

**Complements** the `octo-devtools` skill (build/start/stop operations) and `octo` skill (CLI/data exploration). This skill focuses on the **why** and **how** of debugging — understanding the build dependency chain, CK model internals, and safe investigation workflows.

**Prerequisites:**
- **`octo-devtools` skill** — this skill reuses its PowerShell wrapper (`run_pwsh.sh`) for build commands
- **MongoDB MCP server** — must be configured and connected for direct database diagnostic queries
- **Workspace root** — backup/restore operations require the working directory to be the OctoMesh monorepo workspace root (where `octo-tools/` lives)

## Decision Tree

When a developer needs help, determine the right approach:

```
Developer has a problem
├── "Something is broken at runtime"
│   ├── Check service health endpoints
│   ├── Check service logs (logFiles/*.log)
│   ├── Query MongoDB for CK model states
│   └── See: Debugging Workflows reference
│
├── "I need to test a risky change"
│   ├── Create Docker volume backup FIRST
│   ├── Make the change + rebuild selectively
│   ├── Observe results
│   └── Restore if needed
│
├── "Build is failing / packages not found"
│   ├── Check build dependency chain
│   ├── Verify NuGet packages in ./nuget/
│   ├── Consider clearing global NuGet cache
│   └── See: Build System reference
│
├── "CK model is broken / ResolveFailed"
│   ├── Query CkModel collection for states
│   ├── Check dependency references
│   ├── Identify orphaned version references
│   └── See: CK Model Internals reference
│
├── "Command denied in a child tenant / exit -4 / would be denied (LogOnly)"
│   ├── Read the message: it names the tenant and the cause
│   ├── Not provisioned → ProvisionCurrentUser -ttid <tenant> (per child tenant, new ones too)
│   ├── Many tenants → Invoke-OctoTenantSweep, never a token-scraping script
│   └── See: Debugging Workflows reference, "Denied in a Child Tenant"
│
└── "I need to understand how X works"
    ├── CK model YAML, versioning → CK Model Internals
    ├── Build chain, DebugL, NuGet → Build System
    ├── Database, tenants, backup → Database Operations
    └── Test patterns, fixtures → Debugging Workflows
```

## Safe Investigation Protocol

For any investigation that might corrupt data:

1. **Backup** — Stop infrastructure, create named backup, restart
2. **Baseline** — Record current database state (query, save to temp file)
3. **Change** — Apply the minimal change to reproduce or test
4. **Observe** — Check health, query database, review logs
5. **Restore** — If something broke, stop everything and restore the backup

Use `Backup-OctoInfrastructure -Name <name>` and `Restore-OctoInfrastructure -Name <name>` for Docker volume snapshots. Use `Get-OctoInfrastructureBackup` to list and `Remove-OctoInfrastructureBackup -Name <name>` to delete. Infrastructure must be stopped first.

For full backup/restore procedures, read `references/database-operations.md`.

## Selective Build Strategy

Build only what's needed to minimize iteration time. The build order (`mm-*`, then a pinned core chain from `octo-distributedEventHub` through `octo-construction-kit-engine`, `octo-sdk`, `octo-construction-kit-engine-mongodb` and `octo-common-services` to the services, then the remaining `octo-*` repos alphabetically) is defined only in octo-tools `modules/OctoBuildOrder.psm1`; `Get-OctoBuildOrder -branchRootPath <lane>` prints the current one.

**Key principle:** A change in a library repo needs everything downstream of it rebuilt too, with the packages propagated through `<lane>/nuget`. Two cmdlets do that:

- `Invoke-BuildRange -from <changed repo> -to <last consumer> [-include <service>]` — the fast slice: `-WhatIf` for the plan, then the build, then `-verifyTests` before you trust the result (a plain run compiles no test project); `-purgeStaleCache` when the cache holds another build of a `999.0.0` package.
- `Invoke-BuildAll -configuration DebugL -excludeFrontend $true` — the full reset, only when restores fail with NU1101/NU1102 on a `999.0.0` package or after a pull or branch switch.

Reserve `Invoke-Build` for a single service repo that publishes no package.

For the full dependency chain, NuGet package mappings, and selective build commands, read `references/build-system.md`.

## CK Model Debugging

CK (Construction Kit) models define the entity type system. Each tenant's `CkModel` collection shows model health:

| `modelState` | Meaning | Action |
|--------------|---------|--------|
| 0 | Pending | Import in progress — wait |
| 1 | Available | Healthy |
| 2 | ResolveFailed | Dependency missing — investigate |

**Common cause of ResolveFailed:** A base model (e.g., System) was version-bumped without recompiling all dependent models. The old version ID gets deleted, leaving orphaned references. A *multi-version* conflict (two incompatible versions of the same model resolved transitively) surfaces as fatal **error code 66** at compile time.

**CK dependency diagnostics:**
- `octo-cli -c LibraryStatus` (`-na`/`--needs-action` to filter) — lists installed CK models with catalog availability and which need action. Read-only.
- `octo-cli -c FixAll` (`-w` wait, `-y` skip confirm) — imports/updates all models needing a fix. **Mutating.**
- `Compare-CkVersions <otherBranch> [-Details]` — diffs every `ckModel.yaml` under `$Global:ROOTPATH` against another branch checkout; sets `$LASTEXITCODE` to the count of non-equal models. Use after a merge or branch switch to spot a CK version that drifted. Read-only.

**Blueprint failures:** Blueprint state is stored tenant-locally in three CK types — `System/BlueprintInstallation`, `System/BlueprintHistory`, `System/BlueprintBackup` (no longer a cross-tenant collection). When a blueprint apply fails, query those collections in the tenant DB and check the platform event log for `BlueprintOperationFailed` events.

For CK model YAML format, versioning semantics, source generation, migrations, and blueprint internals, read `references/ck-model-internals.md`.

## Database Diagnostics

Query MongoDB directly via the MongoDB MCP server to diagnose issues. Key collections per tenant database:

| Collection | Content |
|-----------|---------|
| `CkModel` | Model identity, state, dependencies |
| `CkType` | Type definitions |
| `CkAttribute` | Attribute definitions |
| `CkRecord` | Record (value object) definitions |
| `RtEntity` | Runtime entity instances (incl. blueprint state via `System/BlueprintInstallation` etc. and OIDC grants via `System.Identity/PersistedGrant`) |

System tenant database: `octosystem`. Default test tenant: `meshtest`. Local replica set connection string: `mongodb://localhost:27017,localhost:27018,localhost:27019/?replicaSet=rs`.

For diagnostic queries, tenant operations, and log analysis, read `references/database-operations.md`.

## Test Isolation

Run targeted tests without full suite:

```bash
dotnet test -c DebugL --filter "FullyQualifiedName~SpecificTest"   # One test
dotnet test -c DebugL --filter "FullyQualifiedName!~SystemTests"   # Skip system tests
dotnet test ./specific-repo -c DebugL                               # One repo
```

Most integration tests use Testcontainers.MongoDb (ephemeral MongoDB). System tests require running services.

For test framework details and fixture patterns, read `references/debugging-workflows.md`.

## Service Architecture Quick Reference

| Service | Repo | Ports (HTTPS/HTTP) |
|---------|------|--------------------|
| Identity | `octo-identity-services` | 5003/5002 |
| Asset Repo | `octo-asset-repo-services` | 5001/5000 |
| Comm Controller | `octo-communication-controller-services` | 5015/5014 |
| Bot | `octo-bot-services` | 5009/5008 |
| Reporting | `octo-report-services` | 5007/5006 |
| Mesh Adapter | `octo-mesh-adapter` | 5020/5021 |
| MCP Service | `octo-mcp-service` | 5017/5016 |
| AI Services | `octo-ai-services` | 5019/5018 |
| AI Worker | `octo-ai-services` (AiWorker.dll) | 5023/5022 |
| Platform Services | `octo-platform-services` | 5025/5024 |

`Start-Octo` starts bot, identity, asset-repo, mesh-adapter, comm-controller, platform services (System.UI, `_configuration`), the Refinery Studio and frontend-libraries dev servers, MCP and AI services **by default**. `reportingService`, `aiWorker`, `simulationAdapter` and `httpActivator` default to `$false` (off). Reporting, MCP and AI start only when their `bin/<configuration>` output exists in the lane. Parameter defaults: octo-tools `modules/Start-Octo.psm1`.

**Compiler errors CS8032 / CS8785 after a rebuild** (an analyzer or source generator "cannot be created" or "failed to generate"): a reused compiler or build server still holds an older `999.0.0` analyzer. Run `dotnet build-server shutdown` and build again; for a one-off build pass `-p:UseSharedCompilation=false`.

**When the octo-devstack MCP server is available** (optional; see the `octo-devtools` skill): diagnose through it instead of restarting the shared stack — `stack_status` and `stack_attention` for what is down or failing, `service_logs` for one service, `stack_verify` for the health checks, and one lane per suspected regression (`lane_create` with the suspect repository, `lane_build`, `lane_test`, its own `stack_start`) so the shared stack and other sessions keep working.

## References

Consult these for detailed procedures:

- **`references/build-system.md`** — DebugL configuration, NuGet dependency chain, selective build strategies, service startup options
- **`references/ck-model-internals.md`** — CK model YAML format, versioning, dependency resolution, source generation, migrations, MongoDB collections
- **`references/database-operations.md`** — Docker volume backup/restore, MongoDB diagnostic queries, multi-tenant data, service logs, health endpoints
- **`references/debugging-workflows.md`** — Safe investigation protocol, bug isolation steps, common bug categories (incl. denial in a child tenant), test framework reference
