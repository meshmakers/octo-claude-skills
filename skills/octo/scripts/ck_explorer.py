"""Construction Kit schema explorer for OctoMesh.

Explore CK models, types, enums, and associations via GraphQL.

Usage:
    python ck_explorer.py models [--json] [--tenant ID]
    python ck_explorer.py model <name> [--json] [--tenant ID]
    python ck_explorer.py types [--model X] [--first N] [--json] [--tenant ID]
    python ck_explorer.py type <fullName> [--json] [--tenant ID]
    python ck_explorer.py enums [--model X] [--first N] [--json] [--tenant ID]
    python ck_explorer.py enum <fullName> [--json] [--tenant ID]
    python ck_explorer.py search <term> [--first N] [--json] [--tenant ID]
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _octo_common import load_settings, graphql_query, collect_connection


# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

Q_MODELS = """{
    constructionKit {
        models {
            edges {
                node {
                    id { name version fullName semanticVersionedFullName }
                    description
                    modelState
                    dependencies { name version fullName semanticVersionedFullName }
                }
            }
        }
    }
}"""

Q_TYPES = """{
    constructionKit {
        types(first: %d) {
            totalCount
            edges {
                node {
                    ckTypeId { fullName semanticVersionedFullName }
                    isAbstract
                    isFinal
                    description
                    baseType { ckTypeId { fullName } }
                }
            }
        }
    }
}"""

Q_TYPE_DETAIL = """{
    constructionKit {
        types(first: 200) {
            edges {
                node {
                    ckTypeId { fullName semanticVersionedFullName }
                    isAbstract
                    isFinal
                    description
                    baseType { ckTypeId { fullName } }
                    attributes {
                        edges {
                            node {
                                attributeName
                                attributeValueType
                                isOptional
                                autoCompleteValues
                                autoIncrementReference
                            }
                        }
                    }
                    associations {
                        in { all { roleId { fullName } originCkTypeId { fullName } targetCkTypeId { fullName } navigationPropertyName multiplicity } }
                        out { all { roleId { fullName } originCkTypeId { fullName } targetCkTypeId { fullName } navigationPropertyName multiplicity } }
                    }
                    derivedTypes { edges { node { ckTypeId { fullName } } } }
                }
            }
        }
    }
}"""

Q_ENUMS = """{
    constructionKit {
        enums(first: %d) {
            totalCount
            edges {
                node {
                    ckEnumId { fullName semanticVersionedFullName }
                    description
                    useFlags
                    isExtensible
                    values { key name description }
                }
            }
        }
    }
}"""

Q_SEARCH_TYPES = """{
    constructionKit {
        types(first: 200) {
            edges {
                node {
                    ckTypeId { fullName }
                    description
                    isAbstract
                }
            }
        }
        enums(first: 200) {
            edges {
                node {
                    ckEnumId { fullName }
                    description
                }
            }
        }
    }
}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_prefix(full_name):
    """Extract model prefix from a type/enum fullName like 'System-2.0.2/Entity-1'."""
    if "/" in full_name:
        return full_name.rsplit("/", 1)[0]
    return ""


def _group_by_model(items, name_key):
    """Group items by model prefix, extracted from their fullName."""
    groups = {}
    for item in items:
        full = item[name_key]["fullName"]
        model = _model_prefix(full)
        groups.setdefault(model, []).append(item)
    for model in groups:
        groups[model].sort(key=lambda x: x[name_key]["fullName"])
    return groups


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_models(settings, args):
    data = graphql_query(settings, Q_MODELS, tenant_override=args.tenant)
    models = collect_connection(data["constructionKit"]["models"])

    if args.json:
        print(json.dumps(models, indent=2))
        return

    if not models:
        print("No CK models found.")
        return

    print(f"CK Models ({len(models)}):")
    print()
    for m in sorted(models, key=lambda x: x["id"]["fullName"]):
        mid = m["id"]
        state = m.get("modelState", "?")
        desc = m.get("description") or ""
        if desc and len(desc) > 80:
            desc = desc[:77] + "..."
        print(f"  {mid['fullName']:45s} state={state}")
        if desc:
            print(f"    {desc}")


