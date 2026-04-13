from __future__ import annotations

import pytest

from pkg_upgrade import cli, completion


def test_plain_list_managers_returns_sorted_keys():
    keys = completion.plain_list_managers()
    assert keys == sorted(keys)
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
    monkeypatch.setattr(completion.sys, "platform", "linux")  # type: ignore[attr-defined]
    assert completion.cache_path() == tmp_path / "pkg-upgrade" / "managers.list"


def test_cache_path_windows(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(completion.sys, "platform", "win32")  # type: ignore[attr-defined]
    assert completion.cache_path() == tmp_path / "pkg-upgrade" / "managers.list"


def test_cli_list_plain_smoke(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["pkg-upgrade", "--list", "--plain"])
    assert cli.main() == 0
    out = capsys.readouterr().out.splitlines()
    assert "brew" in out
    assert out == sorted(out)


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish", "powershell"])
def test_completion_subcommand_prints_packaged_script(shell, capsys):
    assert completion.completion_subcommand(shell) == 0
    out = capsys.readouterr().out
    assert out
    assert "pkg-upgrade" in out


def test_completion_subcommand_invalid_shell(capsys):
    assert completion.completion_subcommand("tcsh") == 2
    err = capsys.readouterr().err
    assert "bash" in err and "zsh" in err and "fish" in err and "powershell" in err
