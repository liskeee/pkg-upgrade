from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

OS = Literal["macos", "linux", "windows"]

_DEFAULT_OS_RELEASE = Path("/etc/os-release")


def current_os() -> OS:
    platform: str = sys.platform
    if platform == "darwin":
        return "macos"
    if platform.startswith("linux"):
        return "linux"
    if platform == "win32":
        return "windows"
    raise RuntimeError(f"Unsupported platform: {platform}")


def linux_distro(os_release: Path = _DEFAULT_OS_RELEASE) -> str | None:
    if not os_release.exists():
        return None
    values: dict[str, str] = {}
    for raw in os_release.read_text().splitlines():
        if "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        values[key.strip()] = value.strip().strip('"')
    return values.get("ID_LIKE") or values.get("ID")


def is_windows_admin() -> bool:
    if current_os() != "windows":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
