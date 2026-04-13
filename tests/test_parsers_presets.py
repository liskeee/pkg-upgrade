from __future__ import annotations

from pathlib import Path

from pkg_upgrade.parsers import get_parser

FIXTURES = Path(__file__).parent / "fixtures" / "parsers"


def _load(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text()


def test_apt_upgradable_parses_three_packages() -> None:
    parser = get_parser("apt_upgradable")
    pkgs = parser(_load("apt"))
    names = [(p.name, p.current_version, p.latest_version) for p in pkgs]
    assert names == [
        ("curl", "7.81.0-1ubuntu1.14", "7.81.0-1ubuntu1.15"),
        ("git", "1:2.34.1-1ubuntu1.10", "1:2.34.1-1ubuntu1.11"),
        ("libc6", "2.35-0ubuntu3.6", "2.35-0ubuntu3.7"),
    ]
