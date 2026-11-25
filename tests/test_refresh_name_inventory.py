"""Tests of scripts/refresh_name_inventory.py: rename in a fixture tree -> inventory, check, Bugs (AB#9741).

The run uses the fixture source tree instead of clones and an in-memory Azure Boards
double instead of the Azure CLI; nothing is pushed.

Run:  python3 -m unittest discover -s tests -v
"""
import argparse
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

import refresh_name_inventory as refresh  # noqa: E402


class FakeBoards:
    """In-memory stand-in for AzureBoards."""

    def __init__(self):
        self.bugs = {}       # id -> dict(title, area, repro, parent, state)
        self.comments = []   # (id, text)
        self.next_id = 1000

    def find_open_bug(self, skill):
        prefix = refresh.BUG_TITLE_PREFIX.format(skill=skill)
        for bug_id, bug in sorted(self.bugs.items()):
            if bug["title"].startswith(prefix) and bug["state"] not in ("Closed", "Removed"):
                return bug_id
        return None

    def create_bug(self, title, area, repro, parent):
        self.next_id += 1
        self.bugs[self.next_id] = {"title": title, "area": area, "repro": repro, "parent": parent, "state": "New"}
        return self.next_id

    def update_bug(self, bug_id, title, repro):
        self.bugs[bug_id].update(title=title, repro=repro)

    def comment(self, item_id, text):
        self.comments.append((item_id, text))


def skill(root, name, body):
    folder = root / "skills" / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: \"fixture\"\n---\n\n{body}\n")


class RefreshTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.src = self.tmp / "src"
        shutil.copytree(FIXTURES / "monorepo", self.src)
        self.skills = self.tmp / "skills-repo"
        (self.skills / "inventory").mkdir(parents=True)
        (self.skills / "inventory" / "allowlist.json").write_text('{"entries": []}')
        (self.skills / "OWNERS").write_text("ops-skill Heimdall\ncore-skill Thor\nclean-skill Thor\n")
        skill(self.skills, "ops-skill", "Build with `Invoke-DemoBuild -repo x`.")
        skill(self.skills, "core-skill", "```powershell\nInvoke-DemoBuild -configuration DebugL\n```")
        skill(self.skills, "clean-skill", "Start with `Start-DemoStack -nonInteractive $true`.")
        self.boards = FakeBoards()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_refresh(self, date):
        args = argparse.Namespace(
            date=date, teams_json=str(FIXTURES / "teams.json"), org="https://example.invalid", file_bugs=True,
            monorepo=str(self.src), work_dir=str(self.tmp / "work"), keep=True, source_tree=str(self.src),
            skills_tree=str(self.skills), user="tester", work_item="1", push=False,
            sources=str(FIXTURES / "sources.json"), update_self=False,
        )
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = refresh.run(args, boards=self.boards)
        return code, out.getvalue() + err.getvalue()

    def rename_cmdlet(self):
        module = self.src / "octo-tools" / "modules" / "Demo-Build.psm1"
        module.write_text(module.read_text().replace("Invoke-DemoBuild", "Invoke-DemoCompile"))

    def inventory(self):
        return json.loads((self.skills / "inventory" / "names.json").read_text())

    def test_clean_run_files_nothing(self):
        code, log = self.run_refresh("2026-01-05")
        self.assertEqual(code, 0, log)
        self.assertIn("Invoke-DemoBuild", self.inventory()["cmdlets"])
        self.assertEqual(self.boards.bugs, {})

    def test_renamed_cmdlet_fails_every_skill_naming_it_with_one_bug_each_and_updates_on_rerun(self):
        self.assertEqual(self.run_refresh("2026-01-05")[0], 0)
        self.rename_cmdlet()

        code, log = self.run_refresh("2026-01-12")
        self.assertEqual(code, 0, log)
        cmdlets = self.inventory()["cmdlets"]
        self.assertNotIn("Invoke-DemoBuild", cmdlets)
        self.assertIn("Invoke-DemoCompile", cmdlets)
        self.assertEqual(self.inventory()["generated"], "2026-01-12")

        bugs = sorted(self.boards.bugs.values(), key=lambda b: b["title"])
        self.assertEqual(len(bugs), 2, log)
        core, ops = bugs
        self.assertTrue(core["title"].startswith("Skill drift: core-skill "))
        self.assertEqual((core["parent"], core["area"]), (101, "Fixture\\Core"))
        self.assertTrue(ops["title"].startswith("Skill drift: ops-skill "))
        self.assertEqual((ops["parent"], ops["area"]), (104, "Fixture\\Ops"))
        self.assertIn("Invoke-DemoBuild", ops["repro"])
        self.assertIn("skills/ops-skill/SKILL.md:6", ops["repro"])

        code, log = self.run_refresh("2026-01-19")
        self.assertEqual(code, 0, log)
        self.assertEqual(len(self.boards.bugs), 2, "second run must update, not create")
        self.assertEqual(sum(1 for item, _ in self.boards.comments if item in self.boards.bugs), 2)

    def test_fixed_skill_gets_a_comment_on_its_open_bug(self):
        self.rename_cmdlet()
        self.run_refresh("2026-01-12")
        ops_bug = self.boards.find_open_bug("ops-skill")
        skill_md = self.skills / "skills" / "ops-skill" / "SKILL.md"
        skill_md.write_text(skill_md.read_text().replace("Invoke-DemoBuild", "Invoke-DemoCompile"))
        self.run_refresh("2026-01-19")
        texts = [text for item, text in self.boards.comments if item == ops_bug]
        self.assertTrue(any("finds no name any more" in t for t in texts), texts)

    def test_failed_run_comments_on_the_platform_ops_sustain_feature(self):
        shutil.rmtree(self.src / "octo-tools")
        code, log = self.run_refresh("2026-01-12")
        self.assertEqual(code, 3)
        self.assertEqual(self.boards.bugs, {})
        self.assertEqual(len(self.boards.comments), 1)
        item, text = self.boards.comments[0]
        self.assertEqual(item, 104)
        self.assertIn("refresh failed", text)
        self.assertIn("required source repositories missing: octo-tools", text)

    def test_missing_node_repository_fails_instead_of_dropping_its_names(self):
        shutil.rmtree(self.src / "octo-mesh-demo")
        code, log = self.run_refresh("2026-01-12")
        self.assertEqual(code, 3, log)
        self.assertIn("octo-mesh-demo", self.boards.comments[0][1])

    def test_unexpected_exception_is_reported_by_type_only(self):
        def boom(*_args, **_kwargs):
            raise ValueError("https://user:secret@example.invalid/repo.git")

        original = refresh.generate_name_inventory.generate
        refresh.generate_name_inventory.generate = boom
        try:
            code, log = self.run_refresh("2026-01-12")
        finally:
            refresh.generate_name_inventory.generate = original
        self.assertEqual(code, 3)
        item, text = self.boards.comments[0]
        self.assertEqual(item, 104)
        self.assertIn("unexpected ValueError", text)
        self.assertNotIn("secret", text + log)

    def test_newest_plugin_version_wins(self):
        base = "/c/octo-claude-pm/octo-claude-pm/{}/skills/backlog-conventions/references/teams.json"
        paths = [base.format(v) for v in ("0.52.11", "0.53.0", "0.9.40")]
        self.assertEqual(max(paths, key=refresh.plugin_version_key), base.format("0.53.0"))

    def test_default_is_a_dry_run_that_prints_what_it_would_file(self):
        self.rename_cmdlet()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = refresh.main(["--monorepo", str(self.src), "--source-tree", str(self.src),
                                 "--skills-tree", str(self.skills), "--teams-json", str(FIXTURES / "teams.json"),
                                 "--sources", str(FIXTURES / "sources.json"), "--user", "tester",
                                 "--date", "2026-01-12"])
        log = out.getvalue() + err.getvalue()
        self.assertEqual(code, 0, log)
        self.assertIn("dry run: nothing is pushed, filed or commented", log)
        self.assertIn("would create Bug 'Skill drift: ops-skill", log)
        self.assertIn("would create Bug 'Skill drift: core-skill", log)
        self.assertNotIn("pushed", log.replace("nothing is pushed", ""))

    def test_apply_turns_on_push_and_bug_filing(self):
        captured = {}

        def fake_run(args, boards=None):
            captured.update(push=args.push, file_bugs=args.file_bugs)
            return 0

        original = refresh.run
        refresh.run = fake_run
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                refresh.main(["--monorepo", str(self.src), "--apply", "--user", "tester"])
        finally:
            refresh.run = original
        self.assertEqual(captured, {"push": True, "file_bugs": True})

    def test_owner_targets_read_from_teams_json(self):
        teams = json.loads((FIXTURES / "teams.json").read_text())
        targets = refresh.owner_targets(teams)
        self.assertEqual(targets["Thor"]["feature"], 101)
        self.assertEqual(targets["Heimdall"]["areaPath"], "Fixture\\Ops")


