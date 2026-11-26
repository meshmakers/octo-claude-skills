#!/usr/bin/env python3
"""Check every skill against the committed name inventory (drift check, AB#6366).

The skills name octo-tools cmdlets and their parameters, octo-cli commands and
their arguments, pipeline nodes (``Name@<version>``) and documentation paths in
other repositories. Those names live in private repositories, which public CI
cannot read. ``inventory/names.json`` (generated from the private repositories by
``scripts/generate_name_inventory.py``, AB#9741) lists the names that exist; this
script reports every name a skill uses that the inventory does not list.

Run:  python3 scripts/check_skill_drift.py            (human-readable, grouped by owner)
      python3 scripts/check_skill_drift.py --json     (machine-readable)
      python3 scripts/check_skill_drift.py --summary  (counts per skill and owner)

Exit codes: 0 = no finding, 1 = at least one finding (or a skill without an
owner), 2 = the inventory, allow-list or OWNERS file cannot be read.
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import sys
from dataclasses import asdict, dataclass

REPO = pathlib.Path(__file__).resolve().parent.parent

# PowerShell approved verbs (Get-Verb) plus Manage; Inventory adds every other verb octo-tools uses.
VERBS = (
    "Add Approve Assert Backup Block Build Checkpoint Clear Close Compare Complete Compress Confirm Connect "
    "Convert ConvertFrom ConvertTo Copy Debug Deny Deploy Disable Disconnect Dismount Edit Enable Enter Exit "
    "Expand Export Find Format Get Grant Group Hide Import Initialize Install Invoke Join Limit Lock Measure "
    "Merge Mount Move New Open Optimize Out Ping Pop Protect Publish Push Read Receive Redo Register Remove "
    "Rename Repair Request Reset Resize Resolve Restart Restore Resume Revoke Save Search Select Send Set Show "
    "Skip Split Start Step Stop Submit Suspend Switch Sync Test Trace Unblock Undo Uninstall Unlock Unprotect "
    "Unpublish Unregister Update Use Wait Watch Write Manage"
).split()

# Verbs outside the approved list that octo-tools uses (or used). They stay here even when the inventory no
# longer has a cmdlet with that verb: otherwise renaming the last Clone-* cmdlet would take the verb out of
# the pattern and a stale Clone-Repo in a skill would pass silently (AB#9840). A refresh that brings a new
# verb fails tests/test_check_skill_drift.py until the verb is added here.
OCTO_TOOLS_VERBS = "Check Clone Compile Create Delete Normalize".split()

# Parameters every advanced PowerShell function accepts.
COMMON_PARAMETERS = {
    p.lower()
    for p in (
        "Verbose Debug ErrorAction WarningAction InformationAction ProgressAction ErrorVariable "
        "WarningVariable InformationVariable OutVariable OutBuffer PipelineVariable WhatIf Confirm"
    ).split()
}

QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")

# PowerShell's own cmdlets: not in the inventory (it lists octo-tools only) and never drift.
BUILTIN_CMDLETS = {
    c.lower()
    for c in (
        "Add-Content Add-Member Clear-Host Compare-Object ConvertFrom-Json ConvertTo-Json ConvertFrom-StringData "
        "ConvertTo-SecureString Copy-Item Export-Csv Export-ModuleMember ForEach-Object Format-List Format-Table "
        "Get-ChildItem Get-Command Get-Content Get-Date Get-Help Get-Item Get-Location Get-Member Get-Module "
        "Get-Process Get-Variable Get-Verb Group-Object Import-Csv Import-Module Invoke-Command Invoke-Expression "
        "Invoke-RestMethod Invoke-WebRequest Join-Path Measure-Object Move-Item New-Item New-Object Out-File "
        "Out-Host Out-Null Out-String Pop-Location Push-Location Read-Host Remove-Item Remove-Module Rename-Item "
        "Resolve-Path Select-Object Select-String Set-Content Set-Item Set-Location Set-StrictMode Set-Variable "
        "Sort-Object Split-Path Start-Job Start-Process Start-Sleep Stop-Job Stop-Process Test-Connection "
        "Test-Path Wait-Job Receive-Job Where-Object Write-Debug Write-Error Write-Host Write-Output "
        "Write-Progress Write-Verbose Write-Warning"
    ).split()
}

PARAM_RE = re.compile(r"(?<![\w-])-([A-Za-z][A-Za-z0-9]*)(?![\w-])")
OCTO_CLI_RE = re.compile(r"(?<![\w-])octo-cli(?:\.exe)?(?![\w-])")
CLI_ARG_RE = re.compile(r"(?<![\w-])(--?|/)([A-Za-z?][A-Za-z0-9-]*)(?![\w])")
NODE_RE = re.compile(r"(?<![\w.@/-])([A-Z][A-Za-z0-9]+)@(\d+)(?![\w.@]|\.\d)")
REPO_DOC_RE = re.compile(
    r"(?<![\w./-])([A-Za-z][A-Za-z0-9_-]*)/(AGENTS\.md|CLAUDE\.md|docs/[A-Za-z0-9_./-]*[A-Za-z0-9_-])"
)
MACHINE_PATH_RE = re.compile(r"[Cc]:[\\/]+dev\b")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN_RE = re.compile(r"`+[^`]*`+")
CLI_STOP = re.compile(r"[|;&]|\s#\s")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    kind: str
    name: str
    owner: str
    detail: str = ""


class ConfigError(Exception):
    """An input file is missing or malformed (exit code 2)."""


def load_json(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"{path}: not found") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: not valid JSON ({exc})") from exc


def load_owners(path: pathlib.Path) -> dict[str, str]:
    """Parse OWNERS: one ``<skill> <owner>`` pair per line, ``#`` starts a comment."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"{path}: not found") from exc
    owners: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ConfigError(f"{path}:{number}: expected '<skill> <owner>', got {raw.strip()!r}")
        skill, owner = parts
        if skill in owners:
            raise ConfigError(f"{path}:{number}: skill {skill!r} is listed twice")
        owners[skill] = owner
    return owners


