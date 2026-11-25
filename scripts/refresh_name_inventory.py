#!/usr/bin/env python3
"""Weekly refresh of the skill name inventory and filing of drift findings (AB#9741).

One run:
 1. makes fresh shallow clones of the default branch of every source repository
    (the repositories of the --monorepo folder that match inventory/sources.json;
    clone URLs are taken from their ``origin`` remotes and never printed);
 2. clones this repository's default branch and regenerates inventory/names.json
    there with scripts/generate_name_inventory.py;
 3. scans the new inventory with scripts/scan_inventory_secrets.py (names only);
 4. with --push: commits the inventory on the branch ``<user>/AB#<id>_name-inventory-refresh``
    (continuing it while an earlier refresh is still waiting for the docs batch) and
    pushes it without a pull request — the daily docs batch takes it to main;
 5. runs scripts/check_skill_drift.py against the new inventory;
 6. with --file-bugs: files the findings as one Bug per skill under the Sustain
    Feature of the skill's owner (OWNERS -> PO agent -> team -> teams.json
    ``sustain.features``), updating the open Bug of the skill instead of creating a
    second one, and commenting on the open Bug of a skill that has no finding any more.

A failed run (not a finding) is reported as a comment on the Platform Ops Sustain
Feature (with --file-bugs). Without --push and --file-bugs the run changes nothing
and prints what it would do.

Owner IDs, the project and the Sustain Features are read at run time from the
octo-claude-pm plugin (``skills/backlog-conventions/references/teams.json``); none
of them is stored in this public repository.

Run:  python3 scripts/refresh_name_inventory.py --monorepo <path> [--apply | --push | --file-bugs]   (default: dry run)
Standard library only; needs git and, for --file-bugs, the Azure CLI (az boards) logged in.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = pathlib.Path(__file__).resolve().parent
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import check_skill_drift  # noqa: E402
import generate_name_inventory  # noqa: E402
import scan_inventory_secrets  # noqa: E402

BUG_TAG = "skill-drift"
BUG_TITLE = "Skill drift: {skill} names {count} name(s) that do not exist"
BUG_TITLE_PREFIX = "Skill drift: {skill} "
COMMENT_PREFIX = "[skill-drift]"
DEFAULT_ORG = "https://dev.azure.com/meshmakers"
TEAMS_JSON_GLOB = "~/.claude/plugins/cache/octo-claude-pm/octo-claude-pm/*/skills/backlog-conventions/references/teams.json"


class RunFailed(Exception):
    """A step of the run failed; the message names the step, never a URL or secret."""


# ------------------------------------------------------------------ helpers


def git(*args: str, cwd: pathlib.Path | None = None, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, timeout=900)
    if check and result.returncode != 0:
        # git errors can carry remote URLs: report the subcommand and exit code only.
        raise RunFailed(f"git {args[0]} failed (exit {result.returncode})")
    return result.stdout.strip()


def find_teams_json(explicit: str | None) -> pathlib.Path:
    if explicit:
        return pathlib.Path(explicit).expanduser()
    candidates = glob.glob(os.path.expanduser(TEAMS_JSON_GLOB))

    def version_key(path: str):
        part = pathlib.Path(path).parts[-6]
        return tuple(int(x) if x.isdigit() else 0 for x in part.split("."))

    if not candidates:
        raise RunFailed("teams.json of octo-claude-pm not found; pass --teams-json")
    return pathlib.Path(max(candidates, key=version_key))


def owner_targets(teams: dict) -> dict[str, dict]:
    """Map PO agent name (e.g. 'Thor') to its team's Sustain Feature and area path."""
    features = teams.get("sustain", {}).get("features", {})
    targets = {}
    for team in teams.get("teams", []):
        match = re.search(r"\((\w+)\)", team.get("productOwnerAgent", ""))
        if match and team.get("key") in features:
            targets[match.group(1)] = {"feature": features[team["key"]], "areaPath": team["areaPath"],
                                       "team": team["key"]}
    return targets


def findings_html(skill: str, findings: list[dict], date: str) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(f['file'])}:{f['line']}</td><td>{html.escape(f['kind'])}</td>"
        f"<td>{html.escape(f['name'])}</td><td>{html.escape(f['detail'])}</td></tr>"
        for f in findings
    )
    return (
        f"<p>The weekly drift check of octo-claude-skills ({date}) found {len(findings)} name(s) in skill "
        f"<code>{html.escape(skill)}</code> that the name inventory does not list. Fix the skill (or add a "
        f"deliberate mention to <code>inventory/allowlist.json</code> with a reason). Run locally: "
        f"<code>python3 scripts/check_skill_drift.py</code>.</p>"
        f"<table><tr><th>File:line</th><th>Kind</th><th>Name</th><th>Detail</th></tr>{rows}</table>"
    )


