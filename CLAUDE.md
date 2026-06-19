# CLAUDE.md — octo-claude-skills

## What This Is

A Claude Code plugin providing skills for working with the OctoMesh platform. Users invoke skills like `/octo <natural language>` and Claude translates intent into `octo-cli` commands, data model exploration queries, build/devops operations, pipeline YAML, or development guidance — with confirmation for mutating operations.

## Plugin Structure

```
.claude-plugin/plugin.json   — Plugin manifest (name, version, metadata; $schema-validated)
.claude-plugin/marketplace.json — Marketplace listing (kept in version sync with plugin.json)
hooks/hooks.json              — SessionStart hooks (venv pre-warm, pwsh probe)
skills/
  octo/                       — Hub skill: octo-cli NL interface, CK/RT exploration, routing to siblings
    SKILL.md                  — Skill definition (frontmatter + operational guide)
    references/               — command-reference.md (full flag detail), environments.md (URLs per env),
                                temp-tenants.md (non-interactive temp-tenant lifecycle via client credentials)
    scripts/                  — Python explorers (ck_explorer, rt_explorer, gql_introspect,
                                pipeline_validate) + run_python.sh venv wrapper + _octo_common.py
  octo-devtools/              — Build, services (incl. non-interactive), infra, git, kind/Kubernetes
  octo-agent/                 — Debugging/investigation: CK internals, MongoDB, build chain, rollback
  octo-commit/                — Commit/PR workflow with Azure DevOps work-item linking
  pipeline-expert/            — ETL pipeline YAML authoring, nodes, DataContext, validation
  octo-mcp/                   — Developing/extending the OctoMesh MCP server (octo-mcp-service)
  refinery-studio/            — Angular development on the Data Refinery Studio frontend
  octo-operator/              — Kubernetes Communication Operator + octo-helm-core charts
  octo-app-builder/           — End-to-end OctoMesh app building: CK model → catalog → blueprint →
                                HTTP-API pipelines → operator-deployed Application workload
  octo-deploy/                — Promotion local → test-2: shared-catalog publishing (octo-ckc/octo-bpm),
                                docker.mm.cloud image push, test-2 context/tenant setup, kubectl-free verify
  octo-ck-miro/               — UML class diagrams of all Construction Kits on a Miro board, read from
                                a given git branch of octo-construction-kit via `git show` (non-destructive)
```

## Python Script Development

All scripts **must** be invoked through the venv wrapper — never use `python` or `python3` directly:

```bash
bash skills/octo/scripts/run_python.sh skills/octo/scripts/<script.py> [args...]
```

The wrapper (`run_python.sh`) automatically creates a virtual environment in `scripts/.venv/`, installs dependencies from `requirements.txt`, and tracks an md5 hash to reinstall only when deps change. Status messages go to stderr so they don't corrupt `--json` output.

All scripts share `_octo_common.py` which provides:
- Reading the active context from `~/.octo-cli/contexts.json` for endpoint URLs, tenant ID, and auth token
- Building HTTP headers with Bearer token
- GraphQL query execution helpers

## Adding New Scripts

1. Import shared utilities from `_octo_common.py` (context, auth, GraphQL helpers)
2. Add any new dependencies to `scripts/requirements.txt`
3. Always invoke via `bash scripts/run_python.sh <your_script.py>`
4. Use `--json` flag convention for machine-readable output and `--first N` for pagination

## Verification / Testing

Verification scripts validate each layer of functionality:

```bash
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step1.py   # Context + auth
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step2.py   # CK explorer basics
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step3.py   # CK explorer detail
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step4.py   # GraphQL introspection
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step5_e2e.py  # End-to-end
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_rt_explorer.py  # RT explorer
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_data_layer.py  # Data layer integration
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_e2e_real.py    # Real e2e with pipeline execution
```

These require a running OctoMesh environment and valid authentication.

Validate the plugin manifests after any manifest or skill-structure change:

```bash
claude plugin validate . --strict
```

## Skill Authoring

- **SKILL.md frontmatter description**: prose-first — one or two sentences stating what the skill does and the key use case FIRST, then a `Trigger on:` tail with the most important keywords. Keep the whole description **under 1200 characters** (Claude Code truncates the combined listing entry at 1536 chars; leave headroom). Highest-value triggers go earliest.
- **SKILL.md body**: keep **under 500 lines** — the body is loaded into context every turn, so every line is recurring token cost. State what to do, don't narrate why.
- **Reference docs** in `references/`: detailed content that SKILL.md points to for drill-down (command flags, node properties, URL mappings). Keep SKILL.md as the operational overview; put exhaustive details in references — Claude loads them on demand.
- **Progressive drill-down**: exploration workflows go broad-to-narrow: models → types in model → type detail → instances → instance detail.
- **Accuracy**: every command, flag, parameter, node property, port, and version documented in a skill must be verified against the OctoMesh source repos or read-only `octo-cli <Command> --help` output before writing. Never document from memory.

## Hooks

`hooks/hooks.json` defines `SessionStart` hooks that pre-create the Python venv (so the first real script invocation is fast) and probe the PowerShell version. Hooks are silent on failure (`|| true`).

## Versioning

The `version` field in `.claude-plugin/plugin.json` is the release gate: **bump it (semver) when releasing a meaningful change set, not on every commit**. Users on a pinned version only receive updates when the version increases.

Keep `marketplace.json`'s plugin entry version in sync for clarity — but note that when both files declare a version, **`plugin.json` wins** per the Claude Code plugin spec.

Record every release in `CHANGELOG.md`. Run `claude plugin validate . --strict` before tagging a release.

## Naming Conventions

| Pattern | Meaning |
|---------|---------|
| `_*.py` | Internal/verification scripts (not direct user entry points) |
| `*.py` (no prefix) | Public scripts invoked by the skill (ck_explorer, rt_explorer, gql_introspect, pipeline_validate) |
| `_octo_common.py` | Shared library module imported by all scripts |
