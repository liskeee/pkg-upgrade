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


def test_pacman_qu_parses_arrows() -> None:
    parser = get_parser("pacman_qu")
    pkgs = parser(_load("pacman"))
    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [
        ("linux", "6.6.10.arch1-1", "6.7.2.arch1-1"),
        ("firefox", "122.0-1", "123.0.1-1"),
        ("python", "3.11.7-1", "3.12.2-1"),
    ]


def test_flatpak_parses_tab_columns() -> None:
    parser = get_parser("flatpak_remote_ls_updates")
    pkgs = parser(_load("flatpak"))
    assert [(p.name, p.latest_version) for p in pkgs] == [
        ("org.mozilla.firefox", "123.0.1"),
        ("org.gimp.GIMP", "2.10.36"),
        ("com.github.tchx84.Flatseal", "2.2.0"),
    ]


def test_snap_refresh_list_skips_header() -> None:
    parser = get_parser("snap_refresh_list")
    pkgs = parser(_load("snap"))
    assert [(p.name, p.latest_version) for p in pkgs] == [
        ("core22", "20240111"),
        ("firefox", "123.0.1-1"),
        ("snapd", "2.61.2"),
    ]


def test_winget_upgrade_parses_fixed_width_table() -> None:
    parser = get_parser("winget_upgrade")
    pkgs = parser(_load("winget"))
    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [
        ("Git.Git", "2.43.0", "2.44.0"),
        ("Microsoft.PowerShell", "7.4.0.0", "7.4.1.0"),
        ("Python.Python.3.12", "3.12.1150.0", "3.12.2150.0"),
    ]