# --------------------------------------------------------------------- ADO


class AzureBoards:
    """Bug filing through the Azure CLI (az boards)."""

    def __init__(self, org: str, project: str):
        self.org, self.project = org, project

    def _az(self, *args: str) -> dict | list:
        result = subprocess.run(["az", *args, "--org", self.org, "--output", "json"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RunFailed(f"az {' '.join(args[:2])} failed (exit {result.returncode})")
        return json.loads(result.stdout or "null")

    def find_open_bug(self, skill: str) -> int | None:
        title = BUG_TITLE_PREFIX.format(skill=skill).replace("'", "''")
        wiql = (
            "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '" + self.project.replace("'", "''") +
            "' AND [System.WorkItemType] = 'Bug' AND [System.Tags] CONTAINS '" + BUG_TAG +
            "' AND [System.Title] CONTAINS '" + title + "' AND [System.State] NOT IN ('Closed', 'Removed') "
            "ORDER BY [System.Id]"
        )
        rows = self._az("boards", "query", "--wiql", wiql, "--project", self.project)
        for row in rows or []:
            return int(row["id"])
        return None

    def create_bug(self, title: str, area: str, repro: str, parent: int) -> int:
        item = self._az("boards", "work-item", "create", "--type", "Bug", "--title", title, "--area", area,
                        "--iteration", self.project, "--project", self.project,
                        "--fields", f"Microsoft.VSTS.TCM.ReproSteps={repro}", f"System.Tags={BUG_TAG}; octo-claude-skills")
        bug_id = int(item["id"])
        self._az("boards", "work-item", "relation", "add", "--id", str(bug_id), "--relation-type", "parent",
                 "--target-id", str(parent))
        return bug_id

    def update_bug(self, bug_id: int, title: str, repro: str) -> None:
        self._az("boards", "work-item", "update", "--id", str(bug_id), "--title", title,
                 "--fields", f"Microsoft.VSTS.TCM.ReproSteps={repro}")

    def comment(self, item_id: int, text: str) -> None:
        self._az("boards", "work-item", "update", "--id", str(item_id), "--discussion", text)


class DryRunBoards:
    """Prints what would be filed. Does not query Azure Boards, so it cannot tell an update from a create."""

    def find_open_bug(self, skill: str) -> int | None:
        return None

    def create_bug(self, title, area, repro, parent) -> int | None:
        print(f"would create Bug '{title}' under Feature {parent} ({area})")
        return None

    def update_bug(self, bug_id, title, repro) -> None:
        print(f"would update Bug {bug_id}: '{title}'")

    def comment(self, item_id, text) -> None:
        print(f"would comment on {item_id}: {text[:120]}")


def file_findings(boards, findings: list[dict], owners: dict[str, str], targets: dict[str, dict],
                  skills: list[str], date: str) -> list[str]:
    """Create or update one Bug per skill with findings; comment on open Bugs of clean skills."""
    log = []
    by_skill: dict[str, list[dict]] = {}
    for f in findings:
        by_skill.setdefault(pathlib.PurePosixPath(f["file"]).parts[1], []).append(f)
    for skill in sorted(set(skills) | set(by_skill)):
        items = by_skill.get(skill, [])
        owner = owners.get(skill)
        target = targets.get(owner or "")
        existing = boards.find_open_bug(skill)
        if not items:
            if existing:
                boards.comment(existing, f"{COMMENT_PREFIX} {date}: the drift check finds no name any more in "
                                         f"skill {skill}. Verify and close this Bug.")
                log.append(f"{skill}: clean, commented on Bug {existing}")
            continue
        if target is None:
            raise RunFailed(f"no Sustain Feature for owner {owner!r} of skill {skill!r}")
        title = BUG_TITLE.format(skill=skill, count=len(items))
        repro = findings_html(skill, items, date)
        if existing:
            boards.update_bug(existing, title, repro)
            boards.comment(existing, f"{COMMENT_PREFIX} {date}: {len(items)} finding(s) in the weekly run; "
                                     "repro steps updated.")
            log.append(f"{skill}: {len(items)} finding(s), updated Bug {existing}")
        else:
            bug_id = boards.create_bug(title, target["areaPath"], repro, target["feature"])
            action = f"created Bug {bug_id}" if bug_id else "would create a Bug"
            log.append(f"{skill}: {len(items)} finding(s), {action} under Feature {target['feature']}")
    return log


# --------------------------------------------------------------------- run


def source_repos(monorepo: pathlib.Path, sources: dict) -> list[str]:
    patterns = sources.get("repoPatterns", []) + sources.get("nodeRepoPatterns", [])
    names = {p.name for p in generate_name_inventory.matching_repos(monorepo, patterns, sources.get("excludeRepos", []))}
    names |= {sources.get("cmdletRepo", "octo-tools"), sources.get("cliRepo", "octo-cli")}
    names = {n for n in names if (monorepo / n / ".git").exists()}
    # extraRepos need no local checkout: they are cloned from the owner of the octo-tools remote.
    names |= set(sources.get("extraRepos", []))
    return sorted(names)


def remote_url(monorepo: pathlib.Path, name: str, sources: dict) -> str:
    if (monorepo / name / ".git").exists():
        return https_url(git("remote", "get-url", "origin", cwd=monorepo / name))
    anchor = https_url(git("remote", "get-url", "origin", cwd=monorepo / sources.get("cmdletRepo", "octo-tools")))
    return re.sub(r"/[^/]+?(\.git)?$", f"/{name}.git", anchor)


def https_url(url: str) -> str:
    """GitHub remotes as HTTPS URLs without user info (credentials come from the credential helper)."""
    match = re.match(r"^(?:ssh://)?git@([\w.-]+)[:/](.+?)(?:\.git)?/?$", url)
    if match:
        return f"https://{match.group(1)}/{match.group(2)}.git"
    return re.sub(r"^(https?://)[^/@]*@", r"\1", url)


def clone_args() -> list[str]:
    """git options for non-interactive clones: credentials from the GitHub CLI, never a prompt."""
    return ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]


def clone_sources(monorepo: pathlib.Path, names: list[str], target: pathlib.Path, sources: dict) -> None:
    from concurrent.futures import ThreadPoolExecutor

    target.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    def clone(name: str) -> tuple[str, int]:
        try:
            url = remote_url(monorepo, name, sources)
        except RunFailed:
            return name, -2
        try:
            result = subprocess.run(
                ["git", *clone_args(), "clone", "--quiet", "--depth", "1", "--single-branch", "--no-tags",
                 "--filter=blob:limit=1m", url, str(target / name)],
                capture_output=True, text=True, env=env, timeout=600,
            )
            return name, result.returncode
        except subprocess.TimeoutExpired:
            return name, -1

    with ThreadPoolExecutor(max_workers=6) as pool:
        failed = [(n, rc) for n, rc in pool.map(clone, names) if rc != 0]
    if failed:
        raise RunFailed("clone failed for " + ", ".join(f"{n} (exit {rc})" for n, rc in failed))


def prepare_skills_clone(skills_url: str, work: pathlib.Path, branch: str) -> tuple[pathlib.Path, bool]:
    """Clone this repository; continue the refresh branch when it is still on the remote."""
    clone = work / "octo-claude-skills"
    git(*clone_args(), "clone", "--quiet", "--depth", "50", "--no-tags", https_url(skills_url), str(clone))
    git("config", "credential.helper", "!gh auth git-credential", cwd=clone)
    remote_branch = git("ls-remote", "--heads", "origin", branch, cwd=clone)
    if remote_branch:
        git("fetch", "--quiet", "--depth", "50", "origin", f"refs/heads/{branch}:refs/remotes/origin/{branch}", cwd=clone)
        git("checkout", "--quiet", "-b", branch, f"origin/{branch}", cwd=clone)
        return clone, True
    git("checkout", "--quiet", "-b", branch, cwd=clone)
    return clone, False


def run(args, boards=None) -> int:
    date = args.date or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    teams_path = None
    teams: dict = {}
    try:
        teams_path = find_teams_json(args.teams_json)
        teams = json.loads(teams_path.read_text(encoding="utf-8"))
        project = teams.get("project", "OctoMesh")
        if isinstance(project, dict):
            project = project.get("name", "OctoMesh")
        if boards is None:
            boards = AzureBoards(args.org, project) if args.file_bugs else DryRunBoards()

        monorepo = pathlib.Path(args.monorepo).expanduser().resolve()
        sources = json.loads((REPO / "inventory" / "sources.json").read_text(encoding="utf-8"))
        work = pathlib.Path(args.work_dir or tempfile.mkdtemp(prefix="skill-inventory-"))
        try:
            if args.source_tree:
                src = pathlib.Path(args.source_tree).resolve()
            else:
                src = work / "src"
                names = source_repos(monorepo, sources)
                print(f"cloning {len(names)} repositories", file=sys.stderr)
                clone_sources(monorepo, names, src, sources)

            branch = f"{args.user}/AB#{args.work_item}_name-inventory-refresh"
            if args.skills_tree:
                skills_root = pathlib.Path(args.skills_tree).resolve()
                continued = False
            else:
                skills_url = git("remote", "get-url", "origin", cwd=REPO)
                skills_root, continued = prepare_skills_clone(skills_url, work, branch)

            inventory = generate_name_inventory.generate(src, sources, date)
            if not inventory["cmdlets"] or not inventory["octoCli"]["commands"] or not inventory["nodes"]:
                raise RunFailed("generator found no cmdlets, commands or nodes")
            problems = scan_inventory_secrets.scan(inventory)
            if problems:
                raise RunFailed(f"inventory scan found {len(problems)} value(s) that are not names")
            names_path = skills_root / "inventory" / "names.json"
            old = names_path.read_text(encoding="utf-8") if names_path.exists() else ""
            new = generate_name_inventory.render(inventory)
            names_path.parent.mkdir(parents=True, exist_ok=True)
            names_path.write_text(new, encoding="utf-8")
            print(f"inventory {'changed' if old != new else 'unchanged'} ({date})", file=sys.stderr)

            if args.push and old != new:
                git("add", "inventory/names.json", cwd=skills_root)
                git("commit", "--quiet", "-m", f"AB#{args.work_item} Chore: Refresh the skill name inventory ({date})",
                    cwd=skills_root)
                git("push", "--quiet", "-u", "origin", branch, cwd=skills_root)
                print(f"pushed {branch} ({'continued' if continued else 'new'}); the docs batch takes it to main",
                      file=sys.stderr)
            elif old != new:
                print(f"would push {branch} with the new inventory", file=sys.stderr)

            findings, errors, warnings, counts = check_skill_drift.run(
                skills_root, names_path, skills_root / "inventory" / "allowlist.json", skills_root / "OWNERS",
                _dt.date.fromisoformat(date), 14,
            )
            if errors:
                raise RunFailed(f"drift check errors: {'; '.join(errors)}")
            owners = check_skill_drift.load_owners(skills_root / "OWNERS")
            log = file_findings(boards, [f.__dict__ for f in findings], owners, owner_targets(teams),
                                sorted(counts), date)
            for line in log:
                print(line)
            print(f"{len(findings)} finding(s) in {sum(1 for c in counts.values() if c['findings'])} skill(s)",
                  file=sys.stderr)
            return 0
        finally:
            if not args.keep and not args.work_dir:
                shutil.rmtree(work, ignore_errors=True)
    except (RunFailed, OSError, json.JSONDecodeError, check_skill_drift.ConfigError) as exc:
        message = f"{COMMENT_PREFIX} {date}: the weekly skill name inventory refresh failed: {exc}"
        print(message, file=sys.stderr)
        ops = teams.get("sustain", {}).get("features", {}).get("ops")
        if boards is not None and ops:
            try:
                boards.comment(int(ops), message)
            except RunFailed as inner:
                print(f"could not report the failure: {inner}", file=sys.stderr)
        return 3


def default_user() -> str:
    name = git("config", "user.name", check=False) or "agent"
    return name.split()[0].lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--monorepo", required=True, help="folder with the repository checkouts (source of the "
                                                          "repository list and their origin remotes)")
    parser.add_argument("--push", action="store_true", help="commit and push the refreshed inventory")
    parser.add_argument("--file-bugs", action="store_true", help="file findings and failures in Azure Boards")
    parser.add_argument("--apply", action="store_true",
                        help="act: the same as --push --file-bugs (without it, and without those two, the run is a "
                             "dry run that only prints what it would push, file and comment)")
    parser.add_argument("--teams-json", help="teams.json of octo-claude-pm (default: newest installed plugin)")
    parser.add_argument("--org", default=DEFAULT_ORG, help="Azure DevOps organization URL")
    parser.add_argument("--work-item", default="9741", help="work item of the refresh commits (default 9741)")
    parser.add_argument("--user", default=None, help="branch prefix (default: first name of git user.name)")
    parser.add_argument("--date", default=None, help="run date YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--work-dir", default=None, help="keep clones here instead of a temporary folder")
    parser.add_argument("--keep", action="store_true", help="do not delete the temporary folder")
    parser.add_argument("--source-tree", default=None, help=argparse.SUPPRESS)  # tests: use this tree, no clones
    parser.add_argument("--skills-tree", default=None, help=argparse.SUPPRESS)  # tests: use this tree, no clone
    args = parser.parse_args(argv)
    args.user = args.user or default_user()
    if args.apply:
        args.push = args.file_bugs = True
    if not (args.push or args.file_bugs):
        print("dry run: nothing is pushed, filed or commented (use --apply to act)", file=sys.stderr)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
