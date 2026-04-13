"""pkg_upgrade terminal UI."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Protocol

# mypy: ignore-errors

if TYPE_CHECKING:
    from pkg_upgrade.executor import Executor


class DashboardUI(Protocol):
    async def run(
        self,
        executor: Executor,
        *,
        auto_yes: bool,
        dry_run: bool,
    ) -> None: ...


class OnboardingUI(Protocol):
    def run(self, initial: dict[str, Any]) -> dict[str, Any] | None: ...


def select_dashboard() -> DashboardUI:
    if sys.stdout.isatty():
        from pkg_upgrade.ui.rich_dashboard import RichDashboardUI  # noqa: PLC0415
        return RichDashboardUI()
    from pkg_upgrade.ui.plain_dashboard import PlainDashboardUI  # noqa: PLC0415
    return PlainDashboardUI()


def select_onboarding() -> OnboardingUI | None:
    if not sys.stdout.isatty():
        return None
    from pkg_upgrade.ui.rich_onboarding import RichOnboardingUI  # noqa: PLC0415
    return RichOnboardingUI()
