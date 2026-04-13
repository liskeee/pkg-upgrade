from __future__ import annotations

import pytest

from pkg_upgrade.ui._input import FakeInput
from pkg_upgrade.ui.plain_dashboard import PlainDashboardUI
from pkg_upgrade.ui.rich_dashboard import RichDashboardUI
from tests._ui_fakes import FakeExecutor, canned_states_all_outdated


@pytest.fixture(params=["plain", "rich"])
def ui(request: pytest.FixtureRequest) -> PlainDashboardUI | RichDashboardUI:
    if request.param == "plain":
        return PlainDashboardUI()
    return RichDashboardUI(input=FakeInput([]), quiet=True)


async def test_ui_completes_with_auto_yes(ui: PlainDashboardUI | RichDashboardUI) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    await ui.run(ex, auto_yes=True, dry_run=False)
    assert ex.all_done()


async def test_ui_respects_dry_run(ui: PlainDashboardUI | RichDashboardUI) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    await ui.run(ex, auto_yes=True, dry_run=True)
    assert ex.upgrade_calls == 0
