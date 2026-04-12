from pkg_upgrade.executor import ExecutionGroup, Executor
from pkg_upgrade.managers.brew import BrewManager
from pkg_upgrade.managers.gem import GemManager
from pkg_upgrade.managers.npm import NpmManager


def test_execution_group_fields():
    mgr = NpmManager()
    group = ExecutionGroup(managers=[mgr], parallel=False)
    assert group.parallel is False
    assert len(group.managers) == 1


def test_default_executor_builds_groups():
    executor = Executor.default()
    assert len(executor.groups) == 2
    assert any(not g.parallel for g in executor.groups)
    assert any(g.parallel for g in executor.groups)


def test_executor_subset_only_independent():
    executor = Executor.from_managers([NpmManager(), GemManager()])
    assert len(executor.groups) == 1
    assert executor.groups[0].parallel is True


def test_executor_subset_only_chain():
    executor = Executor.from_managers([BrewManager()])
    assert len(executor.groups) == 1
    assert executor.groups[0].parallel is False


def test_all_managers_flattens_groups():
    executor = Executor.default()
    assert len(executor.all_managers()) == 6
