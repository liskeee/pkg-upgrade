from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest

from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.registry import (
    clear_registry,
    discover_managers,
    register_manager,
)


class _FakeManager(PackageManager):
    name = "Fake"
    key = "fake"
    icon = "x"
    platforms = frozenset({"macos", "linux", "windows"})

    async def is_available(self) -> bool:
        return True

    async def check_outdated(self) -> list[Package]:
        return []

    async def upgrade(self, package: Package) -> Result:  # pragma: no cover
        raise NotImplementedError


def _ensure_builtins_loaded() -> None:
    """Import (not reload) builtin manager modules so decorators fire exactly once."""
    for sub in ("brew", "cask", "pip", "npm", "gem", "system"):
        importlib.import_module(f"pkg_upgrade.managers.{sub}")


def _repopulate_builtins() -> None:
    """Clear and re-register builtins by reloading their modules."""
    clear_registry()
    for sub in ("brew", "cask", "pip", "npm", "gem", "system"):
        mod = importlib.import_module(f"pkg_upgrade.managers.{sub}")
        importlib.reload(mod)


@pytest.fixture(autouse=True)
def _clean():
    # Ensure built-in modules are loaded (so import is a no-op inside discover_managers)
    # then clear so each test starts with an empty registry.
    _ensure_builtins_loaded()
    clear_registry()
    yield
    # Restore builtins for other test modules that rely on them.
    _repopulate_builtins()


def test_decorator_registers_manager():
    register_manager(_FakeManager)
    managers = discover_managers(load_entry_points=False, load_declarative=False)
    assert [m.key for m in managers] == ["fake"]


def test_decorator_returns_class_unchanged():
    result = register_manager(_FakeManager)
    assert result is _FakeManager


def test_platforms_gate_filters_by_current_os():
    class MacOnly(_FakeManager):
        key = "macos_only"
        platforms = frozenset({"macos"})

    register_manager(MacOnly)
    with patch("pkg_upgrade.registry.current_os", return_value="linux"):
        managers = discover_managers(load_entry_points=False, load_declarative=False)
    assert managers == []


def test_entry_point_registration(monkeypatch):
    class EPManager(_FakeManager):
        key = "entrypoint_mgr"

    class _FakeEP:
        name = "entrypoint_mgr"
        value = "x:y"

        def load(self) -> type[EPManager]:
            return EPManager

    def fake_entry_points(*, group: str) -> list[_FakeEP]:
        assert group == "pkg_upgrade.managers"
        return [_FakeEP()]

    monkeypatch.setattr("pkg_upgrade.registry.entry_points", fake_entry_points)
    managers = discover_managers(load_declarative=False)
    assert "entrypoint_mgr" in {m.key for m in managers}


def test_duplicate_key_raises():
    register_manager(_FakeManager)

    class Dup(_FakeManager):
        pass

    with pytest.raises(ValueError, match="already registered"):
        register_manager(Dup)
