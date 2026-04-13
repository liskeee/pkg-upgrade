from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser

_LINE = re.compile(r"^(?P<name>[^\s.]+)\.\S+\s+(?P<latest>\S+)\s+\S+\s*$")


def dnf_check_update(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for raw in stdout.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("Obsoleting Packages"):
            break
        if line.startswith("Last metadata"):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        pkgs.append(Package(name=gd["name"], current_version="", latest_version=gd["latest"]))
    return pkgs


register_parser("dnf_check_update", dnf_check_update)
