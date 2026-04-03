"""Data layer integration test -- CK import, RT import, and query validation.

Creates a fresh tenant, imports a custom CK model, seeds entity data,
attempts pipeline-driven simulation, and validates via 6 query types.

Usage:
    bash skills/octo/scripts/run_python.sh skills/octo/scripts/_verify_e2e_full.py
"""
import json
import os
import subprocess
import sys
import time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(SCRIPTS, "e2e_fixtures")
RT_EXPLORER = os.path.join(SCRIPTS, "rt_explorer.py")

sys.path.insert(0, SCRIPTS)
from _octo_common import load_settings, graphql_query, get_graphql_url, get_token


def get_context_info():
    """Read the active context name, service URLs, and auth from ~/.octo-cli/contexts.json."""
    import json as _json
    path = os.path.join(os.path.expanduser("~"), ".octo-cli", "contexts.json")
    with open(path) as f:
        config = _json.load(f)
    active_name = config.get("ActiveContext", "default")
    active = config.get("Contexts", {}).get(active_name, {})
    opts = active.get("OctoToolOptions", {})
    auth = active.get("Authentication", {})
    return {
        "active_context": active_name,
        "identity_url": opts.get("IdentityServiceUrl", ""),
        "asset_url": opts.get("AssetServiceUrl", ""),
        "bot_url": opts.get("BotServiceUrl", ""),
        "comm_url": opts.get("CommunicationServiceUrl", ""),
        "reporting_url": opts.get("ReportingServiceUrl", ""),
        "auth": auth,
    }


def create_e2e_context(context_name, tenant_id, source_ctx):
    """Create a CLI context for the e2e test by cloning the source context with a new tenant ID.

    Uses direct file manipulation because AddContext doesn't copy auth tokens.
    """
    import json as _json
    path = os.path.join(os.path.expanduser("~"), ".octo-cli", "contexts.json")
    with open(path) as f:
        config = _json.load(f)

    # Clone the source context's options with the new tenant ID
    source = config["Contexts"][source_ctx["active_context"]]
    new_opts = dict(source.get("OctoToolOptions", {}))
    new_opts["TenantId"] = tenant_id

    config["Contexts"][context_name] = {
        "OctoToolOptions": new_opts,
        "Authentication": dict(source.get("Authentication", {})),
    }
    config["ActiveContext"] = context_name

    with open(path, "w") as f:
        _json.dump(config, f, indent=2)



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def timestamp_id():
    """Generate a unique tenant ID based on the current time."""
    return time.strftime("e2etest-%Y%m%d-%H%M%S")


def run_cli(args, label, check=True):
    """Run an octo-cli command and print output.

    Runs ["octo-cli"] + args with a 120-second timeout.
    Prints the first 10 lines of combined stdout/stderr.
    If *check* is True, exits on non-zero return code.
    Returns the CompletedProcess.
    """
    print(f"  Running: octo-cli {' '.join(args)}")
    result = subprocess.run(
        ["octo-cli"] + args,
        capture_output=True, text=True, timeout=120,
    )
    output = (result.stdout or "") + (result.stderr or "")
    lines = output.strip().splitlines()
    for line in lines[:10]:
        print(f"    {line}")
    if len(lines) > 10:
        print(f"    ... ({len(lines) - 10} more lines)")
    if check and result.returncode != 0:
        print(f"  FAILED: {label} (exit {result.returncode})")
        sys.exit(1)
    return result


def run_rt_explorer(args, tenant_id, label, check=True):
    """Run rt_explorer.py with --tenant and --json flags.

    Runs with a 30-second timeout.
    If *check* is True, exits on non-zero return code.
    Returns the CompletedProcess.
    """
    full_args = [sys.executable, RT_EXPLORER] + args + ["--tenant", tenant_id, "--json"]
    print(f"  Running: rt_explorer.py {' '.join(args)} --tenant {tenant_id} --json")
    result = subprocess.run(
        full_args,
        capture_output=True, text=True, timeout=30,
    )
    if check and result.returncode != 0:
        output = (result.stdout or "") + (result.stderr or "")
        lines = output.strip().splitlines()
        for line in lines[:10]:
            print(f"    {line}")
        print(f"  FAILED: {label} (exit {result.returncode})")
        sys.exit(1)
    return result


