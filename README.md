# octo-claude-skills

Claude Code plugin for the [OctoMesh](https://meshmakers.io) data mesh platform. Ten skills turn natural language into verified `octo-cli` commands, GraphQL exploration, build/devops operations, pipeline YAML, and development guidance — with confirmation gates for everything mutating.

## Skills

| Skill | Use it for |
|-------|-----------|
| `/octo` | **Hub & CLI.** Natural-language `octo-cli` (identity, tenants, blueprints, CK catalogs, stream-data archives, communication, AI services), CK model + runtime instance exploration via GraphQL, environment switching. Routes everything else to the right sibling skill. |
| `/octo-devtools` | Building repos (`Invoke-BuildAll`), starting/stopping services (incl. the non-interactive agent pattern `Start-Octo -nonInteractive $true` / `Stop-Octo`), Docker + kind/Kubernetes infrastructure, git sync, NuGet, certificates. |
| `/octo-agent` | Debugging and investigation: CK model failures (`ResolveFailed`, error code 66), MongoDB diagnostics, the DebugL NuGet dependency chain, selective builds, infrastructure backup/rollback, blueprint failures. |
| `/octo-commit` | Finishing work: commit message format (`AB#<id> New|Fix: …`), Azure DevOps work-item linking, feature branches, PR creation — with a hard review checkpoint before any push. |
| `/pipeline-expert` | ETL pipeline YAML: authoring, node reference (SDK + Mesh Adapter + Zenon), DataContext semantics, validation against adapter schemas, debugging executions. |
| `/octo-mcp` | Developing and extending the OctoMesh MCP server (`octo-mcp-service`): tool families, `*ClientContext` helpers, `[McpRisk]` classification, test conventions, adding-a-tool checklist. |
| `/refinery-studio` | Angular development on the Data Refinery Studio (`octo-frontend-refinery-studio`): OctoGraphQlDataSource pattern, GraphQL codegen, LCARS theme system, lint/test gates. |
| `/octo-operator` | The Kubernetes Communication Operator (`octo-communication-operator`): KubeOps, CommunicationPool CRDs, Helm values layering, TUnit/MTP testing, plus the `octo-helm-core` charts. |
| `/octo-app-builder` | Building a complete OctoMesh-powered app: custom CK model → catalog, HTTP API as Mesh-Adapter pipelines, web UI as operator-deployed Application, packaged as one installable blueprint — the verified end-to-end recipe plus its pitfalls. |
| `/octo-deploy` | Promoting an app from local dev to the shared **test-2** environment: shared-catalog publishing (`octo-ckc`/`octo-bpm`), `docker.mm.cloud` image push, test-2 context + tenant setup, install + kubectl-free verification. Staging/prod deliberately out of scope. |

When in doubt, start with `/octo` — it routes to the right place.

## Installation

```bash
# Add the marketplace and install the plugin
claude plugin marketplace add meshmakers/octo-claude-skills
claude plugin install octo-claude-skills
```

## Prerequisites

- **octo-cli** on PATH (local DebugL build or released version) with a configured context (`~/.octo-cli/contexts.json`)
- **PowerShell 7+** (`pwsh`) for the devtools skill — the OctoMesh workspace must contain `octo-tools/`
- **Python 3.x** for the exploration scripts (venv is created automatically on first use)
- The OctoMesh monorepo workspace for skills that read source (pipeline-expert, octo-agent, octo-mcp, refinery-studio, octo-operator)

## Development

See [CLAUDE.md](CLAUDE.md) for authoring conventions (description budgets, the 500-line SKILL.md rule, the accuracy mandate) and the versioning/release process. Validate after structural changes:

```bash
claude plugin validate . --strict
```

Release history lives in [CHANGELOG.md](CHANGELOG.md).
