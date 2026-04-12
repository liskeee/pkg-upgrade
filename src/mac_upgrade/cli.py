import argparse
from datetime import date
from pathlib import Path

from mac_upgrade import __version__


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mac-upgrade",
        description="Upgrade all macOS package managers with a beautiful TUI dashboard",
    )
    parser.add_argument("--skip", type=lambda s: set(s.split(",")), default=None, metavar="MANAGERS")
    parser.add_argument("--only", type=lambda s: set(s.split(",")), default=None, metavar="MANAGERS")
    parser.add_argument("--yes", "-y", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    parser.add_argument("--no-log", action="store_true")
    parser.add_argument("--log-dir", type=str, default=None, metavar="PATH")
    parser.add_argument("--list", action="store_true", dest="list_managers")
    parser.add_argument("--version", action="version", version=f"mac-upgrade {__version__}")
    return parser.parse_args(argv)


def get_log_path(args: argparse.Namespace) -> str | None:
    if args.no_log:
        return None
    log_dir = Path(args.log_dir) if args.log_dir else Path.home()
    today = date.today().isoformat()
    return str(log_dir / f"mac-upgrade-{today}.log")


def main() -> None:
    args = parse_args()
    from mac_upgrade.app import MacUpgradeApp

    app = MacUpgradeApp(
        skip=args.skip,
        only=args.only,
        auto_yes=args.yes,
        dry_run=args.dry_run,
        notify=not args.no_notify,
        log_path=get_log_path(args),
        list_only=args.list_managers,
    )
    app.run()
