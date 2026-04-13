# tests/_ui_fakes.py
from __future__ import annotations

from collections.abc import Awaitable, Callable

from pkg_upgrade.status import ManagerStatus


class _FakeManager:
    def __init__(self, key: str, name: str, icon: str) -> None:
        self.key = key
        self.name = name
        self.icon = icon


class _FakeState:
    def __init__(self, manager: _FakeManager, outdated: list[str]) -> None:
        self.manager = manager
        self.outdated = list(outdated)
        self.results: list[tuple[str, bool]] = []
        self.status = ManagerStatus.PENDING
        self.error: str | None = None


class FakeExecutor:
    def __init__(self, states: dict[str, _FakeState]) -> None:
        self.states = states
        self.upgrade_calls = 0

    def all_managers(self) -> list[_FakeManager]:
        return [s.manager for s in self.states.values()]

    async def check_all(self, on_update: Callable[[str], Awaitable[None]] | None = None) -> None:
        for k, s in self.states.items():
            s.status = ManagerStatus.CHECKING
            if on_update:
                await on_update(k)
            s.status = ManagerStatus.AWAITING_CONFIRM if s.outdated else ManagerStatus.DONE
            if on_update:
                await on_update(k)

    async def upgrade_manager(
        self,
        key: str,
        on_update: Callable[[str], Awaitable[None]] | None = None,
        on_result: Callable[[str, str, bool], Awaitable[None]] | None = None,
    ) -> None:
        self.upgrade_calls += 1
        s = self.states[key]
        s.status = ManagerStatus.UPGRADING
        if on_update:
            await on_update(key)
        for pkg in s.outdated:
            s.results.append((pkg, True))
            if on_result:
                await on_result(key, pkg, True)
        s.status = ManagerStatus.DONE
        if on_update:
            await on_update(key)

    def skip_manager(self, key: str) -> None:
        self.states[key].status = ManagerStatus.SKIPPED

    def all_done(self) -> bool:
        from pkg_upgrade.status import ACTIVE_STATUSES  # noqa: PLC0415
        return all(s.status not in ACTIVE_STATUSES for s in self.states.values())


def canned_states_all_outdated() -> dict[str, _FakeState]:
    return {
        "brew": _FakeState(_FakeManager("brew", "Homebrew", "🍺"), ["wget", "jq"]),
        "pip": _FakeState(_FakeManager("pip", "pip", "🐍"), ["rich"]),
    }
