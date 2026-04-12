import re
import shutil

from pkg_upgrade._subprocess import run_command
from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result

LABEL_RE = re.compile(r"^\* Label:\s+(.+)$")
VERSION_RE = re.compile(r"^\s+Title:\s+.+,\s+Version:\s+([^,]+),")


class SystemManager(PackageManager):
    name = "System Updates"
    key = "system"
    icon = "🍎"
    platforms = frozenset({"macos"})

    async def is_available(self) -> bool:
        return shutil.which("softwareupdate") is not None

    async def check_outdated(self) -> list[Package]:
        _code, stdout, stderr = await run_command(["softwareupdate", "--list"])
        output = stdout + stderr
        if "No new software available" in output:
            return []
        packages: list[Package] = []
        current_label: str | None = None
        for line in output.splitlines():
            lm = LABEL_RE.match(line)
            if lm:
                current_label = lm.group(1).strip()
                continue
            vm = VERSION_RE.match(line)
            if vm and current_label:
                packages.append(
                    Package(
                        name=current_label,
                        current_version="installed",
                        latest_version=vm.group(1).strip(),
                    )
                )
                current_label = None
        return packages

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(["softwareupdate", "--install", package.name])
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)
