#!/usr/bin/env python3
"""
Parse octo-construction-kit YAMLs at a given git branch and emit Miro UML
class diagram DSL per Construction Kit.

Reads from git non-destructively (`git show <branch>:<path>`) so the user's
working tree is untouched. Supports both YAML schema variants:
  - Standard: top-level `types:`, `records:`, `enums:`, `attributes:`,
    `associationRoles:` arrays. Refs use `${CkName}/elementName`.
  - Compact: filename is the id, `derivedFrom: CK/Name`, `attributeName`
    instead of `name`. Used by Octo.Energy.Demo.

Output (stdout, JSON):
{
  "branch": "main",
  "repo": "/path",
  "cks": [
    {"name": "Basic", "modelId": "Basic-2.0.2", "deps": [...],
     "title": "Basic (v2.0.2)", "dsl": "graphdir TB\\n...",
     "x": 0, "y": -2000, "node_count": 26, "edge_count": 13},
    ...
  ],
  "dependency_tree_md": "...",
  "legend_md": "...",
  "stats_md": "..."
}
"""
import argparse
import json
import re
import subprocess
import sys
from io import StringIO
from typing import Any

import yaml

CK_DIR_PREFIX = "src/ConstructionKits/"

TYPE_COLOR = "#c6dcff"     # blue
RECORD_COLOR = "#dbfaad"   # green
ENUM_COLOR = "#fff6b6"     # yellow
EXTERNAL_COLOR = "#e7e7e7" # gray

MULTIPLICITY = {
    "N": "*",
    "One": "1",
    "ZeroOrOne": "0..1",
    "ZeroOrMany": "0..*",
    "OneOrMany": "1..*",
}

REF_RE = re.compile(r"\$\{([^}]+)\}/(.+)")


def mult(v: Any) -> str:
    return MULTIPLICITY.get(v, str(v) if v is not None else "1")


def parse_ref(s: Any, this_ck: str) -> tuple[str | None, str | None]:
    if not isinstance(s, str):
        return None, None
    m = REF_RE.match(s)
    if m:
        ck = m.group(1)
        if ck == "this":
            ck = this_ck
        return ck, m.group(2)
    return this_ck, s


def git_ls(repo: str, branch: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "-C", repo, "ls-tree", "-r", branch, "--name-only"],
        text=True,
    )
    return out.splitlines()


