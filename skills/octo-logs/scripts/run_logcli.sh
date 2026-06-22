#!/usr/bin/env bash
# Wrapper: load the OctoMesh PowerShell profile (which dot-sources the private
# profile holding LOKI_USERNAME / LOKI_PASSWORD), resolve the target cluster's
# Loki datasource-proxy URL, then run logcli. The skill itself never sees or
# handles the credentials — they live only in the PowerShell session.
#
# Usage: bash run_logcli.sh <cluster> <logcli-subcommand> [args...]
#   bash run_logcli.sh test-2 labels
#   bash run_logcli.sh test-2 query --since=1h --limit=20 '{namespace="octo", level="ERROR"}'
#
# Status messages go to stderr so they don't corrupt logcli output on stdout.
set -euo pipefail

# Find the monorepo root by walking up from the current working directory
# looking for octo-tools/modules/profile.ps1 (mirrors octo-devtools/run_pwsh.sh).
find_monorepo_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/octo-tools/modules/profile.ps1" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 2 ]; then
    echo "ERROR: usage: bash run_logcli.sh <cluster> <logcli-subcommand> [args...]" >&2
    echo "  e.g.: bash run_logcli.sh test-2 query --since=1h '{namespace=\"octo\", level=\"ERROR\"}'" >&2
    exit 1
fi

if ! command -v pwsh >/dev/null 2>&1; then
    echo "ERROR: PowerShell (pwsh) is not installed or not on PATH" >&2
    exit 1
fi

if ! command -v logcli >/dev/null 2>&1; then
    echo "ERROR: logcli is not installed or not on PATH. Install it with: brew install logcli" >&2
    exit 1
fi

MONOREPO_ROOT="$(find_monorepo_root)" || {
    echo "ERROR: Could not find monorepo root (no octo-tools/modules/profile.ps1 above $PWD)" >&2
    echo "Run this from within the OctoMesh monorepo workspace." >&2
    exit 1
}
PROFILE="$MONOREPO_ROOT/octo-tools/modules/profile.ps1"

# pwsh -File passes the remaining tokens to the script as literal $args, so the
# LogQL query (with its braces, pipes and quotes) survives without re-parsing.
exec pwsh -NoProfile -NoLogo -File "$SCRIPT_DIR/_logcli.ps1" "$PROFILE" "$@"
