from pkg_upgrade.models import Package, Result


def test_package_fields():
    pkg = Package(name="node", current_version="22.15", latest_version="22.16")
    assert pkg.name == "node"
    assert pkg.current_version == "22.15"
    assert pkg.latest_version == "22.16"


def test_package_str():
    pkg = Package(name="node", current_version="22.15", latest_version="22.16")
    assert str(pkg) == "node 22.15 -> 22.16"


def test_result_success():
    pkg = Package(name="node", current_version="22.15", latest_version="22.16")
    result = Result(success=True, message="Upgraded", package=pkg)
    assert result.success is True


def test_result_failure():
    pkg = Package(name="git", current_version="2.44", latest_version="2.45")
    result = Result(success=False, message="permission denied", package=pkg)
    assert result.success is False
