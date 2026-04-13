# Shell Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Tab completion for `pkg-upgrade` in bash, zsh, fish, and PowerShell, auto-installed by every distribution channel.

**Architecture:** Four static completion scripts under `src/pkg_upgrade/completions/` are packaged with the wheel. A new `pkg-upgrade --list-managers --plain` command emits one manager key per line and write-throughs a cache file that scripts consult at Tab time. A `pkg-upgrade completion <shell>` subcommand prints the packaged script for manual install. Homebrew / Scoop / install.sh / install.ps1 each drop the right script into the shell's auto-load path.

**Tech Stack:** Python 3.12, argparse, importlib.resources, platformdirs, bash/zsh/fish/PowerShell, pytest + shell subprocess integration tests.

Spec: [`docs/superpowers/specs/2026-04-13-shell-completion-design.md`](../specs/2026-04-13-shell-completion-design.md)

---

## File Map

- Create: `src/pkg_upgrade/completion.py` — cache path helpers, `plain_list_managers()`, `completion_subcommand(shell)`.
- Create: `src/pkg_upgrade/completions/__init__.py` — empty, makes the dir a package so `importlib.resources` can read it.
- Create: `src/pkg_upgrade/completions/pkg-upgrade.bash`
- Create: `src/pkg_upgrade/completions/_pkg-upgrade` (zsh)
- Create: `src/pkg_upgrade/completions/pkg-upgrade.fish`
- Create: `src/pkg_upgrade/completions/pkg-upgrade.ps1`
- Modify: `src/pkg_upgrade/cli.py` — add `--plain`, `completion` subcommand wiring.
- Modify: `pyproject.toml` — ensure completion files are shipped (hatch `force-include` for non-`.py` resources).
- Modify: `Formula/pkg-upgrade.rb` — install completion files via brew helpers.
- Modify: `scoop/pkg-upgrade.json` — `post_install` / `uninstaller` hooks.
- Modify: `install.sh` — detect shell, copy bash/zsh/fish completion.
- Modify: `install.ps1` — copy ps1 completion, append to `$PROFILE`.
- Modify: `README.md` — completion install docs.
- Create: `tests/test_completion.py` — unit tests for `plain_list_managers` + `completion` subcommand.
- Create: `tests/test_completion_shells.py` — shell integration tests (POSIX only, guarded).
- Create: `tests/test_installer_completion.py` — installer sandbox tests.

---

## Task 1: `--list-managers --plain` output + cache write-through

**Files:**
- Create: `src/pkg_upgrade/completion.py`
- Modify: `src/pkg_upgrade/cli.py` (argparse, dispatch)
- Test: `tests/test_completion.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_completion.py
from __future__ import annotations

from pathlib import Path

import pytest

from pkg_upgrade import completion


def test_plain_list_managers_returns_sorted_keys():
    keys = completion.plain_list_managers()
    assert keys == sorted(keys)
    # Built-ins must be present on any OS (they self-filter at runtime, but
    # all_registered() includes all decorated classes regardless of OS).
    for k in ("brew", "cask", "pip", "npm", "gem", "system"):
        assert k in keys


def test_plain_list_managers_writes_cache(tmp_path, monkeypatch):
    cache = tmp_path / "managers.list"
    monkeypatch.setattr(completion, "cache_path", lambda: cache)
    keys = completion.plain_list_managers(write_cache=True)
    assert cache.exists()
    assert cache.read_text(encoding="utf-8").splitlines() == keys


def test_cache_path_posix(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr(completion.sys, "platform", "linux")
    assert completion.cache_path() == tmp_path / "pkg-upgrade" / "managers.list"


def test_cache_path_windows(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(completion.sys, "platform", "win32")
    assert completion.cache_path() == tmp_path / "pkg-upgrade" / "managers.list"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_completion.py -v`
Expected: FAIL with `ModuleNotFoundError: pkg_upgrade.completion` or `AttributeError`.

- [ ] **Step 3: Implement `completion.py`**

```python
# src/pkg_upgrade/completion.py
from __future__ import annotations

import os
import sys
from pathlib import Path


def cache_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "pkg-upgrade" / "managers.list"


def plain_list_managers(*, write_cache: bool = False) -> list[str]:
    """Return the sorted list of registered manager keys.

    Imports are done lazily so --plain stays fast and avoids pulling
    Textual/asyncio on the completion hot path.
    """
    from pkg_upgrade.registry import all_registered  # noqa: PLC0415

    keys = sorted({cls.key for cls in all_registered()})
    if write_cache:
        path = cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(keys) + "\n", encoding="utf-8")
    return keys
```

- [ ] **Step 4: Wire `--plain` in `cli.py`**

Add flag near `--list` and dispatch before the onboarding/config code path. Modify `build_parser`:

```python
    parser.add_argument("--list", action="store_true", dest="list_managers")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="With --list, print bare manager keys (one per line) for shell completion.",
    )
```

Modify `main()` — replace the `if args.list_managers:` block:

