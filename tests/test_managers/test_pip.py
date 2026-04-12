import json
from unittest.mock import AsyncMock, patch

import pytest

from mac_upgrade.managers.pip import PipManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/opt/homebrew/bin/pip3"):
        assert await PipManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_json():
    pip_output = json.dumps(
        [
            {"name": "requests", "version": "2.31.0", "latest_version": "2.32.0"},
        ]
    )
    with patch(
        "mac_upgrade.managers.pip.run_command", new=AsyncMock(return_value=(0, pip_output, ""))
    ):
        packages = await PipManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "requests"


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("requests", "2.31.0", "2.32.0")
    with patch(
        "mac_upgrade.managers.pip.run_command", new=AsyncMock(return_value=(0, "Installed", ""))
    ):
        result = await PipManager().upgrade(pkg)
    assert result.success is True
