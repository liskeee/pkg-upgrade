import re
import shutil

from pkg_upgrade._subprocess import run_command
from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.registry import register_manager

GEM_LINE_RE = re.compile(r"^(\S+)\s+\((\S+)\s+<\s+(\S+)\)$")


@register_manager
class GemManager(PackageManager):
    name = "gem"
    key = "gem"
    icon = "💎"
    platforms = frozenset({"macos", "linux", "windows"})

    async def is_available(self) -> bool:
        return shutil.which("gem") is not None

    async def check_outdated(self) -> list[Package]:
        code, stdout, _ = await run_command(["gem", "outdated"])
        if code != 0 or not stdout.strip():
            return []
        packages = []
        for line in stdout.splitlines():
            m = GEM_LINE_RE.match(line.strip())
            if m:
                packages.append(
                    Package(
                        name=m.group(1),
                        current_version=m.group(2),
                        latest_version=m.group(3),
                    )
                )
        return packages

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(["gem", "update", package.name])
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)
