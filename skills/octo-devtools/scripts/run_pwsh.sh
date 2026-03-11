#!/usr/bin/env bash
# Wrapper script that loads the OctoMesh PowerShell profile and runs a command.
# Status messages go to stderr so they don't corrupt structured output.
#
# Usage: bash run_pwsh.sh "Invoke-BuildAll -configuration DebugL"
#        bash run_pwsh.sh "Get-AllGitRepStatus"

set -euo pipefail

# Self-locate: derive paths from this script's location
# Script lives at <monorepo>/octo-claude-skills/skills/octo-devtools/scripts/run_pwsh.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PROFILE="$MONOREPO_ROOT/octo-tools/modules/profile.ps1"

# Verify pwsh is available
if ! command -v pwsh >/dev/null 2>&1; then
    echo "ERROR: PowerShell (pwsh) is not installed or not on PATH" >&2
    echo "Install it from: https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell" >&2
    exit 1
fi

# Verify profile exists
if [ ! -f "$PROFILE" ]; then
    echo "ERROR: Profile not found at $PROFILE" >&2
    echo "Ensure octo-tools is checked out at $MONOREPO_ROOT/octo-tools/" >&2
    exit 1
fi

# Join all arguments as a single PowerShell command string
if [ $# -eq 0 ]; then
    echo "ERROR: No command provided" >&2
    echo "Usage: bash run_pwsh.sh \"<PowerShell command>\"" >&2
    exit 1
fi

COMMAND="$*"

echo "Loading OctoMesh profile and running: $COMMAND" >&2

exec pwsh -NoProfile -NoLogo -Command ". '$PROFILE'; $COMMAND"
