from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from mac_upgrade.manager import PackageManager
from mac_upgrade.managers import ALL_MANAGERS
from mac_upgrade.models import Package, Result


SEQUENTIAL_CHAIN = ["brew", "cask", "pip"]
INDEPENDENT = ["npm", "gem", "system"]


@dataclass
class ManagerState:
    manager: PackageManager
    outdated: list[Package] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)
    status: str = "pending"
    error: str | None = None


@dataclass
class ExecutionGroup:
    managers: list[PackageManager]
    parallel: bool = True


OnUpdate = Callable[[str, ManagerState], Awaitable[None]]
OnResult = Callable[[str, Result], Awaitable[None]]


class Executor:
    def __init__(self, groups: list[ExecutionGroup]):
        self.groups = groups
        self.states: dict[str, ManagerState] = {
            m.key: ManagerState(manager=m) for m in self.all_managers()
        }

    @classmethod
    def default(cls) -> Executor:
        return cls.from_managers(ALL_MANAGERS)

    @classmethod
    def from_managers(cls, managers: list[PackageManager]) -> Executor:
        by_key = {m.key: m for m in managers}
        groups: list[ExecutionGroup] = []

        chain = [by_key[k] for k in SEQUENTIAL_CHAIN if k in by_key]
        if chain:
            groups.append(ExecutionGroup(managers=chain, parallel=False))

        independent = [by_key[k] for k in INDEPENDENT if k in by_key]
        if independent:
            groups.append(ExecutionGroup(managers=independent, parallel=True))

        known = set(SEQUENTIAL_CHAIN) | set(INDEPENDENT)
        extra = [m for m in managers if m.key not in known]
        if extra:
            groups.append(ExecutionGroup(managers=extra, parallel=True))

        return cls(groups)

    def all_managers(self) -> list[PackageManager]:
        result: list[PackageManager] = []
        for g in self.groups:
            result.extend(g.managers)
        return result

    async def check_all(self, on_update: OnUpdate | None = None) -> None:
        async def check_one(mgr: PackageManager) -> None:
            state = self.states[mgr.key]
            if not await mgr.is_available():
                state.status = "unavailable"
                if on_update:
                    await on_update(mgr.key, state)
                return
            state.status = "checking"
            if on_update:
                await on_update(mgr.key, state)
            try:
                state.outdated = await mgr.check_outdated()
            except Exception as exc:
                state.error = str(exc)
                state.status = "error"
                if on_update:
                    await on_update(mgr.key, state)
                return
            state.status = "awaiting_confirm" if state.outdated else "done"
            if on_update:
                await on_update(mgr.key, state)

        async def run_group(group: ExecutionGroup) -> None:
            if group.parallel:
                await asyncio.gather(*(check_one(m) for m in group.managers))
            else:
                for m in group.managers:
                    await check_one(m)

        await asyncio.gather(*(run_group(g) for g in self.groups))

    async def upgrade_manager(
        self,
        key: str,
        on_update: OnUpdate | None = None,
        on_result: OnResult | None = None,
    ) -> list[Result]:
        state = self.states[key]
        state.status = "upgrading"
        if on_update:
            await on_update(key, state)

        for pkg in state.outdated:
            result = await state.manager.upgrade(pkg)
            state.results.append(result)
            if on_result:
                await on_result(key, result)
            if on_update:
                await on_update(key, state)

        state.status = "done"
        if on_update:
            await on_update(key, state)
        return state.results

    def skip_manager(self, key: str) -> None:
        self.states[key].status = "skipped"
