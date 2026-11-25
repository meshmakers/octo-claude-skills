# octo-claude-skills

Claude Code plugin for the [OctoMesh](https://meshmakers.io) data mesh platform. Thirteen skills turn natural language into verified `octo-cli` commands, GraphQL exploration, build/devops operations, pipeline YAML, Miro CK visualizations, cluster log access, and development guidance — with confirmation gates for everything mutating.

## Skills

| Skill | Use it for |
|-------|-----------|
| `/octo` | **Hub & CLI.** Natural-language `octo-cli` (identity, tenants, blueprints, CK catalogs, stream-data archives, communication, AI services), CK model + runtime instance exploration via GraphQL, environment switching. Routes everything else to the right sibling skill. |
| `/octo-devtools` | Building repos (`Invoke-BuildAll`), starting/stopping services (incl. the non-interactive agent pattern `Start-Octo -nonInteractive $true` / `Stop-Octo`), Docker + kind/Kubernetes infrastructure, git sync, NuGet, certificates. |
| `/octo-agent` | Debugging and investigation: CK model failures (`ResolveFailed`, error code 66), MongoDB diagnostics, the DebugL NuGet dependency chain, selective builds, infrastructure backup/rollback, blueprint failures. |
| `/octo-commit` | Finishing work: commit message and PR title format (`AB#<id> <Type>: …`, type one of Fix, New, Chore, Refactor, Test, Docs), Azure DevOps work-item linking, feature branches, PR creation and hand-over for review: with `octo-claude-pm` installed its `agent-operating-rules` §2.3 decide the CodeRabbit review rounds and the merge queue (`request_merge`); the agent never merges — the developer or a maintainer tests and merges — with a hard review checkpoint before any push. |
| `/pipeline-expert` | ETL pipeline YAML: authoring, node reference (SDK + Mesh Adapter + Zenon), DataContext semantics, validation against adapter schemas, debugging executions. |
| `/octo-mcp` | Developing and extending the OctoMesh MCP server (`octo-mcp-service`): tool families, `*ClientContext` helpers, `[McpRisk]` classification, test conventions, adding-a-tool checklist. |
| `/refinery-studio` | Angular development on the Data Refinery Studio (`octo-frontend-refinery-studio`): OctoGraphQlDataSource pattern, GraphQL codegen, LCARS theme system, lint/test gates. |
| `/octo-operator` | The Kubernetes Communication Operator (`octo-communication-operator`): KubeOps, CommunicationPool CRDs, Helm values layering, TUnit/MTP testing, plus the `octo-helm-core` charts. |
| `/octo-app-builder` | Building a complete OctoMesh-powered app: custom CK model → catalog, HTTP API as Mesh-Adapter pipelines, web UI as operator-deployed Application, packaged as one installable blueprint — the verified end-to-end recipe plus its pitfalls. |
| `/octo-deploy` | Promoting an app from local dev to the shared **test-2** environment: shared-catalog publishing (`octo-ckc`/`octo-bpm`), `<registry>` image push, test-2 context + tenant setup, install + kubectl-free verification. Staging/prod deliberately out of scope. |
| `/octo-ck-miro` | Visualizing Construction Kits as detailed UML class diagrams on a Miro board — types with attributes/datatypes, records, enums, inheritance, associations with multiplicity, cross-CK references. Reads YAMLs from a given git branch in `octo-construction-kit` (non-destructive via `git show`), creates a new board or adds to an existing one. |
| `/octo-logs` | Reading and tracing **deployed-cluster logs** in **Dash0** via the Dash0 MCP tools: filters by namespace/container/pod/service/severity, body search, D0QL error-rate counts, tracing an error across pod redeployments and into its trace. No credentials — the MCP connection authenticates itself. (Loki/LogQL no longer exist.) |
| `/octo-logs-setup` | One-time **setup / health check of the Dash0 MCP connection** used by `/octo-logs`: register the server, OAuth login via `/mcp`, verify with `listDatasets`. Also explains removing the obsolete `LOKI_*` profile variables. |

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
claude plugin validate .
```

## Skill owners and the same-change rule

Every skill has an owning PO agent, listed in [`OWNERS`](OWNERS): Heimdall (octo-devtools, octo-agent, octo-commit, octo-deploy, octo-logs, octo-logs-setup, octo-operator), Thor (octo, pipeline-expert, octo-app-builder), Freya (refinery-studio, octo-ck-miro), Mimir (octo-mcp). The owner keeps the skill true and receives its drift findings.

**Same-change rule:** whoever changes behaviour a skill describes (a cmdlet, an octo-cli command or argument, a pipeline node, a documentation path, a workflow) updates the skill in the same change.

## Drift check

A skill that names something that no longer exists sends an agent into a dead end. The drift check compares every name the skills use with a committed inventory of the names that exist:

| Kind | Found in the skills as | Inventory source |
|------|------------------------|------------------|
| `cmdlet`, `cmdlet-parameter` | `Verb-Noun` and its `-Parameter` in code (inline code or fenced blocks; PowerShell's own cmdlets and common parameters are always accepted, parameter prefixes too) | octo-tools `modules/*.psm1` |
| `octo-cli-command`, `octo-cli-argument` | `octo-cli … -c <Command> -arg --argument` | octo-cli `src/ManagementTool/Commands/**` |
| `node` | `Name@<version>` in code | `[NodeName("Name", n)]` outside test folders of the `octo-*` repositories |
| `repo-doc` | `<repo>/AGENTS.md`, `<repo>/CLAUDE.md`, `<repo>/docs/…` for repositories matching `repoPatterns` | AGENTS.md/CLAUDE.md presence and the paths below `docs/` |
| `reference-to-shim` | `<repo>/CLAUDE.md` for a repository that has AGENTS.md (point to AGENTS.md) | as above |
| `machine-path` | `C:\dev` anywhere | — |

Run it locally (Python 3.10+, standard library only):

```bash
python3 scripts/check_skill_drift.py              # findings grouped by owner; exit 1 on a finding or a skill without owner
python3 scripts/check_skill_drift.py --summary    # plus counts per skill and owner
python3 scripts/check_skill_drift.py --ignore-baseline   # also the baselined findings
python3 -m unittest discover -s tests -v          # fixture tests
```

The GitHub Actions workflow [`skill-drift`](.github/workflows/skill-drift.yml) runs the inventory scan, the unit tests, the drift check and the frontmatter validation on every pull request (also the daily `docs/batch-*` PRs) and on every push to `main`. Each step runs even when an earlier one failed, so a red drift check never hides a failed scan or frontmatter step; the committed skills are checked only by the drift check step (the unit tests use fixtures). It needs no secrets and no access to other repositories. It **warns** (does not fail) when the inventory is more than 14 days old, so a missed weekly refresh is visible.

Cmdlets are recognised by their verb: the PowerShell approved verbs, the verbs octo-tools uses outside that list (`OCTO_TOOLS_VERBS` in `scripts/check_skill_drift.py`: Check, Clone, Compile, Create, Delete, Normalize) and every verb of the current inventory. The static list keeps a verb after its last cmdlet was renamed, so a skill that still names the old cmdlet fails. A refresh that brings a cmdlet with a new non-approved verb fails the unit tests until the verb is added to `OCTO_TOOLS_VERBS`.

### Inventory (`inventory/names.json`, schema version 1)

```json
{
  "schemaVersion": 1,
  "generated": "2026-11-25",
  "repoPatterns": ["octo-*"],
  "excludeRepos": ["…"],
  "cmdlets": {"Start-Octo": ["nonInteractive", "…"]},
  "octoCli": {"commands": {"Setup": ["--email", "-e", "…"]}, "globalArguments": ["-c", "--context", "…"]},
  "nodes": {"ApplyChanges": [1, 2]},
  "repos": {"octo-tools": {"agentsMd": true, "claudeMd": true, "docHashes": ["<16 hex digits>", "…"]}}
}
```

Names only: no hosts, URLs, file contents or secrets. Paths below `docs/` are stored as the first 16 hex digits of the SHA-256 of the path (`docs/guide.md`, and every folder on the way such as `docs/guides`), so internal document names stay out of this public repository while the check can still resolve every path a skill names. `scripts/scan_inventory_secrets.py` fails on anything in the inventory that is not a name; CI and the weekly refresh run it.

### Accepted mentions and the baseline (`inventory/allowlist.json`)

Each entry has `kind`, `name` (case-insensitive glob), optional `files` (globs), a `reason` and the `workItem` that tracks it; an entry without a work item is refused, and so is an entry whose kind is `*` or whose name contains a glob character (`*`, `?`, `[`) without `files`. Two uses: deliberate mentions (a removed node named as the predecessor of its replacement) and the **baseline** of known findings (`reason` starting with `baseline <date>:`), each tracked by a Bug or story until the owner fixes the skill — then the entry is removed. The check fails only on findings that are not accepted.

### Weekly refresh (AB#9741)

The inventory comes from repositories public CI cannot read, so it is generated where the checkouts are:

```bash
python3 scripts/generate_name_inventory.py --monorepo <folder with the checkouts> [--date YYYY-MM-DD]
python3 scripts/refresh_name_inventory.py --monorepo <folder with the checkouts>                     # dry run
python3 scripts/refresh_name_inventory.py --monorepo <folder with the checkouts> --apply   # the real run (= --push --file-bugs)
```

`generate_name_inventory.py` is deterministic: the same trees and the same `--date` give byte-identical output. `inventory/sources.json` names the repositories (`repoPatterns`, `nodeRepoPatterns`, `extraRepos`, `excludeRepos`, and `requiredRepos`, whose absence fails the refresh instead of dropping their names).

`refresh_name_inventory.py` is a dry run unless `--apply` (or `--push` / `--file-bugs`) is given. It makes fresh shallow HTTPS clones of the default branches (credentials from the GitHub CLI, never a prompt; URLs are never printed), regenerates the inventory in a fresh clone of this repository, scans it, and with `--push` commits it on `<user>/AB#9741_name-inventory-refresh` and pushes it **without a pull request** — the daily docs batch takes it to `main`. While the refresh branch exists on the remote, it is continued with today's `main` merged into it (`main` takes squash or rebase merges only, so a batched branch is never an ancestor of `main`); once the docs batch is merged and has deleted the branch, the next run starts again from `main`. The refresh branch carries `inventory/names.json` only: when it differs from `main` in any other file after the merge, the run fails and names the files instead of pushing. The drift check then runs on today's `main` with the new inventory, and with `--file-bugs` every finding that is not accepted becomes one Bug per skill (`Skill drift: <skill> …`, tag `skill-drift`) under the Sustain Feature of the skill's owner; an open Bug is updated instead of creating a second one, and while a skill is clean its open Bug gets a comment in every run until someone closes it. The open Bug of a skill is found by its exact title key: the word after `Skill drift: ` must equal the skill name, so the Bug of `octo-agent` is never taken for `octo` (the WIQL `CONTAINS` query is only a coarse filter); of several open Bugs of one skill the lowest ID wins. A failed run (not a finding) is reported as a comment on the Platform Ops Sustain Feature; `--update-self` (used by the launchd job) fast-forwards the job's own checkout first and reports a failed update the same way. Owners, project and Sustain Features are read at run time from the `octo-claude-pm` plugin (`teams.json`); none of them is stored here. It needs `git`, `gh` (logged in) and, for `--file-bugs`, `az` (logged in).

- **Run mode:** a scheduled launchd job on a developer Mac (template [`scripts/launchd/skill-name-inventory-refresh.plist.example`](scripts/launchd/skill-name-inventory-refresh.plist.example)). Moving it to a scheduled Azure DevOps pipeline is the later option, owned by the build agent of `octo-claude-pm` (Argos).
- **Owner:** Heimdall (Platform Ops / DevEx); the job runs on the workstation of the developer who installed it.
- **Schedule:** Mondays 06:30 local time. A missed run (machine off) becomes the 14-day warning of the drift check.
- **By hand:** `launchctl kickstart gui/$(id -u)/skill-name-inventory-refresh`, or the command above.

#### Merging a refresh that found drift

A refresh with findings pushes an inventory against which some skills fail. In the next `docs/batch-*` PR the **Drift check** step is red (the scan, unit tests and frontmatter steps still run and must be green); the docs batch itself does not run the drift check, so it does not leave the refresh branch out. Do not merge the batch PR over a red drift check (a convention: the check is not a required status check on `main`). Instead, before the batch PR is made ready:

1. Take the Bugs the run filed (`Skill drift: <skill> …`, one per skill).
2. Either fix the skills on their own story branches (they ride in the same batch), or accept the findings for now: on a story branch of the Bug (`<user>/AB#<Bug ID>_<desc>`, never the refresh branch) add one entry per finding to `inventory/allowlist.json` with `kind`, `name`, `files` (the repository path of the skill file, e.g. `skills/octo/SKILL.md`), `reason` `baseline <date>: <Bug title>` and `workItem` = the Bug ID. Commit with `AB#<Bug ID> Chore: …` and push the story branch; it rides in the same batch.
3. Check that `python3 scripts/check_skill_drift.py --summary` exits 0 on the batch branch with these changes, then re-run the docs batch so its PR picks them up; the drift check step turns green.
4. The owner removes the baseline entries when fixing the skill and closes the Bug.

Release history lives in [CHANGELOG.md](CHANGELOG.md).
