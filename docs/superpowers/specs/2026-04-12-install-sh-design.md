# `install.sh` — curl | bash installer

## Goal

Provide a third installation path for `mac-upgrade` (in addition to the
Homebrew Formula and `pipx install`) so that new users can install the CLI
with a single copy-pasteable command:

```
curl -fsSL https://raw.githubusercontent.com/liskeee/mac-upgrade/main/install.sh | bash
```

## Non-goals

- Linux support. `mac-upgrade` is macOS-only; the installer aborts on other
  platforms.
- An `--uninstall` flag. Users run `pipx uninstall mac-upgrade` or
  `rm -rf ~/.local/share/mac-upgrade ~/.local/bin/mac-upgrade` depending on
  which install path was taken. Documented in README.
- Checksum verification of the project tarball. We install from
  `git+https://github.com/liskeee/mac-upgrade`; trust is anchored in TLS.
- Interactive prompts. The script must be safe to pipe to `bash`.

## User-facing interface

```bash
# install from main (default)
curl -fsSL .../install.sh | bash

# pin a tag, branch, or commit
curl -fsSL .../install.sh | MAC_UPGRADE_REF=v0.1.0 bash
```

Environment variables:

| Variable           | Default  | Purpose                                  |
| ------------------ | -------- | ---------------------------------------- |
| `MAC_UPGRADE_REF`  | `main`   | git ref (tag/branch/SHA) to install from |

Exit codes: `0` on success, `1` on any failure. All log lines go to stdout
with a `==>` prefix; errors go to stderr.

## Behavior

The script executes in strict mode (`set -euo pipefail`) and proceeds
top-down:

1. **Platform guard.** If `uname -s` ≠ `Darwin`, print an error and exit 1.
2. **Resolve inputs.**
   `REF="${MAC_UPGRADE_REF:-main}"`,
   `SOURCE="git+https://github.com/liskeee/mac-upgrade@${REF}"`.
3. **Find Python 3.12+.** Probe `python3.13`, `python3.12`, then `python3`
   in that order. For each candidate, verify
   `sys.version_info >= (3, 12)`. If none qualifies, instruct the user to
   `brew install python@3.12` and exit 1.
4. **Path A — pipx (preferred).** If `pipx` is on `PATH`, run
   `pipx install --force "$SOURCE"`. On success, skip to step 7.
5. **Bootstrap pipx.** If `pipx` is missing but `brew` exists, run
   `brew install pipx` and retry Path A. If that still fails, fall through
   to Path B.
6. **Path B — self-managed venv.**
   - `VENV="$HOME/.local/share/mac-upgrade/venv"`.
   - Remove `$VENV` if it already exists (clean reinstall).
   - `"$PY" -m venv "$VENV"`.
   - `"$VENV/bin/pip" install --quiet "$SOURCE"`.
   - Ensure `$HOME/.local/bin` exists and symlink
     `$VENV/bin/mac-upgrade` → `$HOME/.local/bin/mac-upgrade` (overwriting
     any existing symlink).
7. **PATH sanity check.** Determine the bin dir the CLI now lives in
   (`pipx` resolves via `pipx environment --value PIPX_BIN_DIR`; venv
   fallback is `$HOME/.local/bin`). If that dir is not on `PATH`, print a
   warning with the exact `export PATH=...` line to add to
   `~/.zshrc`/`~/.bash_profile`.
8. **Smoke test.** Invoke `mac-upgrade --version` via its full path and
   print `==> ✓ Installed mac-upgrade <version>`.

## Error handling

Every failure point prints a single-line `==> error: ...` message to stderr
before exiting 1. No partial state is left behind by step 6 — if the pip
install fails after the venv is created, the venv directory is removed in a
trap on `ERR`.

## File layout

- `install.sh` at the repo root. Mode `0755`. Committed.
- README gets a new "Install" section listing all three paths (Homebrew,
  curl|bash, `pipx install`) in decreasing order of recommendation.

## Testing

Manual, on a clean macOS user account:

1. With pipx preinstalled → Path A executes, `mac-upgrade --version`
   succeeds.
2. Without pipx, with brew → bootstrap path installs pipx, then Path A.
3. Without pipx, without brew (simulate by `PATH` override) → Path B
   executes, venv is created, symlink works.
4. `MAC_UPGRADE_REF=some-branch bash install.sh` installs from that ref.
5. Running the installer a second time reinstalls cleanly (the `--force`
   in Path A and the `rm -rf $VENV` in Path B both idempotent).

No automated test is added; a `bats` suite would exceed the value of an
~80-line shell script. The CI workflow added in PR3 already exercises
`pip install -e .` which is the load-bearing step.

## Security considerations for curl | bash

- Strict shell mode (`set -euo pipefail`) plus an `ERR` trap.
- No `eval`, no dynamic command construction from env vars other than the
  quoted `$REF`.
- No network fetch other than the `git+https` URL pip passes to git; the
  script itself performs no additional downloads.
- The script is short enough (~90 lines) that a user can skim it before
  piping to bash. Encourage this in the README.
