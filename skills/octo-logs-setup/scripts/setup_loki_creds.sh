#!/usr/bin/env bash
# Safely store Loki (monitoring Grafana) credentials in the private PowerShell
# profile that the octo-tools profile dot-sources at load time. The password is
# read from STDIN only — never passed as a CLI argument (so it can't leak into
# shell history or a process listing) and never printed back.
#
# Subcommands:
#   status
#       Report the private-profile path, its perms, and which LOKI_* variables
#       are already defined in it. Prints variable NAMES only — never values.
#
#   write [-u <username>] [-c <cluster>]
#       Read the password from STDIN and write/update the credential exports in
#       the private profile (perms forced to 600). Default username: mesh-admin.
#       With -c, writes per-cluster vars LOKI_USERNAME_<SUF> / LOKI_PASSWORD_<SUF>
#       (SUF = uppercase cluster, dashes removed, e.g. prod-1 -> PROD1); without
#       -c, writes the generic LOKI_USERNAME / LOKI_PASSWORD.
#
# Recommended (keeps the secret out of any command output) — fetch from Vault and
# pipe straight in; run it yourself in-session with the `!` prefix:
#   ! vault kv get -field=admin_password meshmakers/test-2/grafana | \
#       bash <this-script> write -c test-2
#
# Override the target file for testing with OCTO_LOGS_PRIVATE_PROFILE=/path.
set -euo pipefail

# --- locate the private profile the octo-tools profile loads -----------------
# macOS:  ~/.config/powershell/Microsoft.PowerShell_profile_private.ps1
# others: ~/.pwsh/profile.ps1   (per octo-tools/modules/profile.ps1)
private_profile_path() {
    if [ -n "${OCTO_LOGS_PRIVATE_PROFILE:-}" ]; then
        echo "$OCTO_LOGS_PRIVATE_PROFILE"; return
    fi
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "$HOME/.config/powershell/Microsoft.PowerShell_profile_private.ps1"
    else
        echo "$HOME/.pwsh/profile.ps1"
    fi
}

cluster_suffix() {
    # prod-1 -> PROD1 ; test-2 -> TEST2 ; staging-1 -> STAGING1
    echo "$1" | tr '[:lower:]' '[:upper:]' | tr -d '-'
}

cmd_status() {
    local pp; pp="$(private_profile_path)"
    echo "Private profile: $pp"
    if [ ! -f "$pp" ]; then
        echo "  (does not exist yet — 'write' will create it)"
        return 0
    fi
    local perms
    perms="$(stat -f '%Lp' "$pp" 2>/dev/null || stat -c '%a' "$pp" 2>/dev/null || echo '?')"
    echo "  perms: $perms"
    echo "  defined LOKI_* variables:"
    if grep -oE '\$env:LOKI_[A-Z0-9_]+' "$pp" 2>/dev/null | sort -u | sed 's/^/    /'; then
        :
    fi
    if ! grep -qE '\$env:LOKI_(USERNAME|PASSWORD)' "$pp" 2>/dev/null; then
        echo "    (none — run 'write' to add them)"
    fi
}

cmd_write() {
    local user="mesh-admin" cluster=""
    while [ $# -gt 0 ]; do
        case "$1" in
            -u) user="$2"; shift 2 ;;
            -c) cluster="$2"; shift 2 ;;
            *)  echo "ERROR: unknown arg '$1'" >&2; exit 1 ;;
        esac
    done

    if [ -t 0 ]; then
        echo "ERROR: no password on STDIN. Pipe it in, e.g.:" >&2
        echo "  vault kv get -field=admin_password meshmakers/<cluster>/grafana | bash $0 write -c <cluster>" >&2
        echo "  printf %s 'PASTED_PASSWORD' | bash $0 write" >&2
        exit 1
    fi
    local pass; pass="$(cat)"
    pass="${pass%$'\n'}"
    if [ -z "$pass" ]; then echo "ERROR: empty password on STDIN" >&2; exit 1; fi

    local uvar="LOKI_USERNAME" pvar="LOKI_PASSWORD"
    if [ -n "$cluster" ]; then
        local suf; suf="$(cluster_suffix "$cluster")"
        uvar="LOKI_USERNAME_$suf"; pvar="LOKI_PASSWORD_$suf"
    fi

    # PowerShell single-quoted string: escape ' as ''.
    local user_esc pass_esc
    user_esc="${user//\'/\'\'}"
    pass_esc="${pass//\'/\'\'}"

    local pp; pp="$(private_profile_path)"
    mkdir -p "$(dirname "$pp")"
    touch "$pp"; chmod 600 "$pp"

    # Drop any existing assignments for these two vars, then append fresh ones.
    local tmp; tmp="$(mktemp)"
    grep -vE "^\\\$env:($uvar|$pvar)[[:space:]]*=" "$pp" > "$tmp" || true
    {
        echo "\$env:$uvar = '$user_esc'"
        echo "\$env:$pvar = '$pass_esc'"
    } >> "$tmp"
    mv "$tmp" "$pp"
    chmod 600 "$pp"

    echo "Wrote \$env:$uvar and \$env:$pvar to $pp (perms 600)."
    echo "Open a fresh shell (or re-load the octo-tools profile) for them to take effect."
}

case "${1:-}" in
    status) shift; cmd_status "$@" ;;
    write)  shift; cmd_write "$@" ;;
    *) echo "usage: $0 {status|write [-u <username>] [-c <cluster>]}" >&2; exit 1 ;;
esac
