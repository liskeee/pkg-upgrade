# install.sh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `curl | bash` installer that installs `mac-upgrade` via pipx when available and falls back to a self-managed venv otherwise.

**Architecture:** Single POSIX-ish bash script at the repo root (`install.sh`). Strict mode (`set -euo pipefail`) with an `ERR` trap for cleanup. Two code paths (pipx / venv fallback) behind a common Python-detection and PATH-hint tail. Accepts `MAC_UPGRADE_REF` env var (default `main`) to pick the git ref. README gains an Install section. No test file — manual verification per spec.

**Tech Stack:** bash, pipx, Python 3.12+ venv, git+https install via pip.

**Spec:** `docs/superpowers/specs/2026-04-12-install-sh-design.md`.

---

### Task 1: Scaffold script skeleton with strict mode and platform guard

**Files:**
- Create: `install.sh`

- [ ] **Step 1: Create `install.sh` with shebang, strict mode, helpers, platform guard**

```bash
#!/usr/bin/env bash
# mac-upgrade installer — https://github.com/liskeee/mac-upgrade
set -euo pipefail

REPO_URL="https://github.com/liskeee/mac-upgrade"
REF="${MAC_UPGRADE_REF:-main}"
SOURCE="git+${REPO_URL}@${REF}"

log()  { printf '==> %s\n' "$*"; }
warn() { printf '==> warning: %s\n' "$*" >&2; }
die()  { printf '==> error: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "mac-upgrade is macOS-only (detected $(uname -s))."

log "Installing mac-upgrade from ${SOURCE}"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x install.sh`

- [ ] **Step 3: Verify platform guard runs and logs header**

Run: `bash install.sh 2>&1 | head -2`
Expected: line `==> Installing mac-upgrade from git+https://github.com/liskeee/mac-upgrade@main` (and then either an error about missing `python3`/`pipx` or continues — both acceptable; later tasks add the rest).

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "feat(install): scaffold curl|bash installer with strict mode and platform guard"
```

---

### Task 2: Add Python 3.12+ detection

**Files:**
- Modify: `install.sh` (append after the platform-guard block from Task 1)

- [ ] **Step 1: Append Python-detection block to `install.sh`**

```bash
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
```

- [ ] **Step 2: Run and verify detection works**

Run: `bash install.sh 2>&1 | head -3`
Expected: second line begins with `==> Using Python: Python 3.1` followed by a version ≥ 3.12.

- [ ] **Step 3: Negative test — simulate missing Python 3.12+**

Run: `PATH=/usr/bin bash install.sh 2>&1 | tail -1`
Expected: `==> error: Python 3.12+ not found. Install with: brew install python@3.12` (macOS system `/usr/bin/python3` is older than 3.12).

If the machine's `/usr/bin/python3` is already 3.12+, skip this negative test and note it on the commit message.

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "feat(install): detect Python 3.12+ (python3.13 → python3.12 → python3)"
```

---

### Task 3: Add pipx-preferred install path

**Files:**
- Modify: `install.sh` (append after the Python-detection block)

- [ ] **Step 1: Append pipx path and brew-bootstrap block**

```bash
INSTALLED_BIN=""

try_pipx() {
    command -v pipx >/dev/null 2>&1 || return 1
    log "Installing via pipx..."
    pipx install --force "$SOURCE"
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
```

- [ ] **Step 2: Verify pipx path works end-to-end**

Prereq: `pipx` must be on PATH (already installed earlier in this session).

Run: `bash install.sh 2>&1 | tail -5`
Expected: output includes `==> Installing via pipx...` and `installed package mac-upgrade 0.1.0` from pipx. `INSTALLED_BIN` is set (no user-visible output yet — step 3 verifies).

- [ ] **Step 3: Verify pipx-installed binary exists**

