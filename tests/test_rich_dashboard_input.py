from __future__ import annotations

from pkg_upgrade.ui._input import FakeInput
from pkg_upgrade.ui.rich_dashboard import RichDashboardUI
from tests._ui_fakes import FakeExecutor, canned_states_all_outdated


async def test_quit_immediately() -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = RichDashboardUI(input=FakeInput(["q"]), quiet=True)
    await ui.run(ex, auto_yes=True, dry_run=False)
    # quit short-circuits; may or may not have run upgrades


async def test_auto_yes_runs_all_and_exits() -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = RichDashboardUI(input=FakeInput([]), quiet=True)
    await ui.run(ex, auto_yes=True, dry_run=False)
    assert ex.all_done()
    assert ex.upgrade_calls >= 1


async def test_manual_confirm_then_skip() -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = RichDashboardUI(input=FakeInput(["y", "j", "s"]), quiet=True)
    await ui.run(ex, auto_yes=False, dry_run=False)
    assert ex.all_done()
