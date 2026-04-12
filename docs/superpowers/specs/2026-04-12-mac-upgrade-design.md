# mac-upgrade — Design Spec

A Python CLI app with a Textual TUI dashboard that upgrades all macOS package managers with smart parallel execution, detailed progress, and beautiful terminal UI.

## Package Managers

| Manager            | Key      | Icon | Detection         |
|--------------------|----------|------|-------------------|
| Homebrew Formulas  | `brew`   | 🍺   | `which brew`      |
| Homebrew Casks     | `cask`   | 🍻   | `which brew`      |
| pip3               | `pip`    | 🐍   | `which pip3`      |
| npm (global)       | `npm`    | 📦   | `which npm`       |
| gem                | `gem`    | 💎   | `which gem`       |
| macOS System       | `system` | 🍎   | `which softwareupdate` |

## Architecture

### Project Structure

```
mac-upgrade/
├── pyproject.toml          # Project config, dependencies, entry point
├── src/
│   └── mac_upgrade/
│       ├── __init__.py
│       ├── cli.py           # CLI entry point (argument parsing)
│       ├── app.py           # Textual app (dashboard UI)
│       ├── manager.py       # Base class for package managers
│       ├── managers/        # One module per manager
│       │   ├── __init__.py
│       │   ├── brew.py      # Homebrew formulas
│       │   ├── cask.py      # Homebrew casks
│       │   ├── pip.py       # pip3
│       │   ├── npm.py       # npm global packages
│       │   ├── gem.py       # gem
│       │   └── system.py    # softwareupdate
│       ├── executor.py      # Parallel/sequential execution engine
│       └── notifier.py      # macOS notification + log file
```

### Dependencies

- `textual` — TUI framework (pulls in `rich` automatically)
- No other external dependencies — everything else is stdlib (`subprocess`, `asyncio`, `logging`, `argparse`)

### Installation

`pipx install .` — gives a global `mac-upgrade` command without polluting the Python environment.

## Package Manager Interface

Each manager implements a base class:

```python
class PackageManager(ABC):
    name: str           # e.g. "Homebrew Formulas"
    key: str            # e.g. "brew" (used in --skip/--only flags)
    icon: str           # e.g. "🍺"

    async def is_available() -> bool      # check if the tool exists on PATH
    async def check_outdated() -> list[Package]  # return list of outdated packages
    async def upgrade(package) -> Result   # upgrade a single package
    async def upgrade_all() -> Result      # upgrade all outdated packages
```

`Package` is a dataclass with fields: `name`, `current_version`, `latest_version`.

`Result` is a dataclass with fields: `success: bool`, `message: str`, `package: Package`.

## Execution Model

### Smart Grouping

Managers are grouped to avoid conflicts while maximizing parallelism:

```
Group 1 (sequential chain): brew formulas → brew casks → pip
Group 2 (parallel with Group 1): npm + gem
Group 3 (parallel with Group 1): softwareupdate
```

**Rationale:**
- Brew formulas before casks — casks can depend on formulas
- Pip after brew — brew Python upgrades can affect pip
- npm, gem, and softwareupdate are fully independent of everything else

### Flow Per Manager

1. Check if available → skip with note if not installed
2. Fetch outdated list → display in dashboard
3. Wait for user confirmation (per manager) → skip if declined
4. Run upgrades → stream progress to dashboard
5. Report results (success/failure per package)

### Error Handling

- On failure: continue through all managers, collect errors
- Final summary shows all successes and failures
- Failed packages are listed with their error messages
- Retry option available on the summary screen

## Dashboard UI

### Main Screen Layout

```
┌─────────────────────────────────────────────────────────┐
│  🚀 mac-upgrade                          12 Apr 2026    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🍺 Homebrew Formulas    ██████████░░░░  3/5  ✓✓✓◌◌   │
│  🍻 Homebrew Casks       ⏳ waiting (depends on brew)   │
│  🐍 pip                  ⏳ waiting (depends on brew)   │
│  📦 npm                  ██████████████  4/4  ✓✓✓✓    │
│  💎 gem                  ━━ no updates                  │
│  🍎 System Updates       ██░░░░░░░░░░░  1/3  ✓◌◌      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  LIVE LOG                                               │
│  21:04:02  brew  Upgrading node 22.15→22.16... done     │
│  21:04:05  brew  Upgrading python 3.13→3.14... done     │
│  21:04:08  npm   Upgrading eslint 9.1→9.2... done       │
│  21:04:09  brew  Upgrading git 2.44→2.45... error ✗     │
│  21:04:10  npm   All packages upgraded ✓                │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [S]kip manager  [Q]uit  [Enter] Confirm                │
└─────────────────────────────────────────────────────────┘
```

### UI Elements

- **Header** — app name + current date
- **Manager cards** — icon, name, progress bar, package count, per-package status icons (✓/✗/spinner)
- **Manager states:** `checking...` → `N updates found [confirm?]` → `upgrading M/N` → `done ✓` / `failed ✗` / `skipped ⏭` / `no updates ━`
- **Live log panel** — scrollable, timestamped stream of activity across all managers
- **Footer keybindings** — contextual actions (confirm, skip, quit)

### Confirmation Flow

When a manager finishes checking, its card shows the outdated package list and highlights, waiting for `Enter` to confirm or `S` to skip. Multiple managers can be in "awaiting confirmation" state simultaneously if they finish checking at the same time. When `--yes` is passed, confirmation is skipped and upgrades proceed automatically — the card transitions directly from "N updates found" to "upgrading".

### Summary Screen

```
┌─────────────────────────────────────────────────────────┐
│  ✅ mac-upgrade complete                   Duration: 2m │
├─────────────────────────────────────────────────────────┤
│  🍺 Homebrew Formulas    4 upgraded, 1 failed           │
│  🍻 Homebrew Casks       2 upgraded                     │
│  🐍 pip                  skipped by user                │
│  📦 npm                  4 upgraded                     │
│  💎 gem                  no updates                     │
│  🍎 System Updates       3 upgraded                     │
├─────────────────────────────────────────────────────────┤
│  ❌ FAILURES:                                           │
│  brew: git 2.44→2.45 — permission denied /usr/local     │
├─────────────────────────────────────────────────────────┤
│  Log saved to ~/mac-upgrade-2026-04-12.log              │
│  [Enter] Exit  [R] Retry failed                         │
└─────────────────────────────────────────────────────────┘
```

## CLI Interface

```
mac-upgrade [OPTIONS]

Options:
  --skip <managers>    Comma-separated managers to skip (e.g. --skip brew,pip)
  --only <managers>    Only run these managers (e.g. --only npm,gem)
  --yes / -y           Skip confirmations, upgrade everything automatically
  --dry-run            Show what would be upgraded without doing anything
  --no-notify          Suppress macOS notification on completion
  --no-log             Skip writing log file
  --log-dir <path>     Custom log directory (default: ~/)
  --list               Just list all detected managers and their status, then exit
  --version            Show version
  --help               Show help
```

**Manager keys for `--skip`/`--only`:** `brew`, `cask`, `pip`, `npm`, `gem`, `system`

## Notifications

- Uses `osascript` to send a native macOS notification on completion
- Title: "mac-upgrade complete" or "mac-upgrade finished with errors"
- Body: quick summary like "10 upgraded, 1 failed, 1 skipped"

## Log File

- Default path: `~/mac-upgrade-YYYY-MM-DD.log`
- Plain text (no ANSI codes), timestamped lines matching the live log panel
- Appends if run multiple times on the same day
