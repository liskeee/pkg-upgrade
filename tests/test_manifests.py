from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pkg_upgrade.declarative import _Manifest
from pkg_upgrade.parsers import get_parser

DECL_DIR = Path(__file__).parent.parent / "src" / "pkg_upgrade" / "managers" / "declarative"

EXPECTED_KEYS = {
    "apt",
    "dnf",
    "pacman",
    "flatpak",
    "snap",
    "winget",
    "scoop",
    "choco",
    "mas",
}


def _all_yaml() -> list[Path]:
    return sorted(DECL_DIR.glob("*.yaml"))


def test_all_expected_manifests_shipped() -> None:
    keys = {p.stem for p in _all_yaml()}
    assert EXPECTED_KEYS <= keys, f"Missing: {EXPECTED_KEYS - keys}"


@pytest.mark.parametrize("path", _all_yaml(), ids=lambda p: p.stem)
def test_manifest_schema_valid(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest = _Manifest.from_dict(data)
    assert manifest.key == path.stem
    assert manifest.platforms
    get_parser(manifest.check_parser)
