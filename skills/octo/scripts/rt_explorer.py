"""Runtime instance explorer for OctoMesh.

Explore runtime entities (instances of CK types) via the GraphQL runtime API.

Usage:
    python rt_explorer.py list <ckId> [--attrs] [--sort attr:asc|desc] [--first N] [--json] [--tenant ID]
    python rt_explorer.py get <ckId> <rtId> [--json] [--tenant ID]
    python rt_explorer.py count <ckId> [--json] [--tenant ID]
    python rt_explorer.py search <ckId> <term> [--attr name] [--sort attr:asc|desc] [--first N] [--json] [--tenant ID]
    python rt_explorer.py query <ckId> --columns c1,c2 [--sort attr:asc|desc] [--first N] [--json] [--tenant ID]
    python rt_explorer.py filter <ckId> <attr> <op> <val> [--sort attr:asc|desc] [--first N] [--json] [--tenant ID]
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _octo_common import load_settings, graphql_query, collect_connection


# ---------------------------------------------------------------------------
# Filter operators accepted by the runtime API
# ---------------------------------------------------------------------------

FILTER_OPERATORS = [
    "EQUALS", "NOT_EQUALS",
    "LESS_THAN", "LESS_EQUAL_THAN",
    "GREATER_THAN", "GREATER_EQUAL_THAN",
    "IN", "NOT_IN",
    "LIKE", "MATCH_REG_EX",
    "ANY_EQ", "ANY_LIKE",
]


# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

Q_LIST_COMPACT = """
query($ckId: String!, $first: Int, $after: String, $sortOrder: [Sort]) {
  runtime {
    runtimeEntities(ckId: $ckId, first: $first, after: $after, sortOrder: $sortOrder) {
      totalCount
      pageInfo { hasNextPage endCursor }
      edges { node { rtId ckTypeId rtWellKnownName } }
    }
  }
}"""

Q_LIST = """
query($ckId: String!, $first: Int, $after: String, $sortOrder: [Sort]) {
  runtime {
    runtimeEntities(ckId: $ckId, first: $first, after: $after, sortOrder: $sortOrder) {
      totalCount
      pageInfo { hasNextPage endCursor }
      edges { node {
        rtId ckTypeId rtWellKnownName
        attributes { items { attributeName value } }
      } }
    }
  }
}"""

Q_GET = """
query($ckId: String!, $rtId: OctoObjectId!) {
  runtime {
    runtimeEntities(ckId: $ckId, rtId: $rtId, first: 1) {
      edges { node {
        rtId ckTypeId rtWellKnownName rtCreationDateTime rtChangedDateTime rtVersion
        attributes { items { attributeName value } }
        associations { definitions(direction: OUTBOUND) {
          items { ckAssociationRoleId targetRtId targetCkTypeId }
        } }
      } }
    }
  }
}"""

Q_COUNT = """
query($ckId: String!) {
  runtime {
    runtimeEntities(ckId: $ckId) { totalCount }
  }
}"""

Q_SEARCH = """
query($ckId: String!, $first: Int, $after: String, $sortOrder: [Sort], $fieldFilter: [FieldFilter]) {
  runtime {
    runtimeEntities(ckId: $ckId, first: $first, after: $after, sortOrder: $sortOrder, fieldFilter: $fieldFilter) {
      totalCount
      pageInfo { hasNextPage endCursor }
      edges { node {
        rtId ckTypeId rtWellKnownName
        attributes { items { attributeName value } }
      } }
    }
  }
}"""

Q_FILTER = """
query($ckId: String!, $first: Int, $after: String, $sortOrder: [Sort], $fieldFilter: [FieldFilter]) {
  runtime {
    runtimeEntities(ckId: $ckId, first: $first, after: $after, sortOrder: $sortOrder, fieldFilter: $fieldFilter) {
      totalCount
      pageInfo { hasNextPage endCursor }
      edges { node {
        rtId ckTypeId rtWellKnownName
        attributes { items { attributeName value } }
      } }
    }
  }
}"""

Q_QUERY = """
query($ckId: String!, $columnPaths: [String!]!, $first: Int, $sortOrder: [Sort], $fieldFilter: [FieldFilter]) {
  runtime {
    transientQuery {
      simple(ckId: $ckId, columnPaths: $columnPaths, first: $first, sortOrder: $sortOrder, fieldFilter: $fieldFilter) {
        totalCount
        items {
          columns { attributePath attributeValueType }
          rows { items { cells { items { attributePath value } } } }
        }
      }
    }
  }
}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_sort(sort_str):
    """Parse 'name:desc' into [{"attributePath": "name", "sortOrder": "DESCENDING"}].

    Accepts 'attr:asc', 'attr:desc', or just 'attr' (defaults to ascending).
    """
    if not sort_str:
        return None
    parts = sort_str.split(":", 1)
    attr = parts[0]
    direction = "DESCENDING" if len(parts) > 1 and parts[1].lower().startswith("desc") else "ASCENDING"
    return [{"attributePath": attr, "sortOrder": direction}]


