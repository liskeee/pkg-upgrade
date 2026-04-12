from types import SimpleNamespace

from mac_upgrade.cli import parse_args, get_log_path, resolve_settings
from mac_upgrade.config import DEFAULT_CONFIG


def test_default_args():
    args = parse_args([])
    assert args.skip is None
    assert args.only is None
    assert args.yes is False
    assert args.dry_run is False
    assert args.no_notify is False
    assert args.no_log is False
    assert args.log_dir is None
    assert args.list_managers is False
    assert args.onboard is False


def test_skip_flag():
    assert parse_args(["--skip", "brew,pip"]).skip == {"brew", "pip"}


def test_only_flag():
    assert parse_args(["--only", "npm,gem"]).only == {"npm", "gem"}


def test_yes_flag():
    assert parse_args(["--yes"]).yes is True
    assert parse_args(["-y"]).yes is True


def test_dry_run():
    assert parse_args(["--dry-run"]).dry_run is True


def test_no_notify_no_log():
    args = parse_args(["--no-notify", "--no-log"])
    assert args.no_notify is True
    assert args.no_log is True


def test_log_dir():
    assert parse_args(["--log-dir", "/tmp/logs"]).log_dir == "/tmp/logs"


def test_list_flag():
    assert parse_args(["--list"]).list_managers is True


def test_onboard_flag():
    assert parse_args(["--onboard"]).onboard is True


def test_get_log_path_disabled():
    assert get_log_path(False, None) is None


def test_get_log_path_default(tmp_path):
    path = get_log_path(True, str(tmp_path))
    assert path is not None
    assert str(tmp_path) in path
    assert path.endswith(".log")


def test_get_log_path_expands_tilde(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = get_log_path(True, "~/logs")
    assert path is not None
    assert str(tmp_path) in path


# --- resolve_settings ---

def _args(**overrides):
    base = dict(
        skip=None, only=None, yes=False, dry_run=False,
        no_notify=False, no_log=False, log_dir=None,
        list_managers=False, onboard=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_resolve_uses_config_defaults():
    cfg = dict(DEFAULT_CONFIG)
    cfg["auto_yes"] = True
    cfg["notify"] = False
    s = resolve_settings(_args(), cfg)
    assert s["auto_yes"] is True
    assert s["notify"] is False


def test_resolve_flag_overrides_auto_yes():
    cfg = dict(DEFAULT_CONFIG)
    cfg["auto_yes"] = False
    s = resolve_settings(_args(yes=True), cfg)
    assert s["auto_yes"] is True


def test_resolve_no_notify_overrides_config():
    cfg = dict(DEFAULT_CONFIG)
    cfg["notify"] = True
    s = resolve_settings(_args(no_notify=True), cfg)
    assert s["notify"] is False


def test_resolve_no_log_disables_log_path():
    cfg = dict(DEFAULT_CONFIG)
    s = resolve_settings(_args(no_log=True), cfg)
    assert s["log_path"] is None


def test_resolve_skip_subtracts_from_config_managers():
    cfg = dict(DEFAULT_CONFIG)
    cfg["managers"] = ["brew", "npm", "gem"]
    s = resolve_settings(_args(skip={"npm"}), cfg)
    assert s["managers"] == {"brew", "gem"}


def test_resolve_only_intersects_with_config_managers():
    cfg = dict(DEFAULT_CONFIG)
    cfg["managers"] = ["brew", "npm", "gem"]
    s = resolve_settings(_args(only={"brew", "system"}), cfg)
    # system is in --only but not in config managers → excluded
    assert s["managers"] == {"brew"}


def test_resolve_log_dir_flag_overrides(tmp_path):
    cfg = dict(DEFAULT_CONFIG)
    cfg["log_dir"] = "/does/not/exist"
    s = resolve_settings(_args(log_dir=str(tmp_path)), cfg)
    assert str(tmp_path) in s["log_path"]