def cmd_model(settings, args):
    data = graphql_query(settings, Q_MODELS, tenant_override=args.tenant)
    models = collect_connection(data["constructionKit"]["models"])

    target = args.model_name
    match = None
    for m in models:
        fn = m["id"]["fullName"]
        # Match by fullName or by name (without version)
        if fn == target or m["id"]["name"] == target:
            match = m
            break

    if not match:
        print(f"No model found matching '{target}'.", file=sys.stderr)
        print("Available models:", file=sys.stderr)
        for m in models:
            print(f"  {m['id']['fullName']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(match, indent=2))
        return

    mid = match["id"]
    print(f"Model: {mid['fullName']}")
    print(f"  Name:    {mid['name']}")
    v = mid.get("version")
    if v:
        print(f"  Version: {v}")
    print(f"  State:   {match.get('modelState', '?')}")
    if match.get("description"):
        print(f"  Description: {match['description']}")

    deps = match.get("dependencies", [])
    if deps:
        print(f"  Dependencies ({len(deps)}):")
        for d in deps:
            print(f"    - {d['fullName']}")
    else:
        print("  Dependencies: none")


def cmd_types(settings, args):
    first = args.first or 200
    data = graphql_query(settings, Q_TYPES % first, tenant_override=args.tenant)
    conn = data["constructionKit"]["types"]
    total = conn.get("totalCount", "?")
    types = collect_connection(conn)

    # Filter by model if requested
    if args.model:
        types = [t for t in types if _model_prefix(t["ckTypeId"]["fullName"]) == args.model]

    if args.json:
        print(json.dumps({"totalCount": total, "types": types}, indent=2))
        return

    if not types:
        if args.model:
            print(f"No types found in model '{args.model}'.")
        else:
            print("No types found.")
        return

    label = f" in {args.model}" if args.model else ""
    print(f"CK Types{label} ({len(types)} shown, {total} total):")
    print()

    groups = _group_by_model(types, "ckTypeId")
    for model in sorted(groups.keys()):
        print(f"  [{model}]")
        for t in groups[model]:
            fn = t["ckTypeId"]["fullName"]
            short = fn.split("/", 1)[1] if "/" in fn else fn
            flags = []
            if t.get("isAbstract"):
                flags.append("abstract")
            if t.get("isFinal"):
                flags.append("final")
            base = ""
            if t.get("baseType") and t["baseType"].get("ckTypeId"):
                base = f" extends {t['baseType']['ckTypeId']['fullName']}"
            flag_str = f" ({', '.join(flags)})" if flags else ""
            print(f"    {short:40s}{flag_str}{base}")
        print()


def cmd_type(settings, args):
    data = graphql_query(settings, Q_TYPE_DETAIL, tenant_override=args.tenant)
    types = collect_connection(data["constructionKit"]["types"])

    target = args.type_name
    match = None
    for t in types:
        fn = t["ckTypeId"]["fullName"]
        svfn = t["ckTypeId"].get("semanticVersionedFullName", "")
        if fn == target or svfn == target:
            match = t
            break
    # Also try partial match (just the type name without model prefix)
    if not match:
        for t in types:
            fn = t["ckTypeId"]["fullName"]
            short = fn.split("/", 1)[1] if "/" in fn else fn
            if short == target:
                match = t
                break

    if not match:
        print(f"No type found matching '{target}'.", file=sys.stderr)
        print("Use 'ck_explorer.py types' to list available types.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(match, indent=2))
        return

    tid = match["ckTypeId"]
    print(f"Type: {tid['fullName']}")
    print(f"  Abstract: {match.get('isAbstract', '?')}")
    print(f"  Final:    {match.get('isFinal', '?')}")
    if match.get("description"):
        print(f"  Description: {match['description']}")
    if match.get("baseType") and match["baseType"].get("ckTypeId"):
        print(f"  Base type: {match['baseType']['ckTypeId']['fullName']}")
    else:
        print("  Base type: (none — root type)")

    # Attributes
    attrs = collect_connection(match.get("attributes"))
    if attrs:
        print(f"\n  Attributes ({len(attrs)}):")
        for a in attrs:
            opt = " (optional)" if a.get("isOptional") else ""
            vtype = a.get("attributeValueType", "?")
            print(f"    {a['attributeName']:35s} {vtype}{opt}")
    else:
        print("\n  Attributes: none")

    # Associations
    assoc = match.get("associations", {})
    out_assocs = (assoc.get("out") or {}).get("all") or []
    in_assocs = (assoc.get("in") or {}).get("all") or []
    if out_assocs or in_assocs:
        print(f"\n  Associations:")
        if out_assocs:
            print(f"    Outbound ({len(out_assocs)}):")
            for a in out_assocs:
                role = a.get("roleId", {}).get("fullName", "?")
                target_id = a.get("targetCkTypeId", {}).get("fullName", "?")
                nav = a.get("navigationPropertyName", "")
                mult = a.get("multiplicity", "?")
                print(f"      -> {target_id}  (role: {role}, nav: {nav}, mult: {mult})")
        if in_assocs:
            print(f"    Inbound ({len(in_assocs)}):")
            for a in in_assocs:
                role = a.get("roleId", {}).get("fullName", "?")
                origin = a.get("originCkTypeId", {}).get("fullName", "?")
                nav = a.get("navigationPropertyName", "")
                mult = a.get("multiplicity", "?")
                print(f"      <- {origin}  (role: {role}, nav: {nav}, mult: {mult})")
    else:
        print("\n  Associations: none")

    # Derived types
    derived = collect_connection(match.get("derivedTypes"))
    if derived:
        print(f"\n  Derived types ({len(derived)}):")
        for d in derived:
            print(f"    - {d['ckTypeId']['fullName']}")
    else:
        print("\n  Derived types: none")


def cmd_enums(settings, args):
    first = args.first or 200
    data = graphql_query(settings, Q_ENUMS % first, tenant_override=args.tenant)
    conn = data["constructionKit"]["enums"]
    total = conn.get("totalCount", "?")
    enums = collect_connection(conn)

    # Filter by model if requested
    if args.model:
        enums = [e for e in enums if _model_prefix(e["ckEnumId"]["fullName"]) == args.model]

    if args.json:
        print(json.dumps({"totalCount": total, "enums": enums}, indent=2))
        return

    if not enums:
        if args.model:
            print(f"No enums found in model '{args.model}'.")
        else:
            print("No enums found.")
        return

    label = f" in {args.model}" if args.model else ""
    print(f"CK Enums{label} ({len(enums)} shown, {total} total):")
    print()

    groups = _group_by_model(enums, "ckEnumId")
    for model in sorted(groups.keys()):
        print(f"  [{model}]")
        for e in groups[model]:
            fn = e["ckEnumId"]["fullName"]
            short = fn.split("/", 1)[1] if "/" in fn else fn
            flags = []
            if e.get("useFlags"):
                flags.append("flags")
            if e.get("isExtensible"):
                flags.append("extensible")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            val_count = len(e.get("values") or [])
            print(f"    {short:40s}{flag_str}  [{val_count} values]")
        print()


def cmd_enum(settings, args):
    data = graphql_query(settings, Q_ENUMS % 200, tenant_override=args.tenant)
    enums = collect_connection(data["constructionKit"]["enums"])

    target = args.enum_name
    match = None
    for e in enums:
        fn = e["ckEnumId"]["fullName"]
        svfn = e["ckEnumId"].get("semanticVersionedFullName", "")
        if fn == target or svfn == target:
            match = e
            break
    if not match:
        for e in enums:
            fn = e["ckEnumId"]["fullName"]
            short = fn.split("/", 1)[1] if "/" in fn else fn
            if short == target:
                match = e
                break

    if not match:
        print(f"No enum found matching '{target}'.", file=sys.stderr)
        print("Use 'ck_explorer.py enums' to list available enums.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(match, indent=2))
        return

    eid = match["ckEnumId"]
    print(f"Enum: {eid['fullName']}")
    if match.get("description"):
        print(f"  Description: {match['description']}")
    print(f"  Use flags:    {match.get('useFlags', '?')}")
    print(f"  Extensible:   {match.get('isExtensible', '?')}")

    values = match.get("values") or []
    if values:
        print(f"\n  Values ({len(values)}):")
        for v in values:
            desc = f"  — {v['description']}" if v.get("description") else ""
            print(f"    {v['key']:4d}  {v['name']}{desc}")
    else:
        print("\n  Values: none")


def cmd_search(settings, args):
    data = graphql_query(settings, Q_SEARCH_TYPES, tenant_override=args.tenant)
    types = collect_connection(data["constructionKit"]["types"])
    enums = collect_connection(data["constructionKit"]["enums"])

    term = args.search_term.lower()

    matched_types = [t for t in types if term in t["ckTypeId"]["fullName"].lower()
                     or (t.get("description") and term in t["description"].lower())]
    matched_enums = [e for e in enums if term in e["ckEnumId"]["fullName"].lower()
                     or (e.get("description") and term in e["description"].lower())]

    if args.first:
        matched_types = matched_types[:args.first]
        matched_enums = matched_enums[:args.first]

    if args.json:
        print(json.dumps({"types": matched_types, "enums": matched_enums}, indent=2))
        return

    if not matched_types and not matched_enums:
        print(f"No types or enums matching '{args.search_term}'.")
        return

    if matched_types:
        print(f"Types matching '{args.search_term}' ({len(matched_types)}):")
        for t in matched_types:
            fn = t["ckTypeId"]["fullName"]
            flags = []
            if t.get("isAbstract"):
                flags.append("abstract")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            print(f"  {fn}{flag_str}")
        print()

    if matched_enums:
        print(f"Enums matching '{args.search_term}' ({len(matched_enums)}):")
        for e in matched_enums:
            fn = e["ckEnumId"]["fullName"]
            print(f"  {fn}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OctoMesh Construction Kit schema explorer")

    sub = parser.add_subparsers(dest="command")

    # Shared flags added to each subparser so they work in any position
    def add_common_flags(p, with_first=False, with_model=False):
        p.add_argument("--json", action="store_true", help="Output raw JSON")
        p.add_argument("--tenant", type=str, default=None, help="Override tenant ID")
        if with_first:
            p.add_argument("--first", type=int, default=None, help="Pagination limit")
        if with_model:
            p.add_argument("--model", type=str, default=None, help="Filter by model fullName")

    p_models = sub.add_parser("models", help="List all CK models")
    add_common_flags(p_models)

    p_model = sub.add_parser("model", help="Show detail for a specific model")
    p_model.add_argument("model_name", help="Model fullName or name")
    add_common_flags(p_model)

    p_types = sub.add_parser("types", help="List all types")
    add_common_flags(p_types, with_first=True, with_model=True)

    p_type = sub.add_parser("type", help="Show detail for a specific type")
    p_type.add_argument("type_name", help="Type fullName (e.g. System-2.0.2/Entity-1)")
    add_common_flags(p_type)

    p_enums = sub.add_parser("enums", help="List all enums")
    add_common_flags(p_enums, with_first=True, with_model=True)

    p_enum = sub.add_parser("enum", help="Show detail for a specific enum")
    p_enum.add_argument("enum_name", help="Enum fullName (e.g. System-2.0.2/AggregationTypes-1)")
    add_common_flags(p_enum)

    p_search = sub.add_parser("search", help="Search type and enum names")
    p_search.add_argument("search_term", help="Search term (case-insensitive)")
    add_common_flags(p_search, with_first=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    settings = load_settings()

    commands = {
        "models": cmd_models,
        "model": cmd_model,
        "types": cmd_types,
        "type": cmd_type,
        "enums": cmd_enums,
        "enum": cmd_enum,
        "search": cmd_search,
    }
    commands[args.command](settings, args)


if __name__ == "__main__":
    main()
