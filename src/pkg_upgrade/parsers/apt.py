from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser

_LINE = re.compile(
    r"^(?P<name>[^/\s]+)/\S+\s+(?P<latest>\S+)\s+\S+\s+\[upgradable from: (?P<current>[^\]]+)\]"
)


def apt_upgradable(stdout: str, **_: Any) -> list[Package]:
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


register_parser("apt_upgradable", apt_upgradable)
