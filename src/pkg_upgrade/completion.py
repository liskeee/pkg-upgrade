from __future__ import annotations

import os
import sys
from pathlib import Path


def cache_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "pkg-upgrade" / "managers.list"


def plain_list_managers(*, write_cache: bool = False) -> list[str]:
    from pkg_upgrade.registry import all_registered, discover_managers  # noqa: PLC0415

    # Ensure registry is populated (rebuilds built-ins if previously cleared).
    discover_managers(load_entry_points=False, load_declarative=True)
    keys = sorted({cls.key for cls in all_registered()})
    if write_cache:
        path = cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(keys) + "\n", encoding="utf-8")
    return keys
