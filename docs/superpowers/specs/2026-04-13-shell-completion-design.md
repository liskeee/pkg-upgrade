# Shell Completion Design

**Date:** 2026-04-13
**Status:** Design

## Goal

Press Tab in bash, zsh, fish, or PowerShell and have `pkg-upgrade` complete its flags and manager names (including third-party plugins and YAML declarative managers).

## Architecture

Four static completion scripts, shipped in the repo at `completions/`:

- `completions/pkg-upgrade.bash`
- `completions/_pkg-upgrade` (zsh)
- `completions/pkg-upgrade.fish`
- `completions/pkg-upgrade.ps1`

Each script hardcodes the flag list and the six built-in manager keys (`brew`, `cask`, `pip`, `npm`, `gem`, `system`). At Tab time, each script consults a cache file of live manager keys (which includes plugin/declarative managers) and falls back to the hardcoded list if the cache is missing or the CLI is unreachable.

## New CLI Surface

Two additions to `pkg_upgrade.cli`:

### `pkg-upgrade --list-managers --plain`

- Prints one registered manager key per line to stdout.
- Sorted alphabetically. No ANSI, no header, no trailing blank line.
- Write-through: also writes the same content to the cache file.
- Exit 0 on success; exit 1 only on catastrophic registry failure.

This is the stable contract the completion scripts depend on.

### `pkg-upgrade completion <bash|zsh|fish|powershell>`

- Reads the matching packaged script from `importlib.resources` and prints to stdout.
- Used as the pipx/pip fallback install path and as a reinstall escape hatch.
- Invalid shell name → exit 2 with a short error listing valid shells.

## Cache

- POSIX: `${XDG_CACHE_HOME:-~/.cache}/pkg-upgrade/managers.list`
- Windows: `%LOCALAPPDATA%\pkg-upgrade\managers.list`
- TTL: 24 hours.
- Format: one manager key per line, UTF-8, LF line endings.
- Past TTL: the completion script returns the stale cache immediately for zero Tab latency, then fires `pkg-upgrade --list-managers --plain &` in the background to refresh. On Windows PowerShell, use `Start-Job`.
- Missing cache on first Tab: hardcoded built-ins only (no blocking subprocess).

## Flag-Value Completion

| Flag | Completion behavior |
|---|---|
| `--only`, `--skip` | Comma-separated manager list. Complete the token after the last comma. Completed values exclude already-present tokens from the same list. |
| `--dry-run`, `--yes`, `--list`, `--self-update`, `--version`, `--install-completion` | Boolean. No value completion; complete the next flag. |
| Unknown / positional | Shell default (filenames). |

## Distribution

Each install path must drop the relevant script(s) in a location the shell auto-loads.

### Homebrew (`Formula/pkg-upgrade.rb`)

```ruby
bash_completion.install "completions/pkg-upgrade.bash"
zsh_completion.install  "completions/_pkg-upgrade" => "_pkg-upgrade"
fish_completion.install "completions/pkg-upgrade.fish"
```

Brew sources these automatically when the user has brew shellenv loaded.

### Scoop (`scoop/pkg-upgrade.json`)

- Ship `pkg-upgrade.ps1` under the install dir.
- `post_install` appends `. "$dir\pkg-upgrade.ps1"` to `$PROFILE` if not already present (idempotent check via `Select-String`).
- `uninstaller` removes the same line.

### `install.sh`

Detect the invoking shell (`$SHELL` basename) and copy:

- bash → `~/.local/share/bash-completion/completions/pkg-upgrade`
- zsh → `~/.zsh/completions/_pkg-upgrade` and ensure `fpath+=~/.zsh/completions` is in `.zshrc`
- fish → `~/.config/fish/completions/pkg-upgrade.fish`

Print a one-line "restart your shell or `exec $SHELL`" hint.

### `install.ps1`

- Copy `pkg-upgrade.ps1` to the install dir.
- Append `. "<path>\pkg-upgrade.ps1"` to `$PROFILE` if missing.

### pipx / pip (PyPI)

No post-install hook available. README instructs:

```bash
pkg-upgrade completion bash  | sudo tee /etc/bash_completion.d/pkg-upgrade
pkg-upgrade completion zsh   > "${fpath[1]}/_pkg-upgrade"
pkg-upgrade completion fish  > ~/.config/fish/completions/pkg-upgrade.fish
pkg-upgrade completion powershell | Out-String | Invoke-Expression
```

## Packaging

Add `completions/*` to `pyproject.toml` `[tool.hatch.build.targets.wheel.force-include]` (or equivalent) so `importlib.resources.files("pkg_upgrade.completions")` can find them at runtime. Move the directory into the package: `src/pkg_upgrade/completions/`.

## Testing

### Unit

- `test_list_managers_plain`: registered keys are printed one per line, sorted, no ANSI, no header.
- `test_list_managers_plain_writes_cache`: running the command creates the cache file with identical content.
- `test_completion_subcommand`: `pkg-upgrade completion bash` prints the packaged file byte-for-byte; invalid shell exits 2.
- `test_cache_ttl_logic`: helper that returns stale-vs-fresh decides correctly around the 24h boundary.

### Shell integration (CI matrix: macos-latest, ubuntu-latest)

- **bash**: source the script in a subshell, use `compgen -F _pkg_upgrade_completions -- br` and assert `brew` is present; same for `--skip p` → `pip`; comma handling: `--only brew,c` → `cask`.
- **zsh**: run with `zsh -f`, prepend completion dir to `fpath`, call `_main_complete` via a known harness, assert candidate list includes all six built-ins for `--only <TAB>`.
- **fish**: `fish -c "complete -C 'pkg-upgrade --only '"` assert output includes `brew`.
- **PowerShell** (windows-latest CI job): `TabExpansion2` on `pkg-upgrade --only ` returns the six keys.

### Installer tests

- `install.sh` tmp-HOME test: run in a sandbox, assert the right file landed in the right shell's completion dir, and (for zsh) that `fpath+=` was appended to `.zshrc` idempotently (running twice doesn't duplicate).
- `install.ps1` tmp-`$PROFILE` test: script runs twice; `. "..."` line is present exactly once.

## Out of Scope (YAGNI)

- Completing package names inside a manager (e.g. `pkg-upgrade --only brew upgrade wget<TAB>`). Expensive and rarely useful.
- Dynamic refresh on plugin install. 24h TTL + a manual `pkg-upgrade --list-managers` refresh is sufficient.
- Fancy descriptions in zsh completion (one-line help per flag). Can be added later without breaking the contract.

## Risks

- **Stale cache surprises**: first Tab after installing a plugin won't list it. Acceptable; documented in README ("run `pkg-upgrade --list-managers` to refresh").
- **Windows `$PROFILE` drift**: appending to `$PROFILE` is the standard pattern but users with unusual profile setups may miss the hook. Scoop uninstall removes the line; for install.ps1, document the manual source command as a fallback.
- **Shell detection in `install.sh`**: `$SHELL` is the login shell, not necessarily the running one. Acceptable — users running a non-default shell can run `pkg-upgrade completion <shell>` manually.