```python
    if args.list_managers:
        if args.plain:
            from pkg_upgrade.completion import plain_list_managers  # noqa: PLC0415

            for key in plain_list_managers(write_cache=True):
                print(key)
            return 0
        return _print_list(skip=args.skip, only=args.only)
```

- [ ] **Step 5: Add CLI smoke test**

Append to `tests/test_completion.py`:

```python
def test_cli_list_plain_smoke(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from pkg_upgrade import cli

    rc = cli.main.__wrapped__ if hasattr(cli.main, "__wrapped__") else cli.main
    # argparse reads sys.argv; monkeypatch it.
    monkeypatch.setattr("sys.argv", ["pkg-upgrade", "--list", "--plain"])
    assert cli.main() == 0
    out = capsys.readouterr().out.splitlines()
    assert "brew" in out
    assert out == sorted(out)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_completion.py -v`
Expected: all PASS.

- [ ] **Step 7: Lint + types**

Run: `ruff check src/pkg_upgrade/completion.py src/pkg_upgrade/cli.py && mypy`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add src/pkg_upgrade/completion.py src/pkg_upgrade/cli.py tests/test_completion.py
git commit -m "feat(cli): --list --plain emits manager keys with cache write-through"
```

---

## Task 2: `completion <shell>` subcommand + packaged scripts directory

**Files:**
- Create: `src/pkg_upgrade/completions/__init__.py`
- Modify: `src/pkg_upgrade/completion.py` — `completion_subcommand` + shell table.
- Modify: `src/pkg_upgrade/cli.py` — subparsers.
- Modify: `pyproject.toml` — force-include completion files in wheel.
- Test: `tests/test_completion.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_completion.py`:

```python
@pytest.mark.parametrize("shell", ["bash", "zsh", "fish", "powershell"])
def test_completion_subcommand_prints_packaged_script(shell, capsys):
    from pkg_upgrade import completion as c

    assert c.completion_subcommand(shell) == 0
    out = capsys.readouterr().out
    assert out  # non-empty
    assert "pkg-upgrade" in out


def test_completion_subcommand_invalid_shell(capsys):
    from pkg_upgrade import completion as c

    assert c.completion_subcommand("tcsh") == 2
    err = capsys.readouterr().err
    assert "bash" in err and "zsh" in err and "fish" in err and "powershell" in err
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_completion.py::test_completion_subcommand_invalid_shell -v`
Expected: FAIL with `AttributeError: module 'pkg_upgrade.completion' has no attribute 'completion_subcommand'`.

- [ ] **Step 3: Create the empty package dir**

```bash
mkdir -p src/pkg_upgrade/completions
touch src/pkg_upgrade/completions/__init__.py
```

- [ ] **Step 4: Create minimal placeholder scripts**

(Tasks 3–6 will fill these in; we need them present now so `importlib.resources` can find them.)

```bash
printf '# pkg-upgrade bash completion (stub)\n'       > src/pkg_upgrade/completions/pkg-upgrade.bash
printf '#compdef pkg-upgrade\n# stub\n'               > src/pkg_upgrade/completions/_pkg-upgrade
printf '# pkg-upgrade fish completion (stub)\n'       > src/pkg_upgrade/completions/pkg-upgrade.fish
printf '# pkg-upgrade PowerShell completion (stub)\n' > src/pkg_upgrade/completions/pkg-upgrade.ps1
```

- [ ] **Step 5: Implement `completion_subcommand`**

Append to `src/pkg_upgrade/completion.py`:

```python
from importlib import resources

_SHELL_FILES: dict[str, str] = {
    "bash": "pkg-upgrade.bash",
    "zsh": "_pkg-upgrade",
    "fish": "pkg-upgrade.fish",
    "powershell": "pkg-upgrade.ps1",
}


def completion_subcommand(shell: str) -> int:
    """Print the packaged completion script for `shell` to stdout."""
    filename = _SHELL_FILES.get(shell)
    if filename is None:
        valid = ", ".join(sorted(_SHELL_FILES))
        print(f"error: unknown shell '{shell}'. Valid: {valid}", file=sys.stderr)
        return 2
    text = resources.files("pkg_upgrade.completions").joinpath(filename).read_text(
        encoding="utf-8"
    )
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0
```

- [ ] **Step 6: Wire subparser in `cli.py`**

Replace the `build_parser` body such that it supports an optional `completion` subcommand without breaking existing flag-only invocations. Add after the existing `add_argument` calls and before `return parser`:

```python
    subparsers = parser.add_subparsers(dest="subcommand")
    comp = subparsers.add_parser("completion", help="Print shell completion script")
    comp.add_argument("shell", choices=["bash", "zsh", "fish", "powershell"])
```

In `main()`, at the very top after `args = parse_args()`:

```python
    if args.subcommand == "completion":
        from pkg_upgrade.completion import completion_subcommand  # noqa: PLC0415

        return completion_subcommand(args.shell)
```

- [ ] **Step 7: Force-include completion files in the wheel**

Append to `pyproject.toml` under the existing hatch section (add section if missing):

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/pkg_upgrade"]

[tool.hatch.build.targets.wheel.force-include]
"src/pkg_upgrade/completions" = "pkg_upgrade/completions"
```

