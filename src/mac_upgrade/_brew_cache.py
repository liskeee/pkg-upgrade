"""Shared cache for `brew outdated --json=v2` so brew and cask managers don't double-invoke it."""
from __future__ import annotations

import asyncio
import json

from mac_upgrade._subprocess import run_command

_lock = asyncio.Lock()
_cache: dict | None = None


async def get_brew_outdated() -> dict:
    global _cache
    async with _lock:
        if _cache is not None:
            return _cache
        code, stdout, stderr = await run_command(["brew", "outdated", "--json=v2"])
        if code != 0:
            raise RuntimeError(f"brew outdated failed: {stderr.strip()}")
        _cache = json.loads(stdout) if stdout.strip() else {}
        return _cache


def reset_cache() -> None:
    """Test helper — clear the cached brew output."""
    global _cache
    _cache = None
