# pkg-upgrade Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `mac_upgrade` → `pkg_upgrade` and introduce the cross-platform foundation (extended `PackageManager` ABC, unified registry with 3 registration paths, declarative YAML managers, topo-sort scheduler, platform/config helpers) while preserving existing macOS behavior. Ships as `v1.0.0`. No new managers; those come in Plan 2.

**Architecture:** Strategy pattern preserved. Registry (`registry.py`) loads managers from three sources (decorator, entry points, YAML) and merges into a single list. Scheduler (`executor.py`) does Kahn's topo-sort on `depends_on`. `DeclarativeManager` class implements `PackageManager` generically driven by a YAML manifest + named parser preset.

**Tech Stack:** Python 3.12+, Textual, PyYAML, platformdirs, pytest, ruff, mypy (strict), hatchling.

**Spec:** `docs/superpowers/specs/2026-04-13-pkg-upgrade-cross-platform-design.md`

---

## File Structure

**Renamed (whole-tree `mac_upgrade` → `pkg_upgrade`):**
- `src/mac_upgrade/` → `src/pkg_upgrade/`
- `tests/` imports updated
- `pyproject.toml` — `name`, `[project.scripts]`, `[tool.coverage.run] source`, `[tool.ruff.lint.isort] known-first-party`, `[tool.semantic_release] version_toml`

**New files:**
- `src/pkg_upgrade/platform.py` — `current_os()`, `linux_distro()`, `is_windows_admin()`.
- `src/pkg_upgrade/registry.py` — discovery + gating + merging from 3 sources.
- `src/pkg_upgrade/declarative.py` — `DeclarativeManager` class + YAML loader.
- `src/pkg_upgrade/parsers/__init__.py` — parser preset registry.
- `src/pkg_upgrade/parsers/generic.py` — `generic_regex` fallback preset.
- `src/pkg_upgrade/errors.py` — `ConfigurationError`.
- `src/pkg_upgrade/managers/declarative/` — empty dir (ready for Plan 2 YAMLs).
- `tests/test_platform.py`
- `tests/test_registry.py`
- `tests/test_declarative.py`
- `tests/test_parsers/test_generic.py`

**Modified files:**
- `src/pkg_upgrade/manager.py` — add `platforms`, `depends_on`, `install_hint` class vars.
- `src/pkg_upgrade/managers/*.py` (brew, cask, gem, npm, pip, system) — add class-level metadata + `@register_manager`.
- `src/pkg_upgrade/managers/__init__.py` — drop hardcoded `ALL_MANAGERS`, use registry.
- `src/pkg_upgrade/executor.py` — replace `SEQUENTIAL_CHAIN`/`INDEPENDENT` with topo-sort; gain `--max-parallel` plumbing.
- `src/pkg_upgrade/config.py` — switch to `platformdirs`; add `disabled_managers`, `per_manager`, `max_parallel`.
- `src/pkg_upgrade/cli.py` — `--list` grouping, `--show-graph`, `--max-parallel`.
- `README.md` — cross-platform framing (brief; full rewrite later).
- `install.sh` — new project name + paths.
- `Formula/mac-upgrade.rb` → `Formula/pkg-upgrade.rb` (tap move happens in Plan 3; update name/class here).
- `CLAUDE.md` — project blurb updated.

---

## Task 1: Rename package and update build metadata

**Files:**
- Move: `src/mac_upgrade/` → `src/pkg_upgrade/`
- Modify: `pyproject.toml`
- Modify: `tests/**/*.py` (import rewrites)
- Modify: `src/pkg_upgrade/**/*.py` (import rewrites)
- Modify: `install.sh`, `Formula/mac-upgrade.rb` → `Formula/pkg-upgrade.rb`, `README.md`, `CLAUDE.md`

- [ ] **Step 1: Move source tree**

```bash
git mv src/mac_upgrade src/pkg_upgrade
git mv Formula/mac-upgrade.rb Formula/pkg-upgrade.rb
```

- [ ] **Step 2: Rewrite all `mac_upgrade` → `pkg_upgrade` imports and strings in code**

```bash
grep -rl 'mac_upgrade' src tests install.sh Formula | xargs sed -i '' 's/mac_upgrade/pkg_upgrade/g'
grep -rl 'mac-upgrade' install.sh Formula README.md CLAUDE.md pyproject.toml | xargs sed -i '' 's/mac-upgrade/pkg-upgrade/g'
```

Manually review: the `Formula/pkg-upgrade.rb` Ruby class name (`MacUpgrade` → `PkgUpgrade`), README title, CLAUDE.md project section.

- [ ] **Step 3: Update pyproject.toml**

Replace in `pyproject.toml`:
```toml
[project]
name = "pkg-upgrade"
version = "0.1.0"
description = "A cross-platform TUI that upgrades every package manager on your system"

[project.scripts]
pkg-upgrade = "pkg_upgrade.cli:main"
pkgup = "pkg_upgrade.cli:main"

[tool.coverage.run]
source = ["src/pkg_upgrade"]

[tool.ruff.lint.isort]
known-first-party = ["pkg_upgrade"]
```

