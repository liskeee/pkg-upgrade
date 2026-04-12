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
