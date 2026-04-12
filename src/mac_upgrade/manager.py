from abc import ABC, abstractmethod

from mac_upgrade.models import Package, Result


class PackageManager(ABC):
    name: str
    key: str
    icon: str

    @abstractmethod
    async def is_available(self) -> bool: ...

    @abstractmethod
    async def check_outdated(self) -> list[Package]: ...

    @abstractmethod
    async def upgrade(self, package: Package) -> Result: ...

    @abstractmethod
    async def upgrade_all(self) -> list[Result]: ...
