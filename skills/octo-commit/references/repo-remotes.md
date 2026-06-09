# Repo Remotes Reference

Mapping of local OctoMesh repo directories to their git remotes and the correct PR tool.
Verify any uncertain entry before pushing: `git -C <repo> remote get-url origin`.

| Repo | Remote | PR Tool |
|------|--------|---------|
| Most `octo-*` repos | `meshmakers/<repo>` (GitHub) | `gh pr create` |
| octo-mcp-service | `meshmakers/octo-mcp-service` (GitHub) | `gh pr create` |
| octo-communication-operator | `meshmakers/octo-communication-operator` (GitHub) | `gh pr create` |
| octo-frontend-refinery-studio | `meshmakers/octo-frontend-refinery-studio` (GitHub) | `gh pr create` |
| octo-frontend-libraries | `meshmakers/octo-frontend-libraries` (GitHub) | `gh pr create` |
| octo-construction-kit | `meshmakers/octo-construction-kit` (GitHub) | `gh pr create` |
| octo-construction-kit-engine-mongodb | `meshmakers/octo-construction-kit-engine-mongodb` (GitHub) | `gh pr create` |
| octo-helm-core | `meshmakers/octo-helm-core` (GitHub) | `gh pr create` |
| octo-documentation | `meshmakers/octo-documentation` (GitHub) | `gh pr create` |
| octo-distributedEventHub | `meshmakers/octo-distributedEventHub` (GitHub) | `gh pr create` |
| `meshmakers_staging` | `meshmakers/OctoMesh/meshmakers_staging` (Azure DevOps) | `az repos pr create` |
| pipeline-editor | `reikla/pipeline-editor` (GitHub) | `gh pr create --repo reikla/pipeline-editor` |
| docs (local dir) | `reikla/ai-docs` (GitHub) | `gh pr create --repo reikla/ai-docs` |
| zenon-dynprop-api | `reikla/zenon-dynprop-api` (GitHub) | `gh pr create --repo reikla/zenon-dynprop-api` |
| aspire-management-prototype | `reikla/aspire-management-prototype` (GitHub) | `gh pr create --repo reikla/aspire-management-prototype` |

**CRITICAL:** The local directory `docs` maps to the GitHub repo `reikla/ai-docs` (NOT `reikla/docs`).

**Hosts:**
- `meshmakers/<repo>` and `reikla/<repo>` are GitHub — use `gh pr create` (add `--repo reikla/<name>` for reikla-owned repos).
- `meshmakers_staging` is the sole Azure DevOps-hosted repo — use `az repos pr create`.
