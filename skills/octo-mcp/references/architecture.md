# octo-mcp-service — Architecture Reference

Exhaustive detail behind the SKILL.md overview. Verified against `C:\dev\meshmakers\octo-mcp-service` source. The repo's own `CLAUDE.md` remains the authoritative source — re-read it before any substantial change.

## Why Three Tool Families Coexist

The MCP server began as a thin runtime-CRUD proxy (v1.0–1.1). v1.2–1.3 added the full `octo-cli` surface via the SDK service clients plus out-of-band file transfer. v1.4 added aggregation + stream-data query parity with the asset-repo GraphQL transient-query API. Three families coexist **on purpose** and must not be merged:

- **Family 1 (platform-admin)** talks HTTP to the backend services via `OctoServiceClientFactory` + `*ClientContext` helpers — the same code path the CLI uses, so orchestrated workflows (tenant create + admin provision, blueprint update + auto-backup, workload deploy through pool) behave identically.
- **Family 2 (generic CK CRUD + schema)** talks directly to `ITenantRepository` (MongoDB) — fast generic CRUD and schema discovery, no HTTP overhead, no platform-admin orchestration.
- **Family 3 (aggregation + stream-data)** also hits the engine directly (`ITenantRepository` for runtime aggregations; `ITenantContext.GetStreamDataRepository()` for stream-data), with its own lowercase enum + `AggregationMapper` conventions, mirroring the asset-repo GraphQL transient/persisted query surface so the AI never builds GraphQL.

They have different cost profiles and validation needs: generic CRUD skips the service clients (no HTTP overhead for read-heavy queries); platform-admin must not bypass the service clients (skipping them skips orchestration); aggregations need direct engine access for `RtEntityQueryOptions` configuration so they don't go through `*ClientContext`.

## Family 3 — Aggregation & Stream-Data Internals

Tools: `RuntimeAggregationTools` (`query_entities_aggregation`, `query_entities_grouping`), `StreamDataAggregationTools` (`query_stream_data_simple`, `query_stream_data_aggregation`, `query_stream_data_grouping`, `query_stream_data_downsampling`), `StreamDataMetadataTools` (`get_archive_storage_stats`, `get_rollup_query_metadata`), plus the persisted-query executors (`execute_runtime_query`, `execute_stream_data_query`).

### Lowercase `AggregationFunctionDto`

Counter to the rest of the codebase (PascalCase enums), this enum uses **lowercase short names**: `count` / `sum` / `avg` / `min` / `max`. Intentional and AI-driven — LLMs construct lowercase strings more reliably, and it mirrors SQL. Translation to the engine's `AggregationFunction` (`Count`/`Sum`/`Average`/`Minimum`/`Maximum`) happens in `AggregationMapper.ToEngineFunction`. **Do not "fix" it to PascalCase.**

### `AggregationMapper` — single point of validation + engine mapping

`Services/AggregationMapper.cs`. Every aggregation tool routes through it — don't bypass:

- `Validate(aggregations)` — at-least-one rule; non-count requires `attributePath`; alias uniqueness.
- `ValidateGroupBy(paths)` — non-empty, no blanks, no duplicates.
- `DeriveAlias(column)` — `<function>_<sanitised-path>` when no explicit alias (e.g. `avg_Power`); special-cases `"count"` for unparametrised count.
- `ApplyToAggregationInput(input, columns)` — pushes columns into the engine's `AggregationInput` (runtime aggregation tools).
- `ToEngineColumns(columns)` — maps to `AggregationColumn[]` (stream-data tools).
- `MapCkAggregationName(...)` — translates persisted CK `AggregationTypes` enum names (`Count`/`Sum`/`Average`/`Minimum`/`Maximum` + short `Avg`/`Min`/`Max`) to `AggregationFunctionDto` for persisted-query execution.

The validation strings are user-visible error messages — keeping them consistent matters.

### Engine column key convention (stream-data only)

Stream-data aggregation results return as `StreamDataRow` with `Values` keyed by the engine's column-name format `{Function}({path})` (the `ToString()` of `AggregationColumn`). The projection layer rebuilds that key (`EngineColumnKey` inside `StreamDataAggregationTools`), then writes the value under the MCP-side alias from `AggregationMapper.DeriveAlias`. Group-key columns flow straight from `Values` into the response dict, indexed by the supplied group-by paths.

### `StreamDataContext` — four-stage cascade

Stream-data tools take an `archiveRtId` (not a `ckTypeId`) — the target CK type is on the archive snapshot. Resolution:

```
ITenantResolutionService.GetTenantContextAsync(tenantId)
    → ITenantContext.GetStreamDataRepository()   → null if StreamData not enabled
    → ITenantContext.GetArchiveRuntimeStore()
        → archiveStore.GetAsync(rtId)            → null if archive not found
        → snapshot.TargetCkTypeId                → the ckTypeId for the engine call
```

