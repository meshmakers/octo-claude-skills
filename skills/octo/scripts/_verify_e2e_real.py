"""Real end-to-end verification of Communication Controller CLI commands.

Requires a running OctoMesh environment with:
- At least one adapter online
- At least one deployed pipeline
- Valid authentication (octo-cli -c LogIn -i)
"""
import json
import subprocess
import sys


def run_cli(command, args, label):
    """Run an octo-cli command and return parsed output."""
    print(f"=== {label} ===")
    cmd = ["octo-cli", "-c", command] + args
    print(f"  CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
        if result.stderr:
            print(f"  STDERR: {result.stderr[:500]}")
        if result.stdout:
            print(f"  STDOUT: {result.stdout[:500]}")
        return None
    lines = result.stdout.strip().splitlines()
    for line in lines[:15]:
        print(f"  {line}")
    if len(lines) > 15:
        print(f"  ... ({len(lines) - 15} more lines)")
    print()
    return result


def extract_json(text):
    """Extract JSON from CLI output that may contain banner lines before the JSON."""
    # Try the full text first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Look for the first line starting with [ or { (the JSON payload)
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            json_text = "\n".join(text.splitlines()[i:])
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                continue
    return None


def run_cli_json(command, args, label):
    """Run an octo-cli command with --json and parse the JSON output."""
    result = run_cli(command, args + ["--json"], label)
    if result is None:
        return None
    data = extract_json(result.stdout)
    if data is None:
        print(f"  WARNING: Could not parse JSON output")
    return data


print("=" * 60)
print("  COMMUNICATION CONTROLLER E2E VERIFICATION")
print("=" * 60)
print()

passed = 0
failed = 0


def check(condition, description):
    global passed, failed
    if condition:
        print(f"  PASS: {description}")
        passed += 1
    else:
        print(f"  FAIL: {description}")
        failed += 1
    print()


# --- Step 1: List adapters ---
data = run_cli_json("GetAdapters", [], "Step 1: List adapters")
check(data is not None, "GetAdapters returns data")

adapter_id = None
if isinstance(data, list) and len(data) > 0:
    adapter_id = data[0].get("rtId") or data[0].get("RtId")
    check(True, f"At least one adapter found (rtId={adapter_id})")
elif isinstance(data, dict):
    # Might be wrapped in an object
    items = data.get("items") or data.get("Items") or []
    if items:
        adapter_id = items[0].get("rtId") or items[0].get("RtId")
        check(True, f"At least one adapter found (rtId={adapter_id})")
    else:
        check(False, "At least one adapter found")
else:
    check(False, "At least one adapter found")

# --- Step 2: Get pipeline schema ---
if adapter_id:
    result = run_cli("GetPipelineSchema", ["--adapterId", adapter_id], "Step 2: Get pipeline schema")
    if result and result.stdout:
        schema = extract_json(result.stdout)
        if schema and isinstance(schema, dict):
            has_defs = "$defs" in schema or "definitions" in schema
            check(has_defs, "Pipeline schema contains node definitions")
        else:
            check(False, "Pipeline schema is valid JSON")
    else:
        check(False, "GetPipelineSchema returns data")
else:
    print("  SKIP: Step 2 (no adapter found)")
    print()

# --- Step 3: Get adapter nodes ---
result = run_cli("GetAdapterNodes", [], "Step 3: Get adapter nodes")
check(result is not None and len(result.stdout.strip()) > 0, "GetAdapterNodes returns node list")

# --- Step 4: Find a pipeline and execute it ---
pipeline_id = None
# Use rt_explorer to find pipelines
scripts_dir = sys.path[0] or "."
rt_explorer = f"{scripts_dir}/rt_explorer.py"

print("=== Step 4a: Discover pipelines ===")
rt_result = subprocess.run(
    [sys.executable, rt_explorer, "list", "System.Communication/Pipeline", "--json", "--first", "1", "--insecure"],
    capture_output=True, text=True
)
if rt_result.returncode == 0 and rt_result.stdout.strip():
    try:
        pipelines = json.loads(rt_result.stdout)
        items = pipelines if isinstance(pipelines, list) else (
            pipelines.get("entities") or pipelines.get("items") or pipelines.get("Items") or []
        )
        if items:
            pipeline_id = items[0].get("rtId") or items[0].get("RtId")
            print(f"  Found pipeline rtId={pipeline_id}")
    except json.JSONDecodeError:
        print(f"  WARNING: Could not parse rt_explorer output")
else:
    if rt_result.returncode != 0:
        print(f"  rt_explorer failed (exit {rt_result.returncode}): {rt_result.stderr[:300]}")
print()

if pipeline_id:
    # Execute the pipeline
    result = run_cli("ExecutePipeline", ["--identifier", pipeline_id], "Step 4b: Execute pipeline")
    check(result is not None and result.returncode == 0, "ExecutePipeline succeeds")

    # Get execution history
    data = run_cli_json("GetPipelineExecutions", ["--identifier", pipeline_id], "Step 4c: Get pipeline executions")
    check(data is not None, "GetPipelineExecutions returns data")

    # Get latest execution
    data = run_cli_json("GetLatestPipelineExecution", ["--identifier", pipeline_id], "Step 4d: Get latest execution")
    check(data is not None, "GetLatestPipelineExecution returns data")

    # Check for debug points if execution has them
    if isinstance(data, dict):
        exec_id = data.get("Id") or data.get("id") or data.get("executionId") or data.get("ExecutionId")
        has_debug = data.get("HasDebugData") or data.get("hasDebugData")
        if exec_id and has_debug:
            data = run_cli_json(
                "GetPipelineDebugPoints",
                ["--identifier", pipeline_id, "--executionId", exec_id],
                "Step 4e: Get debug points"
            )
            check(data is not None, "GetPipelineDebugPoints returns data")
        else:
            print("  SKIP: Step 4e (no debug data on latest execution)")
            print()
    else:
        print("  SKIP: Step 4e (could not parse execution data)")
        print()
else:
    print("  SKIP: Steps 4b-4e (no pipeline found)")
    print()

# --- Step 5: Get data flow status ---
print("=== Step 5a: Discover data flows ===")
rt_result = subprocess.run(
    [sys.executable, rt_explorer, "list", "System.Communication/DataFlow", "--json", "--first", "1", "--insecure"],
    capture_output=True, text=True
)
dataflow_id = None
if rt_result.returncode == 0 and rt_result.stdout.strip():
    try:
        dataflows = json.loads(rt_result.stdout)
        items = dataflows if isinstance(dataflows, list) else (
            dataflows.get("entities") or dataflows.get("items") or dataflows.get("Items") or []
        )
        if items:
            dataflow_id = items[0].get("rtId") or items[0].get("RtId")
            print(f"  Found data flow rtId={dataflow_id}")
    except json.JSONDecodeError:
        print(f"  WARNING: Could not parse rt_explorer output")
else:
    if rt_result.returncode != 0:
        print(f"  rt_explorer failed (exit {rt_result.returncode}): {rt_result.stderr[:300]}")
print()

if dataflow_id:
    data = run_cli_json("GetDataFlowStatus", ["--identifier", dataflow_id], "Step 5b: Get data flow status")
    check(data is not None, "GetDataFlowStatus returns data")
else:
    print("  SKIP: Step 5b (no data flow found)")
    print()

# --- Step 6: Deploy/undeploy triggers ---
result = run_cli("DeployTriggers", [], "Step 6a: Deploy triggers")
check(result is not None and result.returncode == 0, "DeployTriggers succeeds")

result = run_cli("UndeployTriggers", [], "Step 6b: Undeploy triggers")
check(result is not None and result.returncode == 0, "UndeployTriggers succeeds")

# --- Summary ---
print("=" * 60)
total = passed + failed
print(f"  RESULTS: {passed}/{total} checks passed, {failed} failed")
if failed == 0:
    print("  ALL COMMUNICATION E2E CHECKS PASSED")
else:
    print("  SOME CHECKS FAILED — see output above")
print("=" * 60)

sys.exit(1 if failed > 0 else 0)
