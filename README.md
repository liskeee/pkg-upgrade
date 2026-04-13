# pkg-upgrade

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

### One-line (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.sh | bash
```

Pin a specific version:

```bash
curl -fsSL https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.sh \
    | MAC_UPGRADE_REF=v0.1.0 bash
```

The installer uses [pipx](https://pipx.pypa.io/) when available and falls
back to a self-managed venv at `~/.local/share/pkg-upgrade/`. Requires
Python 3.12+ and macOS.

### Homebrew

```bash
brew tap liskeee/pkg-upgrade https://github.com/liskeee/pkg-upgrade
brew install pkg-upgrade
```

### pipx

```bash
pipx install git+https://github.com/liskeee/pkg-upgrade
```

### From source

```bash
git clone https://github.com/liskeee/pkg-upgrade
cd pkg-upgrade
pipx install .
```

### Windows

```powershell
iwr -useb https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.ps1 | iex
```

Or via Scoop:

```powershell
scoop bucket add liskeee https://github.com/liskeee/scoop-bucket
scoop install pkg-upgrade
```

### Uninstall

```bash
# installed via pipx (the default path):
pipx uninstall pkg-upgrade

# installed via the venv fallback:
rm -rf ~/.local/share/pkg-upgrade ~/.local/bin/pkg-upgrade
```

## Usage

```bash
pkg-upgrade                      # interactive dashboard
pkg-upgrade --yes                # upgrade everything without prompts
pkg-upgrade --only brew,npm      # only specific managers
pkg-upgrade --skip system        # skip macOS system updates
pkg-upgrade --dry-run            # preview only
pkg-upgrade --list               # detect installed managers and exit
```

## Shell Completion

Tab completion is installed automatically by every first-party installer
(Homebrew, Scoop, `install.sh`, `install.ps1`). If you installed via
`pipx` or `pip`, set it up manually:

```bash
# bash
pkg-upgrade completion bash  | sudo tee /etc/bash_completion.d/pkg-upgrade

# zsh (ensure ~/.zsh/completions is on your fpath)
pkg-upgrade completion zsh   > "$HOME/.zsh/completions/_pkg-upgrade"

# fish
pkg-upgrade completion fish  > ~/.config/fish/completions/pkg-upgrade.fish

# PowerShell (add to $PROFILE)
pkg-upgrade completion powershell | Out-String | Invoke-Expression
```

Third-party plugin managers appear in Tab completion after the next
`pkg-upgrade --list` call, which refreshes the cached manager list.

## License

MIT