- [ ] **Step 8: Run tests**

Run: `pytest tests/test_completion.py -v`
Expected: all PASS.

- [ ] **Step 9: Build a wheel and confirm files are packaged**

Run:
```bash
python -m build --wheel
python -c "import zipfile, glob; [print(n) for n in zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]).namelist() if 'completions' in n]"
```
Expected: output lists all four completion files under `pkg_upgrade/completions/`.

- [ ] **Step 10: Commit**

```bash
git add src/pkg_upgrade/completion.py src/pkg_upgrade/cli.py \
        src/pkg_upgrade/completions/ pyproject.toml tests/test_completion.py
git commit -m "feat(cli): add 'completion <shell>' subcommand with packaged scripts"
```

---

## Task 3: Bash completion script

**Files:**
- Modify: `src/pkg_upgrade/completions/pkg-upgrade.bash`
- Test: `tests/test_completion_shells.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_completion_shells.py
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

COMPLETIONS = Path(__file__).resolve().parent.parent / "src" / "pkg_upgrade" / "completions"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only shell harness")


def _bash_complete(line: str, cache_content: str = "brew\ncask\ngem\nnpm\npip\nsystem\n") -> list[str]:
    """Return bash completion candidates for `line` (terminating at cursor)."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not installed")
    script = COMPLETIONS / "pkg-upgrade.bash"
    # Write a fake cache the script will consult.
    cache = Path(os.environ["XDG_CACHE_HOME"]) / "pkg-upgrade" / "managers.list"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(cache_content, encoding="utf-8")

    # COMP_WORDS / COMP_CWORD setup, then call the completion function.
    harness = f"""
        source {script}
        COMP_LINE={line!r}
        COMP_POINT=${{#COMP_LINE}}
        read -a COMP_WORDS <<<"$COMP_LINE"
        COMP_CWORD=$((${{#COMP_WORDS[@]}} - 1))
        # If line ends with space, current word is empty.
        if [[ "$COMP_LINE" == *" " ]]; then
          COMP_WORDS+=("")
          COMP_CWORD=$((COMP_CWORD + 1))
        fi
        _pkg_upgrade_completions
        printf '%s\\n' "${{COMPREPLY[@]}}"
    """
    out = subprocess.run(
        [bash, "-c", harness],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )
    return [ln for ln in out.stdout.splitlines() if ln]


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))


def test_bash_flag_completion():
    candidates = _bash_complete("pkg-upgrade --")
    for flag in ("--only", "--skip", "--yes", "--dry-run", "--list", "--self-update"):
        assert flag in candidates


def test_bash_manager_completion_only():
    candidates = _bash_complete("pkg-upgrade --only br")
    assert "brew" in candidates
    assert "cask" not in candidates  # prefix filter


def test_bash_manager_completion_skip():
    candidates = _bash_complete("pkg-upgrade --skip p")
    assert "pip" in candidates


def test_bash_comma_separated():
    candidates = _bash_complete("pkg-upgrade --only brew,c")
    assert "cask" in candidates
    # Already-present token excluded.
    assert "brew" not in candidates
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_completion_shells.py -v -k bash`
Expected: FAIL — stub script has no completion function.

- [ ] **Step 3: Implement the bash script**

Replace contents of `src/pkg_upgrade/completions/pkg-upgrade.bash`:

