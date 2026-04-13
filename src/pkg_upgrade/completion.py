from __future__ import annotations

import os
import sys
from importlib import resources
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


_SHELL_FILES: dict[str, str] = {
    "bash": "pkg-upgrade.bash",
    "zsh": "_pkg-upgrade",
    "fish": "pkg-upgrade.fish",
    "powershell": "pkg-upgrade.ps1",
}


def completion_subcommand(shell: str) -> int:
    filename = _SHELL_FILES.get(shell)
    if filename is None:
        valid = ", ".join(sorted(_SHELL_FILES))
        print(f"error: unknown shell '{shell}'. Valid: {valid}", file=sys.stderr)
        return 2
    text = resources.files("pkg_upgrade.completions").joinpath(filename).read_text(encoding="utf-8")
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0