def _attrs_to_dict(items):
    """Convert [{attributeName, value}, ...] to {name: value}."""
    if not items:
        return {}
    return {item["attributeName"]: item.get("value") for item in items}


def _display_name(entity):
    """Prefer rtWellKnownName, fallback to rtId."""
    return entity.get("rtWellKnownName") or entity.get("rtId") or "?"


def _coerce_value(value_str):
    """Parse CLI string to int/float/bool/string for SimpleScalar comparisons."""
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    return value_str


def _format_attr_value(value, max_len=80):
    """Truncate long attribute values for display."""
    if value is None:
        return "(null)"
    s = str(value)
    if len(s) > max_len:
        return s[:max_len - 3] + "..."
    return s


def _build_field_filter(attribute, operator, value):
    """Build a fieldFilter variable for the runtime API."""
    return [{"attributePath": attribute, "operator": operator, "comparisonValue": value}]


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_list(settings, args):
    query = Q_LIST if args.attrs else Q_LIST_COMPACT
    variables = {"ckId": args.ckId, "first": args.first or 50}
    sort = _parse_sort(args.sort)
    if sort:
        variables["sortOrder"] = sort

    data = graphql_query(settings, query, variables=variables, tenant_override=args.tenant)
    conn = data["runtime"]["runtimeEntities"]
    total = conn.get("totalCount", "?")
    entities = collect_connection(conn)

    if args.json:
        print(json.dumps({"totalCount": total, "entities": entities}, indent=2))
        return

    if not entities:
        print(f"No instances of '{args.ckId}' found.")
        return

    showing = len(entities)
    print(f"Instances of {args.ckId} ({showing} shown, {total} total):")
    print()

    for e in entities:
        name = _display_name(e)
        rtId = e.get("rtId", "?")
        if args.attrs:
            attrs = _attrs_to_dict((e.get("attributes") or {}).get("items"))
            print(f"  {rtId}  {name}")
            for k, v in attrs.items():
                print(f"    {k:35s} = {_format_attr_value(v)}")
            print()
        else:
            print(f"  {rtId}  {name}")

    page = conn.get("pageInfo", {})
    if page.get("hasNextPage"):
        print()
        print(f"  ... more results available (use --first {(args.first or 50) * 2} to see more)")


def cmd_get(settings, args):
    variables = {"ckId": args.ckId, "rtId": args.rtId}

    data = graphql_query(settings, Q_GET, variables=variables, tenant_override=args.tenant)
    entities = collect_connection(data["runtime"]["runtimeEntities"])

    if not entities:
        print(f"Entity not found: ckId={args.ckId} rtId={args.rtId}", file=sys.stderr)
        sys.exit(1)

    entity = entities[0]

    if args.json:
        print(json.dumps(entity, indent=2))
        return

    print(f"Entity: {_display_name(entity)}")
    print(f"  rtId:      {entity.get('rtId', '?')}")
    print(f"  ckTypeId:  {entity.get('ckTypeId', '?')}")
    print(f"  created:   {entity.get('rtCreationDateTime', '?')}")
    print(f"  changed:   {entity.get('rtChangedDateTime', '?')}")
    print(f"  version:   {entity.get('rtVersion', '?')}")

    # Attributes
    attrs = _attrs_to_dict((entity.get("attributes") or {}).get("items"))
    if attrs:
        print(f"\n  Attributes ({len(attrs)}):")
        for k, v in attrs.items():
            print(f"    {k:35s} = {_format_attr_value(v)}")
    else:
        print("\n  Attributes: none")

    # Association definitions (outbound only)
    assoc_defs = (entity.get("associations") or {}).get("definitions") or {}
    assoc_items = assoc_defs.get("items") or []
    if assoc_items:
        print(f"\n  Outbound associations ({len(assoc_items)}):")
        for a in assoc_items:
            role = a.get("ckAssociationRoleId", "?")
            target_rt = a.get("targetRtId", "?")
            target_ck = a.get("targetCkTypeId", "?")
            print(f"    -> {target_ck}  rtId={target_rt}  (role: {role})")
    else:
        print("\n  Outbound associations: none")