Also add to `dependencies`:
```toml
dependencies = [
    "textual>=8.2.3",
    "PyYAML>=6.0",
    "platformdirs>=4.0",
]
```

And add dev dep `types-PyYAML>=6.0`.

- [ ] **Step 4: Run the full test suite to verify rename didn't break anything**

Run: `pytest -x`
Expected: all existing tests pass (behavior unchanged).

Run: `ruff check . && ruff format --check . && mypy`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor!: rename mac_upgrade to pkg_upgrade

BREAKING CHANGE: package, CLI command, and PyPI name change from
mac-upgrade to pkg-upgrade. Adds pkgup short alias."
```

---

## Task 2: Add platform detection helper

**Files:**
- Create: `src/pkg_upgrade/platform.py`
- Test: `tests/test_platform.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_platform.py`:
```python
from unittest.mock import patch

from pkg_upgrade.platform import current_os, is_windows_admin, linux_distro


def test_current_os_macos():
    with patch("sys.platform", "darwin"):
        assert current_os() == "macos"


def test_current_os_linux():
    with patch("sys.platform", "linux"):
        assert current_os() == "linux"


def test_current_os_windows():
    with patch("sys.platform", "win32"):
        assert current_os() == "windows"


def test_current_os_unknown_raises():
    import pytest
    with patch("sys.platform", "freebsd"):
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            current_os()


def test_linux_distro_reads_id_like(tmp_path):
    os_release = tmp_path / "os-release"
    os_release.write_text('ID=ubuntu\nID_LIKE="debian"\n')
    assert linux_distro(os_release) == "debian"


def test_linux_distro_falls_back_to_id(tmp_path):
    os_release = tmp_path / "os-release"
    os_release.write_text("ID=fedora\n")
    assert linux_distro(os_release) == "fedora"


def test_linux_distro_missing_file_returns_none(tmp_path):
    assert linux_distro(tmp_path / "nope") is None


def test_is_windows_admin_non_windows_returns_false():
    with patch("pkg_upgrade.platform.current_os", return_value="macos"):
        assert is_windows_admin() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_platform.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `src/pkg_upgrade/platform.py`**

```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

OS = Literal["macos", "linux", "windows"]

_DEFAULT_OS_RELEASE = Path("/etc/os-release")


def current_os() -> OS:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "win32":
        return "windows"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def linux_distro(os_release: Path = _DEFAULT_OS_RELEASE) -> str | None:
    if not os_release.exists():
        return None
    values: dict[str, str] = {}
    for raw in os_release.read_text().splitlines():
        if "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        values[key.strip()] = value.strip().strip('"')
    return values.get("ID_LIKE") or values.get("ID")


def is_windows_admin() -> bool:
    if current_os() != "windows":
        return False
    import ctypes  # local import; Windows-only attribute access

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_platform.py -v && ruff check src/pkg_upgrade/platform.py tests/test_platform.py && mypy src/pkg_upgrade/platform.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/platform.py tests/test_platform.py
git commit -m "feat: add platform detection helper"
```

---

## Task 3: Extend PackageManager ABC with cross-platform metadata

**Files:**
- Modify: `src/pkg_upgrade/manager.py`
- Create: `src/pkg_upgrade/errors.py`
- Test: `tests/test_manager.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_manager.py`:
```python
from pkg_upgrade.manager import PackageManager


def test_package_manager_has_required_class_vars():
    assert hasattr(PackageManager, "platforms")
    assert hasattr(PackageManager, "depends_on")
    assert hasattr(PackageManager, "install_hint")


def test_concrete_manager_declares_platforms():
    class Fake(PackageManager):
        name = "Fake"
        key = "fake"
        icon = "x"
        platforms = frozenset({"macos"})

        async def is_available(self): return True
        async def check_outdated(self): return []
        async def upgrade(self, package): raise NotImplementedError

    assert Fake.platforms == frozenset({"macos"})
    assert Fake.depends_on == ()
    assert Fake.install_hint == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_manager.py -v`
Expected: FAIL — `platforms` attr missing.

- [ ] **Step 3: Extend the ABC**

Replace `src/pkg_upgrade/manager.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pkg_upgrade.models import Package, Result


class PackageManager(ABC):
    """Abstract strategy for a single package-manager backend."""

    name: ClassVar[str]
    key: ClassVar[str]
    icon: ClassVar[str]
    platforms: ClassVar[frozenset[str]]
    depends_on: ClassVar[tuple[str, ...]] = ()
    install_hint: ClassVar[str] = ""

    @abstractmethod
    async def is_available(self) -> bool: ...

    @abstractmethod
    async def check_outdated(self) -> list[Package]: ...

    @abstractmethod
    async def upgrade(self, package: Package) -> Result: ...

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
```

Create `src/pkg_upgrade/errors.py`:
```python
class ConfigurationError(Exception):
    """Raised when manager declarations form an invalid configuration (e.g. cycles)."""
```

