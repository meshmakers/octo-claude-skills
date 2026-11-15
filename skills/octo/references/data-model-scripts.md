# Data-model scripts and CK types — detail

Drill-down for the `octo` skill (SKILL.md → *Data Model Exploration*). `<RUN>` is the venv-wrapper prefix defined there:

```
<RUN> = bash "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/run_python.sh" "${CLAUDE_PLUGIN_ROOT}/skills/octo/scripts/<script.py>"
```

## `gql_introspect.py` — GraphQL Schema Introspection

Safety valve for when field names change between server versions. `<RUN> gql_introspect.py top` shows top-level query fields; `<RUN> gql_introspect.py type <name>` (e.g. `CkType`) shows a GraphQL type's fields. Flags: `--json`, `--tenant <id>`, `--insecure`.

## `pipeline_validate.py` — Pipeline YAML Validator

Validates a pipeline YAML file against an adapter's JSON Schema **before** deploying: checks that `triggers` and `transformations` sections exist and that every node `type` is known to the schema, recursing into nested container nodes (`ForEach@1`, `For@1`, `If@1`, `Switch@1`, `BufferData@1`). Use it as a pre-deploy gate so a typo'd node type fails fast locally instead of at `DeployPipeline`. Exits 0 with `PASS` when valid, non-zero with a list of `FAIL` errors (each carrying a JSONPath-like location) otherwise. Supply the schema one of two ways (mutually exclusive):

```
<RUN> pipeline_validate.py my-pipeline.yaml --schema schema.json   # local schema file (e.g. saved via GetPipelineSchema -o)
<RUN> pipeline_validate.py my-pipeline.yaml --adapter-id <adapterRtId> --insecure   # live from an adapter via octo-cli (--insecure: localhost self-signed certs)
```

## `::` Association Meta-Query Columns

N:M associations expose two meta columns via the `::` path syntax, usable as query columns and in field filters (GraphQL and saved queries):
- `navigationProp.TargetType::totalCount` — number of associated entities
- `navigationProp.TargetType::exists` — boolean (has any association)

Example: to find machines with more than 3 sensors, filter on `sensors.Sensor::totalCount` `GREATER_THAN` `3`. The `::totalCount` filter compiles to a MongoDB aggregation pipeline server-side.

## Stream-Data & Blueprint CK Types

When stream data is enabled (`EnableStreamData`), the `System.StreamData` CK model is loaded. Its hierarchy is `Archive` (abstract) → `RawArchive` / `RollupArchive` / `TimeRangeArchive`. Browse with `rt_explorer.py`:
- `System.StreamData/Archive` (abstract base), `System.StreamData/RawArchive`, `System.StreamData/RollupArchive`, `System.StreamData/TimeRangeArchive`

Stream-data **query** entities live in the `System` model: `System/SimpleSdQuery`, `System/AggregationSdQuery`, `System/GroupingAggregationSdQuery`, `System/DownsamplingSdQuery` (executed with GraphQL `streamData.streamDataQuery(rtId)`). Aggregation functions (`System/AggregationTypes`): `Count`, `Minimum`, `Maximum`, `Average`, `Sum`, `TimeWeightedAverage`, `StateDuration` and, from System 2.8.0, `Integral` (transient GraphQL `aggregationType: INTEGRAL`, MCP `integral`): the step integral of a numeric column over `[from, to)` in value unit x hours (W -> Wh, kW -> kWh), last value carried forward, carry-in from the last row before `from`, several rtIds summed, empty window = null; `from`/`to` required. Served by raw archives and by rollups that store a `TimeWeightedAvg` of the column (read from the stored per-bucket integral; aligned windows equal the raw result, an unaligned window reads every overlapping bucket in full; a rollup with only `Avg`/`Sum` of the column refuses it, naming the missing TimeWeightedAvg); downsampling only on such rollups (one integral per bin). Energy import/export from a signed power column: split the sign with computed columns (`ActivePower > 0 ? ActivePower : 0`), never with a field filter. Reference: octo-documentation `streamData/retrieve/aggregationQuery.md#integral` and `#integral-rollup`. **Local-day bins** (AB#7360/7361/7362): downsampling cuts local calendar days instead of equal-width UTC buckets with GraphQL `timeZone`, `binInterval` (whole days) and `binOrigin` (`HH:mm`), MCP `query_stream_data_downsampling` `timeZone`, `binIntervalDays`, `binOrigin` (with any of them set, `limit` is ignored: the engine sizes the bins from the query range); a day rollup cuts the same days with `createRollupArchive` `referenceTimeZone` + `dayStartOffsetMs`. Gas day: `Europe/Vienna`, `06:00`, 1 day - days of 23/24/25 hours across DST, an empty day has Count 0. MCP `get_rollup_query_metadata` shows `referenceTimeZone` and `dayStartOffset` of a rollup.

Blueprint state is stored tenant-locally (no longer in a cross-tenant system DB) as `System/BlueprintInstallation`, `System/BlueprintHistory`, `System/BlueprintBackup` — query these to diagnose blueprint state. Always discover the exact loaded type IDs with `ck_explorer.py` first; the `isDataStream`/`isStreamType` GraphQL fields were removed, so any query selecting them will fail.
