---
name: octo-mcp
description: Develop and extend the OctoMesh MCP server (octo-mcp-service) — the Model Context Protocol server exposing ~181 tools that mirror octo-cli plus generic CK CRUD and aggregation/stream-data queries, used by AI assistants to administer OctoMesh tenants without the CLI or GraphQL. Use when adding or modifying MCP tools, classifying tool risk, wiring *ClientContext helpers, building file-transfer flows, or following the mandatory test conventions. Trigger on: MCP tool development, octo-mcp-service, adding MCP tools, McpRisk, MCP server, model context protocol server work in OctoMesh.
---

# OctoMesh MCP Server Development

## Purpose

Guide for developing and extending **`octo-mcp-service`** (`C:\dev\meshmakers\octo-mcp-service`), the OctoMesh **Model Context Protocol** server. It exposes **~177 tools** (181 distinct `[McpServerTool]` methods today) that mirror the full `octo-cli` command surface plus generic CK-type CRUD and aggregation/stream-data queries. AI assistants connect over HTTP and administer tenants — identity, blueprints, communication, time-series, reporting, file transfer — without invoking the CLI or writing GraphQL.

This skill is for **working on the server itself** (adding/changing tools), not for *using* it as a client. The single most valuable workflow is the **Adding a New Tool checklist** below.

**Ground truth lives in the repo's own `CLAUDE.md`** — it is rich and authoritative. Read it before any substantial change. This skill is the fast operational overview that points at the right conventions.

## The Three Tool Families

Know which family you are touching before you write code — they have different code paths, conventions, and cost profiles, and must not be merged.

| Family | Talks to | Helper pattern | Lives in |
|---|---|---|---|
| **1. Platform-admin** | Backend services over HTTP via `Meshmakers.Octo.Sdk.ServiceClient` | `*ClientContext.TryBuild` | most `Tools/*Tools.cs` |
| **2. Generic CK CRUD + schema** | Runtime engine (MongoDB) directly via `ITenantRepository` | none (direct) | `RuntimeEntityCrudTools`, `SchemaDiscoveryTools` |
| **3. Aggregation + stream-data** | Engine directly (`ITenantRepository` / `ITenantContext.GetStreamDataRepository()`) | `AggregationMapper`, `StreamDataContext` | `RuntimeAggregationTools`, `StreamDataAggregationTools`, `StreamDataMetadataTools` |

**Decision:** mirrors an `octo-cli` command → Family 1 (`*ClientContext`). Runtime/CRUD read-write or schema discovery → Family 2. Aggregation, stream-data, or persisted-query execution → Family 3 (`AggregationMapper`, never `*ClientContext`).

For the full architecture rationale, aggregation internals, persisted-query dispatch, and archive-path traversal, read `references/architecture.md`.

## The `*ClientContext` Helper Pattern (Family 1)

Every SDK-backed tool starts the same way — **never call the factory directly**:

```csharp
var ctx = IdentityClientContext.TryBuild(server, tenantId);
if (ctx.Error != null)
{
    return new MyResponse { IsSuccess = false, ErrorMessage = ctx.Error };
}
// ctx.Client is the IIdentityServicesClient; ctx.TenantId is the resolved tenant
```

`TryBuild` is an `internal sealed record` factory that: pulls the session access token (`McpSessionContext.TryGetAccessToken`), returns `"Not authenticated. Call 'authenticate' first."` if missing, resolves the tenant via `ITenantResolutionService`, then builds a **fresh per-request** SDK client through `IOctoServiceClientFactory`. It returns a `(Client, TenantId, Error)` triple.

Six context helpers in `src/McpServices/Services/`:

| Context | Backing SDK client | Tenant routing |
|---|---|---|
| `IdentityClientContext` | `IIdentityServicesClient` | per-tenant (`{tenantId}/v1`) |
| `AssetClientContext` | `IAssetServicesClient` | per-tenant |
| `CommunicationClientContext` | `ICommunicationServicesClient` | per-tenant, falls back to system |
| `StreamDataClientContext` | `IStreamDataServicesClient` | system (`api/v1`), tenant per call |
| `ReportingClientContext` | `IReportingServicesClient` | per-tenant, falls back to system |
| `BotClientContext` | `IBotServicesClient` | system-scoped |

