from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pkg_upgrade.models import Package, Result


class PackageManager(ABC):
    """Abstract strategy for a single package-manager backend."""

    name: ClassVar[str]
    key: ClassVar[str]
    icon: ClassVar[str]
    platforms: ClassVar[frozenset[str]] = frozenset()
    depends_on: ClassVar[tuple[str, ...]] = ()
    install_hint: ClassVar[str] = ""

    @abstractmethod
    async def is_available(self) -> bool: ...

    @abstractmethod
    async def check_outdated(self) -> list[Package]: ...

    @abstractmethod
    async def upgrade(self, package: Package) -> Result: ...

    async def upgrade_all(self) -> list[Result]:
        """Default: check then upgrade each package sequentially."""
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