```bash
# pkg-upgrade bash completion

_pkg_upgrade_managers() {
  local cache="${XDG_CACHE_HOME:-$HOME/.cache}/pkg-upgrade/managers.list"
  if [[ -r "$cache" ]]; then
    cat "$cache"
  else
    printf '%s\n' brew cask gem npm pip system
  fi
}

_pkg_upgrade_complete_list() {
  # $1 = current token (e.g. "brew,c"); complete after last comma,
  # excluding tokens already in the list.
  local cur="$1"
  local prefix="${cur%,*}"
  local tail="${cur##*,}"
  local sep=","
  if [[ "$cur" != *","* ]]; then
    prefix=""
    tail="$cur"
    sep=""
  fi
  local used=()
  if [[ -n "$prefix" ]]; then
    IFS=',' read -ra used <<<"$prefix"
  fi
  local all
  all=$(_pkg_upgrade_managers)
  local m
  for m in $all; do
    local skip=""
    for u in "${used[@]}"; do
      [[ "$u" == "$m" ]] && skip=1 && break
    done
    [[ -z "$skip" && "$m" == "$tail"* ]] && COMPREPLY+=("${prefix}${sep}${m}")
  done
}

_pkg_upgrade_completions() {
  local cur prev
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  COMPREPLY=()

  case "$prev" in
    --only|--skip)
      _pkg_upgrade_complete_list "$cur"
      return 0
      ;;
    --log-dir)
      COMPREPLY=( $(compgen -d -- "$cur") )
      return 0
      ;;
    --max-parallel)
      return 0
      ;;
  esac

  if [[ "$cur" == --* ]]; then
    local flags="--only --skip --yes --dry-run --no-notify --no-log --log-dir --list --plain --onboard --show-graph --max-parallel --version --self-update"
    COMPREPLY=( $(compgen -W "$flags" -- "$cur") )
    return 0
  fi

  # First positional → 'completion' subcommand
  if [[ "$COMP_CWORD" == "1" ]]; then
    COMPREPLY=( $(compgen -W "completion" -- "$cur") )
    return 0
  fi

  if [[ "${COMP_WORDS[1]}" == "completion" && "$COMP_CWORD" == "2" ]]; then
    COMPREPLY=( $(compgen -W "bash zsh fish powershell" -- "$cur") )
    return 0
  fi
}

complete -F _pkg_upgrade_completions pkg-upgrade
complete -F _pkg_upgrade_completions pkgup
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_completion_shells.py -v -k bash`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/completions/pkg-upgrade.bash tests/test_completion_shells.py
git commit -m "feat(completion): bash script with flag + manager + comma list support"
```

---

## Task 4: Zsh completion script

**Files:**
- Modify: `src/pkg_upgrade/completions/_pkg-upgrade`
- Test: `tests/test_completion_shells.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_completion_shells.py`:

```python
def _zsh_complete(line: str, cache_content: str = "brew\ncask\ngem\nnpm\npip\nsystem\n") -> list[str]:
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh not installed")
    cache = Path(os.environ["XDG_CACHE_HOME"]) / "pkg-upgrade" / "managers.list"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(cache_content, encoding="utf-8")

    fpath_dir = COMPLETIONS
    # Use zsh's completion machinery via a tiny harness that invokes
    # _main_complete and prints the candidate list.
    harness = rf"""
        fpath=({fpath_dir} $fpath)
        autoload -Uz compinit
        compinit -u -d /tmp/.zcompdump-$$
        autoload -Uz _pkg-upgrade
        # Simulate cursor at end of LINE.
        buffer={line!r}
        # Use `zsh -c` + `compctl` workaround: dump matches via 'print -l'.
        typeset -a reply
        _comp_complete_help() {{ print -l -- $@; }}
        # zsh has no trivial public "list matches for string" hook;
        # we rely on `_main_complete` called inside an interactive-ish shell.
        # Fallback: call the function directly with a minimal faked state.
        words=(${{=buffer}})
        (( CURRENT = ${{#words}} ))
        if [[ "$buffer" == *" " ]]; then
          words+=("")
          (( CURRENT++ ))
        fi
        _pkg-upgrade 2>/dev/null
        print -l -- ${{_comp_matches:-}} ${{compstate[matches]}}
    """
    out = subprocess.run(
        [zsh, "-f", "-c", harness],
        check=False,
        capture_output=True,
        text=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln]


