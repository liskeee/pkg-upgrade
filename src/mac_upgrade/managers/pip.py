import json
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class PipManager(PackageManager):
    name = "pip"
    key = "pip"
    icon = "🐍"

    async def is_available(self) -> bool:
        return shutil.which("pip3") is not None

    async def check_outdated(self) -> list[Package]:
        code, stdout, _ = await run_command(["pip3", "list", "--outdated", "--format=json"])
        if code != 0 or not stdout.strip():
            return []
        data = json.loads(stdout)
        return [
            Package(
                name=item["name"],
                current_version=item["version"],
                latest_version=item["latest_version"],
            )
            for item in data
        ]

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(["pip3", "install", "--upgrade", package.name])
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)
