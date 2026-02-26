#!/usr/bin/env bash
# Wrapper script that ensures a Python virtual environment exists with
# dependencies installed, then delegates to the venv's Python interpreter.
# Status messages go to stderr so they don't corrupt --json output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MARKER="$VENV_DIR/.installed"

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
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating Python virtual environment..." >&2
    python3 -m venv "$VENV_DIR"
fi

# Install/update dependencies if requirements changed
REQ_HASH="$(_md5 "$REQ_FILE")"
if [ ! -f "$MARKER" ] || [ "$REQ_HASH" != "$(cat "$MARKER")" ]; then
    echo "Installing dependencies..." >&2
    "$VENV_DIR/bin/pip" install --quiet --disable-pip-version-check -r "$REQ_FILE"
    echo "$REQ_HASH" > "$MARKER"
fi

exec "$VENV_DIR/bin/python" "$@"