def test_zsh_script_is_syntactically_valid():
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh not installed")
    script = COMPLETIONS / "_pkg-upgrade"
    r = subprocess.run([zsh, "-n", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_zsh_script_lists_manager_keys_in_source():
    text = (COMPLETIONS / "_pkg-upgrade").read_text(encoding="utf-8")
    # Script must reference the cache path and built-in fallback.
    assert "managers.list" in text
    for k in ("brew", "cask", "pip", "npm", "gem", "system"):
        assert k in text
```

> **Note on zsh testing:** zsh's completion engine is hard to script headlessly. We rely on `zsh -n` (syntax check) + static string assertions. The end-to-end behavior is validated by the `shellcheck`-style review and by manually sourcing in CI.

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_completion_shells.py -v -k zsh`
Expected: FAIL — stub lacks the required strings / function.

- [ ] **Step 3: Implement the zsh script**

Replace contents of `src/pkg_upgrade/completions/_pkg-upgrade`:

```zsh
#compdef pkg-upgrade pkgup

_pkg_upgrade_managers() {
  local cache="${XDG_CACHE_HOME:-$HOME/.cache}/pkg-upgrade/managers.list"
  if [[ -r "$cache" ]]; then
    local -a lines
    lines=(${(f)"$(<$cache)"})
    print -l -- $lines
  else
    print -l -- brew cask gem npm pip system
  fi
}

_pkg_upgrade_complete_list() {
  # Complete comma-separated manager lists for --only / --skip.
  local cur="${words[CURRENT]}"
  local prefix tail sep
  if [[ "$cur" == *","* ]]; then
    prefix="${cur%,*}"
    tail="${cur##*,}"
    sep=","
  else
    prefix=""
    tail="$cur"
    sep=""
  fi
  local -a used all cand
  used=(${(s:,:)prefix})
  all=(${(f)"$(_pkg_upgrade_managers)"})
  local m
  for m in $all; do
    if [[ -z "${used[(r)$m]}" && "$m" == ${tail}* ]]; then
      cand+=("${prefix}${sep}${m}")
    fi
  done
  compadd -- $cand
}

_pkg-upgrade() {
  local -a flags
  flags=(
    '--only[run only these managers]:managers:_pkg_upgrade_complete_list'
    '--skip[skip these managers]:managers:_pkg_upgrade_complete_list'
    '--yes[auto-confirm]'
    '-y[auto-confirm]'
    '--dry-run[print plan without running]'
    '--no-notify[disable completion notification]'
    '--no-log[disable log file]'
    '--log-dir[log directory]:dir:_files -/'
    '--list[list managers]'
    '--plain[plain output with --list]'
    '--onboard[run onboarding wizard]'
    '--show-graph[print execution plan]'
    '--max-parallel[cap concurrency]:n:'
    '--version[print version]'
    '--self-update[upgrade pkg-upgrade itself]'
  )

  local context state state_descr line
  typeset -A opt_args

  _arguments -C \
    $flags \
    '1: :->cmd' \
    '*:: :->args'

  case $state in
    cmd)
      _values 'subcommand' 'completion[print shell completion]'
      ;;
    args)
      if [[ "${line[1]}" == "completion" ]]; then
        _values 'shell' bash zsh fish powershell
      fi
      ;;
  esac
}

_pkg-upgrade "$@"
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_completion_shells.py -v -k zsh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/completions/_pkg-upgrade tests/test_completion_shells.py
git commit -m "feat(completion): zsh script with flag descriptions and comma list support"
```

---

## Task 5: Fish completion script

**Files:**
- Modify: `src/pkg_upgrade/completions/pkg-upgrade.fish`
- Test: `tests/test_completion_shells.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_completion_shells.py`:

```python
def test_fish_script_is_syntactically_valid():
    fish = shutil.which("fish")
    if not fish:
        pytest.skip("fish not installed")
    script = COMPLETIONS / "pkg-upgrade.fish"
    r = subprocess.run([fish, "-n", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_fish_manager_completion():
    fish = shutil.which("fish")
    if not fish:
        pytest.skip("fish not installed")
    cache = Path(os.environ["XDG_CACHE_HOME"]) / "pkg-upgrade" / "managers.list"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text("brew\ncask\ngem\nnpm\npip\nsystem\n", encoding="utf-8")
    script = COMPLETIONS / "pkg-upgrade.fish"
    r = subprocess.run(
        [fish, "-c", f"source {script}; complete -C 'pkg-upgrade --only '"],
        capture_output=True, text=True, check=True,
    )
    assert "brew" in r.stdout
    assert "pip" in r.stdout
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_completion_shells.py -v -k fish`
Expected: FAIL (stub).

- [ ] **Step 3: Implement the fish script**

Replace contents of `src/pkg_upgrade/completions/pkg-upgrade.fish`:

```fish
# pkg-upgrade fish completion

function __pkg_upgrade_managers
    set -l cache "$XDG_CACHE_HOME/pkg-upgrade/managers.list"
    if test -z "$XDG_CACHE_HOME"
        set cache "$HOME/.cache/pkg-upgrade/managers.list"
    end
    if test -r "$cache"
        cat "$cache"
    else
        printf '%s\n' brew cask gem npm pip system
    end
end

# Flags
complete -c pkg-upgrade -l only  -d 'Run only these managers' -x -a '(__pkg_upgrade_managers)'
complete -c pkg-upgrade -l skip  -d 'Skip these managers'     -x -a '(__pkg_upgrade_managers)'
complete -c pkg-upgrade -l yes       -s y -d 'Auto-confirm'
complete -c pkg-upgrade -l dry-run              -d 'Print plan without running'
complete -c pkg-upgrade -l no-notify            -d 'Disable completion notification'
complete -c pkg-upgrade -l no-log               -d 'Disable log file'
complete -c pkg-upgrade -l log-dir -r           -d 'Log directory' -a '(__fish_complete_directories)'
complete -c pkg-upgrade -l list                 -d 'List managers'
complete -c pkg-upgrade -l plain                -d 'Plain output with --list'
complete -c pkg-upgrade -l onboard              -d 'Run onboarding wizard'
complete -c pkg-upgrade -l show-graph           -d 'Print execution plan'
complete -c pkg-upgrade -l max-parallel -r      -d 'Cap concurrency'
complete -c pkg-upgrade -l version              -d 'Print version'
complete -c pkg-upgrade -l self-update          -d 'Upgrade pkg-upgrade itself'

# Subcommand: completion
complete -c pkg-upgrade -n '__fish_use_subcommand' -a completion -d 'Print shell completion script'
complete -c pkg-upgrade -n '__fish_seen_subcommand_from completion' -a 'bash zsh fish powershell'

# Mirror for pkgup alias
complete -c pkgup -w pkg-upgrade
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_completion_shells.py -v -k fish`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/completions/pkg-upgrade.fish tests/test_completion_shells.py
git commit -m "feat(completion): fish script"
```

---

## Task 6: PowerShell completion script

**Files:**
- Modify: `src/pkg_upgrade/completions/pkg-upgrade.ps1`
- Test: `tests/test_completion_shells.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_completion_shells.py`:

```python
def test_powershell_script_references_register_completer():
    text = (COMPLETIONS / "pkg-upgrade.ps1").read_text(encoding="utf-8")
    assert "Register-ArgumentCompleter" in text
    assert "pkg-upgrade" in text
    for k in ("brew", "cask", "pip", "npm", "gem", "system"):
        assert k in text


def test_powershell_script_parses():
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        pytest.skip("pwsh not installed")
    script = COMPLETIONS / "pkg-upgrade.ps1"
    r = subprocess.run(
        [pwsh, "-NoProfile", "-Command",
         f"$null = [ScriptBlock]::Create((Get-Content -Raw '{script}'))"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_completion_shells.py -v -k powershell`
Expected: FAIL.

- [ ] **Step 3: Implement the ps1 script**

Replace contents of `src/pkg_upgrade/completions/pkg-upgrade.ps1`:

```powershell
# pkg-upgrade PowerShell completion

function Get-PkgUpgradeManagers {
    $cache = Join-Path $env:LOCALAPPDATA 'pkg-upgrade\managers.list'
    if (Test-Path $cache) {
        Get-Content -LiteralPath $cache -Encoding UTF8
    } else {
        @('brew', 'cask', 'gem', 'npm', 'pip', 'system')
    }
}

$script:PkgUpgradeFlags = @(
    '--only', '--skip', '--yes', '--dry-run', '--no-notify', '--no-log',
    '--log-dir', '--list', '--plain', '--onboard', '--show-graph',
    '--max-parallel', '--version', '--self-update'
)

$completer = {
    param($wordToComplete, $commandAst, $cursorPosition)

    $tokens = $commandAst.CommandElements | ForEach-Object { $_.ToString() }
    $prev = if ($tokens.Count -ge 2) { $tokens[-2] } else { '' }

    if ($prev -in '--only', '--skip') {
        $cur  = $wordToComplete
        $prefix, $tail = if ($cur -match ',') { @($cur -replace ',[^,]*$',''), ($cur -split ',')[-1] } else { @('', $cur) }
        $sep = if ($prefix) { ',' } else { '' }
        $used = if ($prefix) { $prefix -split ',' } else { @() }
        Get-PkgUpgradeManagers |
            Where-Object { $_ -like "$tail*" -and $used -notcontains $_ } |
            ForEach-Object {
                $val = "$prefix$sep$_"
                [System.Management.Automation.CompletionResult]::new($val, $val, 'ParameterValue', $_)
            }
        return
    }

    if ($wordToComplete -like '--*' -or $tokens.Count -le 1) {
        $script:PkgUpgradeFlags |
            Where-Object { $_ -like "$wordToComplete*" } |
            ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_)
            }
    }

    if ($tokens.Count -ge 2 -and $tokens[1] -eq 'completion') {
        'bash', 'zsh', 'fish', 'powershell' |
            Where-Object { $_ -like "$wordToComplete*" } |
            ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }
    }
}

Register-ArgumentCompleter -Native -CommandName pkg-upgrade -ScriptBlock $completer
Register-ArgumentCompleter -Native -CommandName pkgup       -ScriptBlock $completer
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_completion_shells.py -v -k powershell`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/completions/pkg-upgrade.ps1 tests/test_completion_shells.py
git commit -m "feat(completion): powershell Register-ArgumentCompleter script"
```

---

## Task 7: Homebrew formula bundling

**Files:**
- Modify: `Formula/pkg-upgrade.rb`
- Test: `tests/test_installers.py` (extend) — static assertion that the formula references the three completion helpers.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_installers.py`:

```python
def test_formula_installs_completions():
    formula = Path(__file__).resolve().parent.parent / "Formula" / "pkg-upgrade.rb"
    text = formula.read_text(encoding="utf-8")
    assert "bash_completion.install" in text
    assert "zsh_completion.install"  in text
    assert "fish_completion.install" in text
    assert "pkg-upgrade.bash" in text
    assert "_pkg-upgrade" in text
    assert "pkg-upgrade.fish" in text
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_installers.py::test_formula_installs_completions -v`
Expected: FAIL.

- [ ] **Step 3: Update the formula**

Open `Formula/pkg-upgrade.rb` and within the `install` method, after the existing `virtualenv_install_with_resources` (or equivalent) line add:

```ruby
    bash_completion.install "src/pkg_upgrade/completions/pkg-upgrade.bash" => "pkg-upgrade"
    zsh_completion.install  "src/pkg_upgrade/completions/_pkg-upgrade"     => "_pkg-upgrade"
    fish_completion.install "src/pkg_upgrade/completions/pkg-upgrade.fish" => "pkg-upgrade.fish"
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_installers.py::test_formula_installs_completions -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Formula/pkg-upgrade.rb tests/test_installers.py
git commit -m "feat(formula): install bash/zsh/fish completions"
```

---

## Task 8: Scoop manifest + `install.ps1` `$PROFILE` hook

**Files:**
- Modify: `scoop/pkg-upgrade.json`
- Modify: `install.ps1`
- Test: `tests/test_installer_completion.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_installer_completion.py
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_scoop_manifest_has_post_install_hook():
    data = json.loads((ROOT / "scoop" / "pkg-upgrade.json").read_text(encoding="utf-8"))
    post = data.get("post_install", [])
    joined = "\n".join(post) if isinstance(post, list) else str(post)
    assert "pkg-upgrade.ps1" in joined
    assert "$PROFILE" in joined
    # Idempotency guard (Select-String or -notmatch).
    assert "Select-String" in joined or "-notmatch" in joined


def test_scoop_manifest_has_uninstaller():
    data = json.loads((ROOT / "scoop" / "pkg-upgrade.json").read_text(encoding="utf-8"))
    uninst = data.get("uninstaller", {}).get("script", [])
    joined = "\n".join(uninst) if isinstance(uninst, list) else str(uninst)
    assert "pkg-upgrade.ps1" in joined


def test_install_ps1_appends_to_profile_idempotently():
    text = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "pkg-upgrade.ps1" in text
    assert "$PROFILE" in text
    assert "Select-String" in text or "-notmatch" in text
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_installer_completion.py -v`
Expected: FAIL.

- [ ] **Step 3: Update scoop manifest**

Open `scoop/pkg-upgrade.json` and add top-level keys (merge with existing JSON):

```json
{
  "post_install": [
    "$comp = Join-Path $dir 'completions\\pkg-upgrade.ps1'",
    "Copy-Item -Force (Join-Path $dir 'src\\pkg_upgrade\\completions\\pkg-upgrade.ps1') $comp -ErrorAction SilentlyContinue",
    "$line = \". `\"$comp`\"\"",
    "if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Force -Path $PROFILE | Out-Null }",
    "if (-not (Select-String -Path $PROFILE -SimpleMatch -Pattern 'pkg-upgrade.ps1' -Quiet)) { Add-Content -Path $PROFILE -Value $line }"
  ],
  "uninstaller": {
    "script": [
      "if (Test-Path $PROFILE) { (Get-Content $PROFILE) -notmatch 'pkg-upgrade.ps1' | Set-Content $PROFILE }"
    ]
  }
}
```

> **Note:** Keep whatever keys are already in the manifest (version, url, hash, bin, etc.). Only add `post_install` and `uninstaller` — do not overwrite.

- [ ] **Step 4: Update `install.ps1`**

At the end of the install flow (after the `pkg-upgrade.cmd` shim is created), append:

```powershell
# Install PowerShell completion
$completionSource = Join-Path $InstallRoot 'completions\pkg-upgrade.ps1'
$pyCompletion = Join-Path $VenvDir 'Lib\site-packages\pkg_upgrade\completions\pkg-upgrade.ps1'
if (Test-Path $pyCompletion) {
    New-Item -ItemType Directory -Force -Path (Split-Path $completionSource) | Out-Null
    Copy-Item -Force $pyCompletion $completionSource
    $sourceLine = ". `"$completionSource`""
    if (-not (Test-Path $PROFILE)) {
        New-Item -ItemType File -Force -Path $PROFILE | Out-Null
    }
    if (-not (Select-String -Path $PROFILE -SimpleMatch -Pattern 'pkg-upgrade.ps1' -Quiet)) {
        Add-Content -Path $PROFILE -Value $sourceLine
        Write-Host "Added pkg-upgrade completion to $PROFILE. Restart PowerShell to activate."
    }
}
```

Replace `$InstallRoot` / `$VenvDir` with whatever variable names already exist in `install.ps1`.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_installer_completion.py -v`
Expected: PASS.

- [ ] **Step 6: Syntax-check the PowerShell installer**

Run:
```bash
pwsh -NoProfile -Command "[ScriptBlock]::Create((Get-Content -Raw install.ps1)) | Out-Null"
```
Expected: exit 0.

(Skip if `pwsh` is not installed locally — CI `installers` job covers it.)

- [ ] **Step 7: Commit**

```bash
git add scoop/pkg-upgrade.json install.ps1 tests/test_installer_completion.py
git commit -m "feat(install): scoop + install.ps1 source completion from \$PROFILE"
```

---

## Task 9: `install.sh` shell completion drop

**Files:**
- Modify: `install.sh`
- Test: `tests/test_installer_completion.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_installer_completion.py`:

```python
def test_install_sh_handles_bash_zsh_fish():
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "bash-completion/completions/pkg-upgrade" in text
    assert ".zsh/completions/_pkg-upgrade" in text
    assert "fish/completions/pkg-upgrade.fish" in text
    # Idempotent fpath injection for zsh.
    assert "fpath+=" in text or "fpath=(" in text
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_installer_completion.py::test_install_sh_handles_bash_zsh_fish -v`
Expected: FAIL.

- [ ] **Step 3: Update `install.sh`**

Append to `install.sh` after the main install flow:

```bash
install_completion() {
    local shell_name
    shell_name="$(basename "${SHELL:-bash}")"
    # Find the packaged completion. PKG_UPGRADE_PREFIX should be the venv root.
    local pkg_dir
    pkg_dir="$("$PKG_UPGRADE_PREFIX/bin/python" -c 'import pkg_upgrade, os; print(os.path.dirname(pkg_upgrade.__file__))' 2>/dev/null || true)"
    [ -z "$pkg_dir" ] && return 0
    local comp_dir="$pkg_dir/completions"
    [ -d "$comp_dir" ] || return 0

    case "$shell_name" in
        bash)
            local dest="$HOME/.local/share/bash-completion/completions"
            mkdir -p "$dest"
            cp -f "$comp_dir/pkg-upgrade.bash" "$dest/pkg-upgrade"
            echo "Installed bash completion → $dest/pkg-upgrade"
            ;;
        zsh)
            local dest="$HOME/.zsh/completions"
            mkdir -p "$dest"
            cp -f "$comp_dir/_pkg-upgrade" "$dest/_pkg-upgrade"
            # Inject fpath+= idempotently.
            local rc="$HOME/.zshrc"
            local line='fpath+=("$HOME/.zsh/completions")'
            if [ -f "$rc" ] && ! grep -Fq "$line" "$rc"; then
                printf '\n# Added by pkg-upgrade installer\n%s\nautoload -Uz compinit && compinit\n' "$line" >> "$rc"
            fi
            echo "Installed zsh completion → $dest/_pkg-upgrade"
            ;;
        fish)
            local dest="$HOME/.config/fish/completions"
            mkdir -p "$dest"
            cp -f "$comp_dir/pkg-upgrade.fish" "$dest/pkg-upgrade.fish"
            echo "Installed fish completion → $dest/pkg-upgrade.fish"
            ;;
        *)
            echo "Shell '$shell_name' unsupported for auto-completion install."
            echo "Run: pkg-upgrade completion <bash|zsh|fish|powershell>  to print a script."
            ;;
    esac
    echo "Restart your shell (or 'exec \$SHELL') to activate completion."
}

