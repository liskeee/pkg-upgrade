# tests/test_plain_dashboard.py
from __future__ import annotations

from pkg_upgrade.ui.plain_dashboard import PlainDashboardUI
from tests._ui_fakes import FakeExecutor, canned_states_all_outdated


async def test_plain_ui_streams_lines_and_completes(capsys) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = PlainDashboardUI()
    await ui.run(ex, auto_yes=True, dry_run=False)
    out = capsys.readouterr().out
    assert "[brew]" in out
    assert "done" in out
    assert ex.all_done()


async def test_plain_ui_dry_run_does_not_upgrade(capsys) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = PlainDashboardUI()
    await ui.run(ex, auto_yes=True, dry_run=True)
    assert ex.upgrade_calls == 0
