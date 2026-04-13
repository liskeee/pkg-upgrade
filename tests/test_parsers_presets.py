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


def test_dnf_check_update_parses_packages_and_stops_at_obsoletes() -> None:
    parser = get_parser("dnf_check_update")
    pkgs = parser(_load("dnf"))
    names = [(p.name, p.latest_version) for p in pkgs]
    assert names == [
        ("bash", "5.2.15-1.fc39"),
        ("kernel", "6.6.13-200.fc39"),
        ("vim-enhanced", "2:9.1.0-1.fc39"),
    ]
