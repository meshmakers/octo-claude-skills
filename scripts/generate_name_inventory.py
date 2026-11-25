#!/usr/bin/env python3
"""Generate inventory/names.json from local checkouts of the OctoMesh repositories (AB#9741).

The drift check (scripts/check_skill_drift.py) compares the names the skills use
with this inventory. The names come from repositories public CI cannot read, so
this script runs where the checkouts are (a developer machine, the weekly refresh
of scripts/refresh_name_inventory.py) and writes **names only**:

- octo-tools ``modules/*.psm1``: every ``Verb-Noun`` function and its parameter names
- octo-cli ``src/ManagementTool/Commands/**``: every command name and its argument terms
- every repository matching ``nodeRepoPatterns``: the ``[NodeName("<name>", <version>)]``
  registrations outside test folders
- every repository matching ``repoPatterns``: whether it has AGENTS.md / CLAUDE.md and the
  Markdown files (and their folders) below ``docs/`` as truncated SHA-256 hashes of the path,
  so internal document names do not appear in this public repository

No file contents, hosts, URLs or commit data are written. The output is sorted, so
the same input trees and the same ``--date`` give byte-identical output.

Run:  python3 scripts/generate_name_inventory.py --monorepo <path> [--date YYYY-MM-DD] [--out inventory/names.json]
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DOC_HASH_LENGTH = 16  # hex digits of SHA-256
SKIP_DIRS = {".git", "node_modules", "bin", "obj", ".venv", "dist", "build", ".angular", ".docusaurus"}

FUNCTION_RE = re.compile(
    r"^[ \t]*function[ \t]+(?:(?:global|script|local|private):)?([A-Za-z]+-[A-Za-z0-9]+)\b", re.M | re.I
)
CLASS_RE = re.compile(r"\bclass\s+(\w+)\s*(?:<[^>{]*>)?\s*(?:\([^)]*\))?\s*:\s*([\w.]+)")
COMMAND_NAME_RE = re.compile(r":\s*base\(\s*logger\s*,\s*(?:Constants\.\w+\s*,\s*)?\"(\w+)\"", re.S)
ARGUMENT_RE = re.compile(r"AddArgument\(\s*\"([^\"]*)\"\s*,\s*\"([^\"]*)\"")
CONTEXT_TERM_RE = re.compile(r"ContextArgumentTerm\s*=\s*\"([A-Za-z-]+)\"")
NODE_RE = re.compile(r"\[\s*NodeName\(\s*\"(\w+)\"\s*,\s*(\d+)\s*\)\s*\]")

# Arguments the command-line parser of octo-cli (mm-common CommandLineParser) defines for every command.
PARSER_GLOBAL_ARGUMENTS = ["-c", "--command", "-?", "--help"]


# ---------------------------------------------------------------- PowerShell


def _skip_string(text: str, i: int) -> int:
    """Return the index after the string literal that starts at text[i] (' or ")."""
    quote = text[i]
    i += 1
    while i < len(text):
        ch = text[i]
        if ch == "`" and quote == '"':
            i += 2
            continue
        if ch == quote:
            if i + 1 < len(text) and text[i + 1] == quote:  # doubled quote = escaped
                i += 2
                continue
            return i + 1
        i += 1
    return i


def _skip_comment(text: str, i: int) -> int:
    if text.startswith("<#", i):
        end = text.find("#>", i + 2)
        return len(text) if end < 0 else end + 2
    end = text.find("\n", i)
    return len(text) if end < 0 else end


def _balanced_end(text: str, i: int) -> int:
    """text[i] is an opening bracket; return the index after its matching close."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = [pairs[text[i]]]
    i += 1
    while i < len(text) and stack:
        ch = text[i]
        if ch in "'\"":
            i = _skip_string(text, i)
            continue
        if ch == "#" or text.startswith("<#", i):
            i = _skip_comment(text, i)
            continue
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch == stack[-1]:
            stack.pop()
        i += 1
    return i


def _param_names(block: str) -> list[str]:
    """Parameter names of a param block body (text between the parentheses)."""
    names = []
    depth = 0
    i = 0
    current: str | None = None  # last variable seen at depth 0 in the current item
    after_equals = False
    while i < len(block):
        ch = block[i]
        if ch in "'\"":
            i = _skip_string(block, i)
            continue
        if ch == "#" or block.startswith("<#", i):
            i = _skip_comment(block, i)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and ch == ",":
            if current:
                names.append(current)
            current, after_equals = None, False
        elif depth == 0 and ch == "=":
            after_equals = True
        elif depth == 0 and ch == "$" and not after_equals:
            match = re.match(r"\$([A-Za-z_]\w*)", block[i:])
            if match:
                current = match.group(1)
                i += len(match.group(0))
                continue
        i += 1
    if current:
        names.append(current)
    return names


def function_parameters(text: str, start: int) -> list[str]:
    """Parameters of the function whose name ends at text[start]."""
    i = start
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    params: list[str] = []
    if i < len(text) and text[i] == "(":
        end = _balanced_end(text, i)
        params += _param_names(text[i + 1:end - 1])
        i = end
    brace = text.find("{", i)
    if brace < 0:
        return params
    i = brace + 1
    while i < len(text):
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
        elif ch == "#" or text.startswith("<#", i):
            i = _skip_comment(text, i)
        elif ch == "[":
            i = _balanced_end(text, i)
        else:
            match = re.match(r"param\s*\(", text[i:], re.I)
            if match:
                open_paren = i + match.end() - 1
                end = _balanced_end(text, open_paren)
                params += _param_names(text[open_paren + 1:end - 1])
            break
    return params


def scan_cmdlets(octo_tools: pathlib.Path) -> dict[str, list[str]]:
    cmdlets: dict[str, set[str]] = {}
    modules = octo_tools / "modules"
    if not modules.is_dir():
        return {}
    for path in sorted(modules.glob("*.psm1")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for match in FUNCTION_RE.finditer(text):
            name = match.group(1)
            params = function_parameters(text, match.end())
            cmdlets.setdefault(name, set()).update(params)
    return {name: sorted(params, key=str.lower) for name, params in sorted(cmdlets.items(), key=lambda kv: kv[0].lower())}


# ------------------------------------------------------------------- octo-cli


def scan_octo_cli(octo_cli: pathlib.Path) -> dict:
    root = octo_cli / "src" / "ManagementTool"
    commands_dir = root / "Commands"
    if not commands_dir.is_dir():
        return {"commands": {}, "globalArguments": []}
    classes: dict[str, dict] = {}
    for path in sorted(commands_dir.rglob("*.cs")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        matches = list(CLASS_RE.finditer(text))
        for index, class_match in enumerate(matches):
            # A class owns the text up to the next class declaration of the file.
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[class_match.start():end]
            name, base = class_match.group(1), class_match.group(2).split(".")[-1]
            command = COMMAND_NAME_RE.search(body)
            args = {term for short, long in ARGUMENT_RE.findall(body)
                    for term in (f"-{short}", f"--{long}") if term.strip("-")}
            classes[name] = {"base": base, "command": command.group(1) if command else None, "args": args}

    def all_args(name: str, seen: set[str]) -> set[str]:
        info = classes.get(name)
        if info is None or name in seen:
            return set()
        seen.add(name)
        return info["args"] | all_args(info["base"], seen)

    commands: dict[str, set[str]] = {}
    for name, info in classes.items():
        if info["command"]:
            commands.setdefault(info["command"], set()).update(all_args(name, set()))

    global_args = list(PARSER_GLOBAL_ARGUMENTS)
    constants = root / "Constants.cs"
    if constants.exists():
        term = CONTEXT_TERM_RE.search(constants.read_text(encoding="utf-8-sig", errors="replace"))
        if term:
            global_args.append(f"--{term.group(1)}")
    return {
        "commands": {c: sorted(a, key=str.lower) for c, a in sorted(commands.items(), key=lambda kv: kv[0].lower())},
        "globalArguments": sorted(set(global_args), key=str.lower),
    }


# ---------------------------------------------------------------------- nodes


def _source_files(repo: pathlib.Path, suffix: str):
    for path in sorted(repo.rglob(f"*{suffix}")):
        rel = path.relative_to(repo).parts
        if any(part in SKIP_DIRS for part in rel[:-1]):
            continue
        if any("test" in part.lower() for part in rel[:-1]):
            continue
        yield path


def scan_nodes(repos: list[pathlib.Path]) -> dict[str, list[int]]:
    nodes: dict[str, set[int]] = {}
    for repo in repos:
        for path in _source_files(repo, ".cs"):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if "NodeName" not in text:
                continue
            for name, version in NODE_RE.findall(text):
                nodes.setdefault(name, set()).add(int(version))
    return {name: sorted(versions) for name, versions in sorted(nodes.items())}


# ---------------------------------------------------------------------- repos


def doc_hash(path: str) -> str:
    """Hash of a path below a repository's docs/ folder (see check_skill_drift.doc_hash)."""
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:DOC_HASH_LENGTH]


