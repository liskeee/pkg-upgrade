from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_scoop_manifest_has_post_install_hook():
    data = json.loads((ROOT / "scoop" / "pkg-upgrade.json").read_text(encoding="utf-8"))
    post = data.get("post_install", [])
    joined = "\n".join(post) if isinstance(post, list) else str(post)
    assert "pkg-upgrade.ps1" in joined
    assert "$PROFILE" in joined
    assert "Select-String" in joined or "-notmatch" in joined


def test_scoop_manifest_has_uninstaller():
    data = json.loads((ROOT / "scoop" / "pkg-upgrade.json").read_text(encoding="utf-8"))
    uninst = data.get("uninstaller", {}).get("script", [])
    joined = "\n".join(uninst) if isinstance(uninst, list) else str(uninst)
    assert "pkg-upgrade.ps1" in joined


def test_install_ps1_appends_to_profile_idempotently():
    text = (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert "pkg-upgrade.ps1" in text
    assert "$PROFILE" in text
    assert "Select-String" in text or "-notmatch" in text


def test_install_sh_handles_bash_zsh_fish():
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "bash-completion/completions/pkg-upgrade" in text
    assert ".zsh/completions/_pkg-upgrade" in text
    assert "fish/completions/pkg-upgrade.fish" in text
    assert "fpath+=" in text or "fpath=(" in text