class Inventory:
    def __init__(self, data: dict):
        if data.get("schemaVersion") != 1:
            raise ConfigError(f"inventory: unsupported schemaVersion {data.get('schemaVersion')!r} (expected 1)")
        self.generated = data.get("generated", "")
        self.cmdlets = {name.lower(): (name, [p.lower() for p in params])
                        for name, params in data.get("cmdlets", {}).items()}
        # Approved verbs, the verbs octo-tools uses or used (OCTO_TOOLS_VERBS, so a rename away from a verb is
        # still seen) and every verb of the current inventory.
        self.verbs = set(VERBS) | set(OCTO_TOOLS_VERBS) | {name.split("-", 1)[0] for name, _ in self.cmdlets.values()}
        verbs = self.verbs
        self.cmdlet_re = re.compile(
            r"(?<![\w$.-])(" + "|".join(sorted(verbs, key=len, reverse=True)) + r")-([A-Z][A-Za-z0-9]+)(?![\w-])"
        )
        cli = data.get("octoCli", {})
        self.cli_commands = {name.lower(): (name, {a.lower() for a in args})
                             for name, args in cli.get("commands", {}).items()}
        self.cli_global = {a.lower() for a in cli.get("globalArguments", [])}
        self.nodes = {name: set(versions) for name, versions in data.get("nodes", {}).items()}
        self.repos = data.get("repos", {})
        self.repo_patterns = data.get("repoPatterns", [])
        self.exclude_repos = data.get("excludeRepos", [])

    def knows_repo(self, repo: str) -> bool:
        return repo in self.repos

    def repo_in_scope(self, repo: str) -> bool:
        if self.knows_repo(repo):
            return True
        if any(fnmatch.fnmatchcase(repo, p) for p in self.exclude_repos):
            return False
        return any(fnmatch.fnmatchcase(repo, p) for p in self.repo_patterns)


