---
name: octo-ck-miro
description: Visualizes OctoMesh Construction Kits as UML class diagrams on a Miro board. Reads CK YAML definitions from a specified git branch in the local octo-construction-kit checkout (non-destructive via git show) and creates one detailed UML diagram per CK — types with attributes and datatypes, records, enums, inheritance arrows, associations with multiplicity, and cross-CK references. Lets the user pick a branch (default main) and choose between a new Miro board or adding to an existing board URL. Trigger on - visualize CK, visualize construction kit, CK diagram, CK to Miro, Miro board for CK, UML diagram for construction kit, CK model visualization, octo construction kit visualization, draw CK, show CK on Miro, CK class diagram.
allowed-tools:
  - "Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/octo-ck-miro/scripts/run_python.sh:*)"
  - "Bash(git -C *:ls-tree *)"
  - "Bash(git -C *:show *)"
  - "Bash(git -C *:rev-parse *)"
  - "Bash(git -C *:branch *)"
  - "Bash(ls *)"
  - "Read"
---

# OctoMesh Construction Kits → Miro UML

## Overview

Single entry point. Given a branch of `octo-construction-kit`, generates one detailed UML class diagram per Construction Kit on a Miro board, plus a legend doc and a CK dependency tree doc.

Each diagram contains:
- **Types** (blue) with attributes resolved to their datatype: `+name: String`, `-optional: Int`, `+Address: «Address»`, `+State: <Salutation>`
- **Records** (green) with attribute structure
- **Enums** (yellow) with values (truncated at 8)
- **Inheritance** arrows (▷── filled triangle) from `derivedFromCkTypeId`
- **Associations** with multiplicity (1, 0..1, *, 0..*) from `associationRoles`
- **Cross-CK references** (gray) for `${OtherCK}/Type` parents and association targets

## Inputs the User Provides

Ask the user in this order if not already supplied:

1. **Branch** to read from. Default: `main`. Validate with `git -C <repo> rev-parse <branch>` before parsing.
2. **Miro target**: new board (asks for a board name) OR existing board URL.
3. **Optional**: `--ck <name>` to limit to a single CK (e.g. `Basic.Energy`) instead of all 12.

Do not assume the user wants all CKs unless they say so. If the request is broad ("visualize the CKs"), default to all.

## Workflow

### Step 1 — Locate the repo

Find the local `octo-construction-kit` checkout. Try in order:
1. `/Users/<user>/RiderProjects/meshmakers/main/octo-construction-kit` (the standard layout)
2. `~/source/repos/meshmakers/octo-construction-kit`
3. Ask the user for the absolute path

Verify it is a git repo and the requested branch exists:

```bash
git -C <repo> rev-parse --verify <branch>
```

If the branch doesn't exist locally, suggest `git -C <repo> fetch origin <branch>:<branch>` — do not run it without confirmation.

### Step 2 — Generate the DSL

Run the parser. It reads YAMLs via `git show <branch>:<path>` so the user's working tree is untouched:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/octo-ck-miro/scripts/run_python.sh \
  ${CLAUDE_PLUGIN_ROOT}/skills/octo-ck-miro/scripts/ck_to_miro.py \
  --repo <repo-path> --branch <branch> [--ck <single-ck>]
```

Output (stdout, JSON):
```json
{
  "branch": "main",
  "repo": "...",
  "cks": [
    {"name": "Basic", "title": "Basic (v2.0.2)",
     "dsl": "graphdir TB\n...", "x": 0, "y": -2000,
     "node_count": 26, "edge_count": 13,
     "type_count": 10, "record_count": 10, "enum_count": 5},
    ...
  ],
  "legend_md": "...",
  "dependency_tree_md": "...",
  "stats_md": "..."
}
```

Parse this JSON into memory. It is the single source of truth for all the Miro calls.

### Step 3 — Resolve the Miro board

If the user picked **new board**:
1. Suggest a name like `Octo CKs — <branch> (<date>)` and confirm.
2. Call `mcp__claude_ai_Miro__board_create` with the chosen name.
3. Capture the `miro_url`.

If the user picked **existing board**:
1. They must provide the board URL (asks if not given).
2. Validate format `https://miro.com/app/board/<id>=/`.
3. WARN: diagrams will be added alongside any existing items — the skill does not delete old diagrams (no MCP tool for it). Suggest the user manually clean up or pick a clear area on the board first.

### Step 4 — Create the diagrams

For each `ck` in the JSON output, call:

```
mcp__claude_ai_Miro__diagram_create(
  miro_url=<board_url>,
  diagram_type="uml_class",
  title=ck.title,
  x=ck.x, y=ck.y,
  diagram_dsl=ck.dsl,
  invocation_source="skill"
)
```

Issue calls **sequentially** (not in parallel) — Miro's API rate-limits hard and returns 403 under load. If a 403 hits, wait ~20 s and retry that one CK.

The layout is single-column (x=0, y stepped 3500 px) — this avoids the auto-layout overlap problems that come with multi-column placement (Miro's auto-layout sizes diagrams unpredictably; some are 8000+ px wide).

### Step 5 — Add legend + dependency tree

Two doc cards at the top of the board (above y=-7000 row, do not overlap the first diagram):

```
mcp__claude_ai_Miro__doc_create(
  miro_url=<board_url>,
  x=-10500, y=-12000,
  content=<legend_md>,
  invocation_source="skill"
)
mcp__claude_ai_Miro__doc_create(
  miro_url=<board_url>,
  x=-1500, y=-12000,
  content=<dependency_tree_md + "\n\n" + stats_md>,
  invocation_source="skill"
)
```

### Step 6 — Report back

Print the board URL and the count of diagrams created. Mention the layout is single-column and the user can drag items in Miro to rearrange.

## Single-CK Mode

When `--ck <name>` is passed: only one diagram, no dependency-tree doc needed, only the legend doc. Place the diagram at (0, 0).

## Common Pitfalls

- **Quotes in DSL**: never put double quotes inside attribute strings — the parser already replaces them with single quotes.
- **Empty attribute string**: a class with no attributes needs `" "` (a single space) not `""` — the empty string breaks the Miro DSL parser.
- **External CK refs**: parents and association targets in other CKs render as gray stub boxes inside each diagram. Cross-board CK→CK arrows would require connecting board-level items and we do not draw them — the gray boxes plus the dependency-tree doc convey the dependencies.
- **Rate limits**: Miro 403s under burst. Always sequential calls, ~20 s cool-off on failure.
- **Branch read**: always use `git show <branch>:<path>` — never check out the branch, the user's working tree must not change.

## Updating vs Creating

This skill cannot in-place "update" diagrams on an existing board — the Miro MCP exposes no delete for diagrams. "Update existing board" means: place fresh diagrams on the same board (user-supplied URL). Old diagrams remain until the user removes them in Miro.

If the user wants a clean re-render they should use the **new board** option each time.

## YAML Schema Variants

The parser handles both:
- **Standard schema**: top-level `types:` / `records:` / `enums:` arrays in each file. Refs use `${CkName}/elementName`.
- **Compact schema** (e.g. `Octo.Energy.Demo`): the filename IS the id, `derivedFrom: CK/Name`, `attributeName` instead of `name`, enum values use `value` instead of `key`.

No user action needed — detection is automatic.
