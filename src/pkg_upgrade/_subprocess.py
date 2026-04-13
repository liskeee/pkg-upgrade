from __future__ import annotations

import asyncio
import os


async def run_command(
    argv: list[str],
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a command safely (no shell). Returns (returncode, stdout, stderr)."""
    merged_env: dict[str, str] | None = None
    if env is not None:
        merged_env = {**os.environ, **env}
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=merged_env,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
