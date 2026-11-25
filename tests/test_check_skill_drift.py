"""Tests of scripts/check_skill_drift.py with fixture skills (AB#6366).

Run:  python3 -m unittest discover -s tests -v
"""
import contextlib
import datetime as dt
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

import check_skill_drift  # noqa: E402

INVENTORY = FIXTURES / "expected-names.json"
TODAY = dt.date(2026, 1, 10)  # five days after the fixture inventory was generated


def run_check(root, *extra, inventory=INVENTORY):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = check_skill_drift.main(
            ["--root", str(root), "--inventory", str(inventory), "--today", TODAY.isoformat(), *extra]
        )
    return code, out.getvalue(), err.getvalue()


class DriftFixtureTest(unittest.TestCase):
    def test_drift_fixture_reports_file_line_kind_name_owner_and_exits_1(self):
        code, out, _ = run_check(FIXTURES / "check-drift", "--json")
        self.assertEqual(code, 1)
        findings = {(f["line"], f["kind"], f["name"]) for f in json.loads(out)["findings"]}
        expected = {
            (8, "cmdlet", "Invoke-MissingThing"),
            (9, "cmdlet-parameter", "Invoke-DemoBuild -bogus"),
            (10, "octo-cli-command", "NoSuchCommand"),
            (11, "octo-cli-argument", "ImportDemo --nosuch"),
            (12, "node", "TransformDemo@3"),
            (12, "node", "NoSuchNode@1"),
            (13, "repo-doc", "octo-mesh-demo/docs/missing.md"),
            (14, "repo-doc", "octo-unknown-repo/AGENTS.md"),
            (15, "repo-doc", "octo-legacy-demo/AGENTS.md"),
            (16, "reference-to-shim", "octo-mesh-demo/CLAUDE.md"),
            (17, "machine-path", "C:\\dev"),
            (18, "node", "RetiredDemo@1"),
        }
        self.assertEqual(findings, expected)
        for finding in json.loads(out)["findings"]:
            self.assertEqual(finding["file"], "skills/demo/SKILL.md")
            self.assertEqual(finding["owner"], "Thor")

    def test_text_output_names_file_line_kind_name_and_owner(self):
        code, out, _ = run_check(FIXTURES / "check-drift")
        self.assertEqual(code, 1)
        self.assertIn("== Thor (12 findings)", out)
        self.assertIn("skills/demo/SKILL.md:8: cmdlet: Invoke-MissingThing", out)
        self.assertIn("(owner: Thor)", out)

    def test_node_version_detail_lists_known_versions(self):
        _, out, _ = run_check(FIXTURES / "check-drift", "--json")
        detail = {f["name"]: f["detail"] for f in json.loads(out)["findings"]}
        self.assertIn("known: @1, @2", detail["TransformDemo@3"])


class ValidFixtureTest(unittest.TestCase):
    def test_valid_and_allow_listed_names_exit_0(self):
        code, out, err = run_check(FIXTURES / "check-valid", "--json")
        self.assertEqual(json.loads(out)["findings"], [], out)
        self.assertEqual(code, 0, err)

    def test_allow_list_entry_is_what_makes_the_retired_node_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            (root / "inventory" / "allowlist.json").write_text('{"entries": []}')
            code, out, _ = run_check(root, "--json")
        self.assertEqual(code, 1)
        self.assertEqual([f["name"] for f in json.loads(out)["findings"]], ["RetiredDemo@1"])

    def test_ignore_baseline_reports_baselined_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            allow = {"entries": [{"kind": "node", "name": "RetiredDemo@1", "reason": "baseline 2026-01-05: x",
                                  "workItem": 7}]}
            (root / "inventory" / "allowlist.json").write_text(json.dumps(allow))
            self.assertEqual(run_check(root)[0], 0)
            code, out, _ = run_check(root, "--json", "--ignore-baseline")
        self.assertEqual(code, 1)
        self.assertEqual([f["name"] for f in json.loads(out)["findings"]], ["RetiredDemo@1"])


class OwnersTest(unittest.TestCase):
    def test_skill_without_owner_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            orphan = root / "skills" / "orphan"
            orphan.mkdir()
            (orphan / "SKILL.md").write_text("---\nname: orphan\ndescription: \"x\"\n---\n")
            code, out, _ = run_check(root)
        self.assertEqual(code, 1)
        self.assertIn("skill 'orphan' has no owner", out)

    def test_owner_line_for_missing_skill_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            (root / "OWNERS").write_text("demo Heimdall\nghost Thor\n")
            code, out, _ = run_check(root)
        self.assertEqual(code, 1)
        self.assertIn("'ghost' is not a skill", out)

    def test_repository_owners_cover_every_skill(self):
        owners = check_skill_drift.load_owners(ROOT / "OWNERS")
        skills = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists())
        self.assertEqual(sorted(owners), skills)
        self.assertLessEqual(set(owners.values()), {"Heimdall", "Thor", "Freya", "Mimir", "Sol", "Njord"})


