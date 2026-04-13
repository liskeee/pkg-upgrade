from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pkg_upgrade.self_update import detect_install_method, upgrade_command


@pytest.mark.parametrize(
    "exe_path, expected",
    [
        ("/Users/x/.local/pipx/venvs/pkg-upgrade/bin/python", "pipx"),
        ("/opt/homebrew/Cellar/pkg-upgrade/1.0.0/libexec/bin/python", "brew"),
        ("/usr/local/Cellar/pkg-upgrade/1.0.0/libexec/bin/python", "brew"),
        ("C:/Users/x/scoop/apps/pkg-upgrade/current/python.exe", "scoop"),
        ("/Users/x/.local/share/pkg-upgrade/venv/bin/python", "install_sh"),
        ("C:/Users/x/AppData/Local/pkg-upgrade/venv/Scripts/python.exe", "install_ps1"),
        ("/usr/bin/python3", "pip"),
    ],
)
def test_detect_install_method(exe_path: str, expected: str) -> None:
    with patch("pkg_upgrade.self_update.sys.executable", exe_path):
        with patch("pkg_upgrade.self_update._is_editable_install", return_value=False):
            assert detect_install_method() == expected


def test_detect_editable(tmp_path: Path) -> None:
    fake_pyproject = tmp_path / "pyproject.toml"
    fake_pyproject.write_text("[project]\nname='pkg-upgrade'\n")
    with patch("pkg_upgrade.self_update._editable_pyproject", return_value=fake_pyproject):
        assert detect_install_method() == "editable"


def test_upgrade_command_pipx() -> None:
    cmd, shell = upgrade_command("pipx")
    assert cmd == ["pipx", "upgrade", "pkg-upgrade"]
    assert shell is False


def test_upgrade_command_brew() -> None:
    cmd, shell = upgrade_command("brew")
    assert cmd == ["brew", "upgrade", "pkg-upgrade"]
    assert shell is False


def test_upgrade_command_scoop() -> None:
    cmd, shell = upgrade_command("scoop")
    assert cmd == ["scoop", "update", "pkg-upgrade"]
    assert shell is False


def test_upgrade_command_install_sh() -> None:
    cmd, shell = upgrade_command("install_sh")
    assert shell is True
    assert cmd is not None
    assert "install.sh" in cmd[0]


def test_upgrade_command_install_ps1() -> None:
    cmd, shell = upgrade_command("install_ps1")
    assert shell is True
    assert cmd is not None
    assert "install.ps1" in cmd[0]


def test_upgrade_command_pip_uses_current_python() -> None:
    cmd, shell = upgrade_command("pip")
    assert cmd == [sys.executable, "-m", "pip", "install", "--upgrade", "pkg-upgrade"]
    assert shell is False


def test_upgrade_command_editable_returns_none() -> None:
    cmd, shell = upgrade_command("editable")
    assert cmd is None
    assert shell is False


def test_install_method_literal_values() -> None:
    # Sanity: every method has an upgrade_command branch
    for m in ("pipx", "brew", "scoop", "install_sh", "install_ps1", "pip", "editable"):
        upgrade_command(m)  # must not raise
