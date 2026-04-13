from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Literal

InstallMethod = Literal["pipx", "brew", "scoop", "install_sh", "install_ps1", "editable", "pip"]

_INSTALL_SH_PIPE = (
    "curl -fsSL https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.sh | bash"
)
_INSTALL_PS1_PIPE = (
    "iwr -useb https://raw.githubusercontent.com/liskeee/pkg-upgrade/main/install.ps1 | iex"
)

# Ordered list of (substring, method) — first match wins.
_PATH_SIGNATURES: list[tuple[str, InstallMethod]] = [
    ("pipx/venvs/pkg-upgrade", "pipx"),
    ("/Cellar/pkg-upgrade/", "brew"),
    ("/opt/pkg-upgrade/", "brew"),
    ("scoop/apps/pkg-upgrade", "scoop"),
    ("AppData/Local/pkg-upgrade", "install_ps1"),
    (".local/share/pkg-upgrade", "install_sh"),
]


def _editable_pyproject() -> Path | None:
    """Return path to pyproject.toml if this is an editable install of pkg-upgrade, else None."""
    try:
        import pkg_upgrade  # noqa: PLC0415
    except ImportError:
        return None
    pkg_dir = Path(pkg_upgrade.__file__).resolve().parent
    # editable typically: <repo>/src/pkg_upgrade/__init__.py → repo at parents[1]
    candidate = pkg_dir.parent.parent / "pyproject.toml"
    if candidate.exists() and "pkg-upgrade" in candidate.read_text():
        return candidate
    return None


def _is_editable_install() -> bool:
    return _editable_pyproject() is not None


def detect_install_method() -> InstallMethod:
    if _is_editable_install():
        return "editable"
    exe = str(Path(sys.executable).resolve()).replace("\\", "/")
    for signature, method in _PATH_SIGNATURES:
        if signature in exe:
            return method
    return "pip"


def upgrade_command(method: InstallMethod) -> tuple[list[str] | None, bool]:
    """Return (argv, shell). argv=None means no command (e.g. editable)."""
    _commands: dict[str, tuple[list[str] | None, bool]] = {
        "pipx": (["pipx", "upgrade", "pkg-upgrade"], False),
        "brew": (["brew", "upgrade", "pkg-upgrade"], False),
        "scoop": (["scoop", "update", "pkg-upgrade"], False),
        "install_sh": ([_INSTALL_SH_PIPE], True),
        "install_ps1": ([_INSTALL_PS1_PIPE], True),
        "pip": ([sys.executable, "-m", "pip", "install", "--upgrade", "pkg-upgrade"], False),
        "editable": (None, False),
    }
    if method not in _commands:
        raise ValueError(f"Unknown install method: {method}")
    return _commands[method]


def run_self_update() -> int:
    method = detect_install_method()
    print(f"Detected install method: {method}")
    cmd, shell = upgrade_command(method)
    if cmd is None:
        print("Editable dev install — run `git pull` and re-install with `pip install -e .[dev]`.")
        return 0
    if shell:
        print(f"$ {cmd[0]}")
        return subprocess.run(cmd[0], shell=True, check=False).returncode
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=False).returncode
