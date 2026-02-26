"""End-to-end integration test — Step 5.

Runs the full exploration workflow as a user would experience it.
"""
import subprocess
import sys
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
EXPLORER = os.path.join(SCRIPTS, "ck_explorer.py")
INTROSPECT = os.path.join(SCRIPTS, "gql_introspect.py")


def run(script, args, label):
    print(f"=== {label} ===")
    result = subprocess.run(
        [sys.executable, script] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAILED (exit {result.returncode})")
        print(result.stderr[:500])
        sys.exit(1)
    # Print first 15 lines of output
    lines = result.stdout.strip().splitlines()
    for line in lines[:15]:
        print(f"  {line}")
    if len(lines) > 15:
        print(f"  ... ({len(lines) - 15} more lines)")
    print()
    return result


print("=" * 60)
print("  END-TO-END INTEGRATION TEST")
print("=" * 60)
print()

# Step A: List models
r = run(EXPLORER, ["models"], "Step A: List models")
assert "System" in r.stdout

# Step B: Drill into a model
r = run(EXPLORER, ["model", "Industry.Manufacturing-2.0.0"], "Step B: Drill into a model")
assert "AVAILABLE" in r.stdout or "State:" in r.stdout

# Step C: List types in that model
r = run(EXPLORER, ["types", "--model", "Industry.Manufacturing-2.0.0"], "Step C: List types in model")
assert "ProductionOrder" in r.stdout

# Step D: Inspect a specific type
r = run(EXPLORER, ["type", "Industry.Manufacturing-2.0.0/ProductionOrder-1"], "Step D: Inspect a specific type")
assert "Attributes" in r.stdout or "attributes" in r.stdout.lower()

# Step E: List enums in that model
r = run(EXPLORER, ["enums", "--model", "Industry.Manufacturing-2.0.0"], "Step E: List enums in model")
# May or may not have enums in this model
print("  (enums listed or empty — both valid)")
print()

# Step F: Search across everything
r = run(EXPLORER, ["search", "Shift"], "Step F: Search for 'Shift'")
assert "Shift" in r.stdout

# Step G: Discover API via introspection
r = run(INTROSPECT, ["top"], "Step G: Introspect top-level fields")
assert "constructionKit" in r.stdout

r = run(INTROSPECT, ["type", "ConstructionKitQuery"], "Step H: Introspect ConstructionKitQuery")
assert "models" in r.stdout
assert "types" in r.stdout

print("=" * 60)
print("  ALL END-TO-END CHECKS PASSED")
print("=" * 60)
