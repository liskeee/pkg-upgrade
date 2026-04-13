from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def flatpak_remote_ls_updates(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        pkgs.append(Package(name=cols[0], current_version="", latest_version=cols[1]))
    return pkgs


register_parser("flatpak_remote_ls_updates", flatpak_remote_ls_updates)