For rare `Bot`/`AdminPanel` one-offs (e.g. `reconfigure_log_level`) there is no helper — grab the factory via `server.Services.GetRequiredService<IOctoServiceClientFactory>()`.

**CRITICAL: never share SDK clients across requests.** They cache `ServiceUri` on first use, so a reused client routes the wrong tenant on the second call. `TryBuild` returns a fresh client every time — always go through it.

## Tool Signature & Response Envelope

```csharp
[McpServerTool(Name = "my_snake_case_tool")]
[McpRisk(McpRiskLevel.Medium)]   // omit for Low
[Description("Equivalent to octo-cli MyCommand. Plus what it does.")]
public static async Task<MyResponse> MyTool(
    McpServer server,
    [Description("Required arg description.")] string requiredArg,
    [Description("Optional arg.")] bool? optionalArg = null,
    [Description("Tenant to operate on. Falls back to URL route.")] string? tenantId = null)
```

- `static async Task<TResponse>`; first param is `McpServer server` (**not** `IMcpServer`).
- Every parameter needs a `[Description]` — these become the AI's documentation.
- `tenantId` is the **last** optional parameter on tenant-scoped tools.
- Tool `Name` is `snake_case` mirroring the CLI verb (CLI `CreateTenant` → MCP `create_tenant`).

Response envelope (minimum fields):

```csharp
public class MyResponse
{
    public bool IsSuccess { get; set; }
    public string? ErrorMessage { get; set; }
    public string? Message { get; set; }
    public string? TenantId { get; set; }
    // ... tool-specific payload
}
```

- **Never throw** out of a tool — catch and put `ex.Message` into `ErrorMessage`.
- **Never write to `Console` or `ILogger`** for user-visible output — the MCP transport does not surface stdout to the client. Use `Message` / `ErrorMessage`.
- **Return SDK DTOs as-is** (`UserDto`, `ClientDto`, …); the framework serialises them. For composite payloads add a wrapper DTO in `src/McpServices/Models/<Domain>Responses.cs`, grouped by domain — not one file per type.

**CS1591 breaks the build.** `TreatWarningsAsErrors` is on, so every public type/property/method on a new tool class needs an XML doc summary.

## Risk Classification — `[McpRisk]`

`[McpRisk(McpRiskLevel.Low|Medium|High)]` (in `src/McpServices/Models/`) classifies a tool's blast radius. The AI Adapter worker calls `get_tool_risk_metadata` once at session start and uses the result to drive its **user-facing approval gate**. `ToolRiskRegistry` reflects over the assembly at startup; tools without the attribute resolve as **Low**.

**This is metadata, not authorisation** — authorisation is delegated to the backend services via the propagated OAuth token.

| Level | Use for | Worker behaviour |
|---|---|---|
| **Low** (default, omit attr) | read-only, schema introspection, narrow single-instance create/update | runs without prompting |
| **Medium** | single-instance deletes, schema-driven actions, bulk reads | logs/audits, does not pause |
| **High** | bulk delete, dropping a CK type/attribute/enum value, prod deploy, force-push, blueprint install/uninstall/apply-update | pauses on PreToolUse for approval |

Decide the level **when you write the tool** — flipping it later is a behaviour change for any consumer that cached the registry. (Current spread: ~53 High, ~49 Medium, the rest Low by default.)

## Confirm-Gate for Destructive Operations

The CLI uses an interactive `(y/N)` prompt; MCP cannot, so destructive tools take a `confirm` parameter:

```csharp
public static async Task<MyResponse> DeleteThing(
    McpServer server, string thingId,
    [Description("Must be true to actually delete.")] bool confirm = false,
    string? tenantId = null)
{
    if (!confirm)
        return new MyResponse
        {
            IsSuccess = false,
            ErrorMessage = $"Refusing to delete '{thingId}' without confirm=true."
        };
    // ... actually do it
}
```

**CRITICAL:** never default `confirm = true`; never skip the gate inside a batch helper — every destructive call passes through it. Test the refusal path. A High-risk tool typically pairs `[McpRisk(High)]` with a `confirm` gate.