class RefreshBranchTest(unittest.TestCase):
    """prepare_skills_clone against a local bare repository: the check must see today's main."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.origin = self.tmp / "origin.git"
        self.seed = self.tmp / "seed"
        self.git("init", "--quiet", "--bare", "-b", "main", str(self.origin))
        self.git("clone", "--quiet", str(self.origin), str(self.seed))
        self.git("-C", str(self.seed), "checkout", "--quiet", "-b", "main")
        self.commit("skill.md", "old text\n", "main 1")
        self.git("-C", str(self.seed), "push", "--quiet", "origin", "main")
        self.branch = "tester/AB#1_name-inventory-refresh"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@invalid", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@invalid", "PATH": os.environ["PATH"],
               "HOME": str(self.tmp)}
        return subprocess.run(["git", *args], check=True, capture_output=True, text=True,
                                            env=env).stdout.strip()

    def commit(self, name, text, message):
        (self.seed / name).write_text(text)
        self.git("-C", str(self.seed), "add", name)
        self.git("-C", str(self.seed), "commit", "--quiet", "-m", message)

    def prepare(self, label):

        old = {k: os.environ.get(k) for k in ("HOME", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
                                              "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")}
        os.environ.update(HOME=str(self.tmp), GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@invalid",
                          GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@invalid")
        try:
            work = self.tmp / label
            work.mkdir()
            return refresh.prepare_skills_clone(str(self.origin), work, self.branch)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_waiting_branch_is_continued_with_todays_main_merged(self):
        self.git("-C", str(self.seed), "checkout", "--quiet", "-b", self.branch)
        self.commit("names.json", "week 1\n", "refresh 1")
        self.git("-C", str(self.seed), "push", "--quiet", "origin", self.branch)
        self.git("-C", str(self.seed), "checkout", "--quiet", "main")
        self.commit("skill.md", "fixed text\n", "main 2: skill fixed")
        self.git("-C", str(self.seed), "push", "--quiet", "origin", "main")

        clone, continued = self.prepare("a")
        self.assertTrue(continued)
        self.assertEqual((clone / "skill.md").read_text(), "fixed text\n")
        self.assertEqual((clone / "names.json").read_text(), "week 1\n")

    def test_batched_branch_restarts_from_main(self):
        self.git("-C", str(self.seed), "checkout", "--quiet", "-b", self.branch)
        self.commit("names.json", "week 1\n", "refresh 1")
        self.git("-C", str(self.seed), "push", "--quiet", "origin", self.branch)
        self.git("-C", str(self.seed), "checkout", "--quiet", "main")
        self.git("-C", str(self.seed), "merge", "--quiet", "--no-ff", "-m", "batch", self.branch)
        self.commit("skill.md", "fixed text\n", "main 3")
        self.git("-C", str(self.seed), "push", "--quiet", "origin", "main")

        clone, continued = self.prepare("b")
        self.assertFalse(continued)
        self.assertEqual((clone / "skill.md").read_text(), "fixed text\n")

    def test_no_branch_starts_from_main(self):
        clone, continued = self.prepare("c")
        self.assertFalse(continued)
        self.assertEqual((clone / "skill.md").read_text(), "old text\n")


class HelperTest(unittest.TestCase):
    def test_https_url(self):
        self.assertEqual(refresh.https_url("git@github.com:org/repo.git"), "https://github.com/org/repo.git")
        self.assertEqual(refresh.https_url("https://user:secret@github.com/org/repo.git"),
                         "https://github.com/org/repo.git")


if __name__ == "__main__":
    unittest.main()
