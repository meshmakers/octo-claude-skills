"""Verification script for Step 2: gql_introspect.py."""
import subprocess
import sys
import json
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
INTROSPECT = os.path.join(SCRIPTS, "gql_introspect.py")

print("=== Step 2 Verification: gql_introspect.py ===")
print()

def run(args, expect_fail=False):
    result = subprocess.run(
        [sys.executable, INTROSPECT] + args,
        capture_output=True, text=True
    )
    if expect_fail:
        return result
    if result.returncode != 0:
        print(f"   FAILED (exit {result.returncode})")
        print(f"   stderr: {result.stderr[:500]}")
        sys.exit(1)
    return result

# 1. `top` subcommand returns known top-level fields
print("1. 'top' subcommand...")
r = run(["top"])
output = r.stdout
assert "constructionKit" in output, "Missing 'constructionKit' in top output"
assert "runtime" in output or "Runtime" in output, "Missing 'runtime' in top output"
print("   OK — found constructionKit and runtime in top-level fields")
print(f"   (first 3 lines: {output.strip().splitlines()[:3]})")

# 2. `type` subcommand returns known CkType fields
print()
print("2. 'type CkType' subcommand...")
r = run(["type", "CkType"])
output = r.stdout
assert "ckTypeId" in output, "Missing 'ckTypeId' in CkType fields"
assert "isAbstract" in output, "Missing 'isAbstract' in CkType fields"
assert "associations" in output, "Missing 'associations' in CkType fields"
print("   OK — found ckTypeId, isAbstract, associations in CkType fields")

# 3. `--json` flag produces valid JSON
print()
print("3. '--json' flag check...")
r = run(["top", "--json"])
data = json.loads(r.stdout)
assert isinstance(data, list), "Expected JSON array"
print(f"   OK — valid JSON array with {len(data)} fields")

# 4. Unknown type gives clear error (not a crash)
print()
print("4. Unknown type error handling...")
r = run(["type", "NonExistentType123"], expect_fail=True)
assert r.returncode != 0, "Expected non-zero exit code for unknown type"
assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower(), \
    "Expected 'not found' message"
# Make sure there's no Python traceback
assert "Traceback" not in r.stderr and "Traceback" not in r.stdout, \
    "Got unexpected traceback"
print("   OK — clean error message, no traceback")

print()
print("=== Step 2: ALL CHECKS PASSED ===")