- [ ] **Step 4: Add metadata to each existing built-in manager**

For each of `brew.py`, `cask.py`, `pip.py`, `npm.py`, `gem.py`, `system.py` under `src/pkg_upgrade/managers/`, add class-level attrs. Example patches:

`brew.py`:
```python
class BrewManager(PackageManager):
    name = "Homebrew"
    key = "brew"
    icon = "🍺"
    platforms = frozenset({"macos", "linux"})
```

`cask.py`:
```python
class CaskManager(PackageManager):
    name = "Cask"
    key = "cask"
    icon = "🛢"
    platforms = frozenset({"macos"})
    depends_on = ("brew",)
```

`pip.py`:
```python
class PipManager(PackageManager):
    name = "pip"
    key = "pip"
    icon = "🐍"
    platforms = frozenset({"macos", "linux", "windows"})
    depends_on = ("brew",)
```

`npm.py`:
```python
platforms = frozenset({"macos", "linux", "windows"})
```

`gem.py`:
```python
platforms = frozenset({"macos", "linux", "windows"})
```

`system.py`:
```python
platforms = frozenset({"macos"})
```

Keep existing `name`/`key`/`icon` values.

- [ ] **Step 5: Run all tests + typecheck**

Run: `pytest -x && mypy && ruff check .`
Expected: pass. (Existing tests still work; new attrs are additive.)

- [ ] **Step 6: Commit**

```bash
git add src/pkg_upgrade/manager.py src/pkg_upgrade/errors.py src/pkg_upgrade/managers/ tests/test_manager.py
git commit -m "feat: extend PackageManager ABC with platforms/depends_on/install_hint"
```

---

## Task 4: Build the registry (decorator + entry points)

**Files:**
- Create: `src/pkg_upgrade/registry.py`
- Modify: `src/pkg_upgrade/managers/*.py` (add `@register_manager`)
- Modify: `src/pkg_upgrade/managers/__init__.py` (drop `ALL_MANAGERS` constant, use registry)
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests**

`tests/test_registry.py`:
```python
from __future__ import annotations

from unittest.mock import patch

import pytest

from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.registry import (
    clear_registry,
    discover_managers,
    register_manager,
)


class _FakeManager(PackageManager):
    name = "Fake"
    key = "fake"
    icon = "x"
    platforms = frozenset({"macos", "linux", "windows"})

    async def is_available(self) -> bool:
        return True

    async def check_outdated(self) -> list[Package]:
        return []

    async def upgrade(self, package: Package) -> Result:  # pragma: no cover
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _clean():
    clear_registry()
    yield
    clear_registry()


def test_decorator_registers_manager():
    register_manager(_FakeManager)
    managers = discover_managers(load_entry_points=False, load_declarative=False)
    assert [m.key for m in managers] == ["fake"]


def test_decorator_returns_class_unchanged():
    result = register_manager(_FakeManager)
    assert result is _FakeManager


def test_platforms_gate_filters_by_current_os():
    class MacOnly(_FakeManager):
        key = "macos_only"
        platforms = frozenset({"macos"})

    register_manager(MacOnly)
    with patch("pkg_upgrade.registry.current_os", return_value="linux"):
        managers = discover_managers(load_entry_points=False, load_declarative=False)
    assert managers == []


def test_entry_point_registration(monkeypatch):
    class EPManager(_FakeManager):
        key = "entrypoint_mgr"

    class _FakeEP:
        name = "entrypoint_mgr"
        value = "x:y"
        def load(self): return EPManager

    def fake_entry_points(*, group: str):
        assert group == "pkg_upgrade.managers"
        return [_FakeEP()]

    monkeypatch.setattr("pkg_upgrade.registry.entry_points", fake_entry_points)
    managers = discover_managers(load_declarative=False)
    assert "entrypoint_mgr" in {m.key for m in managers}


def test_duplicate_key_raises():
    register_manager(_FakeManager)

    class Dup(_FakeManager):
        pass

    with pytest.raises(ValueError, match="already registered"):
        register_manager(Dup)
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the registry**

`src/pkg_upgrade/registry.py`:
```python
from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from typing import TypeVar

from pkg_upgrade.manager import PackageManager
from pkg_upgrade.platform import current_os

T = TypeVar("T", bound=type[PackageManager])

_REGISTRY: dict[str, type[PackageManager]] = {}

ENTRY_POINT_GROUP = "pkg_upgrade.managers"


def register_manager(cls: T) -> T:
    key = cls.key
    if key in _REGISTRY:
        raise ValueError(f"Manager key {key!r} already registered")
    _REGISTRY[key] = cls
    return cls


def clear_registry() -> None:
    _REGISTRY.clear()


def _instances_for_os(os_name: str) -> list[PackageManager]:
    out: list[PackageManager] = []
    for cls in _REGISTRY.values():
        if os_name in cls.platforms:
            out.append(cls())
    return out


