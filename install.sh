#!/usr/bin/env bash
# pkg-upgrade installer — https://github.com/liskeee/pkg-upgrade
set -euo pipefail

REPO_URL="https://github.com/liskeee/pkg-upgrade"
REF="${PKG_UPGRADE_REF:-main}"
# PKG_UPGRADE_SOURCE overrides the pip spec entirely (useful for local/dev installs).
SOURCE="${PKG_UPGRADE_SOURCE:-git+${REPO_URL}@${REF}}"

log()  { printf '==> %s\n' "$*"; }
warn() { printf '==> warning: %s\n' "$*" >&2; }
die()  { printf '==> error: %s\n' "$*" >&2; exit 1; }

case "$(uname -s)" in
    Darwin|Linux) ;;
    *) die "install.sh supports macOS and Linux only (detected $(uname -s)). Use install.ps1 on Windows." ;;
esac

log "Installing pkg-upgrade from ${SOURCE}"

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
    INSTALLED_BIN="$(pipx environment --value PIPX_BIN_DIR)/pkg-upgrade"
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
    VENV="$HOME/.local/share/pkg-upgrade/venv"
    BIN_DIR="$HOME/.local/bin"

    cleanup_failed_venv() { rm -rf "$VENV"; }
    trap cleanup_failed_venv ERR

    log "Installing into self-managed venv at ${VENV}..."
    rm -rf "$VENV"
    mkdir -p "$(dirname "$VENV")" "$BIN_DIR"
    "$PY" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet "$SOURCE"
    ln -sf "$VENV/bin/pkg-upgrade" "$BIN_DIR/pkg-upgrade"
    INSTALLED_BIN="$BIN_DIR/pkg-upgrade"

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
log "Run: pkg-upgrade --onboard (first-time setup) or pkg-upgrade"

install_completion() {
    local shell_name
    shell_name="$(basename "${SHELL:-bash}")"
    # Locate the packaged completions dir. Try pipx venv first, then self-managed.
    local pkg_dir=""
    local candidate
    for candidate in \
        "${PKG_UPGRADE_PREFIX:-}/bin/python" \
        "$HOME/.local/pipx/venvs/pkg-upgrade/bin/python" \
        "$HOME/.local/share/pkg-upgrade/venv/bin/python" \
        "$(command -v python3 2>/dev/null)"; do
        if [ -n "$candidate" ] && [ -x "$candidate" ]; then
            pkg_dir="$("$candidate" -c 'import pkg_upgrade, os; print(os.path.dirname(pkg_upgrade.__file__))' 2>/dev/null || true)"
            [ -n "$pkg_dir" ] && break
        fi
    done
    [ -z "$pkg_dir" ] && return 0
    local comp_dir="$pkg_dir/completions"
    [ -d "$comp_dir" ] || return 0

    case "$shell_name" in
        bash)
            # Target: $HOME/.local/share/bash-completion/completions/pkg-upgrade
            local dest="$HOME/.local/share/bash-completion/completions"
            mkdir -p "$dest"
            cp -f "$comp_dir/pkg-upgrade.bash" "$dest/pkg-upgrade"
            echo "Installed bash completion -> $dest/pkg-upgrade"
            ;;
        zsh)
            # Target: $HOME/.zsh/completions/_pkg-upgrade
            local dest="$HOME/.zsh/completions"
            mkdir -p "$dest"
            cp -f "$comp_dir/_pkg-upgrade" "$dest/_pkg-upgrade"
            local rc="$HOME/.zshrc"
            local line='fpath+=("$HOME/.zsh/completions")'
            if [ -f "$rc" ] && ! grep -Fq "$line" "$rc"; then
                printf '\n# Added by pkg-upgrade installer\n%s\nautoload -Uz compinit && compinit\n' "$line" >> "$rc"
            fi
            echo "Installed zsh completion -> $dest/_pkg-upgrade"
            ;;
        fish)
            # Target: $HOME/.config/fish/completions/pkg-upgrade.fish
            local dest="$HOME/.config/fish/completions"
            mkdir -p "$dest"
            cp -f "$comp_dir/pkg-upgrade.fish" "$dest/pkg-upgrade.fish"
            echo "Installed fish completion -> $dest/pkg-upgrade.fish"
            ;;
        *)
            echo "Shell '$shell_name' unsupported for auto-completion install."
            echo "Run: pkg-upgrade completion <bash|zsh|fish|powershell>  to print a script."
            ;;
    esac
    echo "Restart your shell (or 'exec \$SHELL') to activate completion."
}

install_completion
