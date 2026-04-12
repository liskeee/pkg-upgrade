from mac_upgrade.cli import parse_args, get_log_path


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


def test_get_log_path_disabled():
    args = parse_args(["--no-log"])
    assert get_log_path(args) is None


def test_get_log_path_default(tmp_path):
    args = parse_args(["--log-dir", str(tmp_path)])
    path = get_log_path(args)
    assert path is not None
    assert str(tmp_path) in path
    assert path.endswith(".log")
