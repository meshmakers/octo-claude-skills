#!/usr/bin/env python3
"""Scan the name inventory for anything that is not a name (AB#6366, AB#9741).

inventory/names.json is public. It may hold cmdlet, parameter, command, argument
and node names, repository names and hashes of paths below docs/ — nothing else. This
scan fails on URLs, host or domain names, IP addresses, e-mail addresses, private
key blocks, credential assignments and long token-like strings, and on any value
that is not a short single-line name.

Run:  python3 scripts/scan_inventory_secrets.py [inventory/names.json]
Exit codes: 0 = clean, 1 = something found, 2 = file unreadable.
Standard library only.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

PATTERNS = [
    ("url", re.compile(r"[a-z][a-z0-9+.-]*://", re.I)),
    ("ip-address", re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")),
    ("e-mail", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("credential", re.compile(r"(?i)(password|passwd|secret|token|apikey|api_key)\s*[:=]\s*\S")),
    # a long run without separators that mixes letters and digits (keys, tokens); names have hyphens or are short
    ("token-like", re.compile(r"(?=[A-Za-z0-9+/=]*\d)(?=[A-Za-z0-9+/=]*[A-Za-z])[A-Za-z0-9+/=]{32,}")),
    # host or domain names: a dot-separated name ending in a domain suffix (file extensions are allowed)
    ("host", re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:io|com|net|org|cloud|local|internal|lan|at|de|eu|dev|app|ai)\b", re.I)),
]
NAME_RE = re.compile(r"^[A-Za-z0-9_.?*/@+-]{1,120}$")


def strings(value, path="$"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield f"{path}.{key}", key
            yield from strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def scan(data: dict) -> list[str]:
    problems = []
    for path, text in strings(data):
        if path == "$.$comment" or path.startswith("$.$comment"):
            continue
        for kind, pattern in PATTERNS:
            if pattern.search(text):
                problems.append(f"{path}: {kind}: {text[:80]!r}")
                break
        else:
            if not NAME_RE.match(text):
                problems.append(f"{path}: not a name: {text[:80]!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = pathlib.Path(argv[0]) if argv else REPO / "inventory" / "names.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {path}: {exc}", file=sys.stderr)
        return 2
    problems = scan(data)
    for problem in problems:
        print(problem)
    print(f"{path}: {'clean' if not problems else f'{len(problems)} problem(s)'}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
