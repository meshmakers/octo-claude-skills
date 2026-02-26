"""GraphQL schema introspection for OctoMesh.

Safety valve for discovering field names when the schema evolves between
server versions. Uses standard GraphQL __schema/__type introspection.

Usage:
    python gql_introspect.py top [--json] [--tenant ID]
    python gql_introspect.py type <TypeName> [--json] [--tenant ID]
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _octo_common import load_settings, graphql_query


def cmd_top(settings, args):
    """Show top-level query fields."""
    query = """{ __schema { queryType { fields { name type { name kind ofType { name kind } } } } } }"""
    data = graphql_query(settings, query, tenant_override=args.tenant)
    fields = data["__schema"]["queryType"]["fields"]

    if args.json:
        print(json.dumps(fields, indent=2))
        return

    print("Top-level query fields:")
    print()
    for f in sorted(fields, key=lambda x: x["name"]):
        t = f["type"]
        tname = t.get("name") or (t.get("ofType", {}).get("name") if t.get("ofType") else None) or "?"
        print(f"  {f['name']:40s} -> {tname}")


def cmd_type(settings, args):
    """Show fields of a specific GraphQL type."""
    query = """{
        __type(name: "%s") {
            name
            kind
            description
            fields {
                name
                type { name kind ofType { name kind ofType { name kind } } }
            }
            enumValues { name description }
        }
    }""" % args.type_name

    data = graphql_query(settings, query, tenant_override=args.tenant)
    t = data.get("__type")

    if not t:
        print(f"Type '{args.type_name}' not found in the GraphQL schema.", file=sys.stderr)
        print("Use 'gql_introspect.py top' to see available top-level fields,", file=sys.stderr)
        print("or check the type name spelling (types are case-sensitive).", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(t, indent=2))
        return

    print(f"Type: {t['name']}  (kind: {t['kind']})")
    if t.get("description"):
        print(f"Description: {t['description']}")
    print()

    if t.get("fields"):
        print("Fields:")
        for f in t["fields"]:
            ft = f["type"]
            tname = _format_type(ft)
            print(f"  {f['name']:40s} -> {tname}")

    if t.get("enumValues"):
        print("Enum values:")
        for v in t["enumValues"]:
            desc = f"  ({v['description']})" if v.get("description") else ""
            print(f"  {v['name']}{desc}")


def _format_type(t):
    """Format a GraphQL type reference for display."""
    if t.get("name"):
        return t["name"]
    kind = t.get("kind", "")
    inner = t.get("ofType", {})
    if kind == "NON_NULL":
        return _format_type(inner) + "!"
    if kind == "LIST":
        return f"[{_format_type(inner)}]"
    return inner.get("name") or "?"


def main():
    parser = argparse.ArgumentParser(description="OctoMesh GraphQL schema introspection")

    sub = parser.add_subparsers(dest="command")

    top_cmd = sub.add_parser("top", help="Show top-level query fields")
    top_cmd.add_argument("--json", action="store_true", help="Output raw JSON")
    top_cmd.add_argument("--tenant", type=str, default=None, help="Override tenant ID")

    type_cmd = sub.add_parser("type", help="Show fields of a GraphQL type")
    type_cmd.add_argument("type_name", help="GraphQL type name (case-sensitive)")
    type_cmd.add_argument("--json", action="store_true", help="Output raw JSON")
    type_cmd.add_argument("--tenant", type=str, default=None, help="Override tenant ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    settings = load_settings()

    if args.command == "top":
        cmd_top(settings, args)
    elif args.command == "type":
        cmd_type(settings, args)


if __name__ == "__main__":
    main()