def scan_repo_docs(repo: pathlib.Path) -> dict:
    """AGENTS.md/CLAUDE.md presence and the hashed paths of the Markdown files below docs/.

    The paths are stored as hashes: the file names of internal plans and runbooks stay
    out of the public repository, and the drift check can still tell whether a path a
    skill names exists. Every folder on the way is hashed too, so ``docs/guides/``
    resolves.
    """
    paths: set[str] = set()
    docs_dir = repo / "docs"
    if docs_dir.is_dir():
        for path in docs_dir.rglob("*"):
            rel = path.relative_to(repo)
            if not path.is_file() or path.suffix.lower() not in (".md", ".mdx"):
                continue
            if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
                continue
            parts = rel.parts
            paths.update("/".join(parts[:i]) for i in range(2, len(parts) + 1))
    return {
        "agentsMd": (repo / "AGENTS.md").is_file(),
        "claudeMd": (repo / "CLAUDE.md").is_file(),
        "docHashes": sorted(doc_hash(p) for p in paths),
    }


def matching_repos(monorepo: pathlib.Path, patterns: list[str], exclude: list[str]) -> list[pathlib.Path]:
    found = []
    for path in sorted(monorepo.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if any(fnmatch.fnmatchcase(path.name, p) for p in exclude):
            continue
        if any(fnmatch.fnmatchcase(path.name, p) for p in patterns):
            found.append(path)
    return found


def generate(monorepo: pathlib.Path, sources: dict, date: str) -> dict:
    repo_patterns = sources.get("repoPatterns", [])
    exclude = sources.get("excludeRepos", [])
    repos = matching_repos(monorepo, repo_patterns, exclude)
    node_repos = matching_repos(monorepo, sources.get("nodeRepoPatterns", repo_patterns), exclude)
    return {
        "schemaVersion": 1,
        "generated": date,
        "repoPatterns": repo_patterns,
        "excludeRepos": exclude,
        "cmdlets": scan_cmdlets(monorepo / sources.get("cmdletRepo", "octo-tools")),
        "octoCli": scan_octo_cli(monorepo / sources.get("cliRepo", "octo-cli")),
        "nodes": scan_nodes(node_repos),
        "repos": {repo.name: scan_repo_docs(repo) for repo in repos},
    }


def render(inventory: dict) -> str:
    return json.dumps(inventory, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--monorepo", type=pathlib.Path, required=True,
                        help="folder that holds the repository checkouts (octo-tools, octo-cli, ...)")
    parser.add_argument("--sources", type=pathlib.Path, default=REPO / "inventory" / "sources.json")
    parser.add_argument("--out", type=pathlib.Path, default=REPO / "inventory" / "names.json",
                        help="output file; '-' prints to stdout")
    parser.add_argument("--date", default=None, help="generation date YYYY-MM-DD (default: today, UTC)")
    args = parser.parse_args(argv)

    monorepo = args.monorepo.resolve()
    if not monorepo.is_dir():
        print(f"error: {monorepo} is not a folder", file=sys.stderr)
        return 2
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    date = args.date or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    _dt.date.fromisoformat(date)  # validates the format
    inventory = generate(monorepo, sources, date)

    missing = [kind for kind, key in (("cmdlets", "cmdlets"), ("nodes", "nodes")) if not inventory[key]]
    if not inventory["octoCli"]["commands"]:
        missing.append("octo-cli commands")
    if missing and not sources.get("allowEmpty"):
        print(f"error: no {', '.join(missing)} found below {monorepo}; wrong --monorepo?", file=sys.stderr)
        return 2

    text = render(inventory)
    if str(args.out) == "-":
        sys.stdout.write(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(
            f"wrote {args.out}: {len(inventory['cmdlets'])} cmdlets, {len(inventory['octoCli']['commands'])} "
            f"octo-cli commands, {len(inventory['nodes'])} nodes, {len(inventory['repos'])} repositories",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
