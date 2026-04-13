# pkg-upgrade Distribution & Release Automation Plan (Plan 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `pkg-upgrade` installable and auto-releasable on macOS, Linux, and Windows via PyPI, Homebrew tap, Scoop bucket, `install.sh`, and `install.ps1`, with one push-to-main release workflow.

**Architecture:** Keep the existing `release.yml` semantic-release → PyPI pipeline; rename its lingering `mac-upgrade` references. Extend it with a `scoop-bump.yml` that writes the new manifest into `liskeee/scoop-bucket`. Rewrite `install.sh` env var names and `Formula/pkg-upgrade.rb` metadata, and ship a new `install.ps1` + `scoop/pkg-upgrade.json` template. The Scoop manifest points at the wheel built by the release job.

**Tech Stack:** Python 3.12+, python-semantic-release 9, GitHub Actions, Homebrew Ruby DSL, Scoop JSON manifest, PowerShell 5.1+, bash.

**Branch:** `feat/pkg-upgrade-distribution` off `main`.

---

## Files to touch

- Modify: `.github/workflows/release.yml` — fix PyPI environment URL; attach wheel to GH release so downstream jobs can fetch it.
- Modify: `.github/workflows/formula-bump.yml` — point at `Formula/pkg-upgrade.rb` (not `mac-upgrade.rb`).
- Create: `.github/workflows/scoop-bump.yml` — mirror of formula-bump, targeting `liskeee/scoop-bucket`.
- Modify: `install.sh` — rename env vars `MAC_UPGRADE_*` → `PKG_UPGRADE_*`; update venv path; update error message for non-macOS to allow Linux.
- Create: `install.ps1` — Windows installer mirroring `install.sh` behaviour.
- Create: `scoop/pkg-upgrade.json` — committed Scoop manifest template (source of truth for scoop-bump).
- Modify: `Formula/pkg-upgrade.rb` — update description to say macOS + Linux (already macOS-only text).
- Create: `tests/test_installers.py` — lightweight shell-out / text assertions on the two installer scripts.
- Modify: `README.md` — add Windows install instructions.

---

### Task 1: Fix stale `mac-upgrade` references in release.yml

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Read current file**

Run: `cat .github/workflows/release.yml`
Expected: a `release` job with `environment.url: https://pypi.org/project/mac-upgrade/`.

- [ ] **Step 2: Change the PyPI URL**

Replace `https://pypi.org/project/mac-upgrade/` with `https://pypi.org/project/pkg-upgrade/`.

- [ ] **Step 3: Attach built wheel to the GitHub Release so downstream jobs can fetch it**

After the `Publish GitHub Release` step, add:

```yaml
      - name: Upload wheel to release
        if: hashFiles('dist/*.whl') != ''
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG=$(git describe --tags --abbrev=0)
          gh release upload "$TAG" dist/*.whl --clobber
```

- [ ] **Step 4: Validate YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`
Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci(release): fix PyPI URL to pkg-upgrade and attach wheel to GH release"
```

---

### Task 2: Fix Formula path in formula-bump.yml

**Files:**
- Modify: `.github/workflows/formula-bump.yml`

- [ ] **Step 1: Replace the hard-coded formula path**

In `.github/workflows/formula-bump.yml`, globally replace `Formula/mac-upgrade.rb` with `Formula/pkg-upgrade.rb`. There are two occurrences (in the Python heredoc and in the `brew update-python-resources` step).

- [ ] **Step 2: Validate YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/formula-bump.yml'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Verify no `mac-upgrade` remains**

