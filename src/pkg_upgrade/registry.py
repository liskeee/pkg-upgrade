from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from typing import TypeVar

from pkg_upgrade.manager import PackageManager
from pkg_upgrade.platform import current_os

T = TypeVar("T", bound=type[PackageManager])

_REGISTRY: dict[str, type[PackageManager]] = {}

ENTRY_POINT_GROUP = "pkg_upgrade.managers"


def register_manager(cls: T) -> T:  # noqa: UP047
    key = cls.key
    if key in _REGISTRY:
        raise ValueError(f"Manager key {key!r} already registered")
    _REGISTRY[key] = cls
    return cls


def clear_registry() -> None:
    _REGISTRY.clear()


def _rebuild_built_in_managers() -> None:
    """Re-register built-in managers. Used after clear_registry() in tests."""
    from pkg_upgrade.managers.brew import BrewManager  # noqa: PLC0415
    from pkg_upgrade.managers.cask import CaskManager  # noqa: PLC0415
    from pkg_upgrade.managers.gem import GemManager  # noqa: PLC0415
    from pkg_upgrade.managers.npm import NpmManager  # noqa: PLC0415
    from pkg_upgrade.managers.pip import PipManager  # noqa: PLC0415
    from pkg_upgrade.managers.system import SystemManager  # noqa: PLC0415

    managers: list[type[PackageManager]] = [
        BrewManager,
        CaskManager,
        GemManager,
        NpmManager,
        PipManager,
        SystemManager,
    ]
    for cls in managers:
        if cls.key not in _REGISTRY:
            _REGISTRY[cls.key] = cls


def all_registered() -> list[type[PackageManager]]:
    import pkg_upgrade.managers  # noqa: F401, PLC0415

    return list(_REGISTRY.values())


def _instances_for_os(os_name: str) -> list[PackageManager]:
    return [cls() for cls in _REGISTRY.values() if os_name in cls.platforms]


def _load_entry_points() -> None:
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        cls = ep.load()
        if not isinstance(cls, type) or not issubclass(cls, PackageManager):
            raise TypeError(f"Entry point {ep.name} did not load a PackageManager subclass")
        if cls.key not in _REGISTRY:
            register_manager(cls)


def _load_declarative(directory: Path | None) -> None:
    from pkg_upgrade.declarative import load_declarative_dir  # noqa: PLC0415

    load_declarative_dir(directory)


def discover_managers(
    *,
    load_entry_points: bool = True,
    load_declarative: bool = True,
    declarative_dir: Path | None = None,
) -> list[PackageManager]:
    import pkg_upgrade.managers  # noqa: F401, PLC0415

    # Rebuild built-in managers if registry is empty (happens after clear_registry() in tests)
    if not _REGISTRY:
        _rebuild_built_in_managers()

    if load_entry_points:
        _load_entry_points()
    if load_declarative:
        _load_declarative(declarative_dir)
    return _instances_for_os(current_os())


def select_managers(
    managers: list[PackageManager],
    *,
    skip: set[str] | None = None,
    only: set[str] | None = None,
) -> list[PackageManager]:
    result = list(managers)
    if only:
        result = [m for m in result if m.key in only]
    if skip:
        result = [m for m in result if m.key not in skip]
    return result