def assert_true(condition, message):
    """Exit with an error message if condition is false."""
    if not condition:
        print(f"  ASSERTION FAILED: {message}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Phase 1: Create Tenant
# ---------------------------------------------------------------------------

def phase_1_create_tenant(tenant_id):
    """Create a fresh tenant for the E2E test."""
    print()
    print("=" * 60)
    print(f"  Phase 1: Create Tenant '{tenant_id}'")
    print("=" * 60)

    # Read current context info for service URLs and auth
    ctx = get_context_info()

    # Convert hyphens to underscores for db name
    db_name = tenant_id.replace("-", "_")
    run_cli(
        ["-c", "Create", "-tid", tenant_id, "-db", db_name],
        "Create tenant",
    )

    # Create a temporary CLI context with the new tenant ID and service URLs.
    # We only copy URLs (not auth tokens) since a fresh login is required.
    context_name = f"e2e-{tenant_id}"
    create_e2e_context(context_name, tenant_id, ctx)

    print(f"  \u2713 Tenant '{tenant_id}' created (db: {db_name})")
    print(f"  \u2713 CLI context '{context_name}' active")
    print()
    print("  ──────────────────────────────────────────────────")
    print("  LOGIN REQUIRED: Please complete the login flow below.")
    print("  A browser window will open — authorize, then the test continues.")
    print("  ──────────────────────────────────────────────────")
    print()

    # Run login with -i flag to auto-open browser for device code flow.
    # stdout/stderr go directly to terminal so the user can see status.
    # Timeout is 5 minutes to give the user time to complete the browser flow.
    login_result = subprocess.run(
        ["octo-cli", "-c", "LogIn", "-i"],
        timeout=300,
    )
    assert_true(login_result.returncode == 0, "Login failed — cannot continue")
    print()
    print(f"  \u2713 Logged in to context '{context_name}'")


# ---------------------------------------------------------------------------
# Phase 2: Enable Communication
# ---------------------------------------------------------------------------

def phase_2_enable_communication(tenant_id):
    """Enable communication on the tenant so adapters can connect.

    Non-fatal: if this fails (e.g. Forbidden), the test continues
    with the fallback sensor import path instead of pipeline execution.
    """
    print()
    print("=" * 60)
    print("  Phase 2: Enable Communication")
    print("=" * 60)
    result = run_cli(
        ["-c", "EnableCommunication"],
        "Enable communication",
        check=False,
    )
    if result.returncode == 0:
        print(f"  \u2713 Communication enabled for tenant '{tenant_id}'")
    else:
        print(f"  \u26a0 EnableCommunication failed (non-fatal) — pipeline trigger will be skipped")


# ---------------------------------------------------------------------------
# Phase 3: Import CK Model
# ---------------------------------------------------------------------------

def phase_3_import_ck_model(tenant_id):
    """Import the E2E test CK model and verify it appears in the tenant."""
    print()
    print("=" * 60)
    print("  PHASE 3: Import CK Model")
    print("=" * 60)
    ck_file = os.path.join(FIXTURES, "e2e-ck-model.yaml")
    assert_true(os.path.isfile(ck_file), f"CK model file not found: {ck_file}")
    run_cli(
        ["-c", "ImportCk", "-f", ck_file, "-w"],
        "Import CK model",
    )

    # Verify via GraphQL that E2ETest model was imported
    settings = load_settings()
    query = """
    query {
      constructionKit {
        models {
          items { id { fullName } }
        }
      }
    }"""
    data = graphql_query(settings, query, tenant_override=tenant_id)
    models = data.get("constructionKit", {}).get("models", {}).get("items", [])
    model_names = [m["id"]["fullName"] for m in models]
    assert_true(
        any("E2ETest" in n for n in model_names),
        f"E2ETest model not found in imported models: {model_names}",
    )
    print(f"  \u2713 CK model imported and verified (found E2ETest in {len(model_names)} models)")


# ===================================================================
# Phase 4: Import Seed Data
# ===================================================================
def phase_4_import_seed_data(tenant_id):
    print()
    print("=" * 60)
    print("  Phase 4: Import Seed Data")
    print("=" * 60)

    seed_file = os.path.join(FIXTURES, "e2e-rt-seed.yaml")
    assert_true(os.path.isfile(seed_file), f"Seed file not found: {seed_file}")

    run_cli(["-c", "ImportRt", "-f", seed_file, "-r", "-w"], "Import seed data")

    # Verify plant exists
    r = run_rt_explorer(["count", "E2ETest/Plant"], tenant_id, "Count plants")
    data = json.loads(r.stdout)
    assert_true(data["totalCount"] == 1, f"Expected 1 plant, got {data['totalCount']}")

    # Verify areas exist
    r = run_rt_explorer(["count", "E2ETest/Area"], tenant_id, "Count areas")
    data = json.loads(r.stdout)
    assert_true(data["totalCount"] == 2, f"Expected 2 areas, got {data['totalCount']}")

    print("  \u2713 Seed data imported: 1 Plant, 2 Areas")


# ===================================================================
# Phase 5: Create Sensors (pipeline trigger or fallback import)
# ===================================================================
def phase_5_create_sensors(tenant_id):
    print()
    print("=" * 60)
    print("  Phase 5: Create Sensors")
    print("=" * 60)

    # Try importing pipeline infrastructure first
    pipeline_file = os.path.join(FIXTURES, "e2e-rt-pipeline.yaml")
    if os.path.isfile(pipeline_file):
        print("  Importing pipeline infrastructure...")
        result = run_cli(
            ["-c", "ImportRt", "-f", pipeline_file, "-r", "-w"],
            "Import pipeline", check=False
        )
        if result.returncode == 0:
            print("  \u2713 Pipeline entities imported")
            # Give the adapter a moment to pick up the pipeline
            print("  Waiting 5s for adapter to register pipeline...")
            time.sleep(5)

            # Check if sensors were created by the pipeline
            r = run_rt_explorer(["count", "E2ETest/Sensor"], tenant_id, "Count sensors", check=False)
            if r.returncode == 0:
                data = json.loads(r.stdout)
                if data["totalCount"] >= 10:
                    print(f"  \u2713 Pipeline created {data['totalCount']} sensors")
                    return "pipeline"

        print("  Pipeline did not produce sensors \u2014 using fallback import")

    # Fallback: import pre-built sensor entities
    sensors_file = os.path.join(FIXTURES, "e2e-rt-sensors.yaml")
    assert_true(os.path.isfile(sensors_file), f"Sensors file not found: {sensors_file}")

    run_cli(["-c", "ImportRt", "-f", sensors_file, "-r", "-w"], "Import sensors (fallback)")

    # Verify sensors were created
    r = run_rt_explorer(["count", "E2ETest/Sensor"], tenant_id, "Count sensors")
    data = json.loads(r.stdout)
    assert_true(data["totalCount"] == 10, f"Expected 10 sensors, got {data['totalCount']}")

    print(f"  \u2713 Fallback import: {data['totalCount']} sensors created")
    return "fallback"


# ===================================================================
# Phase 6: Query & Assert
# ===================================================================
def phase_6_query_and_assert(tenant_id):
    print()
    print("=" * 60)
    print("  Phase 6: Query & Assert")
    print("=" * 60)

    passed = 0
    total = 6

    # --- Test 1: Count sensors ---
    print()
    print("  [1/6] Count sensors...")
    r = run_rt_explorer(["count", "E2ETest/Sensor"], tenant_id, "Count sensors")
    data = json.loads(r.stdout)
    assert_true(data["totalCount"] == 10, f"Expected 10 sensors, got {data['totalCount']}")
    print(f"  \u2713 [1/6] Sensor count: {data['totalCount']} (expected 10)")
    passed += 1

    # --- Test 2: List with attributes ---
    print()
    print("  [2/6] List sensors with attributes...")
    r = run_rt_explorer(["list", "E2ETest/Sensor", "--attrs", "--first", "10"], tenant_id, "List sensors")
    data = json.loads(r.stdout)
    entities = data.get("entities", [])
    assert_true(len(entities) == 10, f"Expected 10 entities in list, got {len(entities)}")
    for e in entities:
        # Attribute names come back lowercased from the GraphQL API
        attrs = {item["attributeName"].lower(): item.get("value") for item in (e.get("attributes") or {}).get("items", [])}
        assert_true("temperature" in attrs, f"Entity {e.get('rtId')} missing temperature attribute. Has: {sorted(attrs.keys())}")
        assert_true("humidity" in attrs, f"Entity {e.get('rtId')} missing humidity attribute. Has: {sorted(attrs.keys())}")
        assert_true("pressure" in attrs, f"Entity {e.get('rtId')} missing pressure attribute. Has: {sorted(attrs.keys())}")
    print("  \u2713 [2/6] All 10 sensors have Temperature, Humidity, Pressure attributes")
    passed += 1

    # --- Test 3: Filter by attribute ---
    print()
    print("  [3/6] Filter sensors by Temperature > 50...")
    r = run_rt_explorer(
        ["filter", "E2ETest/Sensor", "temperature", "GREATER_THAN", "50"],
        tenant_id, "Filter sensors"
    )
    data = json.loads(r.stdout)
    filtered_count = data.get("totalCount", 0)
    assert_true(0 < filtered_count <= 10, f"Expected 1-10 filtered sensors, got {filtered_count}")
    print(f"  \u2713 [3/6] Filter Temperature > 50: {filtered_count} sensors matched")
    passed += 1

    # --- Test 4: Transient query ---
    print()
    print("  [4/6] Transient query (Name, Temperature, Humidity)...")
    r = run_rt_explorer(
        ["query", "E2ETest/Sensor", "--columns", "name,temperature,humidity", "--first", "10"],
        tenant_id, "Transient query"
    )
    data = json.loads(r.stdout)
    items = data.get("items", [])
    assert_true(len(items) > 0, "Transient query returned no items")
    columns = items[0].get("columns", [])
    col_paths = [c.get("attributePath", "") for c in columns]
    col_paths_lower = [p.lower() for p in col_paths]
    assert_true("name" in col_paths_lower, f"Missing 'name' column in {col_paths}")
    assert_true("temperature" in col_paths_lower, f"Missing 'temperature' column in {col_paths}")
    rows = (items[0].get("rows") or {}).get("items") or []
    assert_true(len(rows) == 10, f"Expected 10 rows, got {len(rows)}")
    print(f"  \u2713 [4/6] Transient query: {len(col_paths)} columns \u00d7 {len(rows)} rows")
    passed += 1

    # --- Test 5: Association traversal ---
    # Note: Sensors link outbound TO Areas (AreaSensor role), so from the Area's
    # perspective these are INBOUND associations. rt_explorer.py 'get' only shows
    # outbound, so we use a direct GraphQL query with direction: INBOUND.
    print()
    print("  [5/6] Association traversal (Plant \u2192 Areas \u2192 Sensors)...")
    settings = load_settings()

    # Step A: Get plant's OUTBOUND associations -> should find 2 Areas
    r = run_rt_explorer(["get", "E2ETest/Plant", "aaa000000000000000000001"], tenant_id, "Get plant")
    plant = json.loads(r.stdout)
    assoc_defs = (plant.get("associations") or {}).get("definitions") or {}
    assoc_items = assoc_defs.get("items") or []
    area_assocs = [a for a in assoc_items if a.get("targetCkTypeId", "").endswith("/Area")]
    assert_true(len(area_assocs) == 2, f"Expected 2 area associations, got {len(area_assocs)}")

    # Step B: For each area, query INBOUND associations to find sensors
    Q_INBOUND_ASSOC = """
    query($ckId: String!, $rtId: OctoObjectId!) {
      runtime {
        runtimeEntities(ckId: $ckId, rtId: $rtId, first: 1) {
          edges { node {
            rtId
            associations { definitions(direction: INBOUND) {
              items { ckAssociationRoleId targetRtId targetCkTypeId }
            } }
          } }
        }
      }
    }"""

    total_sensors_via_assoc = 0
    for area_assoc in area_assocs:
        area_rtId = area_assoc["targetRtId"]
        data = graphql_query(
            settings, Q_INBOUND_ASSOC,
            variables={"ckId": "E2ETest/Area", "rtId": area_rtId},
            tenant_override=tenant_id
        )
        entities = data.get("runtime", {}).get("runtimeEntities", {}).get("edges", [])
        if entities:
            node = entities[0]["node"]
            inbound_defs = (node.get("associations") or {}).get("definitions") or {}
            inbound_items = inbound_defs.get("items") or []
            # For INBOUND direction, targetCkTypeId refers to the association's defined
            # target (the Area), not the source entity (the Sensor). Filter by role instead.
            sensor_assocs = [a for a in inbound_items if "AreaSensor" in a.get("ckAssociationRoleId", "")]
            total_sensors_via_assoc += len(sensor_assocs)

    assert_true(
        total_sensors_via_assoc == 10,
        f"Expected 10 sensors via association traversal, got {total_sensors_via_assoc}"
    )
    print(f"  \u2713 [5/6] Association traversal: Plant \u2192 2 Areas \u2192 {total_sensors_via_assoc} Sensors")
    passed += 1

    # --- Test 6: Search ---
    print()
    print("  [6/6] Search sensors by name...")
    r = run_rt_explorer(
        ["search", "E2ETest/Sensor", "Sensor", "--attr", "name"],
        tenant_id, "Search sensors"
    )
    data = json.loads(r.stdout)
    search_count = data.get("totalCount", 0)
    assert_true(search_count > 0, f"Search for 'Sensor' returned 0 results")
    print(f"  \u2713 [6/6] Search 'Sensor': {search_count} results")
    passed += 1

    print()
    print(f"  All {passed}/{total} query assertions passed")
    return passed, total


def _restore_context(original_context):
    """Restore the original CLI context by updating contexts.json directly."""
    import json as _json
    path = os.path.join(os.path.expanduser("~"), ".octo-cli", "contexts.json")
    try:
        with open(path) as f:
            config = _json.load(f)
        config["ActiveContext"] = original_context
        with open(path, "w") as f:
            _json.dump(config, f, indent=2)
        print(f"  CLI context restored to '{original_context}'")
    except Exception as e:
        print(f"  Warning: could not restore context: {e}", file=sys.stderr)


# ===================================================================
# Main
# ===================================================================
def main():
    print("=" * 60)
    print("  E2E INTEGRATION TEST \u2014 Full OctoMesh Lifecycle")
    print("=" * 60)

    # Check prerequisites
    settings = load_settings()
    print(f"  Active context loaded")

    # Save original context name for restoration
    ctx = get_context_info()
    original_context = ctx["active_context"]

    # Safety check: don't run from a previous e2e context
    if original_context.startswith("e2e-"):
        print(f"  WARNING: Active context '{original_context}' looks like a leftover e2e context.")
        print(f"  Run 'octo-cli -c UseContext -n local_meshtest' first to restore your normal context.")
        sys.exit(1)

    tenant_id = timestamp_id()
    print(f"  Tenant ID: {tenant_id}")

    try:
        phase_1_create_tenant(tenant_id)
        phase_2_enable_communication(tenant_id)
        phase_3_import_ck_model(tenant_id)
        phase_4_import_seed_data(tenant_id)
        sensor_source = phase_5_create_sensors(tenant_id)
        passed, total = phase_6_query_and_assert(tenant_id)
    except SystemExit:
        print()
        print("=" * 60)
        print(f"  E2E TEST FAILED \u2014 tenant '{tenant_id}' left for inspection")
        print("=" * 60)
        _restore_context(original_context)
        sys.exit(1)

    _restore_context(original_context)

    print()
    print("=" * 60)
    print(f"  ALL 6 PHASES PASSED")
    print(f"  Tenant: {tenant_id}")
    print(f"  Sensors created via: {sensor_source}")
    print(f"  Queries: {passed}/{total} passed")
    print("=" * 60)


if __name__ == "__main__":
    main()
