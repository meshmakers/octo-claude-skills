# Pipeline JSON Schema Guide

## What Is the Pipeline Schema?

Every OctoMesh adapter generates a **JSON Schema (draft 2020-12)** describing all pipeline nodes it supports — triggers, transformations, and their properties, types, enums, and descriptions. This schema is the authoritative, machine-generated source of truth for pipeline node configuration. Each adapter's schema includes the shared SDK nodes plus its own adapter-specific nodes.

## Schema Locations

Each adapter generates its schema at build time via an MSBuild target that runs after `dotnet build`. The schema files are only present after the respective adapter has been built locally (e.g., `dotnet build -c DebugL`).

| Adapter | Schema Path (relative to monorepo root) | Typical Use |
|---------|----------------------------------------|-------------|
| **Mesh Adapter** | `octo-mesh-adapter/bin/DebugL/net10.0/pipeline-schema.json` | Most common; richest node set |
| **EDA Adapter** | `octo-adapter-eda/bin/DebugL/net10.0/pipeline-schema.json` | Energy data pipelines |
| **Zenon Adapter** | `octo-plug-zenon/src/Octo.Edge.Adapter.Zenon.WindowsService/bin/DebugL/net10.0/pipeline-schema.json` | SCADA integration pipelines |
| **Simulation Adapter** | `octo-sdk/src/Sdk.Plug.Simulation/bin/DebugL/net10.0/pipeline-schema.json` | Test/simulation pipelines |

**Which schema to use:** Pick the adapter implementation that will execute the pipeline. The Mesh Adapter schema is the most common choice as it has the richest set of nodes. For adapter-specific nodes (EDA, Zenon, Simulation), use that adapter's schema.

**If the schema file does not exist**, fall back to the hand-maintained node reference docs (`node-reference-sdk.md` for shared SDK nodes and `node-reference-mesh.md` for Mesh Adapter nodes).

## Schema Structure

The root document has:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "triggers": { "type": "array", "items": { "$ref": "#/$defs/TriggerNode" } },
    "transformations": { "type": "array", "items": { "$ref": "#/$defs/TransformationNode" } }
  },
  "$defs": {
    "TriggerNode": { "oneOf": [ ...trigger node schemas... ] },
    "TransformationNode": { "oneOf": [ ...transformation node schemas... ] },
    "NodeName@Version_NestedDef": { ... }
  }
}
```

### Node Schema Shape

Each node in `TriggerNode.oneOf` or `TransformationNode.oneOf` looks like:

```json
{
  "title": "ForEachNodeConfiguration",
  "type": "object",
  "description": "Configuration for a for loop node.",
  "properties": {
    "type": { "type": "string", "const": "ForEach@1" },
    "iterationPath": { "type": "string", "description": "..." },
    "maxDegreeOfParallelism": { "type": "integer", "description": "...", "format": "int32" },
    "targetValueWriteMode": { "oneOf": [{ "$ref": "#/$defs/ForEach@1_TargetValueWriteModes" }] }
  },
  "required": ["type"]
}
```

Key elements:
- **`properties.type.const`** — the discriminator (`"NodeName@Version"`)
- **`properties`** — all valid configuration properties with types and descriptions
- **`required`** — mandatory properties (always includes `"type"`)
- **`$ref` entries** — point to `$defs` for enum types and nested objects (e.g., `ForEach@1_TargetValueWriteModes`)

### Enum Definitions

Enum `$defs` entries list all valid values in both PascalCase and CONSTANT_CASE:

```json
{
  "ForEach@1_TargetValueWriteModes": {
    "type": "string",
    "enum": ["Overwrite", "OVERWRITE", "Append", "APPEND", "Prepend", "PREPEND", "Merge", "MERGE"]
  }
}
```

Either casing is accepted. The reference docs use PascalCase.

## Using the Schema for Validation

When validating a pipeline YAML that a user has written or that you generated:

1. **Read the schema file** — because it is minified single-line JSON (~47k tokens), use `Bash` with a targeted `python3` or `jq` command to extract specific node definitions rather than reading the whole file. Use the schema path for the target adapter (see Schema Locations above). For example, using the Mesh Adapter schema:

   ```bash
   cat octo-mesh-adapter/bin/DebugL/net10.0/pipeline-schema.json | python3 -c "
   import json, sys
   schema = json.load(sys.stdin)
   defs = schema['\$defs']
   # Find a specific node in TransformationNode oneOf
   for item in defs.get('TransformationNode', {}).get('oneOf', []) + defs.get('TriggerNode', {}).get('oneOf', []):
       if item.get('properties', {}).get('type', {}).get('const') == 'ForEach@1':
           print(json.dumps(item, indent=2))
           break
   "
   ```

2. **For each node in the pipeline**, look up its `type` value in the schema's `$defs.TriggerNode.oneOf` or `$defs.TransformationNode.oneOf`.

3. **Check required properties** — verify all entries in the `required` array are present.

4. **Check property names** — any property not listed in the schema's `properties` object for that node is invalid.

5. **Check enum values** — for enum-typed properties, verify the value matches one of the `enum` array entries.

6. **Resolve `$ref` entries** — nested object and enum types are in `$defs` with keys like `NodeName@Version_DefName`.

## Using the Schema as Reference

When creating a pipeline and you need exact property names, types, or available enum values:

1. **Look up the node** by `type` const in the schema
2. **Read the `description`** field for the node and each property — these come from C# XML documentation and explain the purpose
3. **Check property types** — `string`, `integer`, `boolean`, `array`, or `$ref` to a nested definition
4. **List available enum values** from the referenced `$defs` entry

This is more reliable than the hand-maintained reference docs for edge cases, since the schema is auto-generated from the source code.

## Schema Generation Mechanism

Schema generation is a **shared SDK capability** that all adapters inherit automatically. The `NodeSchemaRegistry` and `PipelineSchemaGenerator` classes in `octo-sdk` provide the implementation:

1. Each pipeline node has a C# configuration class annotated with `[NodeName("Name", Version)]`
2. Adapters register nodes via `AddDataPipeline()` (SDK base nodes) and adapter-specific methods like `AddOctoMeshAdapter()`, each calling `RegisterNode<T>()` or `RegisterTriggerNode<T>()`
3. An MSBuild target (`GeneratePipelineSchema`) runs after each build, invoking the adapter with `--generate-pipeline-schema <output-path>` to produce the schema file
4. `NJsonSchema` generates a JSON Schema from each registered configuration class; XML documentation comments on C# properties become `description` fields
5. Integer-backed enums are converted to string enums with both PascalCase and CONSTANT_CASE values
6. Individual node schemas are composited into a single document with `TriggerNode.oneOf` and `TransformationNode.oneOf` discriminated unions

Each adapter's schema covers **all nodes it has registered** — shared SDK nodes (control flow, transforms, buffering) plus adapter-specific nodes (e.g., the Mesh Adapter adds entity CRUD and domain nodes, the EDA Adapter adds energy protocol nodes, the Zenon Adapter adds SCADA nodes).
