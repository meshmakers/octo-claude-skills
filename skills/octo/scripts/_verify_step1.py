"""Verification script for Step 1: _octo_common.py shared foundation."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Step 1 Verification: _octo_common.py ===")
print()

# 1. Module imports without errors
print("1. Import check...")
from _octo_common import load_settings, get_graphql_url, get_token, graphql_query, collect_connection
print("   All functions imported OK")

# 2. Settings load correctly
print()
print("2. Settings load check...")
s = load_settings()
print(f"   TenantId: {s['OctoToolOptions']['TenantId']}")
print(f"   AssetUrl: {s['OctoToolOptions']['AssetServiceUrl']}")

# 3. GraphQL URL builds correctly
print()
print("3. GraphQL URL check...")
url = get_graphql_url(s)
print(f"   URL: {url}")

# 4. Live GraphQL query works
print()
print("4. Live GraphQL query check...")
r = graphql_query(s, "{ __schema { queryType { name } } }")
print(f"   Query type: {r['__schema']['queryType']['name']}")

# 5. collect_connection works
print()
print("5. collect_connection check...")
test_conn = {"edges": [{"node": {"a": 1}}, {"node": {"a": 2}}]}
result = collect_connection(test_conn)
assert len(result) == 2, f"Expected 2, got {len(result)}"
assert result[0]["a"] == 1
print(f"   Extracted {len(result)} nodes from test connection OK")
# Edge case: None input
assert collect_connection(None) == []
print("   None input returns [] OK")

print()
print("=== Step 1: ALL CHECKS PASSED ===")
