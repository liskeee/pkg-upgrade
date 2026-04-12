#!/usr/bin/env bash
# mac-upgrade installer — https://github.com/lukaszlis/mac-upgrade
set -euo pipefail

REPO_URL="https://github.com/lukaszlis/mac-upgrade"
REF="${MAC_UPGRADE_REF:-main}"
SOURCE="git+${REPO_URL}@${REF}"

log()  { printf '==> %s\n' "$*"; }
warn() { printf '==> warning: %s\n' "$*" >&2; }
die()  { printf '==> error: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "mac-upgrade is macOS-only (detected $(uname -s))."

log "Installing mac-upgrade from ${SOURCE}"

find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'; then
                printf '%s\n' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PY="$(find_python)" || die "Python 3.12+ not found. Install with: brew install python@3.12"
log "Using Python: $("$PY" --version) ($(command -v "$PY"))"
