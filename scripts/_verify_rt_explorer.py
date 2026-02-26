"""Verification script for rt_explorer.py — Runtime Instance Explorer."""
import subprocess
import sys
import json
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
EXPLORER = os.path.join(SCRIPTS, "rt_explorer.py")

print("=== Verification: rt_explorer.py ===")
print()


def run(args, expect_fail=False):
    result = subprocess.run(
        [sys.executable, EXPLORER] + args,
        capture_output=True, text=True
    )
    if expect_fail:
        return result
    if result.returncode != 0:
        print(f"   FAILED (exit {result.returncode})")
        print(f"   stderr: {result.stderr[:500]}")
        sys.exit(1)
    return result


# 1. list — returns entities with rtId
print("1. 'list Industry.Basic/Machine --first 3'...")
r = run(["list", "Industry.Basic/Machine", "--first", "3"])
output = r.stdout
assert "Industry.Basic/Machine" in output, "Missing ckId in output"
lines = [l for l in output.splitlines() if l.strip() and not l.startswith("Instances") and not l.startswith("  ...")]
assert len(lines) > 0, "No entity lines returned"
# Extract an rtId for later use (first entity line)
entity_line = lines[0].strip()
first_rtId = entity_line.split()[0]
print(f"   OK — got entities, first rtId: {first_rtId}")

# 2. count — returns a number > 0
print()
print("2. 'count Industry.Basic/Machine'...")
r = run(["count", "Industry.Basic/Machine"])
output = r.stdout
assert "instances" in output.lower() or ":" in output, "Missing count output"
# Extract count number
parts = output.strip().split()
count_val = None
for p in parts:
    try:
        count_val = int(p)
        break
    except ValueError:
        continue
assert count_val is not None and count_val > 0, f"Expected count > 0, got: {output.strip()}"
print(f"   OK — {output.strip()}")

# 3. get — shows attributes and associations using rtId from step 1
print()
print(f"3. 'get Industry.Basic/Machine {first_rtId}'...")
r = run(["get", "Industry.Basic/Machine", first_rtId])
output = r.stdout
assert "rtId:" in output or "Entity:" in output, "Missing entity detail"
assert "Attributes" in output, "Missing attributes section"
assert "associations" in output.lower(), "Missing associations section"
print("   OK — entity detail shown")
for line in output.splitlines()[:8]:
    print(f"   {line}")

# 4. search — returns filtered results
print()
print("4. 'search Industry.Basic/Machine DAR'...")
r = run(["search", "Industry.Basic/Machine", "DAR"])
output = r.stdout
# May or may not find results depending on data — just check no crash
if "No instances" in output:
    print("   OK — no matches (clean message)")
else:
    assert "Search" in output or "rtId" in output.lower() or len(output.strip()) > 0, \
        "Unexpected output format"
    result_lines = [l for l in output.splitlines() if l.strip().startswith(("  ")) and not l.strip().startswith("...")]
    print(f"   OK — search returned results ({len(result_lines)} lines)")

# 5. filter — returns matching entities
print()
print("5. 'filter Industry.Basic/Machine name LIKE DAR'...")
r = run(["filter", "Industry.Basic/Machine", "name", "LIKE", "DAR"])
output = r.stdout
if "No instances" in output:
    print("   OK — no matches (clean message)")
else:
    assert "Filter" in output or len(output.strip()) > 0, "Unexpected output format"
    print("   OK — filter returned results")
    first_lines = output.strip().splitlines()[:4]
    for line in first_lines:
        print(f"   {line}")

# 6. query — returns tabular data
print()
print("6. 'query Industry.Basic/Machine --columns name,machineState --first 3'...")
r = run(["query", "Industry.Basic/Machine", "--columns", "name,machineState", "--first", "3"])
output = r.stdout
if "No results" in output:
    print("   OK — no results (clean message)")
else:
    assert "name" in output.lower(), "Missing column name in output"
    print("   OK — tabular query returned results")
    for line in output.strip().splitlines()[:6]:
        print(f"   {line}")

# 7. list --json — valid JSON output
print()
print("7. 'list Industry.Basic/Machine --json --first 1'...")
r = run(["list", "Industry.Basic/Machine", "--json", "--first", "1"])
data = json.loads(r.stdout)
assert "totalCount" in data, "Missing totalCount in JSON"
assert "entities" in data, "Missing entities in JSON"
print(f"   OK — valid JSON with totalCount={data['totalCount']}")

# 8. list NonExistent/Type — clean error, no traceback
print()
print("8. 'list NonExistent/Type' (error handling)...")
r = run(["list", "NonExistent/Type"], expect_fail=False)
# The API may return an empty result or an error — either is fine as long as no traceback
output = r.stdout + r.stderr
assert "Traceback" not in output, "Got unexpected traceback"
print("   OK — clean output, no traceback")

# 9. get with bogus rtId — clean error, no traceback
print()
print("9. 'get Industry.Basic/Machine 000000000000000000000000' (not found)...")
r = run(["get", "Industry.Basic/Machine", "000000000000000000000000"], expect_fail=True)
combined = r.stdout + r.stderr
assert "Traceback" not in combined, "Got unexpected traceback"
if r.returncode != 0:
    assert "not found" in combined.lower() or "error" in combined.lower(), \
        "Expected informative error message"
    print("   OK — clean error message, no traceback")
else:
    print("   OK — handled gracefully (no traceback)")

print()
print("=== rt_explorer.py: ALL CHECKS PASSED ===")