Run: `grep -n mac-upgrade .github/workflows/formula-bump.yml || echo OK`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/formula-bump.yml
git commit -m "ci(formula-bump): target Formula/pkg-upgrade.rb"
```

---

### Task 3: Ship the committed Scoop manifest template

**Files:**
- Create: `scoop/pkg-upgrade.json`

**Context:** Scoop manifests are plain JSON. We commit a template with a placeholder version/URL; `scoop-bump.yml` (Task 4) rewrites the `version`, `url`, and `hash` on release.

- [ ] **Step 1: Create the manifest**

Create `scoop/pkg-upgrade.json`:

```json
{
    "version": "0.0.0",
    "description": "A cross-platform TUI that upgrades every package manager on your system",
    "homepage": "https://github.com/liskeee/pkg-upgrade",
    "license": "MIT",
    "depends": "python",
    "url": "https://github.com/liskeee/pkg-upgrade/releases/download/v0.0.0/pkg_upgrade-0.0.0-py3-none-any.whl",
    "hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "installer": {
        "script": [
            "$whl = \"$dir\\$(Split-Path -Leaf $url)\"",
            "python -m pip install --user --force-reinstall --no-deps \"$whl\" | Out-Null",
            "python -m pip install --user --upgrade textual PyYAML platformdirs | Out-Null"
        ]
    },
    "bin": "pkg-upgrade.exe",
    "checkver": {
        "github": "https://github.com/liskeee/pkg-upgrade"
    },
    "autoupdate": {
        "url": "https://github.com/liskeee/pkg-upgrade/releases/download/v$version/pkg_upgrade-$version-py3-none-any.whl"
    }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python3 -c "import json; json.load(open('scoop/pkg-upgrade.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add scoop/pkg-upgrade.json
git commit -m "feat(scoop): add manifest template for pkg-upgrade"
```

---

### Task 4: Add scoop-bump workflow

**Files:**
- Create: `.github/workflows/scoop-bump.yml`

**Context:** Triggered on release publish. Recomputes `version`/`url`/`hash` from the wheel attached to the release (Task 1), then pushes the result into `liskeee/scoop-bucket` via PR.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/scoop-bump.yml`:

```yaml
name: Bump Scoop Manifest

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      tag:
        description: "Release tag to bump manifest to (e.g. v1.2.0)"
        required: true

permissions:
  contents: write
  pull-requests: write

jobs:
  bump:
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.release.prerelease == false }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          ref: main
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Resolve tag
        id: tag
        run: |
          TAG="${{ github.event.inputs.tag || github.event.release.tag_name }}"
          VERSION="${TAG#v}"
          echo "tag=$TAG" >> "$GITHUB_OUTPUT"
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Download wheel and compute SHA256
        id: wheel
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG="${{ steps.tag.outputs.tag }}"
          VERSION="${{ steps.tag.outputs.version }}"
          WHEEL="pkg_upgrade-${VERSION}-py3-none-any.whl"
          URL="https://github.com/${{ github.repository }}/releases/download/${TAG}/${WHEEL}"
          curl -fsSL "$URL" -o "$WHEEL"
          HASH=$(sha256sum "$WHEEL" | awk '{print $1}')
          echo "url=$URL" >> "$GITHUB_OUTPUT"
          echo "hash=$HASH" >> "$GITHUB_OUTPUT"

      - name: Rewrite scoop/pkg-upgrade.json
        env:
          VERSION: ${{ steps.tag.outputs.version }}
          URL: ${{ steps.wheel.outputs.url }}
          HASH: ${{ steps.wheel.outputs.hash }}
        run: |
          python3 <<'PY'
          import json, os, pathlib
          p = pathlib.Path("scoop/pkg-upgrade.json")
          m = json.loads(p.read_text())
          m["version"] = os.environ["VERSION"]
          m["url"] = os.environ["URL"]
          m["hash"] = os.environ["HASH"]
          p.write_text(json.dumps(m, indent=4) + "\n")
          PY

      - name: Open PR against this repo
        uses: peter-evans/create-pull-request@v8
        with:
          branch: scoop-bump/${{ steps.tag.outputs.tag }}
          commit-message: "chore(scoop): bump to ${{ steps.tag.outputs.tag }}"
          title: "chore(scoop): bump to ${{ steps.tag.outputs.tag }}"
          body: |
            Automated Scoop manifest bump for ${{ steps.tag.outputs.tag }}.

            - Updated `version`, `url`, `hash`
          labels: scoop
          base: main

      - name: Mirror manifest into liskeee/scoop-bucket
        if: ${{ secrets.SCOOP_PUSH_TOKEN != '' }}
        env:
          GH_TOKEN: ${{ secrets.SCOOP_PUSH_TOKEN }}
          TAG: ${{ steps.tag.outputs.tag }}
        run: |
          git clone --depth 1 "https://x-access-token:${GH_TOKEN}@github.com/liskeee/scoop-bucket.git" bucket
          mkdir -p bucket/bucket
          cp scoop/pkg-upgrade.json bucket/bucket/pkg-upgrade.json
          cd bucket
          git -c user.name=github-actions -c user.email=actions@github.com \
              commit -am "pkg-upgrade: bump to ${TAG}" || exit 0
          git push origin HEAD:main
```

