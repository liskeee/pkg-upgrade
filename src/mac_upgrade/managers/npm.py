import json
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class NpmManager(PackageManager):
    name = "npm"
    key = "npm"
    icon = "📦"

    async def is_available(self) -> bool:
        return shutil.which("npm") is not None

    async def check_outdated(self) -> list[Package]:
        # npm outdated exits 1 when there are outdated packages — ignore exit code
        _, stdout, _ = await run_command(
            ["npm", "outdated", "--global", "--json"]
        )
        if not stdout.strip():
            return []
        data = json.loads(stdout)
        return [
            Package(
                name=name,
                current_version=info.get("current", "unknown"),
                latest_version=info["latest"],
            )
            for name, info in data.items()
        ]

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(
            ["npm", "install", "-g", f"{package.name}@latest"]
        )
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)
