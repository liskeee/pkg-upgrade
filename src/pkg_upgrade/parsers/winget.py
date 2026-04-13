from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def winget_upgrade(stdout: str, **_: Any) -> list[Package]:
    lines = [line.rstrip() for line in stdout.splitlines()]
    header_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("Name ") and "Id" in line and "Version" in line and "Available" in line:
            header_idx = i
            break
    if header_idx is None:
        return []
    header = lines[header_idx]
    id_start = header.index("Id")
    ver_start = header.index("Version")
    avail_start = header.index("Available")
    src_start = header.index("Source")
    pkgs: list[Package] = []
    for line in lines[header_idx + 1 :]:
        if not line or set(line) <= {"-"}:
            continue
        if "upgrades available." in line:
            break
        id_ = line[id_start:ver_start].strip()
        current = line[ver_start:avail_start].strip()
        latest = line[avail_start:src_start].strip()
        if not id_ or not current or not latest:
            continue
        pkgs.append(Package(name=id_, current_version=current, latest_version=latest))
    return pkgs


register_parser("winget_upgrade", winget_upgrade)