## Adding a New Tool — Step-by-Step Checklist

The core workflow. Files are under `C:\dev\meshmakers\octo-mcp-service`.

1. **Find the source command.** For a Family-1 tool, locate the equivalent in `octo-cli/src/ManagementTool/Commands/Implementations/**`. Note the SDK method signature, required args, and whether it is destructive.
2. **Pick the family / context.** Family 1 → choose the `*ClientContext` matching the SDK client the CLI uses. Family 2/3 → use `ITenantRepository` / `AggregationMapper` / `StreamDataContext`.
3. **Add a response DTO** if the payload is non-trivial: `src/McpServices/Models/<Domain>Responses.cs` (or `Models/Aggregation/` for Family 3). Reuse existing envelopes where possible.
4. **Write the tool method** in the right `Tools/<Domain>Tools.cs` following the signature pattern. Add `[McpRisk]` and a `confirm` gate if destructive. XML-doc every public member.
5. **New SDK client?** (Bot, AdminPanel) — update `IOctoServiceClientFactory` + `OctoServiceClientFactory` + `OctoServiceUrlOptions` + the test `ToolTestBase`.
6. **Write tests** in `tests/McpServices.Tests/Tools/<Domain>ToolsTests.cs` — see Test Conventions below. Mandatory: happy path, unauthenticated, missing/invalid args, and (if destructive) confirm-required.
7. **`dotnet build src/McpServices/McpServices.csproj -c DebugL`** then **`dotnet test Octo.McpServices.sln -c DebugL`** — all green before commit.
8. **Update `README.md`** Available Tools section only if you added a new tool *category*.

## Mandatory Test Conventions

Tests live in `tests/McpServices.Tests/` (xUnit + Moq + FluentAssertions), **one test file per `Tools/` class**. There are ~525 tests today across 35 tool files — roughly **2.4+ tests per tool**. Do not lower the ratio; every tool ships with its tests in the same commit.

Per-tool minimum coverage:
- **Happy path** — mock the SDK client, return a realistic DTO, assert `IsSuccess = true` and that the right SDK method was called with the right args.
- **Unauthenticated** — `GivenUnauthenticated()`, assert `IsSuccess = false`, `ErrorMessage` contains `"Not authenticated"`, **no** SDK call.
- **Missing required args** — pass empty/null, assert a validation error, no SDK call.
- **Destructive without confirm** — assert refusal when `confirm` is absent.

`ToolTestBase : TestBase` provides the mock `McpServer`, `IMcpSessionTokenStore`, `IOctoServiceClientFactory`, the 7 per-SDK-client mocks (`MockIdentityClient`, `MockAssetClient`, …, `MockAdminPanelClient`), the real `FileTransferStore`, and helpers `GivenAuthenticated()` / `GivenUnauthenticated()` / `GivenTokenExpired()`.

```csharp
public class MyToolsTests : ToolTestBase
{
    public MyToolsTests() { GivenAuthenticated(); }

    [Fact]
    public async Task MyTool_HappyPath_CallsSdk()
    {
        MockIdentityClient.Setup(c => c.DoSomething("x")).ReturnsAsync(new SomeDto());
        var result = await MyTools.MyTool(MockServer.Object, "x");
        result.IsSuccess.Should().BeTrue();
        MockIdentityClient.Verify(c => c.DoSomething("x"), Times.Once);
    }
}
```

**Test pitfalls:**
- `CkTypeId` is `Name-VersionUint`, not SemVer — `new CkTypeId("MyType-1")` works; `"MyType-1.0.0"` throws.
- `OctoObjectId` must be a 24-char hex string (e.g. `"507f1f77bcf86cd799439011"`).
- Moq matchers must use the declared type-param — `It.IsAny<IEnumerable<T>>()`, not `It.IsAny<List<T>>()`.

**CI runs the suite in `Release`** (not `DebugL`) against published NuGet packages. When you suspect a config-sensitive break, mirror it locally with `dotnet test Octo.McpServices.sln -c Release`. Real-service tests go in a separate `*SystemTests` project (the CI glob excludes `*SystemTests.csproj`).

## File-Transfer Architecture

