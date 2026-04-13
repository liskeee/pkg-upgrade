from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser

_LINE = re.compile(r"^(?P<name>\S+)\s+(?P<current>\S+)\s+->\s+(?P<latest>\S+)\s*$")


def pacman_qu(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        pkgs.append(
            Package(
                name=gd["name"],
                current_version=gd["current"],
                latest_version=gd["latest"],
            )
        )
    return pkgs


register_parser("pacman_qu", pacman_qu)
