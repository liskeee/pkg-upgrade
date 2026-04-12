import shutil

from pkg_upgrade._brew_cache import get_brew_outdated
from pkg_upgrade._subprocess import run_command
from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.registry import register_manager


@register_manager
class BrewManager(PackageManager):
    name = "Homebrew Formulas"
    key = "brew"
    icon = "🍺"
    platforms = frozenset({"macos", "linux"})

    async def is_available(self) -> bool:
        return shutil.which("brew") is not None

    async def check_outdated(self) -> list[Package]:
        data = await get_brew_outdated()
        packages = []
        for f in data.get("formulae", []):
            installed = f.get("installed_versions") or []
            current = installed[0] if installed else "unknown"
            packages.append(
                Package(
                    name=f["name"],
                    current_version=current,
                    latest_version=f["current_version"],
                )
            )
        return packages

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(["brew", "upgrade", package.name])
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)
