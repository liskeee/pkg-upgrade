"""Textual onboarding wizard that produces a config dict."""
from __future__ import annotations

import asyncio
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    ContentSwitcher,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Static,
)

from mac_upgrade.config import DEFAULT_CONFIG
from mac_upgrade.managers import ALL_MANAGERS


STEP_IDS = ["step-managers", "step-confirm", "step-notify", "step-log", "step-review"]


class OnboardingScreen(Screen):
    """Wizard screen. Call with `push_screen_wait(OnboardingScreen(...))` —
    dismisses with the saved config dict, or None if cancelled."""

    DEFAULT_CSS = """
    OnboardingScreen {
        align: center middle;
    }
    #onboarding-box {
        width: 70;
        height: auto;
        max-height: 90%;
        border: thick $primary;
        padding: 1 2;
    }
    #step-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }
    .step-panel {
        height: auto;
        padding: 1 0;
    }
    .manager-row {
        height: 1;
        layout: horizontal;
    }
    .manager-row Checkbox {
        width: 30;
    }
    #review-json {
        padding: 1;
        background: $surface;
        height: auto;
    }
    #nav {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    #nav Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "cancel", "Cancel", show=True),
    ]

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._cfg: dict[str, Any] = dict(initial or DEFAULT_CONFIG)
        self._step = 0
        self._available: dict[str, bool] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="onboarding-box"):
            yield Static("Welcome to mac-upgrade — let's get you set up.", id="step-title")
            with ContentSwitcher(initial=STEP_IDS[0], id="switcher"):
                with VerticalScroll(id="step-managers", classes="step-panel"):
                    yield Label("Which package managers do you want to upgrade by default?")
                    yield Label("(detecting installed tools…)", id="detect-status")
                    yield Vertical(id="manager-checks")
                with Vertical(id="step-confirm", classes="step-panel"):
                    yield Label("How should upgrades be confirmed?")
                    with RadioSet(id="confirm-radio"):
                        yield RadioButton(
                            "Ask me before each manager (recommended)",
                            value=not self._cfg["auto_yes"],
                            id="confirm-ask",
                        )
                        yield RadioButton(
                            "Upgrade everything automatically (--yes default)",
                            value=self._cfg["auto_yes"],
                            id="confirm-yes",
                        )
                with Vertical(id="step-notify", classes="step-panel"):
                    yield Label("Notifications")
                    yield Checkbox(
                        "Show a macOS notification when upgrades complete",
                        value=self._cfg["notify"],
                        id="notify-check",
                    )
                with Vertical(id="step-log", classes="step-panel"):
                    yield Label("Logging")
                    yield Checkbox(
                        "Write a log file for each run",
                        value=self._cfg["log"],
                        id="log-check",
                    )
                    yield Label("Log directory:")
                    yield Input(value=self._cfg["log_dir"], id="log-dir-input")
                with VerticalScroll(id="step-review", classes="step-panel"):
                    yield Label("Review your settings:")
                    yield Static("", id="review-json")
            with Horizontal(id="nav"):
                yield Button("Back", id="back-btn", disabled=True)
                yield Button("Next", id="next-btn", variant="primary")
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="error")
        yield Footer()

    async def on_mount(self) -> None:
        self._update_nav()
        self.run_worker(self._detect_managers(), exclusive=True)

    async def _detect_managers(self) -> None:
        results = await asyncio.gather(
            *(m.is_available() for m in ALL_MANAGERS), return_exceptions=True
        )
        self._available = {
            m.key: (bool(r) if not isinstance(r, Exception) else False)
            for m, r in zip(ALL_MANAGERS, results)
        }
        container = self.query_one("#manager-checks", Vertical)
        await container.remove_children()
        saved = set(self._cfg.get("managers") or [])
        for m in ALL_MANAGERS:
            available = self._available[m.key]
            label = (
                f"{m.icon} {m.name}  "
                + ("[dim]✓ installed[/dim]" if available else "[red]✗ not found[/red]")
            )
            cb = Checkbox(
                label,
                value=available and m.key in saved,
                id=f"mgr-{m.key}",
                disabled=not available,
                classes="manager-row",
            )
            await container.mount(cb)
        self.query_one("#detect-status", Label).update(
            f"Detected {sum(self._available.values())} of {len(ALL_MANAGERS)} managers installed."
        )

    def _update_nav(self) -> None:
        back = self.query_one("#back-btn", Button)
        nxt = self.query_one("#next-btn", Button)
        save = self.query_one("#save-btn", Button)
        back.disabled = self._step == 0
        on_review = self._step == len(STEP_IDS) - 1
        nxt.display = not on_review
        save.display = on_review

    def _go_to(self, step: int) -> None:
        self._step = max(0, min(step, len(STEP_IDS) - 1))
        self.query_one("#switcher", ContentSwitcher).current = STEP_IDS[self._step]
        if STEP_IDS[self._step] == "step-review":
            self._collect()
            self._render_review()
        self._update_nav()

    def _collect(self) -> None:
        managers: list[str] = []
        for m in ALL_MANAGERS:
            try:
                cb = self.query_one(f"#mgr-{m.key}", Checkbox)
            except Exception:
                continue
            if cb.value:
                managers.append(m.key)
        self._cfg["managers"] = managers
        self._cfg["auto_yes"] = self.query_one("#confirm-yes", RadioButton).value
        self._cfg["notify"] = self.query_one("#notify-check", Checkbox).value
        self._cfg["log"] = self.query_one("#log-check", Checkbox).value
        self._cfg["log_dir"] = self.query_one("#log-dir-input", Input).value or "~/"

    def _render_review(self) -> None:
        import json
        self.query_one("#review-json", Static).update(
            json.dumps(self._cfg, indent=2, sort_keys=True)
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "next-btn":
            self._go_to(self._step + 1)
        elif bid == "back-btn":
            self._go_to(self._step - 1)
        elif bid == "save-btn":
            self._collect()
            self.dismiss(self._cfg)
        elif bid == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
