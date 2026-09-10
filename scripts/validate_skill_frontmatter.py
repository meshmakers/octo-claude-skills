#!/usr/bin/env python3
"""Validate the YAML frontmatter of every skills/*/SKILL.md.

`claude plugin validate --strict` does NOT parse skill frontmatter: a SKILL.md
whose `description` is an unquoted plain scalar containing ": " fails YAML
parsing, and Claude Code then registers the skill with no description at all —
which removes it from the model's skill listing entirely.

Run:  bash skills/octo/scripts/run_python.sh scripts/validate_skill_frontmatter.py
Exits non-zero on the first problem found.
"""
import pathlib
import sys

import yaml

MAX_DESCRIPTION = 1200  # Claude Code truncates the listing entry at 1536 chars
MAX_BODY_LINES = 500    # SKILL.md body is loaded every turn

repo = pathlib.Path(__file__).resolve().parent.parent
errors = []

for path in sorted((repo / "skills").glob("*/SKILL.md")):
    skill = path.parent.name
    lines = path.read_text(encoding="utf-8").split("\n")

    if not lines or lines[0].strip() != "---":
        errors.append(f"{skill}: SKILL.md does not start with a '---' frontmatter fence")
        continue
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        errors.append(f"{skill}: frontmatter is not closed by '---'")
        continue

    try:
        meta = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as exc:
        detail = str(exc).splitlines()[0]
        errors.append(
            f"{skill}: frontmatter is not valid YAML ({type(exc).__name__}: {detail}) "
            f"— quote the description if it contains ': '"
        )
        continue

    if meta.get("name") != skill:
        errors.append(f"{skill}: frontmatter name is {meta.get('name')!r}, expected {skill!r}")

    description = meta.get("description")
    if not description:
        errors.append(f"{skill}: frontmatter has no description")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"{skill}: description is {len(description)} chars, max {MAX_DESCRIPTION}")

    body_lines = len(lines) - (end + 1)
    if body_lines > MAX_BODY_LINES:
        errors.append(f"{skill}: body is {body_lines} lines, max {MAX_BODY_LINES}")

    if not errors or not errors[-1].startswith(f"{skill}:"):
        print(f"OK    {skill:20} description={len(description)} chars, body={body_lines} lines")

for error in errors:
    print(f"FAIL  {error}", file=sys.stderr)

sys.exit(1 if errors else 0)
