from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def snap_refresh_list(stdout: str, **_: Any) -> list[Package]:
    lines = stdout.splitlines()
    if lines and lines[0].lower().startswith("name"):
        lines = lines[1:]
    pkgs: list[Package] = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        pkgs.append(Package(name=parts[0], current_version="", latest_version=parts[1]))
    return pkgs


register_parser("snap_refresh_list", snap_refresh_list)
