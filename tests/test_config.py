import json
from unittest.mock import patch

from pkg_upgrade.config import (
    CONFIG_VERSION,
    DEFAULT_CONFIG,
    config_exists,
    config_file_path,
    load_config,
    load_config_dict,
    save_config,
)


def test_load_missing_returns_defaults(tmp_path):
    cfg, warning = load_config_dict(tmp_path / ".mac-upgrade")
    assert warning is None
    assert cfg == DEFAULT_CONFIG
    assert cfg is not DEFAULT_CONFIG  # copy, not the same dict


def test_load_malformed_warns_and_returns_defaults(tmp_path):
    p = tmp_path / ".mac-upgrade"
    p.write_text("{not valid json")
    cfg, warning = load_config_dict(p)
    assert warning is not None
    assert "unreadable" in warning
    assert cfg == DEFAULT_CONFIG


def test_load_wrong_version_warns(tmp_path):
    p = tmp_path / ".mac-upgrade"
    p.write_text(json.dumps({"version": 999, "managers": ["brew"]}))
    cfg, warning = load_config_dict(p)
    assert warning is not None
    assert "999" in warning
    assert cfg == DEFAULT_CONFIG


def test_load_non_object_warns(tmp_path):
    p = tmp_path / ".mac-upgrade"
    p.write_text(json.dumps([1, 2, 3]))
    cfg, warning = load_config_dict(p)
    assert warning is not None
    assert cfg == DEFAULT_CONFIG


def test_roundtrip(tmp_path):
    p = tmp_path / ".mac-upgrade"
    new_cfg = {
        "version": CONFIG_VERSION,
        "managers": ["brew", "npm"],
        "auto_yes": True,
        "notify": False,
        "log": True,
        "log_dir": "/tmp/logs",
    }
    save_config(new_cfg, p)
    loaded, warning = load_config_dict(p)
    assert warning is None
    assert loaded == new_cfg


def test_save_preserves_unknown_keys(tmp_path):
    p = tmp_path / ".mac-upgrade"
    p.write_text(
        json.dumps(
            {
                "version": CONFIG_VERSION,
                "managers": ["brew"],
                "auto_yes": False,
                "notify": True,
                "log": True,
                "log_dir": "~/",
                "future_feature": {"hello": "world"},
            }
        )
    )
    save_config({"auto_yes": True}, p)
    reloaded = json.loads(p.read_text())
    assert reloaded["future_feature"] == {"hello": "world"}
    assert reloaded["auto_yes"] is True


def test_save_filters_unknown_managers_on_load(tmp_path):
    p = tmp_path / ".mac-upgrade"
    p.write_text(
        json.dumps(
            {
                "version": CONFIG_VERSION,
                "managers": ["brew", "mystery-manager", "npm"],
            }
        )
    )
    cfg, _ = load_config_dict(p)
    assert "mystery-manager" not in cfg["managers"]
    assert "brew" in cfg["managers"]
    assert "npm" in cfg["managers"]


def test_save_is_atomic_leaves_no_tempfile(tmp_path):
    p = tmp_path / ".mac-upgrade"
    save_config({"auto_yes": False}, p)
    tempfiles = [f for f in tmp_path.iterdir() if f.name.startswith(".mac-upgrade.")]
    assert tempfiles == []


def test_config_exists(tmp_path):
    p = tmp_path / ".mac-upgrade"
    assert config_exists(p) is False
    p.write_text("{}")
    assert config_exists(p) is True


# --- New Task 8 tests: Config dataclass + platformdirs + YAML ---


def test_config_path_uses_platformdirs(tmp_path):
    with patch("pkg_upgrade.config.user_config_path", return_value=tmp_path):
        assert config_file_path().parent == tmp_path


def test_load_yaml_missing_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg.disabled_managers == set()
    assert cfg.per_manager == {}
    assert cfg.max_parallel is None


def test_load_yaml_parses_all_keys(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("""
disabled_managers: [gem, npm]
max_parallel: 2
per_manager:
  brew:
    env:
      HOMEBREW_NO_AUTO_UPDATE: "1"
""")
    cfg = load_config(f)
    assert cfg.disabled_managers == {"gem", "npm"}
    assert cfg.max_parallel == 2
    assert cfg.per_manager["brew"]["env"]["HOMEBREW_NO_AUTO_UPDATE"] == "1"
