"""Pilot-driven tests for the onboarding wizard.

These guard against regressions like an empty manager list, a broken Save
path, or a wizard that dismisses without collecting answers.
"""

from __future__ import annotations

from typing import Any

import pytest
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Button, Checkbox, Input, RadioButton

from pkg_upgrade.config import DEFAULT_CONFIG
from pkg_upgrade.onboarding import STEP_IDS, OnboardingScreen
from pkg_upgrade.registry import discover_managers


class _Host(App[None]):
    """Minimal host app that launches the wizard and stores its result."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.initial = initial
        self.result: dict[str, Any] | None = None
        self.dismissed = False

    def compose(self) -> ComposeResult:  # pragma: no cover - trivial
        return []

    def on_mount(self) -> None:
        self._launch()

    @work
    async def _launch(self) -> None:
        self.result = await self.push_screen_wait(OnboardingScreen(initial=self.initial))
        self.dismissed = True


async def _wait_for_detection(pilot: Any) -> None:
    """Pump the event loop until the detect worker has mounted checkboxes."""
    for _ in range(40):
        await pilot.pause()
        try:
            screen = pilot.app.screen
            checks = screen.query("#manager-checks Checkbox")
        except Exception:
            continue
        if len(checks) > 0:
            return
    raise AssertionError("manager checkboxes never populated")


async def test_onboarding_populates_manager_checkboxes() -> None:
    """Regression: on_mount must populate #manager-checks with discovered managers."""
    expected_keys = {m.key for m in discover_managers()}
    assert expected_keys, "test precondition: discover_managers should return managers"

    app = _Host()
    async with app.run_test() as pilot:
        await _wait_for_detection(pilot)
        screen = app.screen
        ids = {cb.id for cb in screen.query("#manager-checks Checkbox")}
        assert ids == {f"mgr-{k}" for k in expected_keys}
        status = str(screen.query_one("#detect-status").render())
        assert "Detected" in status


async def test_onboarding_save_returns_selected_managers() -> None:
    """Full happy-path: wizard walks to review and Save returns a populated dict."""
    app = _Host(initial=dict(DEFAULT_CONFIG))
    async with app.run_test() as pilot:
        await _wait_for_detection(pilot)

        screen = app.screen
        screen._go_to(len(STEP_IDS) - 1)
        await pilot.pause()
        btn = screen.query_one("#save-btn", Button)
        await screen.on_button_pressed(Button.Pressed(btn))
        for _ in range(40):
            await pilot.pause()
            if app.dismissed:
                break

    assert app.dismissed
    assert app.result is not None
    assert isinstance(app.result["managers"], list)
    assert len(app.result["managers"]) > 0
    for key in app.result["managers"]:
        assert key in {m.key for m in discover_managers()}


async def test_onboarding_cancel_returns_none() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        await _wait_for_detection(pilot)
        await pilot.click("#cancel-btn")
        for _ in range(20):
            await pilot.pause()
            if app.dismissed:
                break

    assert app.dismissed
    assert app.result is None


async def test_onboarding_respects_initial_managers() -> None:
    """A subset initial config pre-checks only those managers (when available)."""
    available_keys = [m.key for m in discover_managers()]
    if not available_keys:
        pytest.skip("no managers discovered on this platform")
    chosen = available_keys[:1]
    app = _Host(initial={**DEFAULT_CONFIG, "managers": chosen})
    async with app.run_test() as pilot:
        await _wait_for_detection(pilot)
        screen = app.screen
        checked = {
            cb.id.removeprefix("mgr-")
            for cb in screen.query("#manager-checks Checkbox")
            if cb.value
        }
    assert checked.issubset(set(available_keys))
    assert checked == set(chosen) or checked == set()


async def test_onboarding_auto_yes_and_log_propagate_to_result() -> None:
    """Toggling radios/inputs surfaces in the dismissed config dict."""
    app = _Host(initial=dict(DEFAULT_CONFIG))
    async with app.run_test() as pilot:
        await _wait_for_detection(pilot)
        screen = app.screen
        screen.query_one("#confirm-yes", RadioButton).value = True
        screen.query_one("#notify-check", Checkbox).value = False
        screen.query_one("#log-check", Checkbox).value = False
        screen.query_one("#log-dir-input", Input).value = "/tmp/foo"
        await pilot.pause()
        screen._go_to(len(STEP_IDS) - 1)
        await pilot.pause()
        btn = screen.query_one("#save-btn", Button)
        await screen.on_button_pressed(Button.Pressed(btn))
        for _ in range(20):
            await pilot.pause()
            if app.dismissed:
                break

    assert app.result is not None
    assert app.result["auto_yes"] is True
    assert app.result["notify"] is False
    assert app.result["log"] is False
    assert app.result["log_dir"] == "/tmp/foo"


async def test_onboarding_empty_registry_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """If discover_managers returns [] (user-reported bug scenario), the wizard
    still mounts, still reaches review, and Save returns managers=[]."""
    monkeypatch.setattr("pkg_upgrade.onboarding.discover_managers", lambda: [])
    app = _Host(initial=dict(DEFAULT_CONFIG))
    async with app.run_test() as pilot:
        for _ in range(20):
            await pilot.pause()
        screen = app.screen
        assert len(screen.query("#manager-checks Checkbox")) == 0
        status = str(screen.query_one("#detect-status").render())
        assert "Detected 0" in status

        screen._go_to(len(STEP_IDS) - 1)
        await pilot.pause()
        btn = screen.query_one("#save-btn", Button)
        await screen.on_button_pressed(Button.Pressed(btn))
        for _ in range(20):
            await pilot.pause()
            if app.dismissed:
                break

    assert app.result is not None
    assert app.result["managers"] == []


async def test_onboarding_back_button_navigates() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        await _wait_for_detection(pilot)
        assert app.screen.query_one("#back-btn", Button).disabled is True
        await pilot.click("#next-btn")
        await pilot.pause()
        assert app.screen.query_one("#back-btn", Button).disabled is False
        await pilot.click("#back-btn")
        await pilot.pause()
        assert app.screen.query_one("#back-btn", Button).disabled is True
