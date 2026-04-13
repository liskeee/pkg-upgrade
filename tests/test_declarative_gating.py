from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pkg_upgrade.declarative import DeclarativeManager, _Manifest


def _mk(requires_sudo: bool = False, requires_admin: bool = False) -> DeclarativeManager:
    manifest = _Manifest(
        name="Fake",
        key="fake",
        icon="🧪",
        platforms=frozenset({"linux"}),
        depends_on=(),
        install_hint="",
        requires_sudo=requires_sudo,
        requires_admin=requires_admin,
        check_cmd=["echo", "x"],
        check_parser="generic_regex",
        check_parser_kwargs={"regex": "(?P<name>.+)"},
        upgrade_cmd=["echo", "{name}"],
        upgrade_env={},
    )
    return DeclarativeManager(manifest)


async def test_is_available_false_without_sudo_credential() -> None:
    mgr = _mk(requires_sudo=True)
    with (
        patch(
            "pkg_upgrade.declarative.sudo_available_noninteractive",
            AsyncMock(return_value=False),
        ),
        patch("pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"),
    ):
        assert await mgr.is_available() is False


async def test_is_available_true_with_sudo_credential() -> None:
    mgr = _mk(requires_sudo=True)
    with (
        patch(
            "pkg_upgrade.declarative.sudo_available_noninteractive",
            AsyncMock(return_value=True),
        ),
        patch("pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"),
    ):
        assert await mgr.is_available() is True


async def test_is_available_false_without_admin_on_windows() -> None:
    mgr = _mk(requires_admin=True)
    with (
        patch("pkg_upgrade.declarative.is_windows_admin", return_value=False),
        patch("pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"),
    ):
        assert await mgr.is_available() is False


async def test_is_available_true_with_admin_on_windows() -> None:
    mgr = _mk(requires_admin=True)
    with (
        patch("pkg_upgrade.declarative.is_windows_admin", return_value=True),
        patch("pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"),
    ):
        assert await mgr.is_available() is True
