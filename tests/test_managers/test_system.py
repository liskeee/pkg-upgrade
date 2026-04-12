from unittest.mock import AsyncMock, patch

import pytest

from mac_upgrade.managers.system import SystemManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/usr/sbin/softwareupdate"):
        assert await SystemManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_output():
    output = (
        "Software Update found the following new or updated software:\n"
        "* Label: Safari18.5-18.5\n"
        "\tTitle: Safari 18.5, Version: 18.5, Size: 200000KiB, Recommended: YES,\n"
    )
    with patch(
        "mac_upgrade.managers.system.run_command", new=AsyncMock(return_value=(0, output, ""))
    ):
        packages = await SystemManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "Safari18.5-18.5"
    assert packages[0].latest_version == "18.5"


@pytest.mark.asyncio
async def test_check_outdated_no_updates():
    with patch(
        "mac_upgrade.managers.system.run_command",
        new=AsyncMock(return_value=(0, "No new software available.\n", "")),
    ):
        assert await SystemManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("Safari18.5-18.5", "installed", "18.5")
    with patch(
        "mac_upgrade.managers.system.run_command", new=AsyncMock(return_value=(0, "Done", ""))
    ):
        result = await SystemManager().upgrade(pkg)
    assert result.success is True