`StreamDataContext.TryResolveAsync` collapses this into one result with a structured per-failure-mode error message. Every stream-data tool starts with that call.

`ITenantResolutionService.GetTenantContextAsync` was added for the aggregation work — platform-admin tools only need `ITenantRepository`, but the stream-data accessors live on the wider `ITenantContext`. The implementation calls `ISystemContext.FindTenantContextAsync(tenantId)`. Use this same entry point when a future tool needs `GetRollupArchiveRuntimeStore()` or any other context-only accessor.

### Pre-SDK validation matters

These tools return `IsSuccess=false` + a clear `ErrorMessage` for: empty aggregation list; non-count function without `attributePath`; duplicate aliases; empty/duplicate group-by paths; invalid time windows (`from >= to`, `limit <= 0`). Without it the engine throws on the SDK side, surfacing as a 500-style exception with less context. The AI reads `ErrorMessage` and fixes its call.

### Filter operators — `FilterOperatorDto`

`Models/Filters/FilterOperatorDto.cs` mirrors the engine's `FieldFilterOperator`. Full set: `Equals`, `NotEquals`, `Contains`, `StartsWith`, `EndsWith`, `GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `Between`, `In`, `NotIn`, `IsNull`, `IsNotNull`, `Regex`, `Like`, `AnyEq`, `AnyLike`.

- **Substring vs SQL pattern:** `Contains`/`StartsWith`/`EndsWith` take a plain substring; `Like` takes a `%`-wildcard pattern. Prefer the dedicated ops when no wildcards are needed.
- **Array predicates:** `AnyEq`/`AnyLike` apply only to scalar-array attributes ("any element matches"); on a non-array attribute it is an engine-side error, not pre-validated.
- **Null predicates:** `IsNull`/`IsNotNull` ignore the `value` field on `FieldFilterDto`.
- **No silent fallback:** `StreamDataAggregationTools.MapFilterOperator` and `RuntimeAggregationTools.BuildTypedFilters` throw `ArgumentOutOfRangeException` on an unknown DTO value rather than mapping to `Equals` (the pre-v1.5.1 behaviour that masked typos). `RuntimeEntityCrudTools.ApplyFieldFilter` already threw.

When adding a new engine operator: extend the DTO + both switches + add a `[Theory]` row in `FilterOperatorMappingTests`.

### Persisted-query execution

`execute_runtime_query` / `execute_stream_data_query` execute a *stored* query entity by RtId: load the entity, dispatch on its CK subtype, build engine query options from persisted state, optionally merge runtime overrides, execute, project.

- **Loading:** `ITenantRepository.GetRtEntityByRtIdAsync<RtPersistentQuery>` / `<RtStreamDataQuery>` — the generic overload uses the entity's CK type from its base, so no separate `ckTypeId`.
- **Dispatch on CK subtype** (switch on runtime type, mirroring the GraphQL resolver):
  - Runtime: `RtSimpleRtQuery` → entity DTOs filtered to persisted `Columns` (reuses `RuntimeEntityCrudTools.FilterAttributes`); `RtAggregationRtQuery` → scalar via `AggregationInput.AggregateResult`; `RtGroupingAggregationRtQuery` → grouped via `AggregateFieldGroupBy`.
  - Stream: `RtSimpleSdQuery` / `RtAggregationSdQuery` / `RtGroupingAggregationSdQuery` / `RtDownsamplingSdQuery` → the four `IStreamDataRepository.Execute*Async` methods; persisted `ArchiveRtId` read off the entity.
- **Runtime overrides:** `extraFilters` is AND-combined with the persisted `FieldFilter` for both tools. Stream adds `fromOverride`/`toOverride`/`limitOverride`/`sourceRtIdsOverride`, each falling back to the persisted value. Merge semantics mirror `StreamDataQueryDtoType.MergeFilters` in asset-repo-services.
- Response envelopes `PersistedRuntimeQueryResponse` / `PersistedStreamDataQueryResponse` discriminate by `QuerySubtype` so the client knows whether `Entities` (simple) or `Rows` (aggregation) carries the payload.

### Studio introspection resolvers

