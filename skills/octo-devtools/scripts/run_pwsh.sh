#!/usr/bin/env bash
# Wrapper script that loads the OctoMesh PowerShell profile and runs a command.
# Status messages go to stderr so they don't corrupt structured output.
#
# Usage: bash run_pwsh.sh "Invoke-BuildAll -configuration DebugL"
#        bash run_pwsh.sh "Get-AllGitRepStatus"

set -euo pipefail

# Find the monorepo root by walking up from the current working directory
# looking for octo-tools/modules/profile.ps1. This works regardless of where
# the script itself is located (e.g., plugin cache vs monorepo checkout).
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

MONOREPO_ROOT="$(find_monorepo_root)" || {
    echo "ERROR: Could not find monorepo root (no octo-tools/modules/profile.ps1 found above $PWD)" >&2
    echo "Ensure the working directory is within the OctoMesh monorepo workspace." >&2
    exit 1
}
PROFILE_UNIX="$MONOREPO_ROOT/octo-tools/modules/profile.ps1"

# Verify pwsh is available
if ! command -v pwsh >/dev/null 2>&1; then
    echo "ERROR: PowerShell (pwsh) is not installed or not on PATH" >&2
    echo "Install it from: https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell" >&2
    exit 1
fi

# Verify profile exists
if [ ! -f "$PROFILE_UNIX" ]; then
    echo "ERROR: Profile not found at $PROFILE_UNIX" >&2
    echo "Ensure octo-tools is checked out at $MONOREPO_ROOT/octo-tools/" >&2
    exit 1
fi

# Convert MSYS2/Git Bash path to Windows path for PowerShell.
# /c/dev/meshmakers/... → C:\dev\meshmakers\... (pwsh cannot resolve Unix-style paths)
if command -v cygpath >/dev/null 2>&1; then
    PROFILE="$(cygpath -w "$PROFILE_UNIX")"
else
    PROFILE="$PROFILE_UNIX"
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
