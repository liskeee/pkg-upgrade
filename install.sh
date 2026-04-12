#!/usr/bin/env bash
# mac-upgrade installer — https://github.com/liskeee/mac-upgrade
set -euo pipefail

REPO_URL="https://github.com/liskeee/mac-upgrade"
REF="${MAC_UPGRADE_REF:-main}"
# MAC_UPGRADE_SOURCE overrides the pip spec entirely (useful for local/dev installs).
SOURCE="${MAC_UPGRADE_SOURCE:-git+${REPO_URL}@${REF}}"

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

INSTALLED_BIN=""

try_pipx() {
    command -v pipx >/dev/null 2>&1 || return 1
    log "Installing via pipx..."
    pipx install --force "$SOURCE" || return 1
    INSTALLED_BIN="$(pipx environment --value PIPX_BIN_DIR)/mac-upgrade"
    return 0
}

if ! try_pipx; then
    if command -v brew >/dev/null 2>&1; then
        log "pipx not found — installing via Homebrew..."
        brew install pipx
        try_pipx || warn "pipx installed but still unavailable; falling back to venv."
    fi
fi

if [[ -z "$INSTALLED_BIN" ]]; then
    VENV="$HOME/.local/share/mac-upgrade/venv"
    BIN_DIR="$HOME/.local/bin"

    cleanup_failed_venv() { rm -rf "$VENV"; }
    trap cleanup_failed_venv ERR

    log "Installing into self-managed venv at ${VENV}..."
    rm -rf "$VENV"
    mkdir -p "$(dirname "$VENV")" "$BIN_DIR"
    "$PY" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet "$SOURCE"
    ln -sf "$VENV/bin/mac-upgrade" "$BIN_DIR/mac-upgrade"
    INSTALLED_BIN="$BIN_DIR/mac-upgrade"

    trap - ERR
fi

bin_dir="$(dirname "$INSTALLED_BIN")"
case ":$PATH:" in
    *":${bin_dir}:"*) ;;
    *)
        warn "${bin_dir} is not on your PATH."
        warn "Add this line to ~/.zshrc or ~/.bash_profile:"
        warn "    export PATH=\"${bin_dir}:\$PATH\""
        ;;
esac

VERSION="$("$INSTALLED_BIN" --version)"
log "✓ Installed ${VERSION}"
log "Run: mac-upgrade --onboard (first-time setup) or mac-upgrade"
