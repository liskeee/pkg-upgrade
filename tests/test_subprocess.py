import pytest
from unittest.mock import AsyncMock, patch
from mac_upgrade._subprocess import run_command


@pytest.mark.asyncio
async def test_run_command_success():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"hello", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        code, stdout, stderr = await run_command(["echo", "hello"])

    assert code == 0
    assert stdout == "hello"
    assert stderr == ""


@pytest.mark.asyncio
async def test_run_command_failure():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"error")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        code, stdout, stderr = await run_command(["false"])

    assert code == 1
    assert stderr == "error"