class AllowList:
    """Accepted mentions: ``{"entries": [{"kind", "name", "files"?, "reason", "workItem"}]}``.

    Two uses: deliberate mentions (a retired name in a "replaces the removed ..." note)
    and the baseline of known findings, each tracked by a work item until the skill is
    fixed. An entry without kind, name, reason and a positive integer ``workItem`` is refused.
    """

    def __init__(self, data: dict):
        self.entries = []
        for number, entry in enumerate(data.get("entries", [])):
            if not entry.get("kind") or not entry.get("name") or not entry.get("reason"):
                raise ConfigError(f"allow-list entry {number}: needs kind, name and reason")
            work_item = entry.get("workItem")
            if not isinstance(work_item, int) or isinstance(work_item, bool) or work_item <= 0:
                raise ConfigError(f"allow-list entry {number} ({entry['name']}): needs the workItem (integer ID) "
                                  "that tracks it")
            # Any glob character counts: "Invoke-*" without files would silence every Invoke-* finding.
            if not entry.get("files") and (entry["kind"] == "*" or any(c in entry["name"] for c in "*?[")):
                raise ConfigError(f"allow-list entry {number} ({entry['name']}): a wildcard kind or name needs "
                                  "'files' to limit it")
            self.entries.append(entry)

    def allows(self, kind: str, name: str, file: str) -> bool:
        for entry in self.entries:
            if entry["kind"] not in (kind, "*"):
                continue
            if not fnmatch.fnmatchcase(name.lower(), entry["name"].lower()):
                continue
            files = entry.get("files")
            if files and not any(fnmatch.fnmatchcase(file, f) for f in files):
                continue
            return True
        return False


def code_segments(lines: list[str], is_json: bool):
    """Yield (line number, segment text, is_code) for every line.

    Markdown: fenced blocks are code as a whole, inline code spans are code, the
    rest is prose. JSON (evals): every line counts as code. Inside a fenced block a
    line ending in a shell (`` \\ ``) or PowerShell (`` ` ``) continuation is joined
    with the following lines and reported under the number of its first line.
    """
    fence = None
    pending: tuple[int, str] | None = None
    for number, line in enumerate(lines, 1):
        if is_json:
            yield number, line, True
            continue
        match = FENCE_RE.match(line)
        if match:
            if pending:
                yield pending[0], pending[1], True
                pending = None
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is not None:
            start, text = pending if pending else (number, "")
            stripped = line.rstrip()
            if stripped.endswith("\\") or stripped.endswith("`"):
                pending = (start, text + stripped[:-1] + " ")
                continue
            pending = None
            yield start, text + line, True
            continue
        last = 0
        for span in CODE_SPAN_RE.finditer(line):
            if span.start() > last:
                yield number, line[last:span.start()], False
            yield number, span.group(0).strip("`"), True
            last = span.end()
        if last < len(line):
            yield number, line[last:], False
    if pending:
        yield pending[0], pending[1], True


def check_cmdlets(segment: str, inv: Inventory) -> list[tuple[str, str, str]]:
    """Return (kind, name, detail) for unknown cmdlets and unknown parameters of known ones."""
    found = []
    matches = list(inv.cmdlet_re.finditer(segment))
    for index, match in enumerate(matches):
        name = match.group(0)
        known = inv.cmdlets.get(name.lower())
        if known is None and name.lower() in BUILTIN_CMDLETS:
            continue
        if known is None:
            found.append(("cmdlet", name, "not in inventory"))
            continue
        canonical, params = known
        end = matches[index + 1].start() if index + 1 < len(matches) else len(segment)
        tail = segment[match.end():end]
        stop = re.search(r"[|;]|\)\s*$|(?<![\w-])octo-cli(?![\w-])", tail)
        if stop:
            tail = tail[:stop.start()]
        # Values in quotes (e.g. -CliArguments '-c','LibraryStatus','-io') are no parameters of the cmdlet.
        tail = QUOTED_RE.sub("''", tail)
        for param in PARAM_RE.finditer(tail):
            given = param.group(1).lower()
            if given in COMMON_PARAMETERS:
                continue
            # PowerShell accepts the full name or a prefix that matches exactly one parameter.
            if given in params or sum(1 for p in params if p.startswith(given)) == 1:
                continue
            found.append(("cmdlet-parameter", f"{canonical} -{param.group(1)}", "parameter not in inventory"))
    return found


