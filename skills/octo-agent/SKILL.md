---
name: octo-agent
description: This skill should be used when the developer needs to investigate OctoMesh bugs, diagnose CK model failures (ResolveFailed, modelState, broken dependencies), inspect MongoDB tenant databases directly, perform selective builds to isolate issues, manage Docker volume backups for safe rollback, understand the DebugL NuGet dependency chain, or run targeted tests. Trigger on "help me fix", "investigate this bug", "what broke", "isolate the issue", "why is the model broken", "check database state", "backup before testing", "restore database", "CK model state", "NuGet dependency chain", "selective build", "test isolation", "service won't start", "build fails", "package not found", "ResolveFailed", "modelState 2", "health check failing", "error in logs", "cascade failure", "version bump broke", "data corruption", "tenant broken", "rollback my changes", "safe rollback", "something broke after upgrade", "why is this failing", "query MongoDB".
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

Build only what's needed to minimize iteration time. The build dependency chain flows:

```
mm-common → octo-distributedEventHub → octo-construction-kit-engine → octo-sdk
  → octo-construction-kit-engine-mongodb → octo-common-services
    → octo-mesh-adapter → octo-bot-services → [service repos]
```

**Key principle:** Only rebuild from the changed repo downward through the chain. Skip everything upstream.

For the full dependency chain, NuGet package mappings, and selective build commands, read `references/build-system.md`.

## CK Model Debugging

CK (Construction Kit) models define the entity type system. Each tenant's `CkModel` collection shows model health:

| `modelState` | Meaning | Action |
|--------------|---------|--------|
| 0 | Pending | Import in progress — wait |
| 1 | Available | Healthy |
| 2 | ResolveFailed | Dependency missing — investigate |

**Common cause of ResolveFailed:** A base model (e.g., System) was version-bumped without recompiling all dependent models. The old version ID gets deleted, leaving orphaned references.

For CK model YAML format, versioning semantics, source generation, and migration scripts, read `references/ck-model-internals.md`.

## Database Diagnostics

Query MongoDB directly via the MongoDB MCP server to diagnose issues. Key collections per tenant database:

| Collection | Content |
|-----------|---------|
| `CkModel` | Model identity, state, dependencies |
| `CkType` | Type definitions |
| `CkAttribute` | Attribute definitions |
| `RtEntity` | Runtime entity instances |

System tenant database: `octosystem`. Default test tenant: `meshtest`.

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
| AI Services | `octo-ai-services` | — |

## References

Consult these for detailed procedures:

- **`references/build-system.md`** — DebugL configuration, NuGet dependency chain, selective build strategies, service startup options
- **`references/ck-model-internals.md`** — CK model YAML format, versioning, dependency resolution, source generation, migrations, MongoDB collections
- **`references/database-operations.md`** — Docker volume backup/restore, MongoDB diagnostic queries, multi-tenant data, service logs, health endpoints
- **`references/debugging-workflows.md`** — Safe investigation protocol, bug isolation steps, common bug categories, test framework reference
