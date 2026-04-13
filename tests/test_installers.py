from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scoop_manifest_has_required_keys() -> None:
    manifest = json.loads((ROOT / "scoop" / "pkg-upgrade.json").read_text(encoding="utf-8"))
    for key in ("version", "description", "homepage", "license", "url", "hash", "bin"):
        assert key in manifest, f"scoop manifest missing key: {key}"


def test_install_sh_uses_pkg_upgrade_env_vars() -> None:
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "PKG_UPGRADE_REF" in text
    assert "PKG_UPGRADE_SOURCE" in text
    assert "MAC_UPGRADE_" not in text


def test_install_ps1_uses_pkg_upgrade_env_vars() -> None:
    text = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "PKG_UPGRADE_REF" in text
    assert "PKG_UPGRADE_SOURCE" in text
    assert "MAC_UPGRADE_" not in text


def test_formula_installs_completions():
    formula = Path(__file__).resolve().parent.parent / "Formula" / "pkg-upgrade.rb"
    text = formula.read_text(encoding="utf-8")
    assert "bash_completion.install" in text
    assert "zsh_completion.install" in text
    assert "fish_completion.install" in text
    assert "pkg-upgrade.bash" in text
    assert "_pkg-upgrade" in text
    assert "pkg-upgrade.fish" in text
