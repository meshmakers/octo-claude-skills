"""Verification script for Step 4: SKILL.md updates."""
import os
import sys

SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md")

print("=== Step 4 Verification: SKILL.md ===")
print()

with open(SKILL) as f:
    content = f.read()

# 1. Frontmatter description mentions data model / CK / GraphQL
print("1. Frontmatter description check...")
lines = content.split("\n")
# Find description line (within frontmatter)
desc_line = ""
for line in lines[:10]:
    if line.startswith("description:"):
        desc_line = line.lower()
        break
assert "data model" in desc_line, "Missing 'data model' in description"
assert "construction kit" in desc_line or "ck type" in desc_line, "Missing CK reference in description"
assert "graphql" in desc_line, "Missing 'graphql' in description"
print("   OK — description mentions data model, CK, and GraphQL")

# 2. New section exists with script references
print()
print("2. Script references check...")
ck_count = content.count("ck_explorer.py")
gql_count = content.count("gql_introspect.py")
assert ck_count >= 5, f"Expected >= 5 references to ck_explorer.py, got {ck_count}"
assert gql_count >= 2, f"Expected >= 2 references to gql_introspect.py, got {gql_count}"
print(f"   OK — ck_explorer.py referenced {ck_count} times, gql_introspect.py referenced {gql_count} times")

# 3. Routing table exists
print()
print("3. Routing table check...")
assert "When to Use Scripts vs octo-cli" in content or "scripts vs octo-cli" in content.lower(), \
    "Missing routing table section"
print("   OK — routing table section found")

# 4. Exploration workflow exists
print()
print("4. Exploration workflow check...")
assert "Exploration Workflow" in content, "Missing exploration workflow section"
assert "drill-down" in content.lower() or "progressive" in content.lower(), \
    "Missing progressive/drill-down mention"
print("   OK — exploration workflow section found")

# 5. Valid YAML frontmatter
print()
print("5. YAML frontmatter check...")
assert content.startswith("---"), "Missing frontmatter start"
end = content.index("---", 3)
print(f"   OK — frontmatter valid, ends at char {end}")

# 6. Schema evolution handling section
print()
print("6. Schema evolution section check...")
assert "Schema Evolution" in content, "Missing schema evolution section"
print("   OK — schema evolution handling section found")

print()
print("=== Step 4: ALL CHECKS PASSED ===")
