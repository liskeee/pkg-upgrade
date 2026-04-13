# pkg-upgrade: Cross-Platform Redesign

**Date:** 2026-04-13
**Status:** Approved (awaiting implementation plan)
**Supersedes:** `2026-04-12-mac-upgrade-design.md` (macOS-only scope)

## Goal

Turn `mac-upgrade` into `pkg-upgrade`: a Textual TUI + CLI that orchestrates upgrades across every installed package manager on macOS, Linux, and Windows, with a registration model that makes adding a new manager trivial — often zero Python.

Full platform parity in v1. Some managers are platform-exclusive (e.g., `winget` on Windows, `apt` on Linux, `mas` on macOS); the architecture surfaces them cleanly without conditional branching in core.

## Non-goals (v1)

- Conflict resolution between managers (`conflicts_with`). Only `depends_on` in v1.
- Signed PowerShell installer.
- Submission to winget-pkgs / AUR / MSI packaging.
- GUI beyond Textual.
- Backwards compatibility with `mac-upgrade` configs/entry points (clean break at v1.0.0).

## Rename & layout

- **PyPI / distribution name:** `pkg-upgrade`.
- **Import package:** `pkg_upgrade` (replaces `mac_upgrade` everywhere).
- **CLI entry points:** `pkg-upgrade` (primary) and `pkgup` (short alias), both → `pkg_upgrade.cli:main`. No `mac-upgrade` transitional shim.
- **Repo:** renamed `liskeee/mac-upgrade` → `liskeee/pkg-upgrade`; GitHub auto-redirects.
- **Version reset:** start at `v1.0.0` under semantic-release; release notes mark BREAKING CHANGE.
- **Homebrew tap:** new `liskeee/tap/pkg-upgrade`; old `liskeee/mac-upgrade` tap archived with a README pointing at the new one.
- **Trusted Publisher on PyPI:** reconfigured for the new repo + workflow + `pypi` environment.

## Manager API

Extended `PackageManager` ABC (`src/pkg_upgrade/manager.py`):

```python
class PackageManager(ABC):
    name: ClassVar[str]
    key: ClassVar[str]
    icon: ClassVar[str]
    platforms: ClassVar[frozenset[str]]           # subset of {"macos","linux","windows"}
    depends_on: ClassVar[tuple[str, ...]] = ()
    install_hint: ClassVar[str] = ""

    async def is_available(self) -> bool: ...
    async def check_outdated(self) -> list[Package]: ...
    async def upgrade(self, package: Package) -> Result: ...
```

### Platform gating (two-stage)

1. **Static:** `platforms` ∌ current OS → manager hidden entirely (not shown in `--list`, not loaded).
2. **Runtime:** `is_available()` probes for the binary. On supported OS but missing binary → status `UNAVAILABLE`, shown with `install_hint`.

## Registration — three paths

All three funnel through a single `pkg_upgrade/registry.py`.

### 1. Built-in decorator

```python
@register_manager
class BrewManager(PackageManager):
    ...
```

Modules in `pkg_upgrade/managers/` are auto-imported at startup.

### 2. Entry points (third-party plugins)

Packages expose classes via `pyproject.toml`:

```toml
[project.entry-points."pkg_upgrade.managers"]
nix = "pkg_upgrade_nix:NixManager"
```

Loaded via `importlib.metadata.entry_points(group="pkg_upgrade.managers")`.

### 3. Declarative YAML

Files at `src/pkg_upgrade/managers/declarative/*.yaml` are loaded into a shared `DeclarativeManager` class implementing `PackageManager` generically.

Schema:

```yaml
name: APT
key: apt
icon: "📦"
platforms: [linux]
depends_on: []
install_hint: "Debian/Ubuntu ships APT by default."
requires_sudo: true

check:
  cmd: [apt, list, --upgradable]
  parser: apt_upgradable          # named preset in pkg_upgrade/parsers/
  skip_first_line: true

upgrade:
  cmd: [sudo, apt-get, install, --only-upgrade, -y, "{name}"]
  env: {}
```

Parser presets live in `src/pkg_upgrade/parsers/` (one function per preset, returning `list[Package]` from stdout). v1 ships: `apt_upgradable`, `dnf_check_update`, `pacman_qu`, `flatpak_remote_ls_updates`, `snap_refresh_list`, `winget_upgrade`, `scoop_status`, `choco_outdated`, `mas_outdated`, plus `generic_regex` fallback (configurable via `regex` + `capture` keys in lieu of `parser`).

**Runtime deps added:** `PyYAML`, `platformdirs`.

## Scheduling

Replace the hardcoded `SEQUENTIAL_CHAIN` / `INDEPENDENT` lists with a topological sort driven by each manager's `depends_on`.

**Algorithm (`Executor.from_managers`):**
1. Filter managers by current OS (`platforms` gate).
2. Build DAG: edge `dep → manager` for each `depends_on` key that's also present.
3. Drop edges to absent deps with a warning. Cycles raise `ConfigurationError` at startup (manifest bug, fail fast).
4. Kahn's algorithm → levels. Each level becomes an `ExecutionGroup(parallel=True)`. Levels run sequentially.

**Declared built-in deps:**
- `cask.depends_on = ("brew",)`
- `pip.depends_on = ("brew",)` (soft — edge is simply dropped on Windows where brew is absent)
- All others: `()`

**CLI flag:** `--max-parallel N` caps per-level concurrency globally.