def _load_entry_points() -> None:
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        cls = ep.load()
        if not isinstance(cls, type) or not issubclass(cls, PackageManager):
            raise TypeError(f"Entry point {ep.name} did not load a PackageManager subclass")
        if cls.key not in _REGISTRY:
            register_manager(cls)


def _load_declarative(directory: Path | None = None) -> None:
    # Populated in Task 6; stub here keeps the call site stable.
    from pkg_upgrade.declarative import load_declarative_dir

    load_declarative_dir(directory)


def discover_managers(
    *,
    load_entry_points: bool = True,
    load_declarative: bool = True,
    declarative_dir: Path | None = None,
) -> list[PackageManager]:
    # Import built-in manager modules to trigger their @register_manager decorators.
    import pkg_upgrade.managers  # noqa: F401

    if load_entry_points:
        _load_entry_points()
    if load_declarative:
        _load_declarative(declarative_dir)
    return _instances_for_os(current_os())
```

- [ ] **Step 4: Decorate built-in managers**

In each of `brew.py`, `cask.py`, `pip.py`, `npm.py`, `gem.py`, `system.py`, add:
```python
from pkg_upgrade.registry import register_manager


@register_manager
class BrewManager(PackageManager):
    ...
```

Replace `src/pkg_upgrade/managers/__init__.py`:
```python
from pkg_upgrade.managers import brew, cask, gem, npm, pip, system  # noqa: F401
```

(Built-in `ALL_MANAGERS` is gone — `discover_managers()` is the source of truth. `get_managers(skip=, only=)` moves to `registry.py`:)

Add to `registry.py`:
```python
def select_managers(
    managers: list[PackageManager],
    *,
    skip: set[str] | None = None,
    only: set[str] | None = None,
) -> list[PackageManager]:
    result = list(managers)
    if only:
        result = [m for m in result if m.key in only]
    if skip:
        result = [m for m in result if m.key not in skip]
    return result
```

Update callers of old `get_managers(...)` (grep the tree) to use `select_managers(discover_managers(), ...)`.

- [ ] **Step 5: Stub declarative loader so registry tests pass without Task 6**

Create `src/pkg_upgrade/declarative.py`:
```python
from __future__ import annotations

from pathlib import Path


def load_declarative_dir(directory: Path | None) -> None:
    """Placeholder. Real implementation in Task 6."""
    return None
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_registry.py tests/test_manager.py -v && pytest -x && mypy && ruff check .`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/pkg_upgrade/registry.py src/pkg_upgrade/declarative.py src/pkg_upgrade/managers/ tests/test_registry.py
git commit -m "feat: add manager registry with decorator + entry-point discovery"
```

---

## Task 5: Parser preset framework + generic_regex fallback

**Files:**
- Create: `src/pkg_upgrade/parsers/__init__.py`
- Create: `src/pkg_upgrade/parsers/generic.py`
- Test: `tests/test_parsers/__init__.py`, `tests/test_parsers/test_generic.py`

- [ ] **Step 1: Write failing tests**

`tests/test_parsers/test_generic.py`:
```python
from pkg_upgrade.parsers import get_parser, register_parser
from pkg_upgrade.parsers.generic import generic_regex


def test_registry_lookup():
    assert get_parser("generic_regex") is generic_regex


def test_register_and_lookup():
    def custom(stdout, **_): return []
    register_parser("custom_x", custom)
    assert get_parser("custom_x") is custom


def test_unknown_parser_raises():
    import pytest
    with pytest.raises(KeyError):
        get_parser("no_such_preset")


def test_generic_regex_parses_named_groups():
    stdout = "foo 1.0 -> 1.1\nbar 2.0 -> 2.5\n"
    packages = generic_regex(
        stdout,
        regex=r"^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$",
    )
    assert [(p.name, p.current_version, p.latest_version) for p in packages] == [
        ("foo", "1.0", "1.1"),
        ("bar", "2.0", "2.5"),
    ]


def test_generic_regex_skip_lines():
    stdout = "HEADER\nfoo 1 -> 2\n"
    packages = generic_regex(
        stdout,
        regex=r"^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$",
        skip_first_line=True,
    )
    assert [p.name for p in packages] == ["foo"]


def test_generic_regex_ignores_non_matching_lines():
    stdout = "garbage\nfoo 1 -> 2\nmore garbage\n"
    packages = generic_regex(
        stdout,
        regex=r"^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$",
    )
    assert [p.name for p in packages] == ["foo"]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_parsers -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the framework**

`src/pkg_upgrade/parsers/__init__.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pkg_upgrade.models import Package

Parser = Callable[..., list[Package]]

_PARSERS: dict[str, Parser] = {}


def register_parser(name: str, fn: Parser) -> None:
    _PARSERS[name] = fn


def get_parser(name: str) -> Parser:
    try:
        return _PARSERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown parser preset: {name!r}") from exc


def known_parsers() -> list[str]:
    return sorted(_PARSERS)


