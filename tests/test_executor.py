import pytest

from pkg_upgrade.errors import ConfigurationError
from pkg_upgrade.executor import ExecutionGroup, Executor
from pkg_upgrade.manager import PackageManager
from pkg_upgrade.managers.brew import BrewManager
from pkg_upgrade.managers.cask import CaskManager
from pkg_upgrade.managers.gem import GemManager
from pkg_upgrade.managers.npm import NpmManager
from pkg_upgrade.managers.pip import PipManager
from pkg_upgrade.managers.system import SystemManager


def test_execution_group_fields():
    mgr = NpmManager()
    group = ExecutionGroup(managers=[mgr], parallel=False)
    assert group.parallel is False
    assert len(group.managers) == 1


def test_default_executor_builds_groups():
    # Use explicit manager list so the test is OS-agnostic (Executor.default() filters by OS).
    executor = Executor.from_managers(
        [BrewManager(), CaskManager(), PipManager(), NpmManager(), GemManager(), SystemManager()]
    )
    # brew/npm/gem/system have no deps → level 0; cask/pip depend on brew → level 1
    assert len(executor.groups) == 2
    assert all(g.parallel for g in executor.groups)


def test_executor_subset_only_independent():
    executor = Executor.from_managers([NpmManager(), GemManager()])
    assert len(executor.groups) == 1
    assert executor.groups[0].parallel is True


def test_executor_subset_only_chain():
    executor = Executor.from_managers([BrewManager()])
    assert len(executor.groups) == 1
    # topo sort always produces parallel=True groups; ordering is enforced by level separation
    assert executor.groups[0].parallel is True


def test_all_managers_flattens_groups():
    executor = Executor.default()
    # 6 built-in managers (brew, cask, pip, npm, gem, system) + 1 declarative (mas on macOS)
    assert len(executor.all_managers()) >= 6


def _mk(
    key: str, platforms: tuple[str, ...] = ("macos",), depends_on: tuple[str, ...] = ()
) -> PackageManager:
    class M(PackageManager):
        name = key
        icon = "x"

        async def is_available(self) -> bool:
            return True

        async def check_outdated(self) -> list[object]:  # type: ignore[override]
            return []

        async def upgrade(self, p: object) -> object:  # type: ignore[override]
            raise NotImplementedError

    M.key = key
    M.platforms = frozenset(platforms)
    M.depends_on = depends_on
    return M()


def test_topo_independent_managers_single_level() -> None:
    mgrs = [_mk("a"), _mk("b"), _mk("c")]
    ex = Executor.from_managers(mgrs)
    assert len(ex.groups) == 1
    assert ex.groups[0].parallel is True
    assert {m.key for m in ex.groups[0].managers} == {"a", "b", "c"}


def test_topo_chain_creates_two_levels() -> None:
    mgrs = [_mk("brew"), _mk("cask", depends_on=("brew",))]
    ex = Executor.from_managers(mgrs)
    assert [m.key for g in ex.groups for m in g.managers] == ["brew", "cask"]
    assert len(ex.groups) == 2


def test_missing_dep_is_dropped_not_fatal() -> None:
    mgrs = [_mk("pip", depends_on=("brew",))]  # brew not present
    ex = Executor.from_managers(mgrs)
    assert [m.key for g in ex.groups for m in g.managers] == ["pip"]


def test_cycle_raises_configuration_error() -> None:
    mgrs = [_mk("a", depends_on=("b",)), _mk("b", depends_on=("a",))]
    with pytest.raises(ConfigurationError, match="cycle"):
        Executor.from_managers(mgrs)
