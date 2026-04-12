import pytest
from tests.conftest import FakeManager
from mac_upgrade.models import Package


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