def cmd_count(settings, args):
    variables = {"ckId": args.ckId}

    data = graphql_query(settings, Q_COUNT, variables=variables, tenant_override=args.tenant)
    total = data["runtime"]["runtimeEntities"]["totalCount"]

    if args.json:
        print(json.dumps({"ckId": args.ckId, "totalCount": total}, indent=2))
        return

    print(f"{args.ckId}: {total} instances")


def cmd_search(settings, args):
    attr = args.attr or "name"
    field_filter = _build_field_filter(attr, "LIKE", args.term)
    variables = {
        "ckId": args.ckId,
        "first": args.first or 50,
        "fieldFilter": field_filter,
    }
    sort = _parse_sort(args.sort)
    if sort:
        variables["sortOrder"] = sort

    data = graphql_query(settings, Q_SEARCH, variables=variables, tenant_override=args.tenant)
    conn = data["runtime"]["runtimeEntities"]
    total = conn.get("totalCount", "?")
    entities = collect_connection(conn)

    if args.json:
        print(json.dumps({"totalCount": total, "entities": entities}, indent=2))
        return

    if not entities:
        print(f"No instances of '{args.ckId}' matching '{args.term}' (on attribute '{attr}').")
        return

    showing = len(entities)
    print(f"Search '{args.term}' on {args.ckId}.{attr} ({showing} shown, {total} matched):")
    print()

    for e in entities:
        name = _display_name(e)
        rtId = e.get("rtId", "?")
        attrs = _attrs_to_dict((e.get("attributes") or {}).get("items"))
        matched_val = attrs.get(attr, "")
        print(f"  {rtId}  {name}  ({attr}={_format_attr_value(matched_val)})")


def cmd_query(settings, args):
    columns = [c.strip() for c in args.columns.split(",")]
    variables = {
        "ckId": args.ckId,
        "columnPaths": columns,
        "first": args.first or 50,
    }
    sort = _parse_sort(args.sort)
    if sort:
        variables["sortOrder"] = sort

    data = graphql_query(settings, Q_QUERY, variables=variables, tenant_override=args.tenant)
    result = data["runtime"]["transientQuery"]["simple"]
    total = result.get("totalCount", "?")
    items = result.get("items") or []

    if args.json:
        print(json.dumps({"totalCount": total, "items": items}, indent=2))
        return

    if not items:
        print(f"No results for transient query on '{args.ckId}'.")
        return

    item = items[0]
    col_defs = item.get("columns") or []
    rows = (item.get("rows") or {}).get("items") or []

    # Header
    col_names = [c.get("attributePath", "?") for c in col_defs]
    col_widths = [max(len(name), 10) for name in col_names]

    # Compute widths from data
    for row in rows:
        cells = (row.get("cells") or {}).get("items") or []
        for i, cell in enumerate(cells):
            if i < len(col_widths):
                val = _format_attr_value(cell.get("value"), max_len=40)
                col_widths[i] = max(col_widths[i], len(val))

    print(f"Transient query on {args.ckId} ({len(rows)} rows, {total} total):")
    print()

    # Print header
    header = "  ".join(name.ljust(col_widths[i]) for i, name in enumerate(col_names))
    print(f"  {header}")
    print(f"  {'  '.join('-' * w for w in col_widths)}")

    # Print rows
    for row in rows:
        cells = (row.get("cells") or {}).get("items") or []
        vals = []
        for i, cell in enumerate(cells):
            val = _format_attr_value(cell.get("value"), max_len=40)
            if i < len(col_widths):
                vals.append(val.ljust(col_widths[i]))
            else:
                vals.append(val)
        print(f"  {'  '.join(vals)}")


