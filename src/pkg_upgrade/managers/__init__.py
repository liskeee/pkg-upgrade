from pkg_upgrade.manager import PackageManager
from pkg_upgrade.managers.brew import BrewManager
from pkg_upgrade.managers.cask import CaskManager
from pkg_upgrade.managers.gem import GemManager
from pkg_upgrade.managers.npm import NpmManager
from pkg_upgrade.managers.pip import PipManager
from pkg_upgrade.managers.system import SystemManager

ALL_MANAGERS: list[PackageManager] = [
    BrewManager(),
    CaskManager(),
    PipManager(),
    NpmManager(),
    GemManager(),
    SystemManager(),
]


def get_managers(
    skip: set[str] | None = None,
    only: set[str] | None = None,
) -> list[PackageManager]:
    managers = list(ALL_MANAGERS)
    if only:
        managers = [m for m in managers if m.key in only]
    if skip:
        managers = [m for m in managers if m.key not in skip]
    return managers
