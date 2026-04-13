"""Persistent user configuration for pkg-upgrade."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict

import yaml
from platformdirs import user_config_path

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


@dataclass
class Config:
    """Structured configuration loaded from the YAML config file.

    Contains new keys added in Task 8 alongside any future fields.
    """

    disabled_managers: set[str] = field(default_factory=set)
    per_manager: dict[str, Any] = field(default_factory=dict)
    max_parallel: int | None = None


def config_file_path() -> Path:
    """Return the canonical path to the YAML config file, using platformdirs."""
    return user_config_path("pkg-upgrade") / "config.yaml"


def load_config(path: Path | None = None) -> Config:
    """Load structured Config from a YAML file.

    Returns a Config with defaults if the file is missing or unreadable.
    The ``path`` argument defaults to ``config_file_path()``.
    """
    p = path if path is not None else config_file_path()
    if not p.exists():
        return Config()
    try:
        raw = p.read_text()
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError):
        return Config()
    if not isinstance(data, dict):
        return Config()

    disabled: set[str] = set()
    raw_disabled = data.get("disabled_managers")
    if isinstance(raw_disabled, list):
        disabled = {str(m) for m in raw_disabled}

    per_manager: dict[str, Any] = {}
    raw_per_manager = data.get("per_manager")
    if isinstance(raw_per_manager, dict):
        per_manager = raw_per_manager

    max_parallel: int | None = None
    raw_max_parallel = data.get("max_parallel")
    if isinstance(raw_max_parallel, int):
        max_parallel = raw_max_parallel

    return Config(
        disabled_managers=disabled,
        per_manager=per_manager,
        max_parallel=max_parallel,
    )


# ---------------------------------------------------------------------------
# Legacy JSON-based config (preserved for backward compatibility)
# ---------------------------------------------------------------------------


def default_config_path() -> Path:
    return Path.home() / ".mac-upgrade"


def config_exists(path: Path | None = None) -> bool:
    return (path or default_config_path()).exists()


def load_config_dict(path: Path | None = None) -> tuple[dict[str, Any], str | None]:
    """Load legacy JSON config from disk.

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
    """Atomically write legacy JSON config.

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
        Path(tmp_path).replace(p)
    except Exception:
        with contextlib.suppress(OSError):
            Path(tmp_path).unlink()
        raise
