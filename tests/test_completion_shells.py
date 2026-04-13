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
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not installed")
    script = COMPLETIONS / "pkg-upgrade.bash"
    cache = Path(os.environ["XDG_CACHE_HOME"]) / "pkg-upgrade" / "managers.list"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(cache_content, encoding="utf-8")

    harness = f"""
        source {script}
        COMP_LINE={line!r}
        COMP_POINT=${{#COMP_LINE}}
        read -a COMP_WORDS <<<"$COMP_LINE"
        COMP_CWORD=$((${{#COMP_WORDS[@]}} - 1))
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
    assert "cask" not in candidates


def test_bash_manager_completion_skip():
    candidates = _bash_complete("pkg-upgrade --skip p")
    assert "pip" in candidates


def test_bash_comma_separated():
    candidates = _bash_complete("pkg-upgrade --only brew,c")
    assert "cask" in candidates
    assert "brew" not in candidates
