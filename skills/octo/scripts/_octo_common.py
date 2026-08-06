"""Shared foundation for OctoMesh GraphQL exploration scripts.

Provides context loading, authentication, and GraphQL query execution
using the connection info from ~/.octo-cli/contexts.json.
"""
import json
import os
import sys
import requests


def load_context():
    """Read ~/.octo-cli/contexts.json and return the effective context as a dict.

    The effective context mirrors octo-cli's own resolution order so scripts and
    octo-cli agree on the same context without touching global state:
      1. the OCTO_CLI_CONTEXT environment variable, if set (octo-cli honors the
         same variable, and its `--context` flag is per-process — export the
         variable to make a whole session, scripts included, target one context);
      2. otherwise the persisted ActiveContext.
    Selecting via OCTO_CLI_CONTEXT never mutates the file, so parallel sessions
    pinned to different contexts do not race each other.

    Returns a dict with "OctoToolOptions" and "Authentication" keys,
    matching the structure expected by get_graphql_url() and get_token().
    Exits with a clear error if the file is missing, malformed, or the requested
    context is absent.
    """
    path = os.path.join(os.path.expanduser("~"), ".octo-cli", "contexts.json")
    if not os.path.isfile(path):
        print(f"Error: contexts file not found at {path}", file=sys.stderr)
        print("Run 'octo-cli -c AddContext -n <name> -isu <url> -asu <url> -tid <tenant>' to create a context,", file=sys.stderr)
        print("then authenticate with 'octo-cli -c LogIn -i --context <name>'.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse {path}: {e}", file=sys.stderr)
        sys.exit(1)

    contexts = config.get("Contexts", {})

    override = os.environ.get("OCTO_CLI_CONTEXT", "").strip()
    if override:
        selected_name, source = override, "OCTO_CLI_CONTEXT"
    else:
        selected_name, source = config.get("ActiveContext"), "active context"

    if not selected_name:
        print("Error: no context selected (no active context, OCTO_CLI_CONTEXT unset).", file=sys.stderr)
        print("Set OCTO_CLI_CONTEXT=<name>, or activate one with 'octo-cli -c UseContext -n <name>'.", file=sys.stderr)
        sys.exit(1)

    selected = contexts.get(selected_name)
    if not selected:
        print(f"Error: {source} '{selected_name}' not found in contexts.", file=sys.stderr)
        print("List available contexts with 'octo-cli -c ListContexts'.", file=sys.stderr)
        sys.exit(1)

    return {
        "OctoToolOptions": selected.get("OctoToolOptions", {}),
        "Authentication": selected.get("Authentication", {}),
    }


def get_graphql_url(context, tenant_override=None):
    """Build the GraphQL endpoint URL from the active context.

    Returns: https://{AssetServiceUrl}tenants/{TenantId}/GraphQL
    """
    opts = context["OctoToolOptions"]
    base = opts["AssetServiceUrl"].rstrip("/")
    tenant = tenant_override or opts["TenantId"]
    return f"{base}/tenants/{tenant}/GraphQL"


def get_token(context):
    """Extract the access token from the active context.

    Exits with error if missing or empty.
    """
    token = context.get("Authentication", {}).get("AccessToken")
    if not token:
        print("Error: no access token found in active context.", file=sys.stderr)
        print("Run 'octo-cli -c LogIn -i' to authenticate.", file=sys.stderr)
        sys.exit(1)
    return token


def graphql_query(context, query, variables=None, tenant_override=None, verify_ssl=True):
    """Execute a GraphQL query and return the 'data' dict.

    Handles HTTP errors, auth failures, GraphQL errors, and connection errors.
    Exits with actionable error messages on failure.

    Args:
        verify_ssl: If False, skip TLS certificate verification (for local dev
                    with self-signed certs). Also automatically disabled for
                    localhost URLs.
    """
    url = get_graphql_url(context, tenant_override)

    # Auto-disable SSL verification for localhost (self-signed certs)
    if verify_ssl and ("://localhost" in url or "://127.0.0.1" in url):
        verify_ssl = False

    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    token = get_token(context)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30, verify=verify_ssl)
    except requests.ConnectionError as e:
        if "SSL" in str(e) or "CERTIFICATE_VERIFY_FAILED" in str(e):
            print(f"Error: SSL certificate verification failed for {url}", file=sys.stderr)
            print("For local development with self-signed certs, use --insecure.", file=sys.stderr)
        else:
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
