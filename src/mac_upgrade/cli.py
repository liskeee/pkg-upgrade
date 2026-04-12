import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult

from mac_upgrade import __version__
from mac_upgrade.app import MacUpgradeApp
from mac_upgrade.config import (
    DEFAULT_CONFIG,
    config_exists,
    load_config,
    save_config,
)
from mac_upgrade.onboarding import OnboardingScreen


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mac-upgrade",
        description="Upgrade all macOS package managers with a beautiful TUI dashboard",
    )
    parser.add_argument(
        "--skip", type=lambda s: set(s.split(",")), default=None, metavar="MANAGERS"
    )
    parser.add_argument(
        "--only", type=lambda s: set(s.split(",")), default=None, metavar="MANAGERS"
    )
    parser.add_argument("--yes", "-y", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    parser.add_argument("--no-log", action="store_true")
    parser.add_argument("--log-dir", type=str, default=None, metavar="PATH")
    parser.add_argument("--list", action="store_true", dest="list_managers")
    parser.add_argument(
        "--onboard",
        action="store_true",
        help="Run the configuration wizard and exit",
    )
    parser.add_argument("--version", action="version", version=f"mac-upgrade {__version__}")
    return parser.parse_args(argv)


def get_log_path(log_enabled: bool, log_dir: str | None) -> str | None:
    if not log_enabled:
        return None
    base = Path(log_dir).expanduser() if log_dir else Path.home()
    today = date.today().isoformat()
    return str(base / f"mac-upgrade-{today}.log")


def resolve_settings(args: argparse.Namespace, cfg: dict[str, Any]) -> dict[str, Any]:
    """Merge CLI flags with config — flags always win."""
    cfg_managers = set(cfg.get("managers") or DEFAULT_CONFIG["managers"])

    effective = cfg_managers & args.only if args.only is not None else set(cfg_managers)
    if args.skip:
        effective -= args.skip

    auto_yes = bool(cfg.get("auto_yes", False)) or args.yes
    notify = bool(cfg.get("notify", True)) and not args.no_notify
    log_enabled = bool(cfg.get("log", True)) and not args.no_log
    log_dir = args.log_dir if args.log_dir is not None else cfg.get("log_dir")

    return {
        "only": effective if args.only is not None else None,
        "skip": args.skip,
        "managers": effective,
        "auto_yes": auto_yes,
        "notify": notify,
        "log_path": get_log_path(log_enabled, log_dir),
        "dry_run": args.dry_run,
        "list_only": args.list_managers,
    }


def _run_onboarding_wizard(initial: dict[str, Any]) -> dict[str, Any] | None:
    """Launch the Textual onboarding screen. Returns saved config or None."""
    result: dict[str, Any] | None = None

    class WizardApp(App[None]):
        def compose(self) -> ComposeResult:
            return []

        async def on_mount(self) -> None:
            nonlocal result
            result = await self.push_screen_wait(OnboardingScreen(initial=initial))
            self.exit()

    WizardApp().run()
    return result


def main() -> None:
    args = parse_args()

    if args.onboard:
        existing, _ = load_config()
        saved = _run_onboarding_wizard(existing)
        if saved is not None:
            save_config(saved)
            print(f"Saved configuration to {Path.home() / '.mac-upgrade'}")
        else:
            print("Onboarding cancelled — no changes written.")
        return

    if args.list_managers or "--version" in sys.argv:
        cfg = DEFAULT_CONFIG
        warning = None
    elif not config_exists():
        saved = _run_onboarding_wizard(dict(DEFAULT_CONFIG))
        if saved is None:
            print("Onboarding cancelled — exiting.")
            return
        save_config(saved)
        cfg = saved
        warning = None
    else:
        cfg, warning = load_config()

    if warning:
        print(f"warning: {warning}", file=sys.stderr)

    settings = resolve_settings(args, cfg)

    app = MacUpgradeApp(
        skip=settings["skip"],
        only=settings["only"],
        auto_yes=settings["auto_yes"],
        dry_run=settings["dry_run"],
        notify=settings["notify"],
        log_path=settings["log_path"],
        list_only=settings["list_only"],
    )
    app.run()
