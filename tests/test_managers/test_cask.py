import json
from unittest.mock import AsyncMock, patch

import pytest

from pkg_upgrade import _brew_cache
from pkg_upgrade.managers.cask import CaskManager
from pkg_upgrade.models import Package


@pytest.fixture(autouse=True)
def _reset_brew_cache():
    _brew_cache.reset_cache()
    yield
    _brew_cache.reset_cache()


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/opt/homebrew/bin/brew"):
        assert await CaskManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_casks():
    brew_output = json.dumps(
        {
            "casks": [
                {"name": "firefox", "installed_versions": ["130.0"], "current_version": "131.0"},
            ]
        }
    )
    with patch(
        "pkg_upgrade._brew_cache.run_command", new=AsyncMock(return_value=(0, brew_output, ""))
    ):
        packages = await CaskManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "firefox"
    assert packages[0].current_version == "130.0"


@pytest.mark.asyncio
async def test_upgrade_cask_success():
    pkg = Package("firefox", "130.0", "131.0")
    with patch(
        "pkg_upgrade.managers.cask.run_command", new=AsyncMock(return_value=(0, "Upgraded", ""))
    ):
        result = await CaskManager().upgrade(pkg)
    assert result.success is True
