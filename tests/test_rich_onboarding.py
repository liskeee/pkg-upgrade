from __future__ import annotations

from pkg_upgrade.config import DEFAULT_CONFIG
from pkg_upgrade.ui._input import FakeInput
from pkg_upgrade.ui.rich_onboarding import RichOnboardingUI


def test_onboarding_cancel_returns_none() -> None:
    ui = RichOnboardingUI(input=FakeInput(["q"]), quiet=True)
    assert ui.run(dict(DEFAULT_CONFIG)) is None


def test_onboarding_happy_path_saves_defaults() -> None:
    # step 1: managers (enter accepts discovered selection)
    # step 2: confirm mode (enter = ask)
    # step 3: notify (enter accepts)
    # step 4: logging (enter accepts both checkbox and path)
    # step 5: review (enter saves)
    keys = ["enter", "enter", "enter", "enter", "enter", "enter"]
    ui = RichOnboardingUI(input=FakeInput(keys), quiet=True)
    result = ui.run(dict(DEFAULT_CONFIG))
    assert result is not None
    assert "managers" in result
    assert "auto_yes" in result
    assert "notify" in result
    assert "log" in result
    assert "log_dir" in result


def test_onboarding_back_navigates() -> None:
    keys = ["enter", "b", "enter", "enter", "enter", "enter", "enter", "enter"]
    ui = RichOnboardingUI(input=FakeInput(keys), quiet=True)
    result = ui.run(dict(DEFAULT_CONFIG))
    assert result is not None
