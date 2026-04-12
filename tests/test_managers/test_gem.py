from unittest.mock import AsyncMock, patch

import pytest

from mac_upgrade.managers.gem import GemManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/usr/bin/gem"):
        assert await GemManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_output():
    gem_output = "nokogiri (1.16.0 < 1.16.5)\nrake (13.1.0 < 13.2.0)\n"
    with patch(
        "mac_upgrade.managers.gem.run_command", new=AsyncMock(return_value=(0, gem_output, ""))
    ):
        packages = await GemManager().check_outdated()
    assert len(packages) == 2
    assert packages[0].name == "nokogiri"
    assert packages[0].current_version == "1.16.0"
    assert packages[0].latest_version == "1.16.5"


@pytest.mark.asyncio
async def test_check_outdated_empty():
    with patch("mac_upgrade.managers.gem.run_command", new=AsyncMock(return_value=(0, "", ""))):
        assert await GemManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("nokogiri", "1.16.0", "1.16.5")
    with patch(
        "mac_upgrade.managers.gem.run_command", new=AsyncMock(return_value=(0, "Installed", ""))
    ):
        result = await GemManager().upgrade(pkg)
    assert result.success is True
