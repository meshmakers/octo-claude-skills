"""Shared foundation for OctoMesh GraphQL exploration scripts.

Provides settings loading, authentication, and GraphQL query execution
using the connection info from ~/.octo-cli/contexts.json.
"""
import json
import os
import sys
import requests


def load_settings():
    """Read ~/.octo-cli/contexts.json and return the active context as a dict.

    Returns a dict with "OctoToolOptions" and "Authentication" keys,
    matching the structure expected by get_graphql_url() and get_token().
    Exits with a clear error if the file is missing, malformed, or has no active context.
    """
    path = os.path.join(os.path.expanduser("~"), ".octo-cli", "contexts.json")
    if not os.path.isfile(path):
        print(f"Error: contexts file not found at {path}", file=sys.stderr)
        print("Run 'octo-cli -c AddContext -n <name> -isu <url> -asu <url> -tid <tenant>' to create a context,", file=sys.stderr)
        print("then 'octo-cli -c UseContext -n <name>' and 'octo-cli -c LogIn -i' to authenticate.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse {path}: {e}", file=sys.stderr)
        sys.exit(1)

    active_name = config.get("ActiveContext")
    if not active_name:
        print("Error: no active context set.", file=sys.stderr)
        print("Run 'octo-cli -c UseContext -n <name>' to activate a context.", file=sys.stderr)
        sys.exit(1)

    contexts = config.get("Contexts", {})
    active = contexts.get(active_name)
    if not active:
        print(f"Error: active context '{active_name}' not found in contexts.", file=sys.stderr)
        print("Run 'octo-cli -c UseContext' to list available contexts.", file=sys.stderr)
        sys.exit(1)

    return {
        "OctoToolOptions": active.get("OctoToolOptions", {}),
        "Authentication": active.get("Authentication", {}),
    }


def get_graphql_url(settings, tenant_override=None):
    """Build the GraphQL endpoint URL from the active context.

    Returns: https://{AssetServiceUrl}tenants/{TenantId}/GraphQL
    """
    opts = settings["OctoToolOptions"]
    base = opts["AssetServiceUrl"].rstrip("/")
    tenant = tenant_override or opts["TenantId"]
    return f"{base}/tenants/{tenant}/GraphQL"


def get_token(settings):
    """Extract the access token from the active context.

    Exits with error if missing or empty.
    """
    token = settings.get("Authentication", {}).get("AccessToken")
    if not token:
        print("Error: no access token found in active context.", file=sys.stderr)
        print("Run 'octo-cli -c LogIn -i' to authenticate.", file=sys.stderr)
        sys.exit(1)
    return token


def graphql_query(settings, query, variables=None, tenant_override=None):
    """Execute a GraphQL query and return the 'data' dict.

    Handles HTTP errors, auth failures, GraphQL errors, and connection errors.
    Exits with actionable error messages on failure.
    """
    url = get_graphql_url(settings, tenant_override)
    token = get_token(settings)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.ConnectionError:
        print(f"Error: cannot connect to {url}", file=sys.stderr)
        print("Check your network and that the AssetServiceUrl is correct in the active context.", file=sys.stderr)
        sys.exit(1)
    except requests.Timeout:
        print(f"Error: request to {url} timed out.", file=sys.stderr)
        sys.exit(1)

    if resp.status_code in (401, 403):
        print(f"Error: authentication failed (HTTP {resp.status_code}).", file=sys.stderr)
        print("Your token may have expired. Run 'octo-cli -c LogIn -i' to re-authenticate.", file=sys.stderr)
        sys.exit(1)

    if resp.status_code != 200:
        print(f"Error: HTTP {resp.status_code} from {url}", file=sys.stderr)
        print(resp.text[:500], file=sys.stderr)
        sys.exit(1)

    body = resp.json()
    if "errors" in body:
        for err in body["errors"]:
            print(f"GraphQL error: {err.get('message', err)}", file=sys.stderr)
        if "data" not in body or body["data"] is None:
            sys.exit(1)

    return body["data"]


def collect_connection(connection):
    """Extract node list from a Relay-style connection (edges[].node).

    Returns an empty list if connection is None or has no edges.
    """
    if not connection or "edges" not in connection:
        return []
    return [edge["node"] for edge in connection["edges"] if edge.get("node")]
