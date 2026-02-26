"""Verification script for Step 3: ck_explorer.py."""
import subprocess
import sys
import json
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
EXPLORER = os.path.join(SCRIPTS, "ck_explorer.py")

print("=== Step 3 Verification: ck_explorer.py ===")
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

# 1. `models` lists known models
print("1. 'models' subcommand...")
r = run(["models"])
output = r.stdout
assert "System" in output, "Missing 'System' model"
assert "Basic" in output, "Missing 'Basic' model"
print("   OK — found System and Basic models")
# Count models
lines_with_state = [l for l in output.splitlines() if "state=" in l]
print(f"   Found {len(lines_with_state)} models")

# 2. `model` shows detail for a specific model
print()
print("2. 'model System-2.0.2' subcommand...")
r = run(["model", "System-2.0.2"])
output = r.stdout
assert "State:" in output, "Missing state info"
print("   OK — model detail shown")
print(f"   {[l.strip() for l in output.splitlines() if 'State:' in l][0]}")

# 3. `types` lists types
print()
print("3. 'types' subcommand...")
r = run(["types"])
output = r.stdout
assert "total" in output.lower() or "Types" in output, "Missing type listing"
print("   OK — types listed")
# Extract count from first line
first_line = output.strip().splitlines()[0]
print(f"   {first_line}")

# 4. `types --model` filters correctly
print()
print("4. 'types --model Industry.Manufacturing-2.0.0'...")
r = run(["types", "--model", "Industry.Manufacturing-2.0.0"])
output = r.stdout
assert "Industry.Manufacturing" in output, "Missing manufacturing types"
# Should not contain System types
lines = output.strip().splitlines()
type_lines = [l for l in lines if l.strip().startswith(("Production", "Partial", "Shift"))]
print(f"   OK — filtered to manufacturing types ({len(type_lines)} type lines found)")

# 5. `type` shows detail for a specific type
print()
print("5. 'type System-2.0.2/Entity-1'...")
r = run(["type", "System-2.0.2/Entity-1"])
output = r.stdout
assert "Abstract" in output, "Missing abstract flag"
print("   OK — type detail shown")
for line in output.splitlines()[:6]:
    print(f"   {line}")

# 6. `enums` lists all enums
print()
print("6. 'enums' subcommand...")
r = run(["enums"])
output = r.stdout
assert "Enums" in output, "Missing enum listing"
first_line = output.strip().splitlines()[0]
print(f"   OK — {first_line}")

# 7. `enum` shows values
print()
print("7. 'enum System-2.0.2/AggregationTypes-1'...")
r = run(["enum", "System-2.0.2/AggregationTypes-1"])
output = r.stdout
assert "Values" in output, "Missing values section"
print("   OK — enum detail shown")
for line in output.splitlines():
    if line.strip() and not line.startswith("Enum:"):
        print(f"   {line}")

# 8. `search` finds relevant results
print()
print("8. 'search Production'...")
r = run(["search", "Production"])
output = r.stdout
assert "Production" in output, "Missing Production results"
print("   OK — search results found")
for line in output.splitlines()[:6]:
    print(f"   {line}")

# 9. `--json` produces valid JSON
print()
print("9. '--json' flag check...")
r = run(["models", "--json"])
data = json.loads(r.stdout)
assert isinstance(data, list), "Expected JSON array"
print(f"   OK — valid JSON array with {len(data)} models")

# 10. Unknown model gives clean output
print()
print("10. Unknown model error handling...")
r = run(["model", "DoesNotExist-1.0.0"], expect_fail=True)
assert r.returncode != 0, "Expected non-zero exit code"
assert "Traceback" not in r.stderr and "Traceback" not in r.stdout, \
    "Got unexpected traceback"
combined = r.stderr + r.stdout
assert "no model found" in combined.lower() or "available" in combined.lower(), \
    "Expected informative message"
print("   OK — clean error message, no traceback")

print()
print("=== Step 3: ALL CHECKS PASSED ===")