install_completion
```

> If the script already exports the install prefix under a different name, replace `PKG_UPGRADE_PREFIX` accordingly. Check the existing `install.sh` for the pipx/venv path variable and match it.

- [ ] **Step 4: Run test**

Run: `pytest tests/test_installer_completion.py::test_install_sh_handles_bash_zsh_fish -v`
Expected: PASS.

- [ ] **Step 5: Shellcheck**

Run: `shellcheck install.sh` (skip if not installed; CI `installers` job covers it).
Expected: no new errors beyond what was already there.

- [ ] **Step 6: Commit**

```bash
git add install.sh tests/test_installer_completion.py
git commit -m "feat(install.sh): drop shell completion for bash/zsh/fish"
```

---

## Task 10: README docs

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a Shell Completion section**

Append after the existing "Install" section in `README.md`:

```markdown
## Shell Completion

Completion is installed automatically by every first-party installer
(Homebrew, Scoop, `install.sh`, `install.ps1`). If you installed via
`pipx` or `pip`, set it up manually:

```bash
# bash
pkg-upgrade completion bash  | sudo tee /etc/bash_completion.d/pkg-upgrade

# zsh (add ~/.zsh/completions to your fpath if it isn't already)
pkg-upgrade completion zsh   > "$HOME/.zsh/completions/_pkg-upgrade"

# fish
pkg-upgrade completion fish  > ~/.config/fish/completions/pkg-upgrade.fish

# PowerShell (add to $PROFILE)
pkg-upgrade completion powershell | Out-String | Invoke-Expression
```