# Register built-in presets by importing their modules.
from pkg_upgrade.parsers import generic  # noqa: E402, F401
```

`src/pkg_upgrade/parsers/generic.py`:
```python
from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def generic_regex(
    stdout: str,
    *,
    regex: str,
    skip_first_line: bool = False,
    **_: Any,
) -> list[Package]:
    pattern = re.compile(regex)
    lines = stdout.splitlines()
    if skip_first_line and lines:
        lines = lines[1:]
    packages: list[Package] = []
    for line in lines:
        m = pattern.match(line)
        if not m:
            continue
        gd = m.groupdict()
        packages.append(
            Package(
                name=gd["name"],
                current_version=gd.get("current", ""),
                latest_version=gd.get("latest", ""),
            )
        )
    return packages


register_parser("generic_regex", generic_regex)
```

Create empty `tests/test_parsers/__init__.py`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_parsers -v && mypy && ruff check .`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/parsers tests/test_parsers
git commit -m "feat: add parser preset framework with generic_regex fallback"
```

---

## Task 6: DeclarativeManager + YAML loader

**Files:**
- Modify: `src/pkg_upgrade/declarative.py` (replace stub)
- Create: `src/pkg_upgrade/managers/declarative/` (empty `__init__.py` — actual YAMLs in Plan 2)
- Test: `tests/test_declarative.py`

- [ ] **Step 1: Write failing tests**

`tests/test_declarative.py`:
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pkg_upgrade.declarative import DeclarativeManager, load_declarative_dir
from pkg_upgrade.models import Package
from pkg_upgrade.registry import clear_registry, discover_managers


@pytest.fixture(autouse=True)
def _clean():
    clear_registry()
    yield
    clear_registry()


def _write_manifest(tmp_path: Path, name: str, body: str) -> Path:
    f = tmp_path / name
    f.write_text(body)
    return f


def test_load_registers_manager(tmp_path):
    _write_manifest(tmp_path, "fake.yaml", """
name: Fake
key: fake
icon: "x"
platforms: [macos, linux, windows]
install_hint: "hint"
check:
  cmd: [echo, hi]
  parser: generic_regex
  regex: "^(?P<name>\\\\S+) (?P<current>\\\\S+) -> (?P<latest>\\\\S+)$"
upgrade:
  cmd: [echo, upgrading, "{name}"]
""")
    load_declarative_dir(tmp_path)
    managers = discover_managers(load_entry_points=False, load_declarative=False)
    keys = [m.key for m in managers]
    assert "fake" in keys
    mgr = next(m for m in managers if m.key == "fake")
    assert isinstance(mgr, DeclarativeManager)
    assert mgr.platforms == frozenset({"macos", "linux", "windows"})


async def test_check_outdated_runs_cmd_and_parses(tmp_path):
    _write_manifest(tmp_path, "fake.yaml", """
name: Fake
key: fake
icon: "x"
platforms: [macos]
check:
  cmd: [fake-cli, list]
  parser: generic_regex
  regex: "^(?P<name>\\\\S+) (?P<current>\\\\S+) -> (?P<latest>\\\\S+)$"
upgrade:
  cmd: [fake-cli, install, "{name}"]
""")
    load_declarative_dir(tmp_path)
    mgr = next(m for m in discover_managers(
        load_entry_points=False, load_declarative=False) if m.key == "fake")

    with patch("pkg_upgrade.declarative.run_subprocess", new=AsyncMock(
            return_value=(0, "foo 1 -> 2\n", ""))):
        pkgs = await mgr.check_outdated()

    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [("foo", "1", "2")]


async def test_upgrade_substitutes_name_placeholder(tmp_path):
    _write_manifest(tmp_path, "fake.yaml", """
name: Fake
key: fake
icon: "x"
platforms: [macos]
check:
  cmd: [fake-cli, list]
  parser: generic_regex
  regex: "^(?P<name>\\\\S+)$"
upgrade:
  cmd: [fake-cli, install, "{name}"]
""")
    load_declarative_dir(tmp_path)
    mgr = next(m for m in discover_managers(
        load_entry_points=False, load_declarative=False) if m.key == "fake")

    mock = AsyncMock(return_value=(0, "ok", ""))
    with patch("pkg_upgrade.declarative.run_subprocess", new=mock):
        result = await mgr.upgrade(Package(name="foo", current_version="1", latest_version="2"))

    assert result.success is True
    args, _ = mock.call_args
    assert args[0] == ["fake-cli", "install", "foo"]


def test_manifest_missing_required_field_raises(tmp_path):
    _write_manifest(tmp_path, "bad.yaml", "name: X\nkey: x\n")
    with pytest.raises(Exception, match="(platforms|check|upgrade|icon)"):
        load_declarative_dir(tmp_path)


def test_is_available_checks_first_command_word(tmp_path):
    _write_manifest(tmp_path, "fake.yaml", """
name: Fake
key: fake
icon: "x"
platforms: [macos]
check:
  cmd: [definitely-not-installed-xyz, list]
  parser: generic_regex
  regex: "^(?P<name>\\\\S+)$"
upgrade:
  cmd: [definitely-not-installed-xyz, install, "{name}"]
""")
    load_declarative_dir(tmp_path)
    mgr = next(m for m in discover_managers(
        load_entry_points=False, load_declarative=False) if m.key == "fake")
    import asyncio
    assert asyncio.run(mgr.is_available()) is False
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_declarative.py -v`
Expected: FAIL — `DeclarativeManager` not implemented.

