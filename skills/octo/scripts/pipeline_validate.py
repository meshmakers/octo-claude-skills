#!/usr/bin/env python3
"""Validate an OctoMesh pipeline YAML file against the adapter's JSON Schema.

Usage:
  pipeline_validate.py <yaml-file> --schema <schema-file>
  pipeline_validate.py <yaml-file> --adapter-id <rtId> [--insecure]

Checks:
  - Pipeline has triggers and transformations sections
  - All node type values exist in the schema's $defs
  - Recursively validates nested transformations (ForEach, For, If, Switch, BufferData)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

# Allow importing _octo_common from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import yaml
except ImportError:
    print("Error: pyyaml is not installed. Run: pip install pyyaml>=6.0", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
except ImportError:
    print("Error: jsonschema is not installed. Run: pip install jsonschema>=4.17.0", file=sys.stderr)
    sys.exit(1)


def load_yaml(path):
    """Load and parse a YAML file."""
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: YAML file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: invalid YAML in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def load_schema_from_file(path):
    """Load a JSON Schema from a local file."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: schema file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def load_schema_from_adapter(adapter_id, insecure=False):
    """Fetch the pipeline JSON Schema from an adapter via octo-cli."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            "octo-cli",
            "-c", "GetPipelineSchema",
            "--adapterId", adapter_id,
            "--outputFile", tmp_path,
        ]
        if insecure:
            cmd.append("--insecure")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Error: octo-cli failed (exit {result.returncode}):", file=sys.stderr)
            if result.stderr:
                print(result.stderr.strip(), file=sys.stderr)
            if result.stdout:
                print(result.stdout.strip(), file=sys.stderr)
            sys.exit(1)

        with open(tmp_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: octo-cli not found on PATH.", file=sys.stderr)
        print("Install octo-cli or use --schema with a local schema file.", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: octo-cli timed out after 30 seconds.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: octo-cli produced invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def extract_valid_types(schema, node_kind):
    """Extract valid type strings from a schema $defs node (TriggerNode or TransformationNode).

    The schema has $defs with TriggerNode and TransformationNode entries,
    each containing a oneOf array. Each option has properties.type.const
    with the node type string (e.g. "ForEach@1").
    """
    defs = schema.get("$defs", {})
    node_def = defs.get(node_kind, {})
    one_of = node_def.get("oneOf", [])
    types = set()
    for entry in one_of:
        const = entry.get("properties", {}).get("type", {}).get("const")
        if const:
            types.add(const)
    return types


# Node types that contain nested transformations
NESTING_NODES = {"ForEach@1", "For@1", "If@1", "Switch@1", "BufferData@1"}


def validate_nodes(nodes, valid_types, node_kind, path_prefix, errors):
    """Validate a list of trigger or transformation nodes.

    Args:
        nodes: List of node dicts from the YAML.
        valid_types: Set of valid type strings.
        node_kind: "trigger" or "transformation" (for error messages).
        path_prefix: JSONPath-like prefix for error messages (e.g. "transformations[2]").
        errors: List to append error strings to.
    """
    if not isinstance(nodes, list):
        errors.append(f"{path_prefix}: expected an array, got {type(nodes).__name__}")
        return

    for i, node in enumerate(nodes):
        node_path = f"{path_prefix}[{i}]"

        if not isinstance(node, dict):
            errors.append(f"{node_path}: expected a mapping, got {type(node).__name__}")
            continue

        node_type = node.get("type")
        if not node_type:
            errors.append(f"{node_path}: missing 'type' field")
            continue

        if node_type not in valid_types:
            errors.append(
                f"{node_path}: unknown {node_kind} type '{node_type}'"
            )

        # Recursively validate nested transformations for container nodes
        if node_kind == "transformation" and node_type in NESTING_NODES:
            # Direct transformations array (ForEach, For, If, BufferData, Switch)
            nested = node.get("transformations")
            if nested is not None:
                validate_nodes(
                    nested, valid_types, "transformation",
                    f"{node_path}.transformations", errors,
                )

            # Switch has cases[].transformations and default
            if node_type == "Switch@1":
                cases = node.get("cases")
                if isinstance(cases, list):
                    for j, case in enumerate(cases):
                        case_transforms = case.get("transformations") if isinstance(case, dict) else None
                        if case_transforms is not None:
                            validate_nodes(
                                case_transforms, valid_types, "transformation",
                                f"{node_path}.cases[{j}].transformations", errors,
                            )

                default = node.get("default")
                if isinstance(default, dict):
                    default_transforms = default.get("transformations")
                    if default_transforms is not None:
                        validate_nodes(
                            default_transforms, valid_types, "transformation",
                            f"{node_path}.default.transformations", errors,
                        )
                elif isinstance(default, list):
                    # default might be a direct list of transformations
                    validate_nodes(
                        default, valid_types, "transformation",
                        f"{node_path}.default", errors,
                    )


def validate_pipeline(pipeline, schema):
    """Validate a pipeline dict against a JSON Schema.

    Returns a list of error strings (empty = valid).
    """
    errors = []

    # Check required top-level sections
    if "triggers" not in pipeline or not pipeline["triggers"]:
        errors.append("Pipeline is missing 'triggers' section (or it is empty)")
    if "transformations" not in pipeline or not pipeline["transformations"]:
        errors.append("Pipeline is missing 'transformations' section (or it is empty)")

    if errors:
        # If structure is fundamentally broken, return early
        return errors

    # Extract valid types from schema
    valid_trigger_types = extract_valid_types(schema, "TriggerNode")
    valid_transform_types = extract_valid_types(schema, "TransformationNode")

    if not valid_trigger_types:
        errors.append("Schema warning: no trigger types found in $defs/TriggerNode")
    if not valid_transform_types:
        errors.append("Schema warning: no transformation types found in $defs/TransformationNode")

    # Validate triggers
    validate_nodes(
        pipeline["triggers"], valid_trigger_types, "trigger", "triggers", errors,
    )

    # Validate transformations (recursive)
    validate_nodes(
        pipeline["transformations"], valid_transform_types, "transformation",
        "transformations", errors,
    )

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate an OctoMesh pipeline YAML against the adapter JSON Schema."
    )
    parser.add_argument("yaml_file", help="Path to the pipeline YAML file")

    schema_group = parser.add_mutually_exclusive_group(required=True)
    schema_group.add_argument(
        "--schema", metavar="FILE",
        help="Path to a local JSON Schema file",
    )
    schema_group.add_argument(
        "--adapter-id", metavar="RTID",
        help="Runtime ID of the adapter to fetch the schema from via octo-cli",
    )

    parser.add_argument(
        "--insecure", action="store_true",
        help="Skip TLS verification when fetching schema from adapter",
    )

    args = parser.parse_args()

    # Load pipeline YAML
    pipeline = load_yaml(args.yaml_file)
    if not isinstance(pipeline, dict):
        print(f"Error: YAML root must be a mapping, got {type(pipeline).__name__}", file=sys.stderr)
        sys.exit(1)

    # Load schema
    if args.schema:
        schema = load_schema_from_file(args.schema)
    else:
        schema = load_schema_from_adapter(args.adapter_id, insecure=args.insecure)

    # Validate
    errors = validate_pipeline(pipeline, schema)

    if errors:
        print(f"FAIL: {len(errors)} validation error(s) found:\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print("PASS: pipeline is valid against the schema.")
        sys.exit(0)


if __name__ == "__main__":
    main()