- [ ] **Step 2: Validate YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/scoop-bump.yml'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/scoop-bump.yml
git commit -m "ci(scoop): auto-bump manifest and mirror into scoop-bucket"
```

---

### Task 5: Rename env vars and drop macOS gate in install.sh

**Files:**
- Modify: `install.sh`

**Context:** The script currently hard-exits on non-Darwin and uses `MAC_UPGRADE_*` env vars. Linux is now supported; env vars should use `PKG_UPGRADE_*`.

- [ ] **Step 1: Read current script**

Run: `head -30 install.sh`

- [ ] **Step 2: Replace env var names and relax platform gate**

Open `install.sh`. Replace these lines:

```bash
REF="${MAC_UPGRADE_REF:-main}"
# MAC_UPGRADE_SOURCE overrides the pip spec entirely (useful for local/dev installs).
SOURCE="${MAC_UPGRADE_SOURCE:-git+${REPO_URL}@${REF}}"
```

With:

```bash
REF="${PKG_UPGRADE_REF:-main}"
# PKG_UPGRADE_SOURCE overrides the pip spec entirely (useful for local/dev installs).
SOURCE="${PKG_UPGRADE_SOURCE:-git+${REPO_URL}@${REF}}"
```

Then replace:

```bash
[[ "$(uname -s)" == "Darwin" ]] || die "pkg-upgrade is macOS-only (detected $(uname -s))."
```

With:

```bash
case "$(uname -s)" in
    Darwin|Linux) ;;
    *) die "install.sh supports macOS and Linux only (detected $(uname -s)). Use install.ps1 on Windows." ;;
esac
```

- [ ] **Step 3: Verify no stale references**

Run: `grep -n MAC_UPGRADE install.sh || echo OK`
Expected: `OK`.

- [ ] **Step 4: Shellcheck**

Run: `shellcheck install.sh || true`
Expected: no new errors introduced by the diff. (If `shellcheck` isn't installed locally, skip.)

- [ ] **Step 5: Commit**

```bash
git add install.sh
git commit -m "feat(install.sh): rename env vars to PKG_UPGRADE_* and support Linux"
```

---

### Task 6: Ship install.ps1 for Windows

**Files:**
- Create: `install.ps1`

- [ ] **Step 1: Create the script**

Create `install.ps1`:

```powershell
# pkg-upgrade installer for Windows — https://github.com/liskeee/pkg-upgrade
# Usage:  iwr -useb https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.ps1 | iex
# Env:
#   $env:PKG_UPGRADE_REF     = "main"                           # git ref for source installs
#   $env:PKG_UPGRADE_SOURCE  = "git+https://github.com/..."     # override pip spec entirely

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/liskeee/pkg-upgrade"
$Ref     = if ($env:PKG_UPGRADE_REF) { $env:PKG_UPGRADE_REF } else { "main" }
$Source  = if ($env:PKG_UPGRADE_SOURCE) { $env:PKG_UPGRADE_SOURCE } else { "git+$RepoUrl@$Ref" }

function Write-Log($msg)  { Write-Host "==> $msg" }
function Write-Warn($msg) { Write-Host "==> warning: $msg" -ForegroundColor Yellow }
function Die($msg)        { Write-Host "==> error: $msg" -ForegroundColor Red; exit 1 }

function Find-Python {
    foreach ($candidate in @("python3.13", "python3.12", "python3", "python", "py -3.13", "py -3.12", "py -3")) {
        $parts = $candidate -split " "
        $exe = $parts[0]
        $args = @()
        if ($parts.Count -gt 1) { $args = $parts[1..($parts.Count - 1)] }
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $check = & $exe @args -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"
            if ($LASTEXITCODE -eq 0) {
                return @{ Exe = $exe; Args = $args }
            }
        } catch { }
    }
    return $null
}

