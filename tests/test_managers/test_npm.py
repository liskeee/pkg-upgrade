import json
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.npm import NpmManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/usr/local/bin/npm"):
        assert await NpmManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_json():
    npm_output = json.dumps({
        "eslint": {"current": "9.1.0", "wanted": "9.2.0", "latest": "9.2.0"},
    })
    with patch("mac_upgrade.managers.npm.run_command",
               new=AsyncMock(return_value=(1, npm_output, ""))):
        packages = await NpmManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "eslint"


@pytest.mark.asyncio
async def test_check_outdated_empty():
    with patch("mac_upgrade.managers.npm.run_command",
               new=AsyncMock(return_value=(0, "", ""))):
        assert await NpmManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("eslint", "9.1.0", "9.2.0")
    with patch("mac_upgrade.managers.npm.run_command",
               new=AsyncMock(return_value=(0, "updated", ""))):
        result = await NpmManager().upgrade(pkg)
    assert result.success is True