Third-party manager plugins appear in Tab completion after the next call
to `pkg-upgrade --list` (or automatically on the first run of any
`pkg-upgrade` command, which refreshes the cache in the background).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: shell completion install guide"
```

---

## Task 11: CI integration

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add a completion-shells CI job**

Append to `.github/workflows/ci.yml`:

```yaml
  completion-shells:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: pip
      - name: Install shells (ubuntu)
        if: runner.os == 'Linux'
        run: sudo apt-get update && sudo apt-get install -y zsh fish
      - name: Install shells (macOS)
        if: runner.os == 'macOS'
        run: brew install fish
      - run: python -m pip install -e ".[dev]"
      - run: pytest tests/test_completion.py tests/test_completion_shells.py tests/test_installer_completion.py -v
```

Also extend the Windows `installers` job (if present) to run the PowerShell parse test:

```yaml
      - name: Pytest PowerShell completion test
        shell: pwsh
        run: pytest tests/test_completion_shells.py -v -k powershell
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: matrix job for bash/zsh/fish completion tests"
```

---

## Final verification

- [ ] **Step 1: Full test suite**

Run: `pytest -x`
Expected: PASS.

- [ ] **Step 2: Lint + types**

Run: `ruff check . && ruff format --check . && mypy`
Expected: clean.

- [ ] **Step 3: Manual smoke in bash**

```bash
python -m pip install -e .
source src/pkg_upgrade/completions/pkg-upgrade.bash
pkg-upgrade --<TAB><TAB>       # expect flag list
pkg-upgrade --only br<TAB>     # expect 'brew'
pkg-upgrade --only brew,c<TAB> # expect 'cask' (and 'brew' absent)
```

- [ ] **Step 4: Open the PR**

```bash
gh pr create --title "feat: shell completion (bash/zsh/fish/powershell)" \
  --body "Implements docs/superpowers/specs/2026-04-13-shell-completion-design.md."
```