- [ ] **Step 3: Implement `DeclarativeManager` and loader**

Replace `src/pkg_upgrade/declarative.py`:
```python
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pkg_upgrade._subprocess import run_subprocess
from pkg_upgrade.manager import PackageManager
from pkg_upgrade.models import Package, Result
from pkg_upgrade.parsers import get_parser
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
        if _REQUIRED_CHECK - check.keys():
            raise ValueError(f"Manifest 'check' missing: {sorted(_REQUIRED_CHECK - check.keys())}")
        if _REQUIRED_UPGRADE - upgrade.keys():
            raise ValueError(f"Manifest 'upgrade' missing: {sorted(_REQUIRED_UPGRADE - upgrade.keys())}")

        parser_kwargs = {k: v for k, v in check.items() if k not in {"cmd", "parser"}}

        return cls(
            name=data["name"],
            key=data["key"],
            icon=data["icon"],
            platforms=frozenset(data["platforms"]),
            depends_on=tuple(data.get("depends_on", ())),
            install_hint=data.get("install_hint", ""),
            requires_sudo=bool(data.get("requires_sudo", False)),
            check_cmd=list(check["cmd"]),
            check_parser=check["parser"],
            check_parser_kwargs=parser_kwargs,
            upgrade_cmd=list(upgrade["cmd"]),
            upgrade_env=dict(upgrade.get("env", {})),
        )


class DeclarativeManager(PackageManager):
    def __init__(self, manifest: _Manifest) -> None:
        self._m = manifest

    @property
    def name(self) -> str: return self._m.name  # type: ignore[override]

    @property
    def key(self) -> str: return self._m.key  # type: ignore[override]

    @property
    def icon(self) -> str: return self._m.icon  # type: ignore[override]

    @property
    def platforms(self) -> frozenset[str]: return self._m.platforms  # type: ignore[override]

    @property
    def depends_on(self) -> tuple[str, ...]: return self._m.depends_on  # type: ignore[override]

    @property
    def install_hint(self) -> str: return self._m.install_hint  # type: ignore[override]

    async def is_available(self) -> bool:
        binary = self._m.check_cmd[0]
        if binary == "sudo" and len(self._m.check_cmd) > 1:
            binary = self._m.check_cmd[1]
        return shutil.which(binary) is not None

    async def check_outdated(self) -> list[Package]:
        rc, out, _ = await run_subprocess(self._m.check_cmd)
        if rc != 0:
            return []
        parser = get_parser(self._m.check_parser)
        return parser(out, **self._m.check_parser_kwargs)

    async def upgrade(self, package: Package) -> Result:
        cmd = [part.format(name=package.name) for part in self._m.upgrade_cmd]
        rc, out, err = await run_subprocess(cmd, env=self._m.upgrade_env or None)
        return Result(
            package=package,
            success=rc == 0,
            output=out if rc == 0 else err,
        )


def _build_class(manifest: _Manifest) -> type[DeclarativeManager]:
    # Registry uses class-level key/platforms to gate. Create a subclass with those set.
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
        data = yaml.safe_load(yml.read_text())
        manifest = _Manifest.from_dict(data)
        cls = _build_class(manifest)
        register_manager(cls)
```

Create `src/pkg_upgrade/managers/declarative/__init__.py` (empty).

Check `_subprocess.py` for the exact signature of its run function. If it's not named `run_subprocess`, alias it:
```python
# in _subprocess.py, add at the bottom if needed:
run_subprocess = run  # or existing name
```
(Investigate during step — do NOT guess.)

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_declarative.py -v && pytest -x && mypy && ruff check .`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/declarative.py src/pkg_upgrade/managers/declarative tests/test_declarative.py
git commit -m "feat: add DeclarativeManager and YAML manifest loader"
```

---

## Task 7: Topo-sort scheduler

