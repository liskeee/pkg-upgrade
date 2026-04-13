from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def generic_regex(
    stdout: str,
    *,
    regex: str,
    skip_first_line: bool = False,
    **_: Any,
) -> list[Package]:
    pattern = re.compile(regex)
    lines = stdout.splitlines()
    if skip_first_line and lines:
        lines = lines[1:]
    packages: list[Package] = []
    for line in lines:
        m = pattern.match(line)
        if not m:
            continue
        gd = m.groupdict()
        packages.append(
            Package(
                name=gd["name"],
                current_version=gd.get("current", ""),
                latest_version=gd.get("latest", ""),
            )
        )
    return packages


register_parser("generic_regex", generic_regex)
