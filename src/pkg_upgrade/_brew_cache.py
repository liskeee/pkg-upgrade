"""Shared cache for `brew outdated --json=v2` so brew and cask managers don't double-invoke it."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from pkg_upgrade._subprocess import run_command


class _BrewCache:
    lock = asyncio.Lock()
    data: dict[str, Any] | None = None


async def get_brew_outdated() -> dict[str, Any]:
    async with _BrewCache.lock:
        if _BrewCache.data is not None:
            return _BrewCache.data
        code, stdout, stderr = await run_command(["brew", "outdated", "--json=v2"])
        if code != 0:
            raise RuntimeError(f"brew outdated failed: {stderr.strip()}")
        _BrewCache.data = json.loads(stdout) if stdout.strip() else {}
        return _BrewCache.data


def reset_cache() -> None:
    """Test helper — clear the cached brew output."""
    _BrewCache.data = None
