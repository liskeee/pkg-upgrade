# mac-upgrade

A beautiful Textual-based TUI that upgrades every macOS package manager you have installed — Homebrew formulas & casks, pip, npm, gem, and macOS system updates — with smart parallel execution, per-manager confirmations, and a detailed dashboard.

## Features

- 🍺 Homebrew formulas + 🍻 casks
- 🐍 pip3
- 📦 npm (global)
- 💎 gem
- 🍎 `softwareupdate`
- Smart parallel execution (brew → cask → pip sequential; npm/gem/system parallel)
- Per-manager confirmation with preview, or `--yes` to skip prompts
- Timestamped log file + native macOS notification on completion
- `--skip` / `--only` / `--dry-run` / `--list`

## Installation

### Homebrew (recommended)

```bash
brew tap lukaszlis/mac-upgrade https://github.com/lukaszlis/mac-upgrade
brew install mac-upgrade
```

### pipx

```bash
pipx install mac-upgrade
```

### From source

```bash
git clone https://github.com/lukaszlis/mac-upgrade
cd mac-upgrade
pipx install .
```

## Usage

```bash
mac-upgrade                      # interactive dashboard
mac-upgrade --yes                # upgrade everything without prompts
mac-upgrade --only brew,npm      # only specific managers
mac-upgrade --skip system        # skip macOS system updates
mac-upgrade --dry-run            # preview only
mac-upgrade --list               # detect installed managers and exit
```

## License

MIT