class InputValidationTest(unittest.TestCase):
    def test_allow_list_entry_without_work_item_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            allow = {"entries": [{"kind": "node", "name": "RetiredDemo@1", "reason": "no work item"}]}
            (root / "inventory" / "allowlist.json").write_text(json.dumps(allow))
            code, _, err = run_check(root)
        self.assertEqual(code, 2)
        self.assertIn("needs the workItem", err)

    def test_unknown_schema_version_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "names.json"
            bad.write_text('{"schemaVersion": 99}')
            code, _, err = run_check(FIXTURES / "check-valid", inventory=bad)
        self.assertEqual(code, 2)
        self.assertIn("schemaVersion", err)


class ScannerRulesTest(unittest.TestCase):
    """Edge cases of the scanners, against the fixture inventory."""

    def findings(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            (root / "skills" / "demo" / "SKILL.md").write_text(f"---\nname: demo\ndescription: \"x\"\n---\n{body}\n")
            _, out, _ = run_check(root, "--json")
        return [(f["line"], f["kind"], f["name"]) for f in json.loads(out)["findings"]]

    def test_short_term_with_double_dash_and_long_term_with_single_dash_are_findings(self):
        found = self.findings("`octo-cli -c ImportDemo --f x -file y -f z --file w`")
        self.assertEqual(sorted(n for _, _, n in found), ["ImportDemo --f", "ImportDemo -file"])

    def test_slash_long_term_is_accepted(self):
        self.assertEqual(self.findings("`octo-cli -c ImportDemo /file x`"), [])

    def test_ambiguous_prefix_is_a_finding_unique_prefix_is_not(self):
        # Start-DemoStack has -profile and -nonInteractive; Invoke-DemoBuild has -repo, -configuration, -extra, -noTests.
        self.assertEqual(self.findings("`Start-DemoStack -prof x -non $true`"), [])
        with tempfile.TemporaryDirectory() as tmp:
            inv = json.loads(INVENTORY.read_text())
            inv["cmdlets"]["Start-DemoStack"].append("profileName")
            path = pathlib.Path(tmp) / "names.json"
            path.write_text(json.dumps(inv))
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            (root / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: \"x\"\n---\n"
                                                              "`Start-DemoStack -prof x`\n")
            _, out, _ = run_check(root, "--json", inventory=path)
        self.assertEqual([f["name"] for f in json.loads(out)["findings"]], ["Start-DemoStack -prof"])

    def test_continuation_lines_belong_to_their_command(self):
        body = "```bash\nocto-cli -c ImportDemo \\\n  --nosuch x \\\n  -f y\n```\n```powershell\nInvoke-DemoBuild `\n  -bogus 1\n```"
        self.assertEqual(sorted(self.findings(body)),
                         [(6, "octo-cli-argument", "ImportDemo --nosuch"), (11, "cmdlet-parameter", "Invoke-DemoBuild -bogus")])

    def test_verbs_outside_the_approved_list_are_checked_when_octo_tools_uses_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = json.loads(INVENTORY.read_text())
            inv["cmdlets"]["Clone-DemoRepos"] = []
            path = pathlib.Path(tmp) / "names.json"
            path.write_text(json.dumps(inv))
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            (root / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: \"x\"\n---\n"
                                                              "`Clone-DemoRepos` and `Clone-OldRepos`\n")
            _, out, _ = run_check(root, "--json", inventory=path)
        self.assertEqual([f["name"] for f in json.loads(out)["findings"]], ["Clone-OldRepos"])

    def test_bare_wildcard_entry_without_files_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "check-valid", root)
            for entry in ({"kind": "*", "name": "Foo@1"}, {"kind": "node", "name": "*"}):
                allow = {"entries": [{**entry, "reason": "x", "workItem": 3}]}
                (root / "inventory" / "allowlist.json").write_text(json.dumps(allow))
                code, _, err = run_check(root)
                self.assertEqual(code, 2, entry)
                self.assertIn("needs 'files'", err)


class StalenessTest(unittest.TestCase):
    def test_old_inventory_warns_but_does_not_fail(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_skill_drift.main(["--root", str(FIXTURES / "check-valid"), "--inventory", str(INVENTORY),
                                           "--today", "2026-02-01"])
        self.assertEqual(code, 0)
        self.assertIn("27 days old", err.getvalue())

    def test_fresh_inventory_does_not_warn(self):
        _, _, err = run_check(FIXTURES / "check-valid")
        self.assertNotIn("days old", err)


class RepositorySelfCheckTest(unittest.TestCase):
    """The committed skills pass against the committed inventory and baseline."""

    def test_repository_skills_pass(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_skill_drift.main(["--root", str(ROOT), "--max-age-days", "100000"])
        self.assertEqual(code, 0, out.getvalue())


if __name__ == "__main__":
    unittest.main()
