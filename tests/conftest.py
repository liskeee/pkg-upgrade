from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result


class FakeManager(PackageManager):
    name = "Fake"
    key = "fake"
    icon = "🧪"

    def __init__(self, available: bool = True, outdated: list[Package] | None = None):
        self._available = available
        self._outdated = outdated or []

    async def is_available(self) -> bool:
        return self._available

    async def check_outdated(self) -> list[Package]:
        return self._outdated

    async def upgrade(self, package: Package) -> Result:
        return Result(success=True, message="ok", package=package)

    async def upgrade_all(self) -> list[Result]:
        return [await self.upgrade(p) for p in self._outdated]
