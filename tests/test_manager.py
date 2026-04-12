import pytest

from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.registry import discover_managers, select_managers
from tests.conftest import FakeManager


@pytest.mark.asyncio
async def test_fake_manager_is_available():
    mgr = FakeManager(available=True)
    assert await mgr.is_available() is True


@pytest.mark.asyncio
async def test_fake_manager_not_available():
    mgr = FakeManager(available=False)
    assert await mgr.is_available() is False


@pytest.mark.asyncio
async def test_check_outdated_empty():
    mgr = FakeManager()
    assert await mgr.check_outdated() == []


@pytest.mark.asyncio
async def test_check_outdated_returns_packages():
    pkgs = [Package("node", "22.15", "22.16")]
    mgr = FakeManager(outdated=pkgs)
    result = await mgr.check_outdated()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_upgrade_all():
    pkgs = [Package("node", "22.15", "22.16"), Package("git", "2.44", "2.45")]
    mgr = FakeManager(outdated=pkgs)
    results = await mgr.upgrade_all()
    assert len(results) == 2
    assert all(r.success for r in results)


def test_all_managers_contains_six():
    assert len(discover_managers(load_entry_points=False, load_declarative=False)) == 6


def test_all_managers_keys_unique():
    keys = [m.key for m in discover_managers(load_entry_points=False, load_declarative=False)]
    assert len(keys) == len(set(keys))


def test_get_managers_skip():
    managers = select_managers(
        discover_managers(load_entry_points=False, load_declarative=False),
        skip={"brew", "pip"},
    )
    keys = {m.key for m in managers}
    assert "brew" not in keys and "pip" not in keys
    assert "npm" in keys


def test_get_managers_only():
    managers = select_managers(
        discover_managers(load_entry_points=False, load_declarative=False),
        only={"npm", "gem"},
    )
    keys = {m.key for m in managers}
    assert keys == {"npm", "gem"}


def test_package_manager_has_required_class_vars():
    assert hasattr(PackageManager, "platforms")
    assert hasattr(PackageManager, "depends_on")
    assert hasattr(PackageManager, "install_hint")


def test_concrete_manager_declares_platforms():
    class Fake(PackageManager):
        name = "Fake"
        key = "fake"
        icon = "x"
        platforms = frozenset({"macos"})

        async def is_available(self) -> bool:
            return True

        async def check_outdated(self) -> list[Package]:
            return []

        async def upgrade(self, package: Package) -> Result:
            raise NotImplementedError

    assert Fake.platforms == frozenset({"macos"})
    assert Fake.depends_on == ()
    assert Fake.install_hint == ""
