from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import yaml

from pkg_upgrade._subprocess import run_command as run_subprocess
from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.parsers import get_parser
from pkg_upgrade.platform import is_windows_admin, sudo_available_noninteractive
from pkg_upgrade.registry import register_manager

_REQUIRED_TOP = {"name", "key", "icon", "platforms", "check", "upgrade"}
_REQUIRED_CHECK = {"cmd", "parser"}
_REQUIRED_UPGRADE = {"cmd"}


@dataclass(frozen=True)
class _Manifest:
    name: str
    key: str
    icon: str
    platforms: frozenset[str]
    depends_on: tuple[str, ...]
    install_hint: str
    requires_sudo: bool
    requires_admin: bool
    check_cmd: list[str]
    check_parser: str
    check_parser_kwargs: dict[str, Any]
    upgrade_cmd: list[str]
    upgrade_env: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> _Manifest:
        missing = _REQUIRED_TOP - data.keys()
        if missing:
            raise ValueError(f"Manifest missing fields: {sorted(missing)}")
        check = data["check"]
        upgrade = data["upgrade"]
        miss_c = _REQUIRED_CHECK - check.keys()
        if miss_c:
            raise ValueError(f"Manifest 'check' missing: {sorted(miss_c)}")
        miss_u = _REQUIRED_UPGRADE - upgrade.keys()
        if miss_u:
            raise ValueError(f"Manifest 'upgrade' missing: {sorted(miss_u)}")
        parser_kwargs = {k: v for k, v in check.items() if k not in {"cmd", "parser"}}
        return cls(
            name=data["name"],
            key=data["key"],
            icon=data["icon"],
            platforms=frozenset(data["platforms"]),
            depends_on=tuple(data.get("depends_on", ())),
            install_hint=data.get("install_hint", ""),
            requires_sudo=bool(data.get("requires_sudo", False)),
            requires_admin=bool(data.get("requires_admin", False)),
            check_cmd=list(check["cmd"]),
            check_parser=check["parser"],
            check_parser_kwargs=parser_kwargs,
            upgrade_cmd=list(upgrade["cmd"]),
            upgrade_env=dict(upgrade.get("env", {})),
        )


class DeclarativeManager(PackageManager):
    """A PackageManager driven entirely by a YAML manifest."""

    name: ClassVar[str] = ""
    key: ClassVar[str] = ""
    icon: ClassVar[str] = ""
    platforms: ClassVar[frozenset[str]] = frozenset()
    depends_on: ClassVar[tuple[str, ...]] = ()
    install_hint: ClassVar[str] = ""

    def __init__(self, manifest: _Manifest) -> None:
        self._m = manifest

    async def is_available(self) -> bool:
        binary = self._m.check_cmd[0]
        if binary == "sudo" and len(self._m.check_cmd) > 1:
            binary = self._m.check_cmd[1]
        if shutil.which(binary) is None:
            return False
        if self._m.requires_sudo and not await sudo_available_noninteractive():
            return False
        return not self._m.requires_admin or is_windows_admin()

    async def check_outdated(self) -> list[Package]:
        rc, out, _ = await run_subprocess(self._m.check_cmd)
        if rc != 0:
            return []
        parser = get_parser(self._m.check_parser)
        return parser(out, **self._m.check_parser_kwargs)

    async def upgrade(self, package: Package) -> Result:
        cmd = [part.format(name=package.name) for part in self._m.upgrade_cmd]
        if self._m.upgrade_env:
            rc, out, err = await run_subprocess(cmd, env=self._m.upgrade_env)
        else:
            rc, out, err = await run_subprocess(cmd)
        return Result(
            package=package,
            success=rc == 0,
            message=out if rc == 0 else err,
        )


def _build_class(manifest: _Manifest) -> type[DeclarativeManager]:
    attrs: dict[str, Any] = {
        "name": manifest.name,
        "key": manifest.key,
        "icon": manifest.icon,
        "platforms": manifest.platforms,
        "depends_on": manifest.depends_on,
        "install_hint": manifest.install_hint,
        "__init__": lambda self, _m=manifest: DeclarativeManager.__init__(self, _m),
    }
    return type(f"Declarative_{manifest.key}", (DeclarativeManager,), attrs)


def load_declarative_dir(directory: Path | None) -> None:
    if directory is None:
        directory = Path(__file__).parent / "managers" / "declarative"
    if not directory.exists():
        return
    for yml in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        manifest = _Manifest.from_dict(data)
        cls = _build_class(manifest)
        register_manager(cls)
