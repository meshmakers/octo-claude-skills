"""Tests of scripts/generate_name_inventory.py and scripts/scan_inventory_secrets.py (AB#9741).

Run:  python3 -m unittest discover -s tests -v
"""
import contextlib
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
import generate_name_inventory as gen  # noqa: E402
import scan_inventory_secrets  # noqa: E402

SOURCES = json.loads((FIXTURES / "sources.json").read_text())


def generate(tree=FIXTURES / "monorepo", date="2026-01-05"):
    return gen.render(gen.generate(tree, SOURCES, date))


class GeneratorTest(unittest.TestCase):
    def test_output_matches_the_golden_file_byte_for_byte(self):
        self.assertEqual(generate(), (FIXTURES / "expected-names.json").read_text())

    def test_same_input_gives_byte_identical_output(self):
        self.assertEqual(generate(), generate())
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "monorepo"
            shutil.copytree(FIXTURES / "monorepo", copy)
            self.assertEqual(generate(copy), generate())

    def test_date_is_written(self):
        self.assertEqual(json.loads(generate(date="2026-03-02"))["generated"], "2026-03-02")

    def test_cmdlets_and_parameters(self):
        cmdlets = json.loads(generate())["cmdlets"]
        self.assertEqual(cmdlets["Invoke-DemoBuild"], ["configuration", "extra", "noTests", "repo"])
        self.assertEqual(cmdlets["Start-DemoStack"], ["nonInteractive", "profile"])  # Global: prefix, inline params
        self.assertEqual(cmdlets["Stop-DemoStack"], [])

    def test_octo_cli_commands_inherit_base_arguments(self):
        cli = json.loads(generate())["octoCli"]
        self.assertEqual(cli["commands"]["ImportDemo"], ["--file", "--replace", "--wait", "-f", "-r", "-w"])
        self.assertIn("--context", cli["globalArguments"])
        self.assertIn("-c", cli["globalArguments"])

    def test_nodes_skip_test_folders(self):
        nodes = json.loads(generate())["nodes"]
        self.assertEqual(nodes, {"FromDemoTrigger": [1], "TransformDemo": [1, 2]})

    def test_repos_agents_and_hashed_docs(self):
        repos = json.loads(generate())["repos"]
        self.assertNotIn("customer-app", repos)  # outside repoPatterns
        demo = repos["octo-mesh-demo"]
        self.assertTrue(demo["agentsMd"])
        expected = sorted(gen.doc_hash(p) for p in ("docs/guide.md", "docs/nodes", "docs/nodes/transform-demo.md"))
        self.assertEqual(demo["docHashes"], expected)
        self.assertFalse(repos["octo-legacy-demo"]["agentsMd"])
        self.assertTrue(repos["octo-legacy-demo"]["claudeMd"])

    def test_doc_hash_matches_the_check(self):
        self.assertEqual(gen.doc_hash("docs/guide.md"), check_skill_drift.doc_hash("docs/guide.md"))

    def test_no_doc_names_in_output(self):
        self.assertNotIn("guide", generate())
        self.assertNotIn("transform-demo", generate())

    def test_cli_refuses_an_empty_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = gen.main(["--monorepo", tmp, "--sources", str(FIXTURES / "sources.json"), "--out", "-"])
        self.assertEqual(code, 2)
        self.assertIn("wrong --monorepo", err.getvalue())


class SecretScanTest(unittest.TestCase):
    def test_fixture_inventory_is_clean(self):
        self.assertEqual(scan_inventory_secrets.scan(json.loads(generate())), [])

    def test_committed_inventory_is_clean(self):
        data = json.loads((ROOT / "inventory" / "names.json").read_text())
        self.assertEqual(scan_inventory_secrets.scan(data), [])

    def test_scan_finds_what_is_not_a_name(self):
        bad = {
            "a": "https://example.invalid/x",
            "b": "build.internal",
            "c": "10.1.2.3",
            "d": "someone@example.org",
            "e": "password=hunter2",
            "f": "ghp" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
            "g": "a value with spaces",
            "h": "-----BEGIN RSA PRIVATE KEY-----",
        }
        problems = scan_inventory_secrets.scan(bad)
        self.assertEqual(len(problems), len(bad), problems)


if __name__ == "__main__":
    unittest.main()
