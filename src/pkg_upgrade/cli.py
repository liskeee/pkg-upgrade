from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult

from pkg_upgrade import __version__
from pkg_upgrade.app import MacUpgradeApp
from pkg_upgrade.config import (
    DEFAULT_CONFIG,
    config_exists,
    load_config_dict,
    save_config,
)
from pkg_upgrade.onboarding import OnboardingScreen


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser (extracted for testability)."""
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
    parser.add_argument(
        "--show-graph",
        action="store_true",
        help="Print execution plan (topo-sorted groups) and exit",
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=None,
        metavar="N",
        help="Cap per-level concurrency",
    )
    parser.add_argument("--version", action="version", version=f"mac-upgrade {__version__}")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


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


def _print_list(skip: set[str] | None = None, only: set[str] | None = None) -> int:
    """Print managers grouped by Available / Unavailable / Not on this OS."""
    from pkg_upgrade.platform import current_os  # noqa: PLC0415
    from pkg_upgrade.registry import (  # noqa: PLC0415
        all_registered,
        discover_managers,
        select_managers,
    )

    on_os = discover_managers(load_entry_points=False, load_declarative=True)
    on_os_filtered = select_managers(on_os, skip=skip, only=only)
    on_os_keys = {m.key for m in on_os}
    all_classes = all_registered()
    cur = current_os()

    async def _probe() -> list[tuple[Any, bool]]:
        return [(m, await m.is_available()) for m in on_os_filtered]

    probed = asyncio.run(_probe())
    available = [m for m, ok in probed if ok]
    unavailable = [m for m, ok in probed if not ok]
    other_os = [c for c in all_classes if c.key not in on_os_keys]

    print("Available:")
    for m in available:
        print(f"  {m.icon} {m.key} — {m.name}")
    print()
    print("Unavailable (declared for this OS, binary missing):")
    for m in unavailable:
        hint = f"  hint: {m.install_hint}" if m.install_hint else ""
        print(f"  {m.icon} {m.key} — {m.name}{hint}")
    print()
    print(f"Not on this OS ({cur}):")
    for c in other_os:
        plats = ",".join(sorted(c.platforms))
        print(f"  {c.icon} {c.key} — {c.name} [{plats}]")
    return 0


def _print_graph(skip: set[str] | None = None, only: set[str] | None = None) -> int:
    """Print the topo-sorted execution plan and exit."""
    from pkg_upgrade.executor import Executor  # noqa: PLC0415
    from pkg_upgrade.registry import discover_managers, select_managers  # noqa: PLC0415

    managers = discover_managers(load_entry_points=False, load_declarative=True)
    managers = select_managers(managers, skip=skip, only=only)
    ex = Executor.from_managers(managers)
    for i, group in enumerate(ex.groups):
        keys = ", ".join(m.key for m in group.managers)
        print(f"Level {i}: {keys}")
    return 0


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


def main() -> int:
    args = parse_args()

    if args.onboard:
        existing, _ = load_config_dict()
        saved = _run_onboarding_wizard(existing)
        if saved is not None:
            save_config(saved)
            print(f"Saved configuration to {Path.home() / '.mac-upgrade'}")
        else:
            print("Onboarding cancelled — no changes written.")
        return 0

    if args.list_managers:
        return _print_list(skip=args.skip, only=args.only)

    if args.show_graph:
        return _print_graph(skip=args.skip, only=args.only)

    if "--version" in sys.argv:
        cfg = DEFAULT_CONFIG
        warning = None
    elif not config_exists():
        saved = _run_onboarding_wizard(dict(DEFAULT_CONFIG))
        if saved is None:
            print("Onboarding cancelled — exiting.")
            return 0
        save_config(saved)
        cfg = saved
        warning = None
    else:
        cfg, warning = load_config_dict()

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
        max_parallel=args.max_parallel,
    )
    app.run()
    return 0