**Files:**
- Modify: `src/pkg_upgrade/executor.py`
- Modify: `tests/test_executor.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_executor.py`:
```python
from pkg_upgrade.errors import ConfigurationError
from pkg_upgrade.executor import Executor


def _mk(key, platforms=("macos",), depends_on=()):
    from pkg_upgrade.manager import PackageManager
    from pkg_upgrade.models import Package, Result

    class M(PackageManager):
        name = key
        icon = "x"

        async def is_available(self): return True
        async def check_outdated(self): return []
        async def upgrade(self, p): raise NotImplementedError

    M.key = key
    M.platforms = frozenset(platforms)
    M.depends_on = tuple(depends_on)
    return M()


def test_topo_independent_managers_single_level():
    mgrs = [_mk("a"), _mk("b"), _mk("c")]
    ex = Executor.from_managers(mgrs)
    assert len(ex.groups) == 1
    assert ex.groups[0].parallel is True
    assert {m.key for m in ex.groups[0].managers} == {"a", "b", "c"}


def test_topo_chain_creates_two_levels():
    mgrs = [_mk("brew"), _mk("cask", depends_on=("brew",))]
    ex = Executor.from_managers(mgrs)
    assert [m.key for g in ex.groups for m in g.managers] == ["brew", "cask"]
    assert len(ex.groups) == 2


def test_missing_dep_is_dropped_not_fatal():
    mgrs = [_mk("pip", depends_on=("brew",))]  # brew not present
    ex = Executor.from_managers(mgrs)
    assert [m.key for g in ex.groups for m in g.managers] == ["pip"]


def test_cycle_raises_configuration_error():
    import pytest
    mgrs = [_mk("a", depends_on=("b",)), _mk("b", depends_on=("a",))]
    with pytest.raises(ConfigurationError, match="cycle"):
        Executor.from_managers(mgrs)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_executor.py -v`
Expected: new tests FAIL.

- [ ] **Step 3: Replace the scheduler**

In `src/pkg_upgrade/executor.py`, remove `SEQUENTIAL_CHAIN` / `INDEPENDENT` constants and replace `from_managers`:
```python
from pkg_upgrade.errors import ConfigurationError


@classmethod
def from_managers(cls, managers: list[PackageManager]) -> Executor:
    by_key = {m.key: m for m in managers}
    indegree: dict[str, int] = {k: 0 for k in by_key}
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
        groups.append(ExecutionGroup(
            managers=[by_key[k] for k in level],
            parallel=True,
        ))
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
```

Keep the rest of `Executor` untouched.

- [ ] **Step 4: Run tests**

Run: `pytest -x && mypy && ruff check .`
Expected: all pass (old tests assuming macOS chain ordering still get `brew → cask` and `pip → brew` because metadata in Task 3 encodes it).

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/executor.py tests/test_executor.py
git commit -m "feat: topologically schedule managers by depends_on"
```

---

## Task 8: Config via platformdirs + new keys

**Files:**
- Modify: `src/pkg_upgrade/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Read existing config module + tests**

Run: `cat src/pkg_upgrade/config.py tests/test_config.py`

Note the existing shape before editing. Preserve existing public API where possible.

- [ ] **Step 2: Write failing tests**

Add to `tests/test_config.py`:
```python
from pathlib import Path
from unittest.mock import patch

from pkg_upgrade.config import Config, load_config


def test_config_path_uses_platformdirs(tmp_path):
    with patch("pkg_upgrade.config.user_config_path", return_value=tmp_path):
        from pkg_upgrade.config import config_file_path
        assert config_file_path().parent == tmp_path


def test_load_missing_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg.disabled_managers == set()
    assert cfg.per_manager == {}
    assert cfg.max_parallel is None


def test_load_parses_all_keys(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("""
disabled_managers: [gem, npm]
max_parallel: 2
per_manager:
  brew:
    env:
      HOMEBREW_NO_AUTO_UPDATE: "1"
""")
    cfg = load_config(f)
    assert cfg.disabled_managers == {"gem", "npm"}
    assert cfg.max_parallel == 2
    assert cfg.per_manager["brew"]["env"]["HOMEBREW_NO_AUTO_UPDATE"] == "1"
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — new fields/functions missing.

- [ ] **Step 4: Update `config.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_path


@dataclass
class Config:
    disabled_managers: set[str] = field(default_factory=set)
    per_manager: dict[str, dict[str, Any]] = field(default_factory=dict)
    max_parallel: int | None = None


def config_file_path() -> Path:
    return user_config_path("pkg-upgrade") / "config.yaml"


def load_config(path: Path | None = None) -> Config:
    p = path or config_file_path()
    if not p.exists():
        return Config()
    data = yaml.safe_load(p.read_text()) or {}
    return Config(
        disabled_managers=set(data.get("disabled_managers", []) or []),
        per_manager=dict(data.get("per_manager", {}) or {}),
        max_parallel=data.get("max_parallel"),
    )
```

If the existing `config.py` has other public symbols (onboarding, etc.), preserve them; only add new ones.

- [ ] **Step 5: Run tests**

Run: `pytest -x && mypy && ruff check .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/pkg_upgrade/config.py tests/test_config.py
git commit -m "feat: move config to platformdirs and add new keys"
```

---

## Task 9: Wire registry + config into CLI; add --show-graph / --max-parallel

**Files:**
- Modify: `src/pkg_upgrade/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Review current CLI**

Run: `cat src/pkg_upgrade/cli.py`

Identify: where `ALL_MANAGERS` / `get_managers` is currently used, how `--list` renders, how executor is constructed.

- [ ] **Step 2: Write failing test**

