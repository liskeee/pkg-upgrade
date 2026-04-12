from __future__ import annotations

from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, RichLog

from mac_upgrade.status import ManagerStatus


class ManagerCard(Widget):
    """Displays a single package manager's status, progress, and results."""

    DEFAULT_CSS = """
    ManagerCard {
        height: 3;
        padding: 0 1;
        layout: horizontal;
        border-bottom: solid $primary-darken-2;
    }
    ManagerCard .icon-name {
        width: 26;
    }
    ManagerCard .status-area {
        width: 1fr;
    }
    ManagerCard .pkg-count {
        width: 12;
        text-align: right;
    }
    ManagerCard.-highlight {
        background: $primary-background;
    }
    """

    status: reactive[ManagerStatus] = reactive(ManagerStatus.PENDING)
    upgraded: reactive[int] = reactive(0)
    total: reactive[int] = reactive(0)
    failed: reactive[int] = reactive(0)

    def __init__(
        self,
        icon: str,
        manager_name: str,
        manager_key: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.icon = icon
        self.manager_name = manager_name
        self.manager_key = manager_key

    def compose(self) -> ComposeResult:
        yield Label(f"{self.icon} {self.manager_name}", classes="icon-name")
        yield Label("", id="status-label", classes="status-area")
        yield Label("", id="count-label", classes="pkg-count")

    def _refresh_labels(self) -> None:
        status_label = self.query_one("#status-label", Label)
        count_label = self.query_one("#count-label", Label)

        if self.status == ManagerStatus.PENDING:
            status_label.update("⏳ pending")
            count_label.update("")
        elif self.status == ManagerStatus.CHECKING:
            status_label.update("🔍 checking...")
            count_label.update("")
        elif self.status == ManagerStatus.AWAITING_CONFIRM:
            status_label.update(
                f"📋 {self.total} update{'s' if self.total != 1 else ''} "
                "found — [Enter] confirm / [S] skip"
            )
            count_label.update("")
        elif self.status == ManagerStatus.UPGRADING:
            status_label.update("⬆️  upgrading...")
            count_label.update(f"{self.upgraded}/{self.total}")
        elif self.status == ManagerStatus.DONE:
            if self.failed > 0:
                status_label.update(f"✅ {self.upgraded} upgraded, ❌ {self.failed} failed")
            elif self.total == 0:
                status_label.update("━━ no updates")
            else:
                status_label.update(f"✅ {self.upgraded} upgraded")
            count_label.update("")
        elif self.status == ManagerStatus.SKIPPED:
            status_label.update("⏭  skipped")
            count_label.update("")
        elif self.status == ManagerStatus.UNAVAILABLE:
            status_label.update("⚠️  not installed")
            count_label.update("")
        elif self.status == ManagerStatus.ERROR:
            status_label.update("❌ check failed")
            count_label.update("")

    def watch_status(self, _value: ManagerStatus) -> None:
        if self.is_mounted:
            self._refresh_labels()

    def watch_upgraded(self, _value: int) -> None:
        if self.is_mounted:
            self._refresh_labels()

    def watch_total(self, _value: int) -> None:
        if self.is_mounted:
            self._refresh_labels()

    def watch_failed(self, _value: int) -> None:
        if self.is_mounted:
            self._refresh_labels()


class LiveLogPanel(Widget):
    """Scrollable log of timestamped events."""

    DEFAULT_CSS = """
    LiveLogPanel {
        height: 1fr;
        border-top: solid $primary;
    }
    LiveLogPanel RichLog {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True, wrap=True, id="live-log")

    def add_line(self, manager_key: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        log = self.query_one("#live-log", RichLog)
        log.write(f"[dim]{ts}[/dim]  [bold cyan]{manager_key:8s}[/bold cyan]  {message}")
