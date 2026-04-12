# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`mac-upgrade` is a Textual-based TUI that orchestrates upgrades across every macOS package manager installed (Homebrew formulas/casks, pip, npm, gem, `softwareupdate`). macOS-only, Python 3.12+.

## Common commands

```bash
# Install dev environment (editable with dev extras)
python -m pip install -e ".[dev]"

# Run the TUI locally
mac-upgrade                       # or: python -m mac_upgrade.cli

# Tests
pytest                            # full suite
pytest tests/test_executor.py     # single file
pytest tests/test_executor.py::test_name -x   # single test, stop on fail
pytest --cov --cov-report=term-missing        # with coverage

# Lint / format / typecheck (match CI exactly)
ruff check .
ruff format --check .
mypy                              # strict mode, configured in pyproject.toml

# Pre-commit (runs ruff + ruff-format + mypy)
pre-commit run --all-files
```

CI runs on `macos-latest` against Python 3.12 and 3.13 — keep both green.

## Architecture

Execution flows through three layers. Understand them before editing:

1. **Managers** ([src/mac_upgrade/managers/](src/mac_upgrade/managers/)) — one module per backend (`brew`, `cask`, `pip`, `npm`, `gem`, `system`). Each implements the `PackageManager` ABC in [manager.py](src/mac_upgrade/manager.py): `is_available()`, `check_outdated() -> list[Package]`, `upgrade(pkg) -> Result`. `ALL_MANAGERS` is the registry exported from `managers/__init__.py`.

2. **Executor** ([executor.py](src/mac_upgrade/executor.py)) — groups managers into `ExecutionGroup`s and runs them. Scheduling rule (important, encoded in `Executor.from_managers`):
   - `SEQUENTIAL_CHAIN = ["brew", "cask", "pip"]` — run strictly in order (cask depends on brew; pip can conflict).
   - `INDEPENDENT = ["npm", "gem", "system"]` — run in parallel with each other, in parallel with the chain.
   - Per-manager state lives in `ManagerState` with a `ManagerStatus` enum ([status.py](src/mac_upgrade/status.py)). Progress is surfaced via `on_update` / `on_result` async callbacks — the UI is a consumer, not a driver.

3. **UI + CLI** ([app.py](src/mac_upgrade/app.py), [widgets.py](src/mac_upgrade/widgets.py), [cli.py](src/mac_upgrade/cli.py)) — Textual app renders `Executor` state; CLI parses `--yes / --only / --skip / --dry-run / --list` and wires the same executor in non-interactive mode.

Shared primitives: [models.py](src/mac_upgrade/models.py) (`Package`, `Result`), [_subprocess.py](src/mac_upgrade/_subprocess.py) (all shell calls go through this — do not call `asyncio.create_subprocess_*` directly from managers), [_brew_cache.py](src/mac_upgrade/_brew_cache.py) (shared `brew outdated` cache so `brew` and `cask` don't double-query), [notifier.py](src/mac_upgrade/notifier.py) (macOS notification on completion), [config.py](src/mac_upgrade/config.py), [onboarding.py](src/mac_upgrade/onboarding.py).

When adding a new package manager: implement `PackageManager`, register it in `managers/__init__.py`, and decide whether it belongs in the sequential chain or the independent set in [executor.py](src/mac_upgrade/executor.py).

## Distribution

Three install paths are maintained in parallel — changes to entry points or runtime deps must be reflected in all three:

- [install.sh](install.sh) — `curl | bash` installer; prefers `pipx`, falls back to a self-managed venv at `~/.local/share/mac-upgrade/`. Honors `MAC_UPGRADE_REF` (git ref) and `MAC_UPGRADE_SOURCE` (override).
- [Formula/mac-upgrade.rb](Formula/mac-upgrade.rb) — Homebrew tap formula.
- [pyproject.toml](pyproject.toml) — `pipx install` / PyPI path; `mac-upgrade` script entry points to `mac_upgrade.cli:main`.

## Conventions

- Ruff config is strict (ANN, B, SIM, PL, PTH, ASYNC, RET, TID enabled). Line length 100, double quotes. Tests exempt from ANN/PLR/B/SIM — don't relax rules for `src/`.
- Mypy is `strict = true` for `src` and `tests`. Tests waive `disallow_untyped_defs`; Textual has `ignore_missing_imports`.
- `pytest-asyncio` is in `asyncio_mode = "auto"` — write async tests without the decorator.
- Plans and specs for larger changes live under [docs/superpowers/](docs/superpowers/).