$py = Find-Python
if (-not $py) { Die "Python 3.12+ not found. Install from https://www.python.org/downloads/windows/ or 'winget install Python.Python.3.12'." }
Write-Log "Using Python: $(& $py.Exe @($py.Args + '--version'))"

function Try-Pipx {
    if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) { return $false }
    Write-Log "Installing via pipx..."
    & pipx install --force $Source
    return ($LASTEXITCODE -eq 0)
}

if (-not (Try-Pipx)) {
    Write-Log "pipx not found — bootstrapping with 'python -m pip install --user pipx'..."
    & $py.Exe @($py.Args + @("-m", "pip", "install", "--user", "pipx"))
    & $py.Exe @($py.Args + @("-m", "pipx", "ensurepath"))
    $env:PATH = "$env:PATH;$env:APPDATA\Python\Scripts;$env:USERPROFILE\.local\bin"
    if (-not (Try-Pipx)) {
        Write-Warn "pipx bootstrap failed; falling back to venv."
        $VenvDir = Join-Path $env:LOCALAPPDATA "pkg-upgrade"
        if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
        & $py.Exe @($py.Args + @("-m", "venv", $VenvDir))
        & "$VenvDir\Scripts\python.exe" -m pip install --upgrade pip
        & "$VenvDir\Scripts\python.exe" -m pip install $Source
        $ShimDir = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
        New-Item -ItemType Directory -Force -Path $ShimDir | Out-Null
        $Shim = Join-Path $ShimDir "pkg-upgrade.cmd"
        "@echo off`r`n`"$VenvDir\Scripts\pkg-upgrade.exe`" %*" | Set-Content -Encoding ASCII $Shim
        Write-Log "Installed to $VenvDir; shim at $Shim"
    }
}

Write-Log "Done. Run: pkg-upgrade"
```

- [ ] **Step 2: Verify PowerShell syntax by parsing it with pwsh**

Run: `pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('install.ps1', [ref]\$null, [ref]\$null) | Out-Null" && echo OK`
Expected: `OK`. (If `pwsh` is not installed locally, skip — CI will exercise it.)

- [ ] **Step 3: Commit**

```bash
git add install.ps1
git commit -m "feat(install.ps1): add Windows installer with pipx + venv fallback"
```

---

### Task 7: Smoke-test the installer scripts in CI

**Files:**
- Modify: `.github/workflows/ci.yml`

**Context:** The scripts should at minimum parse and surface `--help` without needing to install. Add a lightweight lint job.

- [ ] **Step 1: Append a new job `installers` to `.github/workflows/ci.yml`**

Before the `brew:` job, insert:

```yaml
  installers:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            shell: bash
            script: install.sh
          - os: macos-latest
            shell: bash
            script: install.sh
          - os: windows-latest
            shell: pwsh
            script: install.ps1
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v6
      - name: Syntax check (bash)
        if: matrix.shell == 'bash'
        run: bash -n ${{ matrix.script }}
      - name: Syntax check (pwsh)
        if: matrix.shell == 'pwsh'
        shell: pwsh
        run: |
          $errs = $null
          [System.Management.Automation.Language.Parser]::ParseFile('${{ matrix.script }}', [ref]$null, [ref]$errs) | Out-Null
          if ($errs) { $errs | ForEach-Object { Write-Error $_.Message }; exit 1 }
```

- [ ] **Step 2: Validate YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci(installers): parse install.sh and install.ps1 on all OSes"
```

---

### Task 8: Sanity test for scoop manifest template + install.sh env var

**Files:**
- Create: `tests/test_installers.py`

**Context:** Guard against regressions: the manifest must stay parseable JSON with the required keys, and `install.sh` must advertise `PKG_UPGRADE_*` env vars (not `MAC_UPGRADE_*`).

- [ ] **Step 1: Write the test**

Create `tests/test_installers.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scoop_manifest_has_required_keys() -> None:
    manifest = json.loads((ROOT / "scoop" / "pkg-upgrade.json").read_text(encoding="utf-8"))
    for key in ("version", "description", "homepage", "license", "url", "hash", "bin"):
        assert key in manifest, f"scoop manifest missing key: {key}"


def test_install_sh_uses_pkg_upgrade_env_vars() -> None:
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "PKG_UPGRADE_REF" in text
    assert "PKG_UPGRADE_SOURCE" in text
    assert "MAC_UPGRADE_" not in text


def test_install_ps1_uses_pkg_upgrade_env_vars() -> None:
    text = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "PKG_UPGRADE_REF" in text
    assert "PKG_UPGRADE_SOURCE" in text
    assert "MAC_UPGRADE_" not in text
```

- [ ] **Step 2: Run**

Run: `.venv/bin/python3 -m pytest tests/test_installers.py -v`
Expected: 3 passed.

- [ ] **Step 3: Lint/typecheck**

Run: `.venv/bin/ruff check tests/test_installers.py && .venv/bin/mypy tests/test_installers.py`
Expected: no issues (note: mypy on single file may show unrelated noise; the full-tree `mypy` run in Task 10 is authoritative).

- [ ] **Step 4: Commit**

```bash
git add tests/test_installers.py
git commit -m "test: guard scoop manifest schema + installer env var names"
```

---

### Task 9: README Windows install snippet

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Open README.md and locate the install section**

Run: `grep -n "install" README.md | head -20`

- [ ] **Step 2: Add a Windows subsection**

Under the existing install instructions, add:

```markdown
### Windows

```powershell
iwr -useb https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.ps1 | iex
```

Or via Scoop:

```powershell
scoop bucket add liskeee https://github.com/liskeee/scoop-bucket
scoop install pkg-upgrade
```
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): add Windows install instructions (install.ps1 + scoop)"
```

---

### Task 10: Final regression + PR

- [ ] **Step 1: Full test suite + lints**

```bash
.venv/bin/python3 -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
```

All must pass.

- [ ] **Step 2: Push branch**

```bash
git push -u origin feat/pkg-upgrade-distribution
```

- [ ] **Step 3: Open PR**

```bash
gh pr create --base main --title "feat: distribution & release automation (Plan 3)" --body "Ships Plan 3 of the cross-platform redesign: install.ps1, Scoop manifest + scoop-bump workflow, install.sh Linux support and PKG_UPGRADE_* env var rename, release.yml PyPI URL fix and wheel-to-release upload, formula-bump.yml path fix, README Windows docs. See docs/superpowers/plans/2026-04-13-pkg-upgrade-distribution.md."
```

---

## Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-04-13-pkg-upgrade-cross-platform-design.md` §Distribution + §Release workflow):
- PyPI trusted publishing → already in `release.yml`; Task 1 fixes the URL ✓
- Homebrew tap bump → `formula-bump.yml` exists; Task 2 fixes path ✓
- Scoop bucket manifest → Task 3 ships template ✓
- Scoop bump automation → Task 4 ✓
- `install.sh` env vars renamed + Linux support → Task 5 ✓
- `install.ps1` with pipx-preferred, venv fallback, `pkg-upgrade.cmd` shim → Task 6 ✓
- Wheel attached to GH release (needed by scoop-bump) → Task 1 step 3 ✓
- Installer CI smoke → Task 7 ✓
- Guard against regressions → Task 8 ✓
- README docs → Task 9 ✓

**Explicitly deferred (out of scope):**
- Code-signing `install.ps1` — v1 ships unsigned with `Set-ExecutionPolicy -Scope Process Bypass` documented (per spec).
- Auto-rotating `SCOOP_PUSH_TOKEN` — manual setup; Task 4 no-ops the mirror step if unset.

**Placeholder scan:** no TBDs; every code block complete; every env var name consistent across Tasks 5/6/8.

**Type/name consistency:** `PKG_UPGRADE_REF` / `PKG_UPGRADE_SOURCE` used identically in install.sh (Task 5), install.ps1 (Task 6), and the sanity test (Task 8). Scoop manifest path `scoop/pkg-upgrade.json` used identically in Task 3 (create), Task 4 (rewrite), and Task 8 (load).
