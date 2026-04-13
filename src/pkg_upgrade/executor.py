from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from pkg_upgrade.errors import ConfigurationError
from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.registry import discover_managers
from pkg_upgrade.status import ManagerStatus


@dataclass
class ManagerState:
    manager: PackageManager
    outdated: list[Package] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)
    status: ManagerStatus = ManagerStatus.PENDING
    error: str | None = None


@dataclass
class ExecutionGroup:
    managers: list[PackageManager]
    parallel: bool = True


OnUpdate = Callable[[str, ManagerState], Awaitable[None]]
OnResult = Callable[[str, Result], Awaitable[None]]


class Executor:
    def __init__(self, groups: list[ExecutionGroup]) -> None:
        self.groups = groups
        self.states: dict[str, ManagerState] = {
            m.key: ManagerState(manager=m) for m in self.all_managers()
        }
        self._sem: asyncio.Semaphore | None = None

    def set_max_parallel(self, n: int | None) -> None:
        """Cap per-level concurrency. Pass None to remove the limit."""
        self._sem = asyncio.Semaphore(n) if n is not None else None

    @classmethod
    def default(cls) -> Executor:
        return cls.from_managers(discover_managers())

    @classmethod
    def from_managers(cls, managers: list[PackageManager]) -> Executor:
        by_key = {m.key: m for m in managers}
        indegree: dict[str, int] = dict.fromkeys(by_key, 0)
        children: dict[str, list[str]] = {k: [] for k in by_key}

        for mgr in managers:
            for dep in mgr.depends_on:
                if dep not in by_key:
                    continue  # soft dep; silently drop
                indegree[mgr.key] += 1
                children[dep].append(mgr.key)

        groups: list[ExecutionGroup] = []
        ready = [k for k, d in indegree.items() if d == 0]
        placed = 0
        while ready:
            level = sorted(ready)
            groups.append(
                ExecutionGroup(
                    managers=[by_key[k] for k in level],
                    parallel=True,
                )
            )
            placed += len(level)
            next_ready: list[str] = []
            for k in level:
                for child in children[k]:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        next_ready.append(child)
            ready = next_ready

        if placed != len(by_key):
            remaining = [k for k, d in indegree.items() if d > 0]
            raise ConfigurationError(f"Dependency cycle among managers: {sorted(remaining)}")

        return cls(groups)

    def all_managers(self) -> list[PackageManager]:
        result: list[PackageManager] = []
        for g in self.groups:
            result.extend(g.managers)
        return result

    async def check_all(self, on_update: OnUpdate | None = None) -> None:
        async def check_one(mgr: PackageManager) -> None:
            async def _do() -> None:
                state = self.states[mgr.key]
                if not await mgr.is_available():
                    state.status = ManagerStatus.UNAVAILABLE
                    if on_update:
                        await on_update(mgr.key, state)
                    return
                state.status = ManagerStatus.CHECKING
                if on_update:
                    await on_update(mgr.key, state)
                try:
                    state.outdated = await mgr.check_outdated()
                except Exception as exc:
                    state.error = str(exc)
                    state.status = ManagerStatus.ERROR
                    if on_update:
                        await on_update(mgr.key, state)
                    return
                state.status = (
                    ManagerStatus.AWAITING_CONFIRM if state.outdated else ManagerStatus.DONE
                )
                if on_update:
                    await on_update(mgr.key, state)

            if self._sem is not None:
                async with self._sem:
                    await _do()
            else:
                await _do()

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
        async def _do() -> list[Result]:
            state = self.states[key]
            state.status = ManagerStatus.UPGRADING
            if on_update:
                await on_update(key, state)

            for pkg in state.outdated:
                result = await state.manager.upgrade(pkg)
                state.results.append(result)
                if on_result:
                    await on_result(key, result)
                if on_update:
                    await on_update(key, state)

            state.status = ManagerStatus.DONE
            if on_update:
                await on_update(key, state)
            return state.results

        if self._sem is not None:
            async with self._sem:
                return await _do()
        return await _do()

    def skip_manager(self, key: str) -> None:
        self.states[key].status = ManagerStatus.SKIPPED
