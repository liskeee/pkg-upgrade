from __future__ import annotations

import time
from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from mac_upgrade.executor import Executor, ManagerState
from mac_upgrade.managers import get_managers
from mac_upgrade.models import Result
from mac_upgrade.notifier import Notifier
from mac_upgrade.widgets import LiveLogPanel, ManagerCard


class MacUpgradeApp(App):
    """TUI dashboard for upgrading macOS packages."""

    TITLE = "mac-upgrade"
    CSS = """
    #header-bar {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    #managers-container {
        height: auto;
        max-height: 60%;
        padding: 1 0;
    }
    #footer-help {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("enter", "confirm", "Confirm", show=True),
        Binding("s", "skip", "Skip", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("r", "retry", "Retry", show=False),
    ]

    def __init__(
        self,
        skip: set[str] | None = None,
        only: set[str] | None = None,
        auto_yes: bool = False,
        dry_run: bool = False,
        notify: bool = True,
        log_path: str | None = None,
        list_only: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        managers = get_managers(skip=skip, only=only)
        self.executor = Executor.from_managers(managers)
        self.auto_yes = auto_yes
        self.dry_run = dry_run
        self.notifier = Notifier(log_path=log_path, notify=notify)
        self.list_only = list_only
        self.cards: dict[str, ManagerCard] = {}
        self._confirm_queue: list[str] = []
        self._current_confirm: str | None = None
        self._start_time: float = 0.0
        self._phase = "checking"

    def compose(self) -> ComposeResult:
        today = date.today().strftime("%d %b %Y")
        yield Static(f"🚀 mac-upgrade                                           {today}", id="header-bar")
        with VerticalScroll(id="managers-container"):
            for mgr in self.executor.all_managers():
                card = ManagerCard(
                    icon=mgr.icon,
                    manager_name=mgr.name,
                    manager_key=mgr.key,
                    id=f"card-{mgr.key}",
                )
                self.cards[mgr.key] = card
                yield card
        yield LiveLogPanel(id="log-panel")
        yield Static("[Enter] Confirm  [S] Skip  [Q] Quit", id="footer-help")

    async def on_mount(self) -> None:
        self._start_time = time.monotonic()
        if self.list_only:
            self.run_worker(self._list_and_exit())
            return
        self.run_worker(self._run_check_phase())

    async def _list_and_exit(self) -> None:
        for mgr in self.executor.all_managers():
            available = await mgr.is_available()
            self.cards[mgr.key].status = "done" if available else "unavailable"
            self._log(mgr.key, "Available" if available else "Not installed")
        self.set_timer(1.5, self.exit)

    async def _run_check_phase(self) -> None:
        async def on_update(key: str, state: ManagerState) -> None:
            card = self.cards[key]
            card.total = len(state.outdated)
            card.status = state.status
            if state.status == "checking":
                self._log(key, "Checking for updates...")
            elif state.status == "awaiting_confirm":
                count = len(state.outdated)
                self._log(key, f"Found {count} outdated package{'s' if count != 1 else ''}")
                for pkg in state.outdated:
                    self._log(key, f"  {pkg}")
                if self.dry_run:
                    self.executor.skip_manager(key)
                    card.status = "done"
                    self._log(key, "Dry run — no changes made")
                    await self._maybe_finish()
                elif self.auto_yes:
                    self.run_worker(self._run_upgrade(key))
                else:
                    self._confirm_queue.append(key)
                    self._advance_confirm()
            elif state.status == "unavailable":
                self._log(key, "Not installed — skipping")
            elif state.status == "done" and not state.outdated:
                self._log(key, "All packages up to date")

        await self.executor.check_all(on_update=on_update)
        self._phase = "confirming"
        await self._maybe_finish()

    def _advance_confirm(self) -> None:
        if self._current_confirm is not None:
            return
        if not self._confirm_queue:
            return
        key = self._confirm_queue.pop(0)
        self._current_confirm = key
        self.cards[key].add_class("-highlight")

    async def _run_upgrade(self, key: str) -> None:
        async def on_update(k: str, state: ManagerState) -> None:
            c = self.cards[k]
            c.total = len(state.outdated)
            c.upgraded = sum(1 for r in state.results if r.success)
            c.failed = sum(1 for r in state.results if not r.success)
            c.status = state.status

        async def on_result(k: str, result: Result) -> None:
            if result.success:
                self._log(k, f"✓ Upgraded {result.package}")
            else:
                self._log(k, f"✗ Failed {result.package.name}: {result.message}")

        self._log(key, "Starting upgrades...")
        await self.executor.upgrade_manager(
            key, on_update=on_update, on_result=on_result,
        )
        await self._maybe_finish()

    async def action_confirm(self) -> None:
        if self._current_confirm is None:
            return
        key = self._current_confirm
        self.cards[key].remove_class("-highlight")
        self._current_confirm = None
        self.run_worker(self._run_upgrade(key))
        self._advance_confirm()

    async def action_skip(self) -> None:
        if self._current_confirm is None:
            return
        key = self._current_confirm
        self.executor.skip_manager(key)
        self.cards[key].remove_class("-highlight")
        self.cards[key].status = "skipped"
        self._log(key, "Skipped by user")
        self._current_confirm = None
        self._advance_confirm()
        await self._maybe_finish()

    def action_quit_app(self) -> None:
        self.exit()

    async def action_retry(self) -> None:
        self.exit()

    async def _maybe_finish(self) -> None:
        active_statuses = {"pending", "checking", "awaiting_confirm", "upgrading"}
        if self._current_confirm is not None:
            return
        if self._confirm_queue:
            return
        for state in self.executor.states.values():
            if state.status in active_statuses:
                return
        await self._finish()

    async def _finish(self) -> None:
        if self._phase == "summary":
            return
        self._phase = "summary"

        elapsed = time.monotonic() - self._start_time
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        duration = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
        self._log("done", f"Completed in {duration}")

        total_upgraded = sum(
            1 for s in self.executor.states.values() for r in s.results if r.success
        )
        total_failed = sum(
            1 for s in self.executor.states.values() for r in s.results if not r.success
        )
        total_skipped = sum(
            1 for s in self.executor.states.values() if s.status == "skipped"
        )

        summary = f"{total_upgraded} upgraded"
        if total_failed:
            summary += f", {total_failed} failed"
        if total_skipped:
            summary += f", {total_skipped} skipped"

        title = (
            "mac-upgrade complete"
            if total_failed == 0
            else "mac-upgrade finished with errors"
        )
        await self.notifier.send_notification(title, summary)

        footer = self.query_one("#footer-help", Static)
        footer.update(f"Done — {summary}  |  [Q] Quit")

    def _log(self, key: str, message: str) -> None:
        panel = self.query_one("#log-panel", LiveLogPanel)
        panel.add_line(key, message)
        self.notifier.log(key, message)
