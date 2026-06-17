#!/usr/bin/env bash
# Wrapper script that ensures a Python virtual environment exists with
# dependencies installed, then delegates to the venv's Python interpreter.
# Status messages go to stderr so they don't corrupt --json output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MARKER="$VENV_DIR/.installed"

# Detect platform: Windows venvs use Scripts/, Unix uses bin/
if [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]] || [[ "$(uname -s)" == CYGWIN* ]]; then
    PYTHON_CMD="$VENV_DIR/Scripts/python.exe"
    PIP_CMD="$VENV_DIR/Scripts/pip.exe"
    SYS_PYTHON="python"
else
    PYTHON_CMD="$VENV_DIR/bin/python"
    PIP_CMD="$VENV_DIR/bin/pip"
    SYS_PYTHON="python3"
fi

# Portable md5: macOS uses `md5 -q`, Linux uses `md5sum`
_md5() {
    if command -v md5 >/dev/null 2>&1; then
        md5 -q "$1"
    elif command -v md5sum >/dev/null 2>&1; then
        md5sum "$1" | cut -d' ' -f1
    else
        # Fallback: always reinstall if no md5 tool available
        echo "no-md5"
    fi
}

# Create venv if it doesn't exist
if [ ! -f "$PYTHON_CMD" ]; then
    echo "Creating Python virtual environment..." >&2
    $SYS_PYTHON -m venv "$VENV_DIR"
fi

# Install/update dependencies if requirements changed
REQ_HASH="$(_md5 "$REQ_FILE")"
if [ ! -f "$MARKER" ] || [ "$REQ_HASH" != "$(cat "$MARKER")" ]; then
    echo "Installing dependencies..." >&2
    "$PIP_CMD" install --quiet --disable-pip-version-check -r "$REQ_FILE"
    echo "$REQ_HASH" > "$MARKER"
fi

exec "$PYTHON_CMD" "$@"
