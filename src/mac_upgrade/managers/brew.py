import json
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class BrewManager(PackageManager):
    name = "Homebrew Formulas"
    key = "brew"
    icon = "🍺"

    async def is_available(self) -> bool:
        return shutil.which("brew") is not None

    async def check_outdated(self) -> list[Package]:
        code, stdout, _ = await run_command(["brew", "outdated", "--json=v2"])
        if code != 0 or not stdout.strip():
            return []
        data = json.loads(stdout)
        return [
            Package(
                name=f["name"],
                current_version=f["installed_versions"][0],
                latest_version=f["current_version"],
            )
            for f in data.get("formulae", [])
        ]

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(["brew", "upgrade", package.name])
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
