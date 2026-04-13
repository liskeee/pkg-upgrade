import argparse
from typing import Any

import pkg_upgrade.cli as cli_module
from pkg_upgrade.cli import build_parser, get_log_path, main, parse_args, resolve_settings
from pkg_upgrade.config import DEFAULT_CONFIG


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
    assert args.show_graph is False
    assert args.max_parallel is None


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
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    path = get_log_path(True, "~/logs")
    assert path is not None
    assert str(tmp_path) in path


# --- resolve_settings ---


def _args(**overrides: Any) -> argparse.Namespace:
    base = {
        "skip": None,
        "only": None,
        "yes": False,
        "dry_run": False,
        "no_notify": False,
        "no_log": False,
        "log_dir": None,
        "list_managers": False,
        "onboard": False,
        "show_graph": False,
        "max_parallel": None,
        "self_update": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


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


# --- new CLI feature tests ---


def test_parser_exposes_new_flags():
    p = build_parser()
    ns = p.parse_args(["--show-graph", "--max-parallel", "3"])
    assert ns.show_graph is True
    assert ns.max_parallel == 3


def test_list_groups_by_availability(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pkg-upgrade", "--list"])
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Available" in out
    # At least one of these must appear depending on the OS:
    assert "Unavailable" in out or "Not on this OS" in out


def test_show_graph_prints_levels(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pkg-upgrade", "--show-graph"])
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "level" in out.lower() or "Level" in out


def test_max_parallel_flag():
    p = build_parser()
    ns = p.parse_args(["--max-parallel", "4"])
    assert ns.max_parallel == 4


def test_max_parallel_default():
    p = build_parser()
    ns = p.parse_args([])
    assert ns.max_parallel is None


def test_self_update_flag_in_parser() -> None:
    p = build_parser()
    ns = p.parse_args(["--self-update"])
    assert ns.self_update is True


def test_self_update_invokes_helper(monkeypatch: Any, capsys: Any) -> None:
    calls: dict[str, bool] = {}

    def fake_run_self_update() -> int:
        calls["ran"] = True
        return 0

    monkeypatch.setattr(cli_module, "run_self_update", fake_run_self_update)
    monkeypatch.setattr("sys.argv", ["pkg-upgrade", "--self-update"])
    rc = main()
    assert rc == 0
    assert calls["ran"] is True