Binary payloads do **not** go through tool parameters — a separate HTTP channel does. The JSON-RPC tool call coordinates an opaque transfer id; bytes flow through `FileTransferController` at `/file-transfer/{upload,download}/{id}`.

- `IFileTransferStore` / `FileTransferStore` — disk-backed buffers under `Path.GetTempPath()/octo-mcp-file-transfer/<random>/`; ids are random 128-bit GUIDs that expire in 30 min.
- `FileTransferSweeper` — `BackgroundService` purging expired entries every 5 min.
- `FileTransferController` — `PUT .../upload/{id}` (5 GiB cap, streaming) and `GET .../download/{id}` (range support).

Upload-then-import flow (URL built from `McpServiceOptions.PublicUrl`, default `https://localhost:5017`):

```
prepare_file_upload(fileName) → { transferId, uploadUrlPath }
HTTP PUT to <publicUrl>/file-transfer/upload/{transferId}
import_ck_model(transferId, tenantId) → store.GetUpload(transferId) gives the disk path → SDK import → store.DeleteUpload
```

Export-then-download mirrors it: `export_runtime_model_by_query` runs an asset job, downloads to a temp file, `store.RegisterDownload(...)`, returns a `downloadUrlPath`.

**CRITICAL: do NOT add base64-in-tool-parameter as an alternative.** The file-transfer endpoints are the only sanctioned mechanism — base64 in JSON-RPC blows up token budgets and memory.

## Auth, Tenant Resolution & MCP Resources

- **OAuth Device flow:** the `authenticate` tool issues a device code; the user logs in via browser; `check_auth_status` polls until tokens land in `IMcpSessionTokenStore`, keyed by the `Mcp-Session-Id` HTTP header.
- **Per-request token injection:** `McpSessionContext.TryGetAccessToken(server)` → fed into the factory by the `*ClientContext` helpers.
- **Tenant resolution order:** explicit `tenantId` param → route param on `/{tenantId}/mcp` → error. **Never store tenant state on the session** — stateless multi-tenancy is the design.
- **MCP Resources:** `[McpServerResourceType]` classes in `src/McpServices/Resources/` (`CkSchemaResources`, `KnowledgeResources`) are exposed via `resources/list` + `resources/read` so the worker can materialise schema/knowledge into context instead of repeated `get_*` tool calls.

## Run Locally & Connect a Client

Built on **.NET 10 (net10.0)**; default build config is **DebugL** (local NuGet from `../nuget/`, `OctoVersion=999.0.0`).

```bash
# build just the server
dotnet build src/McpServices/McpServices.csproj -c DebugL

# run the dev server directly (https 5017 / http 5016)
cd src/McpServices && dotnet run --environment Development
```

Or start it as part of the full stack with octo-tools (default-on):

```powershell
Start-Octo -mcpService $true -nonInteractive $true
```

`Start-Octo` launches the built `Meshmakers.Octo.Backend.McpServices.dll` with `--urls=https://*:5017;http://*:5016`. (Ports verified in `launchSettings.json` and `Start-Octo.psm1`.) **Read-only** here — never run mutating MCP calls or live-service commands from this skill.

A client connects over HTTP to `https://localhost:5017/mcp` (tenant via tool param) or `https://localhost:5017/{tenantId}/mcp` (tenant in route), authenticates with the `authenticate` + `check_auth_status` device flow, then calls tools.

## Things NOT to Do

- Don't bypass `*ClientContext` helpers (Family 1) — they enforce auth + tenant + factory routing uniformly.
- Don't add a tool without tests in the same commit.
- Don't accept base64 file content as a tool parameter — use file-transfer endpoints.
- Don't default `confirm` to `true`, and don't skip the gate in batch helpers.
- Don't write to `Console`/`ILogger` for user-visible output.
- Don't share SDK clients across requests.
- Don't "fix" `AggregationFunctionDto` to PascalCase — the lowercase `count/sum/avg/min/max` is intentional (see references).

## References

- **`references/architecture.md`** — full three-family rationale, aggregation internals (`AggregationMapper`, lowercase `AggregationFunctionDto`, `StreamDataContext` cascade, filter operators), persisted-query dispatch, archive-path/rollup introspection, and the project layout map.
