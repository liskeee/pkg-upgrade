from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pkg_upgrade.declarative import DeclarativeManager, load_declarative_dir
from pkg_upgrade.models import Package
from pkg_upgrade.registry import clear_registry, discover_managers


def _repopulate_builtins() -> None:
    """Clear registry and reload built-in managers so decorators re-fire."""
    clear_registry()
    for sub in ("brew", "cask", "pip", "npm", "gem", "system"):
        mod = importlib.import_module(f"pkg_upgrade.managers.{sub}")
        importlib.reload(mod)


@pytest.fixture(autouse=True)
def _clean():
    clear_registry()
    yield
    _repopulate_builtins()


def _write_manifest(tmp_path: Path, name: str, body: str) -> Path:
    f = tmp_path / name
    f.write_text(body)
    return f


def test_load_registers_manager(tmp_path):
    _write_manifest(
        tmp_path,
        "fake.yaml",
        r"""
name: Fake
key: fake
icon: "x"
platforms: [macos, linux, windows]
install_hint: "hint"
check:
  cmd: [echo, hi]
  parser: generic_regex
  regex: '^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$'
upgrade:
  cmd: [echo, upgrading, "{name}"]
""",
    )
    load_declarative_dir(tmp_path)
    managers = discover_managers(load_entry_points=False, load_declarative=False)
    keys = [m.key for m in managers]
    assert "fake" in keys
    mgr = next(m for m in managers if m.key == "fake")
    assert isinstance(mgr, DeclarativeManager)
    assert mgr.platforms == frozenset({"macos", "linux", "windows"})


async def test_check_outdated_runs_cmd_and_parses(tmp_path):
    _write_manifest(
        tmp_path,
        "fake.yaml",
        r"""
name: Fake
key: fake
icon: "x"
platforms: [macos, linux, windows]
check:
  cmd: [fake-cli, list]
  parser: generic_regex
  regex: '^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$'
upgrade:
  cmd: [fake-cli, install, "{name}"]
""",
    )
    load_declarative_dir(tmp_path)
    mgr = next(
        m
        for m in discover_managers(load_entry_points=False, load_declarative=False)
        if m.key == "fake"
    )

    # Patch the subprocess function — name must match what declarative.py imports.
    with patch(
        "pkg_upgrade.declarative.run_subprocess",
        new=AsyncMock(return_value=(0, "foo 1 -> 2\n", "")),
    ):
        pkgs = await mgr.check_outdated()

    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [("foo", "1", "2")]


async def test_upgrade_substitutes_name_placeholder(tmp_path):
    _write_manifest(
        tmp_path,
        "fake.yaml",
        r"""
name: Fake
key: fake
icon: "x"
platforms: [macos, linux, windows]
check:
  cmd: [fake-cli, list]
  parser: generic_regex
  regex: '^(?P<name>\S+)$'
upgrade:
  cmd: [fake-cli, install, "{name}"]
""",
    )
    load_declarative_dir(tmp_path)
    mgr = next(
        m
        for m in discover_managers(load_entry_points=False, load_declarative=False)
        if m.key == "fake"
    )

    mock = AsyncMock(return_value=(0, "ok", ""))
    with patch("pkg_upgrade.declarative.run_subprocess", new=mock):
        result = await mgr.upgrade(Package(name="foo", current_version="1", latest_version="2"))

    assert result.success is True
    args, _ = mock.call_args
    assert args[0] == ["fake-cli", "install", "foo"]


def test_manifest_missing_required_field_raises(tmp_path):
    _write_manifest(tmp_path, "bad.yaml", "name: X\nkey: x\n")
    with pytest.raises(Exception, match=r"(platforms|check|upgrade|icon)"):
        load_declarative_dir(tmp_path)


def test_is_available_checks_first_command_word(tmp_path):
    _write_manifest(
        tmp_path,
        "fake.yaml",
        r"""
name: Fake
key: fake
icon: "x"
platforms: [macos, linux, windows]
check:
  cmd: [definitely-not-installed-xyz, list]
  parser: generic_regex
  regex: '^(?P<name>\S+)$'
upgrade:
  cmd: [definitely-not-installed-xyz, install, "{name}"]
""",
    )
    load_declarative_dir(tmp_path)
    mgr = next(
        m
        for m in discover_managers(load_entry_points=False, load_declarative=False)
        if m.key == "fake"
    )
    assert asyncio.run(mgr.is_available()) is False