def git_show(repo: str, branch: str, path: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", repo, "show", f"{branch}:{path}"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return None


def load_yaml_text(text: str | None) -> Any:
    if not text:
        return None
    # Strip BOM
    if text.startswith("﻿"):
        text = text[1:]
    try:
        return yaml.safe_load(StringIO(text))
    except yaml.YAMLError as e:
        print(f"YAML error: {e}", file=sys.stderr)
        return None


def normalize_compact_type(fname: str, data: dict) -> dict:
    t = dict(data)
    t["typeId"] = fname.replace(".yaml", "")
    if "derivedFrom" in t and "derivedFromCkTypeId" not in t:
        df = t.pop("derivedFrom")
        if isinstance(df, str) and "/" in df:
            ck, name = df.split("/", 1)
            t["derivedFromCkTypeId"] = f"${{{ck}}}/{name}"
        elif isinstance(df, str):
            t["derivedFromCkTypeId"] = f"${{this}}/{df}"
    new_attrs = []
    for a in (t.get("attributes") or []):
        if "attributeName" in a:
            na = {"id": a["attributeName"], "name": a["attributeName"]}
            for k in ("isOptional", "valueType", "valueCkEnumId",
                      "valueCkRecordId", "description"):
                if k in a:
                    na[k] = a[k]
            new_attrs.append(na)
        else:
            new_attrs.append(a)
    if new_attrs:
        t["attributes"] = new_attrs
    return t


def normalize_compact_enum(fname: str, data: dict) -> dict:
    e = dict(data)
    e["enumId"] = fname.replace(".yaml", "")
    new_vals = []
    for v in (e.get("values") or []):
        nv = dict(v)
        if "value" in nv and "key" not in nv:
            nv["key"] = nv.pop("value")
        new_vals.append(nv)
    e["values"] = new_vals
    return e


def normalize_compact_record(fname: str, data: dict) -> dict:
    r = dict(data)
    r["recordId"] = fname.replace(".yaml", "")
    return r


def normalize_compact_attribute(fname: str, data: dict) -> dict:
    a = dict(data)
    a["id"] = fname.replace(".yaml", "")
    return a


def normalize_compact_assoc(fname: str, data: dict) -> dict:
    a = dict(data)
    a["id"] = fname.replace(".yaml", "")
    return a


def discover_cks(repo: str, branch: str) -> list[tuple[str, str]]:
    """Return [(ck_name, ck_dir), ...] for every project under ConstructionKits/."""
    files = git_ls(repo, branch)
    ck_dirs = set()
    for f in files:
        if not f.startswith(CK_DIR_PREFIX):
            continue
        if "/ConstructionKit/ckModel.yaml" not in f:
            continue
        rel = f[len(CK_DIR_PREFIX):]
        dir_name = rel.split("/", 1)[0]
        ck_dirs.add(dir_name)
    out = []
    for d in sorted(ck_dirs):
        meta_path = f"{CK_DIR_PREFIX}{d}/ConstructionKit/ckModel.yaml"
        text = git_show(repo, branch, meta_path)
        meta = load_yaml_text(text)
        if not meta:
            continue
        model_id = str(meta.get("modelId") or d)
        name = model_id.split("-")[0] if "-" in model_id else model_id
        out.append((name, d))
    return out


def load_ck(repo: str, branch: str, ck_name: str, dir_name: str) -> dict:
    base = f"{CK_DIR_PREFIX}{dir_name}/ConstructionKit"
    files = [f for f in git_ls(repo, branch)
             if f.startswith(base + "/") and f.endswith(".yaml")]
    meta = load_yaml_text(git_show(repo, branch, f"{base}/ckModel.yaml"))
    ck = {
        "name": ck_name,
        "dir": dir_name,
        "modelId": (meta or {}).get("modelId", ck_name),
        "dependencies": (meta or {}).get("dependencies", []),
        "types": {},
        "records": {},
        "attributes": {},
        "enums": {},
        "associationRoles": {},
    }
    for f in files:
        rel = f[len(base) + 1:]
        if "/" not in rel:
            continue
        kind, fname = rel.split("/", 1)
        if "/" in fname:
            continue  # skip nested dirs
        data = load_yaml_text(git_show(repo, branch, f))
        if not isinstance(data, dict):
            continue
        if kind == "types":
            if "types" in data:
                for t in (data.get("types") or []):
                    ck["types"][t["typeId"]] = t
            else:
                t = normalize_compact_type(fname, data)
                ck["types"][t["typeId"]] = t
        elif kind == "records":
            if "records" in data:
                for r in (data.get("records") or []):
                    ck["records"][r["recordId"]] = r
            else:
                r = normalize_compact_record(fname, data)
                ck["records"][r["recordId"]] = r
        elif kind == "enums":
            if "enums" in data:
                for e in (data.get("enums") or []):
                    ck["enums"][e["enumId"]] = e
            else:
                e = normalize_compact_enum(fname, data)
                ck["enums"][e["enumId"]] = e
        elif kind == "attributes":
            if "attributes" in data:
                for a in (data.get("attributes") or []):
                    ck["attributes"][a["id"]] = a
            else:
                a = normalize_compact_attribute(fname, data)
                ck["attributes"][a["id"]] = a
        elif kind == "associations":
            if "associationRoles" in data:
                for a in (data.get("associationRoles") or []):
                    ck["associationRoles"][a["id"]] = a
            else:
                a = normalize_compact_assoc(fname, data)
                ck["associationRoles"][a["id"]] = a
    return ck


def find_attr(db: dict, ck_name: str, attr_id: str) -> dict | None:
    src_ck, local = parse_ref(attr_id, ck_name)
    if src_ck is None or local is None:
        return None
    return db.get(src_ck, {}).get("attributes", {}).get(local)


def attr_line(db: dict, ck_name: str, attr_ref: dict) -> str:
    aid = attr_ref["id"]
    aname = attr_ref.get("name", aid.split("/")[-1])
    optional = attr_ref.get("isOptional", False)
    a = find_attr(db, ck_name, aid)
    vt = "?"
    if a:
        vt = a.get("valueType", "?")
        if vt == "Record":
            rec_ref = a.get("valueCkRecordId")
            if rec_ref:
                rck, rname = parse_ref(rec_ref, ck_name)
                vt = f"«{rname}»" if rck == ck_name else f"«{rck}.{rname}»"
        elif vt == "Enum":
            en_ref = a.get("valueCkEnumId") or a.get("valueCkEnumTypeId")
            if en_ref:
                eck, ename = parse_ref(en_ref, ck_name)
                vt = f"<{ename}>" if eck == ck_name else f"<{eck}.{ename}>"
    prefix = "-" if optional else "+"
    return f"{prefix}{aname}: {vt}"


def generate_dsl(db: dict, ck_name: str) -> tuple[str, int, int]:
    ck = db[ck_name]
    nodes: list[str] = []
    edges: list[str] = []
    node_id: dict = {}
    counter_n = [0]
    counter_e = [0]

    def add_node(key, label, attrs, color) -> str:
        if key in node_id:
            return node_id[key]
        counter_n[0] += 1
        nid = f"n{counter_n[0]}"
        node_id[key] = nid
        label = label.replace('"', "'")
        attrs = attrs.replace('"', "'")
        nodes.append(f'{nid} "{label}" "{attrs}" "" {color}')
        return nid

    def add_edge(src, tgt, sym, src_card="1", tgt_card="1"):
        if not src or not tgt:
            return
        counter_e[0] += 1
        eid = f"e{counter_e[0]}"
        edges.append(f"{eid} {src} {src_card} {sym} {tgt_card} {tgt}")

    for tname, t in ck["types"].items():
        attr_refs = t.get("attributes") or []
        attr_str = "\\n".join(attr_line(db, ck_name, a) for a in attr_refs)
        if not attr_str:
            attr_str = " "
        add_node(("type", ck_name, tname), tname, attr_str, TYPE_COLOR)

    for rname, r in ck["records"].items():
        attr_refs = r.get("attributes") or []
        attr_str = "\\n".join(attr_line(db, ck_name, a) for a in attr_refs)
        if not attr_str:
            attr_str = " "
        add_node(("record", ck_name, rname), f"«record» {rname}",
                 attr_str, RECORD_COLOR)

    for ename, e in ck["enums"].items():
        vals = e.get("values") or []
        v_lines = []
        for v in vals[:8]:
            v_lines.append(f"+{v.get('name', '?')} = {v.get('key', '?')}")
        if len(vals) > 8:
            v_lines.append(f"+... ({len(vals) - 8} more)")
        attr_str = "\\n".join(v_lines) if v_lines else " "
        add_node(("enum", ck_name, ename), f"«enum» {ename}",
                 attr_str, ENUM_COLOR)

    for tname, t in ck["types"].items():
        src_id = node_id[("type", ck_name, tname)]
        parent_ref = t.get("derivedFromCkTypeId")
        if parent_ref:
            pck, pname = parse_ref(parent_ref, ck_name)
            if pck == ck_name and ("type", pck, pname) in node_id:
                pid = node_id[("type", pck, pname)]
                add_edge(pid, src_id, "<|--")
            else:
                key = ("ext", pck, pname)
                if key not in node_id:
                    add_node(key, f"{pck}.{pname}", " ", EXTERNAL_COLOR)
                add_edge(node_id[key], src_id, "<|--")

        for assoc in (t.get("associations") or []):
            assoc_id = assoc.get("id")
            target = assoc.get("targetCkTypeId")
            if not target:
                continue
            tck, tname2 = parse_ref(target, ck_name)
            rck, rname = parse_ref(assoc_id, ck_name)
            role = db.get(rck, {}).get("associationRoles", {}).get(rname, {})
            in_m = mult(role.get("inboundMultiplicity", "1"))
            out_m = mult(role.get("outboundMultiplicity", "1"))
            if tck == ck_name and ("type", tck, tname2) in node_id:
                tid = node_id[("type", tck, tname2)]
            else:
                key = ("ext", tck, tname2)
                if key not in node_id:
                    add_node(key, f"{tck}.{tname2}", " ", EXTERNAL_COLOR)
                tid = node_id[key]
            counter_e[0] += 1
            eid = f"e{counter_e[0]}"
            edges.append(f"{eid} {src_id} {in_m} -- {out_m} {tid}")

    dsl = "graphdir TB\n\n" + "\n".join(nodes) + "\n\n" + "\n".join(edges)
    return dsl, len(nodes), len(edges)


def build_dependency_tree(db: dict) -> str:
    """Render dependency tree as markdown."""
    children_of: dict[str, list[str]] = {}
    for name, ck in db.items():
        for dep in ck.get("dependencies", []):
            parent = str(dep).split("-")[0]
            children_of.setdefault(parent, []).append(name)
    roots = [n for n, ck in db.items()
             if not any(n in v for v in children_of.values())]
    lines = ["```"]
    seen = set()

    def render(node, indent):
        if node in seen:
            return
        seen.add(node)
        version = ""
        if node in db:
            mid = str(db[node].get("modelId", ""))
            if "-" in mid:
                version = f" (v{mid.split('-', 1)[1]})"
            elif mid != node:
                version = f" ({mid})"
        lines.append(f"{'    ' * indent}└── {node}{version}")
        for c in sorted(children_of.get(node, [])):
            render(c, indent + 1)

    lines.append("System (extern)")
    # Anything not in children_of values but listed as a parent in deps is a root
    all_parents = set()
    for ck in db.values():
        for dep in ck.get("dependencies", []):
            all_parents.add(str(dep).split("-")[0])
    external_roots = all_parents - set(db.keys())
    # Render System children first
    for c in sorted(children_of.get("System", [])):
        render(c, 1)
    # Any other root not anchored to System
    for n in sorted(db.keys()):
        if n not in seen:
            render(n, 1)
    lines.append("```")
    return "\n".join(lines)


def build_legend_md() -> str:
    return (
        "# Octo Construction Kits — Detail-Visualisierung\n\n"
        "## Legende\n\n"
        "| Farbe | Bedeutung |\n"
        "|---|---|\n"
        "| 🟦 **Blau** | Type (Entity) |\n"
        "| 🟩 **Grün** | Record (Value Object, «record») |\n"
        "| 🟨 **Gelb** | Enum («enum») |\n"
        "| ⬜ **Grau** | Externer CK-Verweis |\n\n"
        "### Beziehungen (UML)\n"
        "- **▷── (gefülltes Dreieck)** → Inheritance (`derivedFromCkTypeId`)\n"
        "- **── (einfache Linie)** → Association mit Multiplicity (1, 0..1, *, 0..*)\n\n"
        "### Attribut-Notation\n"
        "- `+name: Type` → Pflichtfeld\n"
        "- `-name: Type` → optional (`isOptional: true`)\n"
        "- `«RecordName»` → Wert ist ein Record\n"
        "- `<EnumName>` → Wert ist ein Enum\n"
    )


def build_stats_md(cks: list[dict]) -> str:
    lines = ["## Inhalts-Übersicht\n",
             "| CK | Types | Records | Enums |",
             "|---|---:|---:|---:|"]
    for ck in cks:
        lines.append(
            f"| {ck['name']} | {ck['type_count']} | "
            f"{ck['record_count']} | {ck['enum_count']} |"
        )
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True,
                   help="Path to octo-construction-kit checkout")
    p.add_argument("--branch", default="main", help="Git branch to read from")
    p.add_argument("--ck", default=None,
                   help="Limit to a single CK (by short name, e.g. Basic.Energy)")
    args = p.parse_args()

    print(f"Discovering CKs on branch {args.branch}...", file=sys.stderr)
    cks_meta = discover_cks(args.repo, args.branch)
    if args.ck:
        cks_meta = [(n, d) for (n, d) in cks_meta if n == args.ck]
        if not cks_meta:
            print(f"CK '{args.ck}' not found on branch {args.branch}",
                  file=sys.stderr)
            sys.exit(2)

    db: dict = {}
    for name, dname in cks_meta:
        print(f"  loading {name}...", file=sys.stderr)
        db[name] = load_ck(args.repo, args.branch, name, dname)

    # Layout: title doc + dep-tree doc at the top, then 1 diagram per row.
    # Y step = 3500 — generous to avoid auto-layout overlap.
    Y_STEP = 3500
    Y_TOP = -2000

    cks_out = []
    for i, (name, _d) in enumerate(cks_meta):
        dsl, nn, ne = generate_dsl(db, name)
        model_id = str(db[name].get("modelId", name))
        version = ""
        if "-" in model_id:
            version = f" (v{model_id.split('-', 1)[1]})"
        title = f"{name}{version}".strip()
        cks_out.append({
            "name": name,
            "dir": db[name]["dir"],
            "modelId": model_id,
            "dependencies": db[name].get("dependencies", []),
            "title": title,
            "dsl": dsl,
            "node_count": nn,
            "edge_count": ne,
            "type_count": len(db[name]["types"]),
            "record_count": len(db[name]["records"]),
            "enum_count": len(db[name]["enums"]),
            "x": 0,
            "y": Y_TOP + i * Y_STEP,
        })

    out = {
        "branch": args.branch,
        "repo": args.repo,
        "cks": cks_out,
        "legend_md": build_legend_md(),
        "dependency_tree_md": "# CK Dependency Tree\n\n" + build_dependency_tree(db),
        "stats_md": build_stats_md(cks_out),
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print("", file=sys.stdout)


if __name__ == "__main__":
    main()