**Resulting levels (illustrative):**
- macOS: L0 `{brew, npm, gem, system, mas}`, L1 `{cask, pip}`
- Linux: L0 `{apt|dnf|pacman, flatpak, snap, npm, gem, pip}`
- Windows: L0 `{winget, scoop, choco, npm, gem, pip}`

## Built-in managers (v1)

| Key | Platforms | Type | Notes |
|---|---|---|---|
| `brew` | macos, linux | Python (existing) | Keep shared outdated cache. |
| `cask` | macos | Python (existing) | |
| `mas` | macos | declarative | Mac App Store CLI. |
| `system` | macos | Python (existing) | `softwareupdate`. |
| `apt` | linux | declarative | sudo. |
| `dnf` | linux | declarative | Fedora/RHEL. |
| `pacman` | linux | declarative | Arch. |
| `flatpak` | linux | declarative | |
| `snap` | linux | declarative | sudo. |
| `winget` | windows | declarative | |
| `scoop` | windows | declarative | User-scoped. |
| `choco` | windows | declarative | Requires admin. |
| `pip` | all | Python (existing) | Detect active Python. |
| `npm` | all | Python (existing) | |
| `gem` | all | Python (existing) | |

## Platform specifics

- **Detection:** new `pkg_upgrade/platform.py` — `current_os()` (wraps `sys.platform`) and `linux_distro()` (reads `/etc/os-release` `ID_LIKE`).
- **Windows:** verify `_subprocess.py` has no shell-quoting assumptions; pass `creationflags=CREATE_NO_WINDOW` to avoid flashing consoles. Admin detection via `ctypes.windll.shell32.IsUserAnAdmin()`; non-elevated → `UNAVAILABLE` with hint (no UAC prompt from TUI).
- **Linux sudo:** for `requires_sudo: true` managers, `is_available()` also runs `sudo -n true`; failure → unavailable with hint "run `sudo -v` first".
- **Textual** renders on Windows Terminal/ConPTY; no special work.

## Distribution

Five install paths, all bumped by one release workflow:

1. **PyPI** (`pipx install pkg-upgrade`) — canonical everywhere.
2. **Homebrew tap** `liskeee/tap/pkg-upgrade` — macOS + Linux.
3. **Scoop bucket** `liskeee/scoop-bucket`, manifest `pkg-upgrade.json` — Windows.
4. **`install.sh`** — bash; prefers `pipx`, falls back to venv at `~/.local/share/pkg-upgrade/`. Env: `PKG_UPGRADE_REF`, `PKG_UPGRADE_SOURCE`.
5. **`install.ps1`** — PowerShell; prefers `pipx` (installs it via `python -m pip install --user pipx` if missing); venv fallback at `%LOCALAPPDATA%\pkg-upgrade\`. Shim `pkg-upgrade.cmd` placed in `%LOCALAPPDATA%\Microsoft\WindowsApps`. Not signed in v1; documented `Set-ExecutionPolicy -Scope Process Bypass` one-liner.

### Release workflow (`.github/workflows/release.yml`)

- Triggers: `workflow_dispatch` + push to `main`.
- `semantic-release` on Linux: bumps version, tags, publishes GH Release with wheels.
- Parallel downstream jobs:
  - `pypi-publish` (trusted publishing, env `pypi`).
  - `bump-homebrew` (pushes updated formula to tap repo; PAT secret `TAP_PUSH_TOKEN`).
  - `bump-scoop` (pushes updated manifest to scoop-bucket repo; PAT secret `SCOOP_PUSH_TOKEN`).

## CI

`.github/workflows/ci.yml`:

- Matrix: `{ubuntu-latest, macos-latest, windows-latest} × {3.12, 3.13}`.
- Each cell: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
- **Smoke job per OS** (blocking on `main`, non-blocking on PRs): `pkg-upgrade --list --dry-run`, `pkg-upgrade --only <native-mgr> --dry-run`.

Pre-commit unchanged.

## Testing

- **Unit tests run on every OS** regardless of manager platform, because `_subprocess.run` is stubbed. No `pytest.mark.skipif` based on OS.
- **Parser preset tests:** table-driven, with real-world stdout fixtures under `tests/fixtures/parsers/{apt,winget,...}.txt`. Every preset must have fixtures.
- **Registry tests:** decorator, entry-point (via fake `importlib.metadata` seam), YAML all surface uniformly.
- **Scheduler tests:** macOS/Linux/Windows grouping examples above, cycle detection, missing-dep warning.
- **Smoke tests** (CI only): exercise real native binaries for the current OS.
- Coverage: keep the existing floor; new code in `registry.py`, `platform.py`, parsers, and `DeclarativeManager` are fully tested.

## Config

- Path: `platformdirs.user_config_path("pkg-upgrade") / "config.yaml"` (cross-platform).
- Keys: `disabled_managers: [key, ...]`, `per_manager: {<key>: {env: {...}}}`, `max_parallel: N`.
- No migration from `mac-upgrade`: if old config is found, log a one-line note on first run and ignore it.

## TUI/CLI changes

- `--list` groups managers by: **Available** / **Unavailable (install hint)** / **Not on this OS**.
- `--show-graph` prints the topo-sorted execution plan (debugging aid).
- `--max-parallel N` caps per-level concurrency.
- Onboarding surfaces `install_hint` for popular missing managers on the user's OS.
- `--only` / `--skip` semantics unchanged.

## Out of scope (explicit)

- Conflict resolution (`conflicts_with`).
- Per-level configurable parallelism.
- Signed PowerShell installer.
- AUR / MSI / winget-pkgs submission.
- Non-Textual GUI.
