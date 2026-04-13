import re
from unittest.mock import AsyncMock, patch

import pytest

from pkg_upgrade.notifier import Notifier


def test_log_writes_to_file(tmp_path):
    log = tmp_path / "test.log"
    n = Notifier(log_path=str(log))
    n.log("brew", "Upgrading node")
    content = log.read_text()
    assert "brew" in content
    assert "Upgrading node" in content


def test_log_has_timestamp(tmp_path):
    log = tmp_path / "test.log"
    n = Notifier(log_path=str(log))
    n.log("npm", "message")
    assert re.search(r"\d{2}:\d{2}:\d{2}", log.read_text())


def test_log_disabled_when_none():
    n = Notifier(log_path=None)
    n.log("brew", "test")


def test_log_appends(tmp_path):
    log = tmp_path / "test.log"
    n = Notifier(log_path=str(log))
    n.log("brew", "first")
    n.log("npm", "second")
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_notification_sends():
    n = Notifier(log_path=None, notify=True)
    with patch(
        "pkg_upgrade.notifier.run_command", new=AsyncMock(return_value=(0, "", ""))
    ) as mock_run:
        await n.send_notification("title", "body")
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_notification_suppressed():
    n = Notifier(log_path=None, notify=False)
    with patch(
        "pkg_upgrade.notifier.run_command", new=AsyncMock(return_value=(0, "", ""))
    ) as mock_run:
        await n.send_notification("title", "body")
        mock_run.assert_not_called()
