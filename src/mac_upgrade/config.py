"""Persistent user configuration at ~/.mac-upgrade (JSON)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, TypedDict


CONFIG_VERSION = 1


class UserConfig(TypedDict, total=False):
    """Shape of the persisted ``~/.mac-upgrade`` JSON file.

    All keys are optional on disk; missing keys fall back to ``DEFAULT_CONFIG``.
    """

    version: int
    managers: list[str]
    auto_yes: bool
    notify: bool
    log: bool
    log_dir: str


DEFAULT_CONFIG: dict[str, Any] = {
    "version": CONFIG_VERSION,
    "managers": ["brew", "cask", "pip", "npm", "gem", "system"],
    "auto_yes": False,
    "notify": True,
    "log": True,
    "log_dir": "~/",
}

KNOWN_MANAGERS = {"brew", "cask", "pip", "npm", "gem", "system"}


def default_config_path() -> Path:
    return Path.home() / ".mac-upgrade"


def config_exists(path: Path | None = None) -> bool:
    return (path or default_config_path()).exists()


def load_config(path: Path | None = None) -> tuple[dict[str, Any], str | None]:
    """Load config from disk.

    Returns (config_dict, warning_or_None). If the file is missing, malformed,
    or has a version mismatch, returns DEFAULT_CONFIG plus a human-readable
    warning describing what happened.
    """
    p = path or default_config_path()
    if not p.exists():
        return dict(DEFAULT_CONFIG), None
    try:
        raw = p.read_text()
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return dict(DEFAULT_CONFIG), (
            f"{p} is unreadable ({exc}) — using defaults. "
            "Run 'mac-upgrade --onboard' to reconfigure."
        )
    if not isinstance(data, dict):
        return dict(DEFAULT_CONFIG), (
            f"{p} is not a JSON object — using defaults. "
            "Run 'mac-upgrade --onboard' to reconfigure."
        )
    if data.get("version") != CONFIG_VERSION:
        return dict(DEFAULT_CONFIG), (
            f"{p} has unknown version {data.get('version')!r} — using defaults. "
            "Run 'mac-upgrade --onboard' to reconfigure."
        )
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    # Filter managers to known keys (ignore unknowns silently).
    if isinstance(merged.get("managers"), list):
        merged["managers"] = [m for m in merged["managers"] if m in KNOWN_MANAGERS]
    else:
        merged["managers"] = list(DEFAULT_CONFIG["managers"])
    return merged, None


def save_config(cfg: dict[str, Any], path: Path | None = None) -> None:
    """Atomically write config JSON.

    Preserves unknown top-level keys that were already present in the file
    on disk (forward compatibility).
    """
    p = path or default_config_path()
    existing: dict[str, Any] = {}
    if p.exists():
        try:
            loaded = json.loads(p.read_text())
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, json.JSONDecodeError):
            existing = {}

    merged = dict(existing)
    merged.update(cfg)
    merged["version"] = CONFIG_VERSION

    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".mac-upgrade.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(merged, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, p)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