def check_octo_cli(segment: str, inv: Inventory) -> list[tuple[str, str, str]]:
    found = []
    for match in OCTO_CLI_RE.finditer(segment):
        rest = segment[match.end():]
        stop = CLI_STOP.search(rest)
        if stop:
            rest = rest[:stop.start()]
        nxt = OCTO_CLI_RE.search(rest)
        if nxt:
            rest = rest[:nxt.start()]
        tokens = rest.split()
        command = None
        for i, token in enumerate(tokens):
            if token.lower() in ("-c", "--command", "/command") and i + 1 < len(tokens):
                command = tokens[i + 1].strip("'\"`")
                break
        if command is None or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", command):
            continue  # no command given, or a placeholder such as <Command>
        known = inv.cli_commands.get(command.lower())
        if known is None:
            found.append(("octo-cli-command", command, "not in inventory"))
            continue
        canonical, args = known
        for arg in CLI_ARG_RE.finditer(rest):
            prefix, term = arg.group(1), arg.group(2)
            if term.lower() == command.lower():
                continue
            # mm-common CommandLineParser: "-x" names the short term, "--x" and "/x" the long term.
            form = f"-{term}".lower() if prefix == "-" else f"--{term}".lower()
            if form in args or form in inv.cli_global:
                continue
            if prefix == "/":
                continue  # most likely a path, not an argument
            found.append(("octo-cli-argument", f"{canonical} {prefix}{term}", "argument not in inventory"))
    return found


def check_nodes(segment: str, inv: Inventory) -> list[tuple[str, str, str]]:
    found = []
    for match in NODE_RE.finditer(segment):
        name, version = match.group(1), int(match.group(2))
        versions = inv.nodes.get(name)
        if versions is None:
            found.append(("node", f"{name}@{version}", "node not in inventory"))
        elif version not in versions:
            known = ", ".join(f"@{v}" for v in sorted(versions))
            found.append(("node", f"{name}@{version}", f"version not in inventory (known: {known})"))
    return found


def check_repo_docs(segment: str, inv: Inventory) -> list[tuple[str, str, str]]:
    found = []
    for match in REPO_DOC_RE.finditer(segment):
        repo, path = match.group(1), match.group(2)
        if not inv.repo_in_scope(repo):
            continue  # a local folder or a path inside this repository, not another repository
        name = f"{repo}/{path}"
        if not inv.knows_repo(repo):
            found.append(("repo-doc", name, "repository not in inventory"))
            continue
        info = inv.repos[repo]
        if path == "CLAUDE.md":
            if info.get("agentsMd"):
                found.append(("reference-to-shim", name, f"{repo} has AGENTS.md; point to AGENTS.md instead"))
            elif not info.get("claudeMd", True):
                found.append(("repo-doc", name, "file not in inventory"))
        elif path == "AGENTS.md":
            if not info.get("agentsMd"):
                found.append(("repo-doc", name, "repository has no AGENTS.md"))
        else:
            if doc_hash(path.rstrip("/")) not in set(info.get("docHashes", [])):
                found.append(("repo-doc", name, "file not in inventory"))
    return found


def doc_hash(path: str) -> str:
    """Truncated SHA-256 of a path below docs/; must match generate_name_inventory.doc_hash."""
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]


def check_file(path: pathlib.Path, rel: str, owner: str, inv: Inventory, allow: AllowList) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    seen: set[tuple[int, str, str]] = set()
    is_json = path.suffix == ".json"

    def add(number: int, kind: str, name: str, detail: str) -> None:
        key = (number, kind, name)
        if key in seen or allow.allows(kind, name, rel):
            return
        seen.add(key)
        findings.append(Finding(rel, number, kind, name, owner, detail))

    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        for match in MACHINE_PATH_RE.finditer(line):
            add(number, "machine-path", match.group(0), "machine-local path; use a placeholder")
    for number, segment, is_code in code_segments(lines, is_json):
        if not is_code:
            continue
        for kind, name, detail in check_cmdlets(segment, inv):
            add(number, kind, name, detail)
        for kind, name, detail in check_octo_cli(segment, inv):
            add(number, kind, name, detail)
        for kind, name, detail in check_nodes(segment, inv):
            add(number, kind, name, detail)
        for kind, name, detail in check_repo_docs(segment, inv):
            add(number, kind, name, detail)
    return findings


def skill_files(skills_dir: pathlib.Path) -> list[pathlib.Path]:
    files = list(skills_dir.rglob("*.md")) + list(skills_dir.glob("*/evals/*.json"))
    return sorted(f for f in files if ".venv" not in f.parts and "node_modules" not in f.parts)


