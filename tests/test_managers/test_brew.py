import json
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.brew import BrewManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available_when_brew_exists():
    with patch("shutil.which", return_value="/opt/homebrew/bin/brew"):
        assert await BrewManager().is_available() is True


@pytest.mark.asyncio
async def test_is_available_when_brew_missing():
    with patch("shutil.which", return_value=None):
        assert await BrewManager().is_available() is False


@pytest.mark.asyncio
async def test_check_outdated_parses_json():
    brew_output = json.dumps({
        "formulae": [
            {"name": "node", "installed_versions": ["22.15"], "current_version": "22.16"},
            {"name": "git", "installed_versions": ["2.44"], "current_version": "2.45"},
        ]
    })
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(0, brew_output, ""))):
        packages = await BrewManager().check_outdated()
    assert len(packages) == 2
    assert packages[0].name == "node"


@pytest.mark.asyncio
async def test_check_outdated_empty():
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(0, '{"formulae": []}', ""))):
        assert await BrewManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("node", "22.15", "22.16")
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(0, "Upgraded", ""))):
        result = await BrewManager().upgrade(pkg)
    assert result.success is True


@pytest.mark.asyncio
async def test_upgrade_failure():
    pkg = Package("git", "2.44", "2.45")
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(1, "", "permission denied"))):
        result = await BrewManager().upgrade(pkg)
    assert result.success is False
    assert "permission denied" in result.message
