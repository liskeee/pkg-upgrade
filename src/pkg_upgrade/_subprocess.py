import asyncio


async def run_command(argv: list[str]) -> tuple[int, str, str]:
    """Run a command safely (no shell). Returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
