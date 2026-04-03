"""End-to-end integration test -- full OctoMesh lifecycle.

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
    print("  PHASE 1: Create Tenant")
    print("=" * 60)
    # Convert hyphens to underscores for db name
    db_name = tenant_id.replace("-", "_")
    run_cli(
        ["-c", "Create", "-tid", tenant_id, "-db", db_name],
        "Create tenant",
    )
    print(f"  \u2713 Tenant '{tenant_id}' created (db: {db_name})")


# ---------------------------------------------------------------------------
# Phase 2: Enable Communication
# ---------------------------------------------------------------------------

def phase_2_enable_communication(tenant_id):
    """Enable communication on the tenant so adapters can connect."""
    print()
    print("=" * 60)
    print("  PHASE 2: Enable Communication")
    print("=" * 60)
    run_cli(
        ["-c", "EnableCommunication", "-tid", tenant_id],
        "Enable communication",
    )
    print(f"  \u2713 Communication enabled for tenant '{tenant_id}'")


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
        ["-c", "ImportCk", "-f", ck_file, "-w", "-tid", tenant_id],
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