- **`get_available_archive_paths`** — mirrors the asset-repo GraphQL `Octo.availableArchivePaths` resolver. Walks the CK type/record graph from a starting `ckTypeId`, emitting one `ArchivePathInfo` per reachable attribute path (`Path`, `PrimitiveType`, `IsRecord`, `IsArray`, `RecordTypeId`). Bounded by `maxDepth` (default 5, clamped ≥1) plus a visited-record set to stop self-referential records looping. Array-flag propagates into a record's children (a leaf under a `RecordArray` is `IsArray=true`). Missing-record references still emit the record row but skip children. Runs entirely against `ICkCacheService` — no engine round-trip (calls `LoadCacheForTenantAsync` first). Lives in `Services/AvailableArchivePathsResolver.cs` as `internal static`; extend it rather than duplicating the walk.
- **`get_rollup_query_metadata`** — returns the *logical* CK-attribute paths a rollup aggregates over, not physical storage columns. Single-step (raw → rollup): `SourcePath` is already logical, returned verbatim. Cascade (rollup → rollup): `SourcePath` is a physical parent column (e.g. `amountValue_sum`); `RollupLogicalPathResolver.ResolveAsync` walks up parent aggregation specs (`RollupAggregationColumns.Resolve`) to the raw/time-range archive where the path is logical. The server passes two callbacks: `getArchive` (from `GetArchiveRuntimeStore()`) and `getRollup` (from `GetRollupArchiveRuntimeStore()`). Broken chains are silently dropped per the resolver contract. The resolver lives in the `Meshmakers.Octo.Runtime.Engine.CrateDb` package (a direct `McpServices.csproj` dependency, pulling Npgsql + Dapper + Polly.Core transitively — but no DB connection is opened by the MCP server itself).

## Project Layout (key paths)

```
src/McpServices/
├── Program.cs                          # composition root; AddMcpServer().WithHttpTransport()
│                                       #   .WithToolsFromAssembly().WithResourcesFromAssembly()
│                                       # MapMcp("/{tenantId:tenantId}/mcp") + MapMcp("/mcp")
├── Properties/launchSettings.json      # https 5017 / http 5016
├── appsettings.json                    # OctoServiceUrls section
├── Options/
│   ├── McpServiceOptions.cs            # PublicUrl (default https://localhost:5017) for file-transfer URLs
│   └── OctoServiceUrlOptions.cs        # backend service URLs
├── Models/
│   ├── McpRiskAttribute.cs / McpRiskLevel.cs   # [McpRisk] + Low/Medium/High enum
│   ├── <Domain>Responses.cs            # response envelope DTOs grouped by domain
│   ├── Filters/FilterOperatorDto.cs    # 18 filter operators
│   └── Aggregation/
│       ├── AggregationFunctionDto.cs   # count/sum/avg/min/max — DON'T fix to PascalCase
│       ├── AggregationColumnDto.cs · SortColumnDto.cs · AggregationResponses.cs
├── Services/
│   ├── IOctoServiceClientFactory.cs / OctoServiceClientFactory.cs   # per-tenant SDK clients
│   ├── McpSessionContext.cs / McpSessionTokenStore.cs               # session id + OAuth tokens
│   ├── TenantResolutionService.cs                                   # param/route resolution
│   ├── {Identity,Asset,Communication,StreamData,Reporting,Bot}ClientContext.cs
│   ├── IFileTransferStore.cs / FileTransferStore.cs                 # disk-backed + sweeper
│   ├── JobPollingHelper.cs                                          # async-job polling
│   ├── AggregationMapper.cs                                         # family 3 validation + mapping
│   ├── IToolRiskRegistry.cs / ToolRiskRegistry.cs                   # reflects [McpRisk] at startup
│   ├── DynamicToolService.cs / ToolExecutionService.cs             # legacy family-2 discovery/stats
├── Routing/
│   ├── TenantIdRouteConstraint.cs                                   # {tenantId:tenantId}
│   └── FileTransferController.cs                                    # PUT/GET /file-transfer/{upload,download}/{id}
├── Resources/                          # [McpServerResourceType] — CkSchemaResources, KnowledgeResources
└── Tools/                              # ~36 tool classes (181 [McpServerTool] methods)
tests/McpServices.Tests/
├── TestBase.cs / ToolTestBase.cs       # base + SDK-client/file-store mocks
├── Services/                           # factory + context + store + ToolRiskRegistry tests
└── Tools/                              # one *ToolsTests.cs per Tools/ class (~530 tests)
```

`InternalsVisibleTo("McpServices.Tests")` on `McpServices.csproj` lets tests touch `FileTransferStore` directly (the public interface is `IFileTransferStore`).

## Build & Test Quick Commands

```bash
dotnet build src/McpServices/McpServices.csproj -c DebugL    # server only
dotnet build Octo.McpServices.sln -c DebugL                  # server + tests + resources
dotnet test  Octo.McpServices.sln -c DebugL                  # all tests
dotnet test  --filter "FullyQualifiedName~TenantManagementToolsTests"
dotnet test  Octo.McpServices.sln -c Release                 # mirror CI (catches config-sensitive breaks)
cd src/McpServices && dotnet run --environment Development    # dev server (https 5017 / http 5016)
```

Configs: `Debug`, `Release`, `DebugL` (local dev, `OctoVersion=999.0.0`, local NuGet from `../nuget/`). Target framework net10.0. `TreatWarningsAsErrors` on — `CS1591` (missing XML doc) breaks the build for any public `McpServices` member.
