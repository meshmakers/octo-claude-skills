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
    python ck_explorer.py preflight <fullName> [--json] [--tenant ID]
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _octo_common import load_context, graphql_query, collect_connection


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
                                ckAttributeId { fullName semanticVersionedFullName }
                            }
                        }
                    }
                    associations {
                        in { all { roleId { fullName semanticVersionedFullName } originCkTypeId { fullName semanticVersionedFullName } targetCkTypeId { fullName semanticVersionedFullName } navigationPropertyName multiplicity } }
                        out { all { roleId { fullName semanticVersionedFullName } originCkTypeId { fullName semanticVersionedFullName } targetCkTypeId { fullName semanticVersionedFullName } navigationPropertyName multiplicity } }
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

def cmd_models(context, args):
    data = graphql_query(context, Q_MODELS, tenant_override=args.tenant, verify_ssl=not args.insecure)
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


def cmd_model(context, args):
    data = graphql_query(context, Q_MODELS, tenant_override=args.tenant, verify_ssl=not args.insecure)
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


def cmd_types(context, args):
    first = args.first or 200
    data = graphql_query(context, Q_TYPES % first, tenant_override=args.tenant, verify_ssl=not args.insecure)
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


def cmd_type(context, args):
    data = graphql_query(context, Q_TYPE_DETAIL, tenant_override=args.tenant, verify_ssl=not args.insecure)
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


def cmd_enums(context, args):
    first = args.first or 200
    data = graphql_query(context, Q_ENUMS % first, tenant_override=args.tenant, verify_ssl=not args.insecure)
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


def cmd_enum(context, args):
    data = graphql_query(context, Q_ENUMS % 200, tenant_override=args.tenant, verify_ssl=not args.insecure)
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


def cmd_search(context, args):
    data = graphql_query(context, Q_SEARCH_TYPES, tenant_override=args.tenant, verify_ssl=not args.insecure)
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


def cmd_preflight(context, args):
    data = graphql_query(context, Q_TYPE_DETAIL, tenant_override=args.tenant, verify_ssl=not args.insecure)
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

    # Extract attributes with CK attribute IDs
    attrs = collect_connection(match.get("attributes"))
    attr_list = []
    for a in attrs:
        ck_attr_id = a.get("ckAttributeId") or {}
        attr_list.append({
            "attributeName": a["attributeName"],
            "attributeValueType": a.get("attributeValueType", "?"),
            "isOptional": a.get("isOptional", False),
            "ckAttributeId": ck_attr_id.get("fullName", ""),
            "ckAttributeIdUnversioned": ck_attr_id.get("semanticVersionedFullName", ""),
        })

    # Extract outbound associations
    assoc = match.get("associations", {})
    out_assocs = (assoc.get("out") or {}).get("all") or []
    assoc_list = []
    for a in out_assocs:
        mult = a.get("multiplicity", "")
        target_id = a.get("targetCkTypeId", {})
        role_id = a.get("roleId", {})
        assoc_list.append({
            "targetCkTypeId": target_id.get("fullName", "?"),
            "targetCkTypeIdUnversioned": target_id.get("semanticVersionedFullName", ""),
            "roleId": role_id.get("fullName", "?"),
            "roleIdUnversioned": role_id.get("semanticVersionedFullName", ""),
            "navigationPropertyName": a.get("navigationPropertyName", ""),
            "multiplicity": mult,
            "isMandatory": mult.upper() == "ONE",
        })

    display_name = match["ckTypeId"].get("semanticVersionedFullName") or match["ckTypeId"]["fullName"]
    ck_type_unversioned = match["ckTypeId"].get("semanticVersionedFullName", "")

    if args.for_import:
        _print_import_template(match, attr_list, assoc_list, ck_type_unversioned, display_name, args.json)
        return

    mandatory = [a for a in assoc_list if a["isMandatory"]]

    if args.json:
        result = {
            "ckTypeId": match["ckTypeId"]["fullName"],
            "semanticVersionedFullName": ck_type_unversioned,
            "attributes": attr_list,
            "mandatoryAssociations": mandatory,
        }
        print(json.dumps(result, indent=2))
        return

    print(f"Pre-flight for {display_name}:")
    print()

    if attr_list:
        print("  Attributes for CreateUpdateInfo:")
        for a in attr_list:
            req = "optional" if a["isOptional"] else "required"
            attr_id = a.get("ckAttributeIdUnversioned") or a["attributeName"]
            print(f"    {a['attributeName']:30s} {a['attributeValueType']:10s} {req:10s} id: {attr_id}")
    else:
        print("  Attributes: none")

    print()
    if mandatory:
        print("  Mandatory associations (must include CreateAssociationUpdate):")
        for a in mandatory:
            role = a.get("roleIdUnversioned") or a["roleId"]
            target = a.get("targetCkTypeIdUnversioned") or a["targetCkTypeId"]
            print(f"    -> {target:30s} role: {role}    nav: {a['navigationPropertyName']}")
        print()
        print("  NOTE: At least one mandatory association must be satisfied.")
    else:
        print("  Mandatory associations: none")


def _print_import_template(match, attr_list, assoc_list, ck_type_unversioned, display_name, as_json):
    """Generate an ImportRt YAML template for the given type."""
    # Determine model dependency from the type's fullName
    type_full = match["ckTypeId"]["fullName"]
    model_dep = type_full.rsplit("/", 1)[0] if "/" in type_full else type_full

    # Build attribute entries for the template
    attr_entries = []
    for a in attr_list:
        attr_id = a.get("ckAttributeIdUnversioned") or a["attributeName"]
        req = "required" if not a["isOptional"] else "optional"
        vtype = a.get("attributeValueType", "?")
        attr_entries.append({
            "id": attr_id,
            "attributeName": a["attributeName"],
            "attributeValueType": vtype,
            "isOptional": a["isOptional"],
            "exampleValue": _example_value(vtype),
        })

    # Build association entries
    assoc_entries = []
    for a in assoc_list:
        role = a.get("roleIdUnversioned") or a["roleId"]
        target = a.get("targetCkTypeIdUnversioned") or a["targetCkTypeId"]
        assoc_entries.append({
            "roleId": role,
            "targetCkTypeId": target,
            "multiplicity": a["multiplicity"],
            "isMandatory": a["isMandatory"],
        })

    if as_json:
        result = {
            "ckTypeId": ck_type_unversioned or type_full,
            "modelDependency": model_dep,
            "attributes": attr_entries,
            "associations": assoc_entries,
        }
        print(json.dumps(result, indent=2))
        return

    # Print YAML template
    print(f"# ImportRt YAML template for {display_name}")
    print(f"# Generated from CK schema — fill in values marked with <...>")
    print()
    print(f"$schema: https://schemas.meshmakers.cloud/runtime-model.schema.json")
    print(f"dependencies:")
    print(f"  - {model_dep}")
    print(f"entities:")
    print(f"  - rtId: <24-hex-char-id>")
    print(f"    ckTypeId: {ck_type_unversioned or type_full}")

    # Associations
    mandatory_assocs = [a for a in assoc_entries if a["isMandatory"]]
    optional_assocs = [a for a in assoc_entries if not a["isMandatory"]]
    if mandatory_assocs or optional_assocs:
        print(f"    associations:")
        for a in mandatory_assocs:
            print(f"      - roleId: {a['roleId']}")
            print(f"        targetRtId: <target-rtId>")
            print(f"        targetCkTypeId: {a['targetCkTypeId']}")
        for a in optional_assocs:
            print(f"      # Optional ({a['multiplicity']}):")
            print(f"      # - roleId: {a['roleId']}")
            print(f"      #   targetRtId: <target-rtId>")
            print(f"      #   targetCkTypeId: {a['targetCkTypeId']}")

    # Attributes
    print(f"    attributes:")
    for a in attr_entries:
        req = "REQUIRED" if not a["isOptional"] else "optional"
        print(f"      - id: {a['id']:40s}  # {a['attributeValueType']}, {req}")
        print(f"        value: {a['exampleValue']}")


def _example_value(vtype):
    """Return a placeholder example value for an attribute type."""
    vtype_upper = vtype.upper() if vtype else ""
    if vtype_upper == "STRING":
        return '"<string>"'
    elif vtype_upper in ("INT", "INT32", "INT64", "LONG"):
        return "0"
    elif vtype_upper in ("DOUBLE", "FLOAT", "DECIMAL"):
        return "0.0"
    elif vtype_upper in ("BOOL", "BOOLEAN"):
        return "false"
    elif vtype_upper == "DATETIME":
        return '"2025-01-01T00:00:00Z"'
    else:
        return f'"<{vtype}>"'


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
        p.add_argument("--insecure", action="store_true",
                       help="Disable SSL certificate verification (for localhost dev)")
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

    p_preflight = sub.add_parser("preflight", help="Pre-flight check for pipeline authoring: attributes and mandatory associations")
    p_preflight.add_argument("type_name", help="Type fullName or semanticVersionedFullName")
    p_preflight.add_argument("--for-import", action="store_true", dest="for_import",
                             help="Output an ImportRt YAML template with full CK attribute IDs")
    add_common_flags(p_preflight)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    context = load_context()

    commands = {
        "models": cmd_models,
        "model": cmd_model,
        "types": cmd_types,
        "type": cmd_type,
        "enums": cmd_enums,
        "enum": cmd_enum,
        "search": cmd_search,
        "preflight": cmd_preflight,
    }
    commands[args.command](context, args)


if __name__ == "__main__":
    main()