def cmd_filter(settings, args):
    value = _coerce_value(args.value)
    field_filter = _build_field_filter(args.attr, args.op, value)
    variables = {
        "ckId": args.ckId,
        "first": args.first or 50,
        "fieldFilter": field_filter,
    }
    sort = _parse_sort(args.sort)
    if sort:
        variables["sortOrder"] = sort

    data = graphql_query(settings, Q_FILTER, variables=variables, tenant_override=args.tenant)
    conn = data["runtime"]["runtimeEntities"]
    total = conn.get("totalCount", "?")
    entities = collect_connection(conn)

    if args.json:
        print(json.dumps({"totalCount": total, "entities": entities}, indent=2))
        return

    if not entities:
        print(f"No instances of '{args.ckId}' where {args.attr} {args.op} {args.value}.")
        return

    showing = len(entities)
    print(f"Filter {args.ckId} where {args.attr} {args.op} {args.value} ({showing} shown, {total} matched):")
    print()

    for e in entities:
        name = _display_name(e)
        rtId = e.get("rtId", "?")
        attrs = _attrs_to_dict((e.get("attributes") or {}).get("items"))
        matched_val = attrs.get(args.attr, "")
        print(f"  {rtId}  {name}  ({args.attr}={_format_attr_value(matched_val)})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OctoMesh runtime instance explorer")

    sub = parser.add_subparsers(dest="command")

    def add_common_flags(p, with_first=False, with_sort=False):
        p.add_argument("--json", action="store_true", help="Output raw JSON")
        p.add_argument("--tenant", type=str, default=None, help="Override tenant ID")
        if with_first:
            p.add_argument("--first", type=int, default=None, help="Pagination limit")
        if with_sort:
            p.add_argument("--sort", type=str, default=None,
                           help="Sort by attribute (e.g. name:asc, name:desc)")

    # list
    p_list = sub.add_parser("list", help="List instances of a CK type")
    p_list.add_argument("ckId", help="CK type fullName (e.g. Industry.Basic/Machine)")
    p_list.add_argument("--attrs", action="store_true", help="Include all attributes")
    add_common_flags(p_list, with_first=True, with_sort=True)

    # get
    p_get = sub.add_parser("get", help="Get single entity with full detail")
    p_get.add_argument("ckId", help="CK type fullName (e.g. Industry.Basic/Machine)")
    p_get.add_argument("rtId", help="Runtime entity ID")
    add_common_flags(p_get)

    # count
    p_count = sub.add_parser("count", help="Count instances of a CK type")
    p_count.add_argument("ckId", help="CK type fullName (e.g. Industry.Basic/Machine)")
    add_common_flags(p_count)

    # search
    p_search = sub.add_parser("search", help="Search by attribute (LIKE match)")
    p_search.add_argument("ckId", help="CK type fullName (e.g. Industry.Basic/Machine)")
    p_search.add_argument("term", help="Search term (LIKE match)")
    p_search.add_argument("--attr", type=str, default=None,
                          help="Attribute to search (default: name)")
    add_common_flags(p_search, with_first=True, with_sort=True)

    # query
    p_query = sub.add_parser("query", help="Transient query with specific columns")
    p_query.add_argument("ckId", help="CK type fullName (e.g. Industry.Basic/Machine)")
    p_query.add_argument("--columns", type=str, required=True,
                         help="Comma-separated column paths (e.g. name,machineState)")
    add_common_flags(p_query, with_first=True, with_sort=True)

    # filter
    p_filter = sub.add_parser("filter", help="Filter by attribute value")
    p_filter.add_argument("ckId", help="CK type fullName (e.g. Industry.Basic/Machine)")
    p_filter.add_argument("attr", help="Attribute name to filter on")
    p_filter.add_argument("op", choices=FILTER_OPERATORS, help="Filter operator")
    p_filter.add_argument("value", help="Comparison value")
    add_common_flags(p_filter, with_first=True, with_sort=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    settings = load_settings()

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "count": cmd_count,
        "search": cmd_search,
        "query": cmd_query,
        "filter": cmd_filter,
    }
    commands[args.command](settings, args)


if __name__ == "__main__":
    main()
