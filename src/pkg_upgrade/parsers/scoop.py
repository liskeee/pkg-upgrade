from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def scoop_status(stdout: str, **_: Any) -> list[Package]:
    lines = [line.rstrip() for line in stdout.splitlines()]
    header_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("Name") and "Installed Version" in line and "Latest Version" in line:
            header_idx = i
            break
    if header_idx is None:
        return []
    header = lines[header_idx]
    installed_start = header.index("Installed Version")
    latest_start = header.index("Latest Version")
    missing_start = (
        header.index("Missing Dependencies") if "Missing Dependencies" in header else len(header)
    )
    pkgs: list[Package] = []
    for line in lines[header_idx + 2 :]:
        if not line.strip():
            continue
        name = line[:installed_start].strip()
        current = line[installed_start:latest_start].strip()
        latest = line[latest_start:missing_start].strip()
        if not name or not current or not latest:
            continue
        pkgs.append(Package(name=name, current_version=current, latest_version=latest))
    return pkgs


register_parser("scoop_status", scoop_status)