Run: `ls -l "$(pipx environment --value PIPX_BIN_DIR)/mac-upgrade"`
Expected: symlink or file exists.

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "feat(install): prefer pipx, bootstrap via brew when missing"
```

---

### Task 4: Add venv fallback with ERR-trap cleanup

**Files:**
- Modify: `install.sh` (append after the pipx block)

- [ ] **Step 1: Append venv fallback with cleanup trap**

```bash
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
```

- [ ] **Step 2: Temporarily force the fallback path to exercise it**

Run:
```bash
env -i HOME="$HOME" PATH="/usr/bin:/bin:/opt/homebrew/bin/python3.12:/opt/homebrew/bin" bash install.sh 2>&1 | tail -10
```
(The `env -i` strips `pipx` from PATH even when it's installed; adjust python path if needed.)

If removing pipx from PATH is awkward on your machine, instead temporarily edit `try_pipx` to `return 1` unconditionally, run the script, then revert the edit.

Expected: output includes `==> Installing into self-managed venv at /Users/.../.local/share/mac-upgrade/venv...` and finishes without error.

- [ ] **Step 3: Verify symlink and binary**

Run: `ls -l ~/.local/bin/mac-upgrade && ~/.local/bin/mac-upgrade --version`
Expected: symlink to the venv; `--version` prints `mac-upgrade 0.1.0`.

- [ ] **Step 4: Cleanup**

Run: `rm -rf ~/.local/share/mac-upgrade ~/.local/bin/mac-upgrade`

Run: `pipx reinstall mac-upgrade 2>/dev/null || pipx install -e /Users/liskeee/Projects/Liskeee/mac-upgrade`
(Leave the pipx install in place so the main binary still works after the test.)

- [ ] **Step 5: Commit**

```bash
git add install.sh
git commit -m "feat(install): venv fallback with ERR-trap cleanup on partial install"
```

---

### Task 5: Add PATH-sanity warning and success message

**Files:**
- Modify: `install.sh` (append at end)

- [ ] **Step 1: Append PATH check and smoke test**

```bash
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
```

- [ ] **Step 2: Verify full happy-path output**

Run: `bash install.sh 2>&1 | tail -5`
Expected: ends with `==> ✓ Installed mac-upgrade 0.1.0` and the "Run:" hint line. Either no PATH warning (if bin dir is on PATH) or a clean three-line warning.

- [ ] **Step 3: Commit**

```bash
git add install.sh
git commit -m "feat(install): warn when bin dir missing from PATH; print installed version"
```

---

### Task 6: Document installer in README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README to find the right insertion point**

Run: read `README.md` end-to-end. Locate the existing "Install" / "Installation" / Homebrew section (if any); the new snippet goes at the top of that section. If no install section exists, insert a new `## Install` section immediately after the project intro.

- [ ] **Step 2: Add Install section**

Insert (or extend) the install section with three subsections in this order:

```markdown
## Install

### One-line (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/liskeee/mac-upgrade/main/install.sh | bash
```

Pin a specific version:

```bash
curl -fsSL https://raw.githubusercontent.com/liskeee/mac-upgrade/main/install.sh \
    | MAC_UPGRADE_REF=v0.1.0 bash
```

The installer uses [pipx](https://pipx.pypa.io/) when available and falls
back to a self-managed venv at `~/.local/share/mac-upgrade/`. Requires
Python 3.12+ and macOS.

### Homebrew

```bash
brew install liskeee/tap/mac-upgrade
```

### pipx

```bash
pipx install git+https://github.com/liskeee/mac-upgrade
```

### Uninstall

```bash
# installed via pipx (the default path):
pipx uninstall mac-upgrade

# installed via the venv fallback:
rm -rf ~/.local/share/mac-upgrade ~/.local/bin/mac-upgrade
```
```

- [ ] **Step 3: Verify the README renders sensibly**

Run: `head -60 README.md`
Expected: the Install section appears with the three paths; headings are balanced with the rest of the file.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add Install section covering curl|bash, brew, pipx"
```

---

## Self-review

- **Spec coverage:** platform guard (Task 1) ✓, Python detection (Task 2) ✓, pipx path (Task 3) ✓, brew bootstrap (Task 3) ✓, venv fallback (Task 4) ✓, ERR-trap cleanup (Task 4) ✓, PATH warning (Task 5) ✓, smoke test (Task 5) ✓, README update (Task 6) ✓, `MAC_UPGRADE_REF` (Task 1) ✓. No `--uninstall` flag — matches spec non-goal.
- **Placeholders:** none — every step has the exact code or command.
- **Type/name consistency:** `PY`, `SOURCE`, `REF`, `INSTALLED_BIN`, `VENV`, `BIN_DIR` used consistently across Tasks 1–5. Helper functions (`log`, `warn`, `die`, `find_python`, `try_pipx`) defined once in earlier tasks, used in later ones.