def run(root: pathlib.Path, inventory_path: pathlib.Path, allow_path: pathlib.Path, owners_path: pathlib.Path,
        today: _dt.date, max_age_days: int, ignore_baseline: bool = False
        ) -> tuple[list[Finding], list[str], list[str], dict]:
    """Return (findings, errors, warnings, per-skill counts)."""
    inv = Inventory(load_json(inventory_path))
    allow = AllowList(load_json(allow_path)) if allow_path.exists() else AllowList({})
    if ignore_baseline:
        allow.entries = [e for e in allow.entries if not e["reason"].lower().startswith("baseline")]
    owners = load_owners(owners_path)
    skills_dir = root / "skills"
    skills = sorted(p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists())

    errors = [f"OWNERS: skill {s!r} has no owner" for s in skills if s not in owners]
    errors += [f"OWNERS: {s!r} is not a skill in skills/" for s in sorted(owners) if s not in skills]

    warnings = []
    try:
        generated = _dt.date.fromisoformat(inv.generated)
        age = (today - generated).days
        if age > max_age_days:
            warnings.append(
                f"inventory generated {inv.generated} is {age} days old (more than {max_age_days}); "
                "the weekly refresh (scripts/refresh_name_inventory.py) has probably not run"
            )
    except ValueError:
        warnings.append(f"inventory has no valid 'generated' date ({inv.generated!r})")

    findings: list[Finding] = []
    for path in skill_files(skills_dir):
        rel = path.relative_to(root).as_posix()
        skill = path.relative_to(skills_dir).parts[0]
        findings += check_file(path, rel, owners.get(skill, "(no owner)"), inv, allow)

    counts: dict[str, dict] = {s: {"owner": owners.get(s, "(no owner)"), "findings": 0} for s in skills}
    for f in findings:
        skill = pathlib.PurePosixPath(f.file).parts[1]
        counts.setdefault(skill, {"owner": f.owner, "findings": 0})["findings"] += 1
    return findings, errors, warnings, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=pathlib.Path, default=REPO, help="repository root (default: this repository)")
    parser.add_argument("--inventory", type=pathlib.Path, help="default: <root>/inventory/names.json")
    parser.add_argument("--allow-list", type=pathlib.Path, help="default: <root>/inventory/allowlist.json")
    parser.add_argument("--owners", type=pathlib.Path, help="default: <root>/OWNERS")
    parser.add_argument("--max-age-days", type=int, default=14, help="warn when the inventory is older (default 14)")
    parser.add_argument("--today", type=_dt.date.fromisoformat, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    parser.add_argument("--summary", action="store_true", help="print counts per skill and owner")
    parser.add_argument("--ignore-baseline", action="store_true",
                        help="report baselined findings too (allow-list entries whose reason starts with 'baseline')")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    try:
        findings, errors, warnings, counts = run(
            root,
            args.inventory or root / "inventory" / "names.json",
            args.allow_list or root / "inventory" / "allowlist.json",
            args.owners or root / "OWNERS",
            args.today or _dt.datetime.now(_dt.timezone.utc).date(),
            args.max_age_days,
            args.ignore_baseline,
        )
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    gha = bool(os.environ.get("GITHUB_ACTIONS"))
    for warning in warnings:
        print(f"::warning::{warning}" if gha else f"warning: {warning}", file=sys.stderr)

    if args.json:
        print(json.dumps({"findings": [asdict(f) for f in findings], "errors": errors, "warnings": warnings,
                          "skills": counts}, indent=2, sort_keys=True))
    else:
        for error in errors:
            print(f"error: {error}")
        by_owner: dict[str, list[Finding]] = {}
        for f in findings:
            by_owner.setdefault(f.owner, []).append(f)
        for owner in sorted(by_owner):
            print(f"== {owner} ({len(by_owner[owner])} findings)")
            for f in by_owner[owner]:
                print(f"{f.file}:{f.line}: {f.kind}: {f.name} — {f.detail} (owner: {f.owner})")
                if gha:
                    print(f"::error file={f.file},line={f.line}::{f.kind}: {f.name} — {f.detail} (owner: {f.owner})")
        if args.summary:
            print("\nskill                owner      findings")
            for skill in sorted(counts):
                print(f"{skill:20} {counts[skill]['owner']:10} {counts[skill]['findings']}")
        total = len(findings)
        print(f"\n{total} finding(s), {len(errors)} error(s) in {len(counts)} skills", file=sys.stderr)

    return 1 if findings or errors else 0


if __name__ == "__main__":
    sys.exit(main())
