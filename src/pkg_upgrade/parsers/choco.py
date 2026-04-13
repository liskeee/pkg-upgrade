from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def choco_outdated(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        name, current, latest = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not name:
            continue
        pkgs.append(Package(name=name, current_version=current, latest_version=latest))
    return pkgs


register_parser("choco_outdated", choco_outdated)