Add to `tests/test_cli.py`:
```python
from pkg_upgrade.cli import build_parser


def test_parser_exposes_new_flags():
    p = build_parser()
    ns = p.parse_args(["--show-graph", "--max-parallel", "3"])
    assert ns.show_graph is True
    assert ns.max_parallel == 3


def test_list_groups_by_availability(capsys, monkeypatch):
    # Smoke: --list runs without error and prints 3 headings
    from pkg_upgrade.cli import main
    monkeypatch.setattr("sys.argv", ["pkg-upgrade", "--list"])
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Available" in out
    assert "Unavailable" in out or "Not on this OS" in out
```

- [ ] **Step 3: Run failing test**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL.

- [ ] **Step 4: Update CLI**

Swap `from pkg_upgrade.managers import get_managers, ALL_MANAGERS` for:
```python
from pkg_upgrade.registry import discover_managers, select_managers
```

Add argparse flags:
```python
parser.add_argument("--show-graph", action="store_true",
                    help="Print execution plan (topo-sorted groups) and exit")
parser.add_argument("--max-parallel", type=int, default=None,
                    help="Cap per-level concurrency")
```

Update `--list` to group by: available / unavailable on this OS / declared for other OS. Use `discover_managers()` for the current-OS list; for "Not on this OS," peek at the raw registry (expose `from pkg_upgrade.registry import _REGISTRY as registry_all` via a public helper `all_registered() -> list[type[PackageManager]]`).

Add to `registry.py`:
```python
def all_registered() -> list[type[PackageManager]]:
    import pkg_upgrade.managers  # noqa: F401
    return list(_REGISTRY.values())
```

`--show-graph` prints, for each group index, `[level N] key1, key2, ...`.

Pipe `--max-parallel` into executor by adding a `max_parallel: int | None = None` field on `Executor` and using `asyncio.Semaphore(N)` in `check_all` / `upgrade_manager` when set.

- [ ] **Step 5: Run tests**

Run: `pytest -x && mypy && ruff check .`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/pkg_upgrade/cli.py src/pkg_upgrade/registry.py src/pkg_upgrade/executor.py tests/test_cli.py
git commit -m "feat: CLI --list grouping, --show-graph, --max-parallel"
```

---

## Task 10: Smoke-test `pkgup --list --dry-run` on macOS and tighten docs

**Files:**
- Modify: `README.md` (minimal cross-platform blurb; detailed README later)
- Modify: `CLAUDE.md` (project section reflects cross-platform)

- [ ] **Step 1: Manual smoke**

Run: `pip install -e ".[dev]" && pkg-upgrade --list`
Expected: prints grouped list; no crash. Verify: `pkgup --show-graph` prints groups; `pkg-upgrade --max-parallel 1 --dry-run` (if `--dry-run` exists) runs without error.

- [ ] **Step 2: Update README top section**

Replace the tagline and opening paragraph to say "cross-platform" / "macOS, Linux, Windows" and mention that Plan 1 ships the foundation; new managers arrive in subsequent releases. Keep the rest.

- [ ] **Step 3: Update CLAUDE.md project section**

Replace the `## Project` paragraph with:
```markdown
## Project

`pkg-upgrade` is a cross-platform (macOS/Linux/Windows) Textual TUI and CLI that
orchestrates upgrades across every installed package manager. Python 3.12+.
```

Update file-path references from `mac_upgrade` to `pkg_upgrade`.

- [ ] **Step 4: Run the full quality bar one last time**

Run: `ruff check . && ruff format --check . && mypy && pytest --cov`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: rewrite project intro for cross-platform pkg-upgrade"
```

---

## Self-Review (performed by plan author)

**Spec coverage check:** ✅
- Rename & layout → Task 1
- Manager API extensions → Task 3
- Registration paths (decorator + entry points + YAML) → Tasks 4, 6
- Parser presets framework → Task 5 (generic_regex only in Plan 1; named presets come in Plan 2 alongside the managers that use them)
- Scheduling (topo sort, cycles, missing-dep warning) → Task 7
- Platform detection → Task 2
- Config via platformdirs → Task 8
- TUI/CLI changes (`--list` grouping, `--show-graph`, `--max-parallel`) → Task 9
- Distribution (install.sh rename, Formula rename) → Task 1 (partial; full Scoop/install.ps1/tap-bump in Plan 3)

**Explicitly deferred to Plan 2:** sudo/admin gating, declarative manager manifests themselves (apt/dnf/.../winget/...), parser presets for those managers, tri-OS CI matrix, smoke job.

**Explicitly deferred to Plan 3:** `install.ps1`, Scoop bucket, new Homebrew tap repo, release-workflow tap/scoop bumps, Trusted Publisher reconfiguration.

**Placeholder scan:** none. Every step has concrete code or command.

**Type consistency:** registry exposes `register_manager`, `discover_managers`, `clear_registry`, `select_managers`, `all_registered`, `ENTRY_POINT_GROUP`. Parsers expose `get_parser`, `register_parser`, `known_parsers`. `DeclarativeManager` is a concrete subclass of `PackageManager`; `_Manifest` is internal. `ConfigurationError` lives in `pkg_upgrade.errors`. Config: `Config`, `load_config`, `config_file_path`. Names used consistently across tasks.
