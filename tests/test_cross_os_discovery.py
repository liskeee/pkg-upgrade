from __future__ import annotations

from unittest.mock import patch

import pytest

from pkg_upgrade.registry import clear_registry, discover_managers

MACOS_DECL = {"mas"}
LINUX_DECL = {"apt", "dnf", "pacman", "flatpak", "snap"}
WINDOWS_DECL = {"winget", "scoop", "choco"}


@pytest.fixture(autouse=True)
def _fresh_registry():
    clear_registry()
    yield
    clear_registry()


@pytest.mark.parametrize(
    ("os_name", "expected_decl"),
    [("macos", MACOS_DECL), ("linux", LINUX_DECL), ("windows", WINDOWS_DECL)],
)
def test_discover_includes_declared_managers_for_os(os_name: str, expected_decl: set[str]) -> None:
    with patch("pkg_upgrade.registry.current_os", return_value=os_name):
        managers = discover_managers(load_entry_points=False)
    keys = {m.key for m in managers}
    assert expected_decl <= keys, f"OS {os_name} missing: {expected_decl - keys}"
