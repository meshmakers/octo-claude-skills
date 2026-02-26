# CLAUDE.md — octo-claude-skills

## What This Is

A Claude Code plugin providing a natural language interface to the OctoMesh platform. Users invoke `/octo <natural language>` and Claude translates intent into `octo-cli` commands, data model exploration queries, or runtime instance lookups — with confirmation for mutating operations.

## Plugin Structure

```
.claude-plugin/plugin.json   — Plugin manifest (name, version, description)
hooks/hooks.json              — SessionStart hook for venv auto-setup
skills/octo/
  SKILL.md                    — Skill definition (frontmatter triggers + full usage guide)
  references/
    command-reference.md      — Complete octo-cli flag reference
    environments.md           — URL mappings per environment (local, test-2, staging, prod)
  scripts/
    run_python.sh             — Venv wrapper (creates .venv, installs deps, delegates to venv Python)
    requirements.txt          — Python dependencies (requests)
    _octo_common.py           — Shared foundation: reads ~/.octo-cli/settings.json, builds auth headers, GraphQL helpers
    ck_explorer.py            — CK model exploration via GraphQL (models, types, enums, search)
    rt_explorer.py            — Runtime instance browsing via GraphQL (list, count, get, search, filter, query)
    gql_introspect.py         — GraphQL schema introspection (top-level fields, type fields)
    _verify_step*.py          — Verification/integration test scripts
    _verify_rt_explorer.py    — RT explorer verification script
```

## Python Script Development

All scripts **must** be invoked through the venv wrapper — never use `python` or `python3` directly:

```bash
bash skills/octo/scripts/run_python.sh skills/octo/scripts/<script.py> [args...]
```

The wrapper (`run_python.sh`) automatically creates a virtual environment in `scripts/.venv/`, installs dependencies from `requirements.txt`, and tracks an md5 hash to reinstall only when deps change. Status messages go to stderr so they don't corrupt `--json` output.

All scripts share `_octo_common.py` which provides:
- Reading `~/.octo-cli/settings.json` for endpoint URLs, tenant ID, and auth token
- Building HTTP headers with Bearer token
- GraphQL query execution helpers

## Adding New Scripts

1. Import shared utilities from `_octo_common.py` (settings, auth, GraphQL helpers)
2. Add any new dependencies to `scripts/requirements.txt`
3. Always invoke via `bash scripts/run_python.sh <your_script.py>`
4. Use `--json` flag convention for machine-readable output and `--first N` for pagination

## Verification / Testing

Verification scripts validate each layer of functionality:

```bash
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step1.py   # Settings + auth
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step2.py   # CK explorer basics
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step3.py   # CK explorer detail
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step4.py   # GraphQL introspection
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_step5_e2e.py  # End-to-end
bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_rt_explorer.py  # RT explorer
```

These require a running OctoMesh environment and valid authentication.

## Skill Authoring

- **SKILL.md frontmatter** (`---` block): The `description` field controls when Claude triggers this skill. It should list all relevant keywords and intents.
- **Reference docs** in `references/`: Detailed content that SKILL.md points to for drill-down (command flags, environment URLs). Keep SKILL.md as the overview; put exhaustive details in references.
- **Progressive drill-down**: Exploration workflows should go broad-to-narrow: models → types in model → type detail → instances → instance detail.

## Hooks

`hooks/hooks.json` defines a `SessionStart` hook that runs `run_python.sh --version` on every session start. This pre-creates the Python venv so the first real script invocation is fast. The hook is silent on failure (`|| true`).

## Versioning

Bump the `version` field in `.claude-plugin/plugin.json` with every commit.

## Naming Conventions

| Pattern | Meaning |
|---------|---------|
| `_*.py` | Internal/verification scripts (not direct user entry points) |
| `*.py` (no prefix) | Public scripts invoked by the skill (ck_explorer, rt_explorer, gql_introspect) |
| `_octo_common.py` | Shared library module imported by all scripts |
