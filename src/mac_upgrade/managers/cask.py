import shutil

from mac_upgrade._brew_cache import get_brew_outdated
from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class CaskManager(PackageManager):
    name = "Homebrew Casks"
    key = "cask"
    icon = "🍻"

    async def is_available(self) -> bool:
        return shutil.which("brew") is not None

    async def check_outdated(self) -> list[Package]:
        data = await get_brew_outdated()
        packages = []
        for c in data.get("casks", []):
            installed = c.get("installed_versions") or []
            current = installed[0] if isinstance(installed, list) and installed else "unknown"
            packages.append(Package(
                name=c["name"],
                current_version=current,
                latest_version=c["current_version"],
            ))
        return packages

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(
            ["brew", "upgrade", "--cask", package.name]
        )
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
