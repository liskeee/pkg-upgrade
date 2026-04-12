# mac-upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI app with a Textual TUI dashboard that upgrades all macOS package managers (brew, cask, pip, npm, gem, softwareupdate) with smart parallel execution, per-manager confirmation, and beautiful progress display.

**Architecture:** Python package using `textual` for the TUI. Each package manager is a separate module implementing a common async ABC. An executor orchestrates parallel groups. CLI uses `argparse`. Notifications via `osascript`. Logging to file via stdlib.

**Tech Stack:** Python 3.14, textual, asyncio, subprocess, argparse, dataclasses, shutil, logging

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Project metadata, dependencies, entry point |
| `src/mac_upgrade/__init__.py` | Package version |
| `src/mac_upgrade/models.py` | `Package` and `Result` dataclasses |
| `src/mac_upgrade/manager.py` | `PackageManager` ABC |
| `src/mac_upgrade/managers/__init__.py` | Registry of all managers |
| `src/mac_upgrade/managers/brew.py` | Homebrew formulas manager |
| `src/mac_upgrade/managers/cask.py` | Homebrew casks manager |
| `src/mac_upgrade/managers/pip.py` | pip3 manager |
| `src/mac_upgrade/managers/npm.py` | npm global packages manager |
| `src/mac_upgrade/managers/gem.py` | gem manager |
| `src/mac_upgrade/managers/system.py` | softwareupdate manager |
| `src/mac_upgrade/executor.py` | Parallel group execution engine |
| `src/mac_upgrade/notifier.py` | macOS notification + log file writer |
| `src/mac_upgrade/cli.py` | argparse CLI entry point |
| `src/mac_upgrade/app.py` | Textual app, dashboard screen, summary screen |
| `src/mac_upgrade/widgets.py` | Custom Textual widgets |
| `tests/conftest.py` | Shared fixtures |
| `tests/test_models.py` | Tests for dataclasses |
| `tests/test_manager.py` | Tests for the ABC contract |
| `tests/test_managers/test_*.py` | Per-manager tests |
| `tests/test_executor.py` | Tests for execution engine |
| `tests/test_notifier.py` | Tests for notification + logging |
| `tests/test_cli.py` | Tests for CLI argument parsing |

---

## Notes On Subprocess Usage

All subprocess calls use `asyncio.create_subprocess_exec` (argv array, no shell) — NOT shell execution. Arguments are passed as a list to avoid shell injection. This is the safe equivalent of `execFile`.

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/mac_upgrade/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mac-upgrade"
version = "0.1.0"
description = "A beautiful TUI dashboard to upgrade all macOS package managers"
requires-python = ">=3.12"
dependencies = [
    "textual>=3.0.0",
]

[project.scripts]
mac-upgrade = "mac_upgrade.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
```

- [ ] **Step 2: Create `src/mac_upgrade/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Install the project in editable mode with dev deps**

Run: `cd /Users/liskeee/Projects/Liskeee/mac-upgrade && pip3 install -e ".[dev]"`
Expected: Successful installation.

- [ ] **Step 4: Verify pytest works**

Run: `cd /Users/liskeee/Projects/Liskeee/mac-upgrade && python3 -m pytest --version`
Expected: Shows pytest version

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/mac_upgrade/__init__.py
git commit -m "feat: project scaffolding"
```

---

### Task 2: Data Models

**Files:**
- Create: `src/mac_upgrade/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
from mac_upgrade.models import Package, Result


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_models.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/models.py`:

```python
from dataclasses import dataclass


@dataclass
class Package:
    name: str
    current_version: str
    latest_version: str

    def __str__(self) -> str:
        return f"{self.name} {self.current_version} -> {self.latest_version}"


@dataclass
class Result:
    success: bool
    message: str
    package: Package
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/models.py tests/test_models.py
git commit -m "feat: add Package and Result data models"
```

---

### Task 3: PackageManager ABC and Fake Fixture

**Files:**
- Create: `src/mac_upgrade/manager.py`
- Create: `tests/conftest.py`
- Create: `tests/test_manager.py`

- [ ] **Step 1: Write the failing test**

Create `tests/conftest.py`:

```python
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class FakeManager(PackageManager):
    name = "Fake"
    key = "fake"
    icon = "🧪"

    def __init__(self, available: bool = True, outdated: list[Package] | None = None):
        self._available = available
        self._outdated = outdated or []

    async def is_available(self) -> bool:
        return self._available

    async def check_outdated(self) -> list[Package]:
        return self._outdated

    async def upgrade(self, package: Package) -> Result:
        return Result(success=True, message="ok", package=package)

    async def upgrade_all(self) -> list[Result]:
        return [await self.upgrade(p) for p in self._outdated]
```

Create `tests/test_manager.py`:

```python
import pytest
from tests.conftest import FakeManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_fake_manager_is_available():
    mgr = FakeManager(available=True)
    assert await mgr.is_available() is True


@pytest.mark.asyncio
async def test_fake_manager_not_available():
    mgr = FakeManager(available=False)
    assert await mgr.is_available() is False


@pytest.mark.asyncio
async def test_check_outdated_empty():
    mgr = FakeManager()
    assert await mgr.check_outdated() == []


@pytest.mark.asyncio
async def test_check_outdated_returns_packages():
    pkgs = [Package("node", "22.15", "22.16")]
    mgr = FakeManager(outdated=pkgs)
    result = await mgr.check_outdated()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_upgrade_all():
    pkgs = [Package("node", "22.15", "22.16"), Package("git", "2.44", "2.45")]
    mgr = FakeManager(outdated=pkgs)
    results = await mgr.upgrade_all()
    assert len(results) == 2
    assert all(r.success for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_manager.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/manager.py`:

```python
from abc import ABC, abstractmethod

from mac_upgrade.models import Package, Result


class PackageManager(ABC):
    name: str
    key: str
    icon: str

    @abstractmethod
    async def is_available(self) -> bool: ...

    @abstractmethod
    async def check_outdated(self) -> list[Package]: ...

    @abstractmethod
    async def upgrade(self, package: Package) -> Result: ...

    @abstractmethod
    async def upgrade_all(self) -> list[Result]: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_manager.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/manager.py tests/conftest.py tests/test_manager.py
git commit -m "feat: add PackageManager ABC and fake fixture"
```

---

### Task 4: Subprocess Helper

**Files:**
- Create: `src/mac_upgrade/_subprocess.py`
- Create: `tests/test_subprocess.py`

This helper wraps `asyncio.create_subprocess_exec` so all managers share one implementation. Argv is always a list — never a shell string.

- [ ] **Step 1: Write the failing test**

Create `tests/test_subprocess.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from mac_upgrade._subprocess import run_command


@pytest.mark.asyncio
async def test_run_command_success():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"hello", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        code, stdout, stderr = await run_command(["echo", "hello"])

    assert code == 0
    assert stdout == "hello"
    assert stderr == ""


@pytest.mark.asyncio
async def test_run_command_failure():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"error")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        code, stdout, stderr = await run_command(["false"])

    assert code == 1
    assert stderr == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_subprocess.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/_subprocess.py`:

```python
import asyncio


async def run_command(argv: list[str]) -> tuple[int, str, str]:
    """Run a command safely (no shell). Returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_subprocess.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/_subprocess.py tests/test_subprocess.py
git commit -m "feat: add shared subprocess helper"
```

---

### Task 5: Homebrew Formulas Manager

**Files:**
- Create: `src/mac_upgrade/managers/__init__.py` (empty stub)
- Create: `src/mac_upgrade/managers/brew.py`
- Create: `tests/test_managers/__init__.py` (empty)
- Create: `tests/test_managers/test_brew.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_managers/__init__.py` (empty file).

Create `tests/test_managers/test_brew.py`:

```python
import json
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.brew import BrewManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available_when_brew_exists():
    with patch("shutil.which", return_value="/opt/homebrew/bin/brew"):
        assert await BrewManager().is_available() is True


@pytest.mark.asyncio
async def test_is_available_when_brew_missing():
    with patch("shutil.which", return_value=None):
        assert await BrewManager().is_available() is False


@pytest.mark.asyncio
async def test_check_outdated_parses_json():
    brew_output = json.dumps({
        "formulae": [
            {"name": "node", "installed_versions": ["22.15"], "current_version": "22.16"},
            {"name": "git", "installed_versions": ["2.44"], "current_version": "2.45"},
        ]
    })
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(0, brew_output, ""))):
        packages = await BrewManager().check_outdated()
    assert len(packages) == 2
    assert packages[0].name == "node"


@pytest.mark.asyncio
async def test_check_outdated_empty():
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(0, '{"formulae": []}', ""))):
        assert await BrewManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("node", "22.15", "22.16")
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(0, "Upgraded", ""))):
        result = await BrewManager().upgrade(pkg)
    assert result.success is True


@pytest.mark.asyncio
async def test_upgrade_failure():
    pkg = Package("git", "2.44", "2.45")
    with patch("mac_upgrade.managers.brew.run_command",
               new=AsyncMock(return_value=(1, "", "permission denied"))):
        result = await BrewManager().upgrade(pkg)
    assert result.success is False
    assert "permission denied" in result.message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_managers/test_brew.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/managers/__init__.py` (empty file).

Create `src/mac_upgrade/managers/brew.py`:

```python
import json
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class BrewManager(PackageManager):
    name = "Homebrew Formulas"
    key = "brew"
    icon = "🍺"

    async def is_available(self) -> bool:
        return shutil.which("brew") is not None

    async def check_outdated(self) -> list[Package]:
        code, stdout, _ = await run_command(["brew", "outdated", "--json=v2"])
        if code != 0 or not stdout.strip():
            return []
        data = json.loads(stdout)
        return [
            Package(
                name=f["name"],
                current_version=f["installed_versions"][0],
                latest_version=f["current_version"],
            )
            for f in data.get("formulae", [])
        ]

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(["brew", "upgrade", package.name])
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_managers/test_brew.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/managers/ tests/test_managers/
git commit -m "feat: add Homebrew formulas manager"
```

---

### Task 6: Homebrew Casks Manager

**Files:**
- Create: `src/mac_upgrade/managers/cask.py`
- Create: `tests/test_managers/test_cask.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_managers/test_cask.py`:

```python
import json
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.cask import CaskManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/opt/homebrew/bin/brew"):
        assert await CaskManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_casks():
    brew_output = json.dumps({
        "casks": [
            {"name": "firefox", "installed_versions": "130.0", "current_version": "131.0"},
        ]
    })
    with patch("mac_upgrade.managers.cask.run_command",
               new=AsyncMock(return_value=(0, brew_output, ""))):
        packages = await CaskManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "firefox"


@pytest.mark.asyncio
async def test_upgrade_cask_success():
    pkg = Package("firefox", "130.0", "131.0")
    with patch("mac_upgrade.managers.cask.run_command",
               new=AsyncMock(return_value=(0, "Upgraded", ""))):
        result = await CaskManager().upgrade(pkg)
    assert result.success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_managers/test_cask.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/managers/cask.py`:

```python
import json
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class CaskManager(PackageManager):
    name = "Homebrew Casks"
    key = "cask"
    icon = "🍻"

    async def is_available(self) -> bool:
        return shutil.which("brew") is not None

    async def check_outdated(self) -> list[Package]:
        code, stdout, _ = await run_command(["brew", "outdated", "--json=v2"])
        if code != 0 or not stdout.strip():
            return []
        data = json.loads(stdout)
        return [
            Package(
                name=c["name"],
                current_version=c["installed_versions"],
                latest_version=c["current_version"],
            )
            for c in data.get("casks", [])
        ]

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(
            ["brew", "upgrade", "--cask", package.name]
        )
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_managers/test_cask.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/managers/cask.py tests/test_managers/test_cask.py
git commit -m "feat: add Homebrew casks manager"
```

---

### Task 7: pip Manager

**Files:**
- Create: `src/mac_upgrade/managers/pip.py`
- Create: `tests/test_managers/test_pip.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_managers/test_pip.py`:

```python
import json
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.pip import PipManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/opt/homebrew/bin/pip3"):
        assert await PipManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_json():
    pip_output = json.dumps([
        {"name": "requests", "version": "2.31.0", "latest_version": "2.32.0"},
    ])
    with patch("mac_upgrade.managers.pip.run_command",
               new=AsyncMock(return_value=(0, pip_output, ""))):
        packages = await PipManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "requests"


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("requests", "2.31.0", "2.32.0")
    with patch("mac_upgrade.managers.pip.run_command",
               new=AsyncMock(return_value=(0, "Installed", ""))):
        result = await PipManager().upgrade(pkg)
    assert result.success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_managers/test_pip.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/managers/pip.py`:

```python
import json
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class PipManager(PackageManager):
    name = "pip"
    key = "pip"
    icon = "🐍"

    async def is_available(self) -> bool:
        return shutil.which("pip3") is not None

    async def check_outdated(self) -> list[Package]:
        code, stdout, _ = await run_command(
            ["pip3", "list", "--outdated", "--format=json"]
        )
        if code != 0 or not stdout.strip():
            return []
        data = json.loads(stdout)
        return [
            Package(
                name=item["name"],
                current_version=item["version"],
                latest_version=item["latest_version"],
            )
            for item in data
        ]

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(
            ["pip3", "install", "--upgrade", package.name]
        )
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_managers/test_pip.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/managers/pip.py tests/test_managers/test_pip.py
git commit -m "feat: add pip manager"
```

---

### Task 8: npm Manager

**Files:**
- Create: `src/mac_upgrade/managers/npm.py`
- Create: `tests/test_managers/test_npm.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_managers/test_npm.py`:

```python
import json
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.npm import NpmManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/usr/local/bin/npm"):
        assert await NpmManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_json():
    npm_output = json.dumps({
        "eslint": {"current": "9.1.0", "wanted": "9.2.0", "latest": "9.2.0"},
    })
    with patch("mac_upgrade.managers.npm.run_command",
               new=AsyncMock(return_value=(1, npm_output, ""))):
        packages = await NpmManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "eslint"


@pytest.mark.asyncio
async def test_check_outdated_empty():
    with patch("mac_upgrade.managers.npm.run_command",
               new=AsyncMock(return_value=(0, "", ""))):
        assert await NpmManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("eslint", "9.1.0", "9.2.0")
    with patch("mac_upgrade.managers.npm.run_command",
               new=AsyncMock(return_value=(0, "updated", ""))):
        result = await NpmManager().upgrade(pkg)
    assert result.success is True
```

Note: `npm outdated` returns exit code 1 when there ARE outdated packages, so we must not treat non-zero as failure for the check step.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_managers/test_npm.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/managers/npm.py`:

```python
import json
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


class NpmManager(PackageManager):
    name = "npm"
    key = "npm"
    icon = "📦"

    async def is_available(self) -> bool:
        return shutil.which("npm") is not None

    async def check_outdated(self) -> list[Package]:
        # npm outdated exits 1 when there are outdated packages — ignore exit code
        _, stdout, _ = await run_command(
            ["npm", "outdated", "--global", "--json"]
        )
        if not stdout.strip():
            return []
        data = json.loads(stdout)
        return [
            Package(
                name=name,
                current_version=info.get("current", "unknown"),
                latest_version=info["latest"],
            )
            for name, info in data.items()
        ]

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(
            ["npm", "install", "-g", f"{package.name}@latest"]
        )
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_managers/test_npm.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/managers/npm.py tests/test_managers/test_npm.py
git commit -m "feat: add npm manager"
```

---

### Task 9: gem Manager

**Files:**
- Create: `src/mac_upgrade/managers/gem.py`
- Create: `tests/test_managers/test_gem.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_managers/test_gem.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.gem import GemManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/usr/bin/gem"):
        assert await GemManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_output():
    gem_output = "nokogiri (1.16.0 < 1.16.5)\nrake (13.1.0 < 13.2.0)\n"
    with patch("mac_upgrade.managers.gem.run_command",
               new=AsyncMock(return_value=(0, gem_output, ""))):
        packages = await GemManager().check_outdated()
    assert len(packages) == 2
    assert packages[0].name == "nokogiri"
    assert packages[0].current_version == "1.16.0"
    assert packages[0].latest_version == "1.16.5"


@pytest.mark.asyncio
async def test_check_outdated_empty():
    with patch("mac_upgrade.managers.gem.run_command",
               new=AsyncMock(return_value=(0, "", ""))):
        assert await GemManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("nokogiri", "1.16.0", "1.16.5")
    with patch("mac_upgrade.managers.gem.run_command",
               new=AsyncMock(return_value=(0, "Installed", ""))):
        result = await GemManager().upgrade(pkg)
    assert result.success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_managers/test_gem.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/managers/gem.py`:

```python
import re
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


GEM_LINE_RE = re.compile(r"^(\S+)\s+\((\S+)\s+<\s+(\S+)\)$")


class GemManager(PackageManager):
    name = "gem"
    key = "gem"
    icon = "💎"

    async def is_available(self) -> bool:
        return shutil.which("gem") is not None

    async def check_outdated(self) -> list[Package]:
        code, stdout, _ = await run_command(["gem", "outdated"])
        if code != 0 or not stdout.strip():
            return []
        packages = []
        for line in stdout.splitlines():
            m = GEM_LINE_RE.match(line.strip())
            if m:
                packages.append(Package(
                    name=m.group(1),
                    current_version=m.group(2),
                    latest_version=m.group(3),
                ))
        return packages

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(["gem", "update", package.name])
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_managers/test_gem.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/managers/gem.py tests/test_managers/test_gem.py
git commit -m "feat: add gem manager"
```

---

### Task 10: softwareupdate (System) Manager

**Files:**
- Create: `src/mac_upgrade/managers/system.py`
- Create: `tests/test_managers/test_system.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_managers/test_system.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.managers.system import SystemManager
from mac_upgrade.models import Package


@pytest.mark.asyncio
async def test_is_available():
    with patch("shutil.which", return_value="/usr/sbin/softwareupdate"):
        assert await SystemManager().is_available() is True


@pytest.mark.asyncio
async def test_check_outdated_parses_output():
    output = (
        "Software Update found the following new or updated software:\n"
        "* Label: Safari18.5-18.5\n"
        "\tTitle: Safari 18.5, Version: 18.5, Size: 200000KiB, Recommended: YES,\n"
    )
    with patch("mac_upgrade.managers.system.run_command",
               new=AsyncMock(return_value=(0, output, ""))):
        packages = await SystemManager().check_outdated()
    assert len(packages) == 1
    assert packages[0].name == "Safari18.5-18.5"
    assert packages[0].latest_version == "18.5"


@pytest.mark.asyncio
async def test_check_outdated_no_updates():
    with patch("mac_upgrade.managers.system.run_command",
               new=AsyncMock(return_value=(0, "No new software available.\n", ""))):
        assert await SystemManager().check_outdated() == []


@pytest.mark.asyncio
async def test_upgrade_success():
    pkg = Package("Safari18.5-18.5", "installed", "18.5")
    with patch("mac_upgrade.managers.system.run_command",
               new=AsyncMock(return_value=(0, "Done", ""))):
        result = await SystemManager().upgrade(pkg)
    assert result.success is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_managers/test_system.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

Create `src/mac_upgrade/managers/system.py`:

```python
import re
import shutil

from mac_upgrade._subprocess import run_command
from mac_upgrade.manager import PackageManager
from mac_upgrade.models import Package, Result


LABEL_RE = re.compile(r"^\* Label:\s+(.+)$")
VERSION_RE = re.compile(r"^\s+Title:\s+.+,\s+Version:\s+([^,]+),")


class SystemManager(PackageManager):
    name = "System Updates"
    key = "system"
    icon = "🍎"

    async def is_available(self) -> bool:
        return shutil.which("softwareupdate") is not None

    async def check_outdated(self) -> list[Package]:
        # softwareupdate writes output to stderr on some macOS versions
        code, stdout, stderr = await run_command(["softwareupdate", "--list"])
        output = stdout + stderr
        if "No new software available" in output:
            return []
        packages: list[Package] = []
        current_label: str | None = None
        for line in output.splitlines():
            lm = LABEL_RE.match(line)
            if lm:
                current_label = lm.group(1).strip()
                continue
            vm = VERSION_RE.match(line)
            if vm and current_label:
                packages.append(Package(
                    name=current_label,
                    current_version="installed",
                    latest_version=vm.group(1).strip(),
                ))
                current_label = None
        return packages

    async def upgrade(self, package: Package) -> Result:
        code, stdout, stderr = await run_command(
            ["softwareupdate", "--install", package.name]
        )
        if code == 0:
            return Result(success=True, message=stdout.strip(), package=package)
        return Result(success=False, message=stderr.strip(), package=package)

    async def upgrade_all(self) -> list[Result]:
        packages = await self.check_outdated()
        return [await self.upgrade(p) for p in packages]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_managers/test_system.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/managers/system.py tests/test_managers/test_system.py
git commit -m "feat: add softwareupdate system manager"
```

---

### Task 11: Manager Registry

**Files:**
- Modify: `src/mac_upgrade/managers/__init__.py`
- Modify: `tests/test_manager.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_manager.py`:

```python
from mac_upgrade.managers import ALL_MANAGERS, get_managers


def test_all_managers_contains_six():
    assert len(ALL_MANAGERS) == 6


def test_all_managers_keys_unique():
    keys = [m.key for m in ALL_MANAGERS]
    assert len(keys) == len(set(keys))


def test_get_managers_skip():
    managers = get_managers(skip={"brew", "pip"})
    keys = {m.key for m in managers}
    assert "brew" not in keys and "pip" not in keys
    assert "npm" in keys


def test_get_managers_only():
    managers = get_managers(only={"npm", "gem"})
    keys = {m.key for m in managers}
    assert keys == {"npm", "gem"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_manager.py -v`
Expected: 4 new tests FAIL with ImportError

- [ ] **Step 3: Write implementation**

Rewrite `src/mac_upgrade/managers/__init__.py`:

```python
from mac_upgrade.manager import PackageManager
from mac_upgrade.managers.brew import BrewManager
from mac_upgrade.managers.cask import CaskManager
from mac_upgrade.managers.pip import PipManager
from mac_upgrade.managers.npm import NpmManager
from mac_upgrade.managers.gem import GemManager
from mac_upgrade.managers.system import SystemManager


ALL_MANAGERS: list[PackageManager] = [
    BrewManager(),
    CaskManager(),
    PipManager(),
    NpmManager(),
    GemManager(),
    SystemManager(),
]


def get_managers(
    skip: set[str] | None = None,
    only: set[str] | None = None,
) -> list[PackageManager]:
    managers = list(ALL_MANAGERS)
    if only:
        managers = [m for m in managers if m.key in only]
    if skip:
        managers = [m for m in managers if m.key not in skip]
    return managers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_manager.py -v`
Expected: 9 passed (5 existing + 4 new)

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/managers/__init__.py tests/test_manager.py
git commit -m "feat: add manager registry with skip/only filtering"
```

---

### Task 12: Execution Engine

**Files:**
- Create: `src/mac_upgrade/executor.py`
- Create: `tests/test_executor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_executor.py`:

```python
import pytest
from mac_upgrade.executor import Executor, ExecutionGroup
from mac_upgrade.managers.npm import NpmManager
from mac_upgrade.managers.gem import GemManager
from mac_upgrade.managers.brew import BrewManager


def test_execution_group_fields():
    mgr = NpmManager()
    group = ExecutionGroup(managers=[mgr], parallel=False)
    assert group.parallel is False
    assert len(group.managers) == 1


def test_default_executor_builds_groups():
    executor = Executor.default()
    # Expect a sequential group (brew/cask/pip) and a parallel group (npm/gem/system)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_executor.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write implementation**

Create `src/mac_upgrade/executor.py`:

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from mac_upgrade.manager import PackageManager
from mac_upgrade.managers import ALL_MANAGERS
from mac_upgrade.models import Package, Result


# Keys that must run in a sequential chain due to dependency conflicts
SEQUENTIAL_CHAIN = ["brew", "cask", "pip"]
# Keys that are independent of each other and of the chain
INDEPENDENT = ["npm", "gem", "system"]


@dataclass
class ManagerState:
    manager: PackageManager
    outdated: list[Package] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)
    # status: pending | checking | awaiting_confirm | upgrading | done | skipped | unavailable
    status: str = "pending"


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
            state.outdated = await mgr.check_outdated()
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_executor.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/executor.py tests/test_executor.py
git commit -m "feat: add execution engine with smart parallel grouping"
```

---

### Task 13: Notifier (log file + macOS notification)

**Files:**
- Create: `src/mac_upgrade/notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_notifier.py`:

```python
import re
import pytest
from unittest.mock import patch, AsyncMock
from mac_upgrade.notifier import Notifier


def test_log_writes_to_file(tmp_path):
    log = tmp_path / "test.log"
    n = Notifier(log_path=str(log))
    n.log("brew", "Upgrading node")
    content = log.read_text()
    assert "brew" in content
    assert "Upgrading node" in content


def test_log_has_timestamp(tmp_path):
    log = tmp_path / "test.log"
    n = Notifier(log_path=str(log))
    n.log("npm", "message")
    assert re.search(r"\d{2}:\d{2}:\d{2}", log.read_text())


def test_log_disabled_when_none():
    n = Notifier(log_path=None)
    n.log("brew", "test")  # should not raise


def test_log_appends(tmp_path):
    log = tmp_path / "test.log"
    n = Notifier(log_path=str(log))
    n.log("brew", "first")
    n.log("npm", "second")
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_notification_sends():
    n = Notifier(log_path=None, notify=True)
    with patch("mac_upgrade.notifier.run_command",
               new=AsyncMock(return_value=(0, "", ""))) as mock_run:
        await n.send_notification("title", "body")
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_notification_suppressed():
    n = Notifier(log_path=None, notify=False)
    with patch("mac_upgrade.notifier.run_command",
               new=AsyncMock(return_value=(0, "", ""))) as mock_run:
        await n.send_notification("title", "body")
        mock_run.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_notifier.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write implementation**

Create `src/mac_upgrade/notifier.py`:

```python
from datetime import datetime
from pathlib import Path

from mac_upgrade._subprocess import run_command


class Notifier:
    def __init__(self, log_path: str | None, notify: bool = True):
        self.log_path = log_path
        self.notify = notify
        if self.log_path:
            Path(self.log_path).touch()

    def log(self, manager_key: str, message: str) -> None:
        if not self.log_path:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts}  {manager_key:8s}  {message}\n"
        with open(self.log_path, "a") as f:
            f.write(line)

    async def send_notification(self, title: str, body: str) -> None:
        if not self.notify:
            return
        # Escape double quotes for AppleScript
        safe_title = title.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        script = f'display notification "{safe_body}" with title "{safe_title}"'
        await run_command(["osascript", "-e", script])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_notifier.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/notifier.py tests/test_notifier.py
git commit -m "feat: add notifier with logging and macOS notifications"
```

---

### Task 14: CLI Argument Parsing

**Files:**
- Create: `src/mac_upgrade/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
from mac_upgrade.cli import parse_args, get_log_path


def test_default_args():
    args = parse_args([])
    assert args.skip is None
    assert args.only is None
    assert args.yes is False
    assert args.dry_run is False
    assert args.no_notify is False
    assert args.no_log is False
    assert args.log_dir is None
    assert args.list_managers is False


def test_skip_flag():
    assert parse_args(["--skip", "brew,pip"]).skip == {"brew", "pip"}


def test_only_flag():
    assert parse_args(["--only", "npm,gem"]).only == {"npm", "gem"}


def test_yes_flag():
    assert parse_args(["--yes"]).yes is True
    assert parse_args(["-y"]).yes is True


def test_dry_run():
    assert parse_args(["--dry-run"]).dry_run is True


def test_no_notify_no_log():
    args = parse_args(["--no-notify", "--no-log"])
    assert args.no_notify is True
    assert args.no_log is True


def test_log_dir():
    assert parse_args(["--log-dir", "/tmp/logs"]).log_dir == "/tmp/logs"


def test_list_flag():
    assert parse_args(["--list"]).list_managers is True


def test_get_log_path_disabled():
    args = parse_args(["--no-log"])
    assert get_log_path(args) is None


def test_get_log_path_default(tmp_path):
    args = parse_args(["--log-dir", str(tmp_path)])
    path = get_log_path(args)
    assert path is not None
    assert str(tmp_path) in path
    assert path.endswith(".log")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write implementation**

Create `src/mac_upgrade/cli.py`:

```python
import argparse
from datetime import date
from pathlib import Path

from mac_upgrade import __version__


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mac-upgrade",
        description="Upgrade all macOS package managers with a beautiful TUI dashboard",
    )
    parser.add_argument(
        "--skip",
        type=lambda s: set(s.split(",")),
        default=None,
        metavar="MANAGERS",
        help="Comma-separated managers to skip (e.g. --skip brew,pip)",
    )
    parser.add_argument(
        "--only",
        type=lambda s: set(s.split(",")),
        default=None,
        metavar="MANAGERS",
        help="Only run these managers (e.g. --only npm,gem)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmations, upgrade everything automatically",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be upgraded without doing anything",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Suppress macOS notification on completion",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Skip writing log file",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        metavar="PATH",
        help="Custom log directory (default: ~/)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_managers",
        help="List all detected managers and their status, then exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mac-upgrade {__version__}",
    )
    return parser.parse_args(argv)


def get_log_path(args: argparse.Namespace) -> str | None:
    if args.no_log:
        return None
    log_dir = Path(args.log_dir) if args.log_dir else Path.home()
    today = date.today().isoformat()
    return str(log_dir / f"mac-upgrade-{today}.log")


def main() -> None:
    args = parse_args()
    from mac_upgrade.app import MacUpgradeApp

    app = MacUpgradeApp(
        skip=args.skip,
        only=args.only,
        auto_yes=args.yes,
        dry_run=args.dry_run,
        notify=not args.no_notify,
        log_path=get_log_path(args),
        list_only=args.list_managers,
    )
    app.run()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add src/mac_upgrade/cli.py tests/test_cli.py
git commit -m "feat: add CLI argument parsing"
```

---

### Task 15: Custom Textual Widgets

**Files:**
- Create: `src/mac_upgrade/widgets.py`

Textual widget visuals are best validated in the running app (Task 17). We keep the widget module focused and simple.

- [ ] **Step 1: Create widgets**

Create `src/mac_upgrade/widgets.py`:

```python
from datetime import datetime

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, RichLog


class ManagerCard(Widget):
    """Displays a single package manager's status, progress, and results."""

    DEFAULT_CSS = """
    ManagerCard {
        height: 3;
        padding: 0 1;
        layout: horizontal;
        border-bottom: solid $primary-darken-2;
    }
    ManagerCard .icon-name {
        width: 26;
    }
    ManagerCard .status-area {
        width: 1fr;
    }
    ManagerCard .pkg-count {
        width: 12;
        text-align: right;
    }
    ManagerCard.-highlight {
        background: $primary-background;
    }
    """

    status: reactive[str] = reactive("pending")
    upgraded: reactive[int] = reactive(0)
    total: reactive[int] = reactive(0)
    failed: reactive[int] = reactive(0)

    def __init__(self, icon: str, manager_name: str, manager_key: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.icon = icon
        self.manager_name = manager_name
        self.manager_key = manager_key

    def compose(self) -> ComposeResult:
        yield Label(f"{self.icon} {self.manager_name}", classes="icon-name")
        yield Label("", id="status-label", classes="status-area")
        yield Label("", id="count-label", classes="pkg-count")

    def _refresh_labels(self) -> None:
        status_label = self.query_one("#status-label", Label)
        count_label = self.query_one("#count-label", Label)

        if self.status == "pending":
            status_label.update("⏳ pending")
            count_label.update("")
        elif self.status == "checking":
            status_label.update("🔍 checking...")
            count_label.update("")
        elif self.status == "awaiting_confirm":
            status_label.update(
                f"📋 {self.total} update{'s' if self.total != 1 else ''} found — [Enter] confirm / [S] skip"
            )
            count_label.update("")
        elif self.status == "upgrading":
            status_label.update("⬆️  upgrading...")
            count_label.update(f"{self.upgraded}/{self.total}")
        elif self.status == "done":
            if self.failed > 0:
                status_label.update(f"✅ {self.upgraded} upgraded, ❌ {self.failed} failed")
            elif self.total == 0:
                status_label.update("━━ no updates")
            else:
                status_label.update(f"✅ {self.upgraded} upgraded")
            count_label.update("")
        elif self.status == "skipped":
            status_label.update("⏭  skipped")
            count_label.update("")
        elif self.status == "unavailable":
            status_label.update("⚠️  not installed")
            count_label.update("")

    def watch_status(self, _value: str) -> None:
        if self.is_mounted:
            self._refresh_labels()

    def watch_upgraded(self, _value: int) -> None:
        if self.is_mounted:
            self._refresh_labels()

    def watch_total(self, _value: int) -> None:
        if self.is_mounted:
            self._refresh_labels()

    def watch_failed(self, _value: int) -> None:
        if self.is_mounted:
            self._refresh_labels()


class LiveLogPanel(Widget):
    """Scrollable log of timestamped events."""

    DEFAULT_CSS = """
    LiveLogPanel {
        height: 1fr;
        border-top: solid $primary;
    }
    LiveLogPanel RichLog {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True, wrap=True, id="live-log")

    def add_line(self, manager_key: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        log = self.query_one("#live-log", RichLog)
        log.write(f"[dim]{ts}[/dim]  [bold cyan]{manager_key:8s}[/bold cyan]  {message}")
```

- [ ] **Step 2: Commit**

```bash
git add src/mac_upgrade/widgets.py
git commit -m "feat: add ManagerCard and LiveLogPanel widgets"
```

---

### Task 16: Main Textual App

**Files:**
- Create: `src/mac_upgrade/app.py`

- [ ] **Step 1: Create the main app**

Create `src/mac_upgrade/app.py`:

```python
from __future__ import annotations

import time
from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from mac_upgrade.executor import Executor, ManagerState
from mac_upgrade.managers import get_managers
from mac_upgrade.models import Result
from mac_upgrade.notifier import Notifier
from mac_upgrade.widgets import LiveLogPanel, ManagerCard


class MacUpgradeApp(App):
    """TUI dashboard for upgrading macOS packages."""

    TITLE = "mac-upgrade"
    CSS = """
    #header-bar {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    #managers-container {
        height: auto;
        max-height: 60%;
        padding: 1 0;
    }
    #footer-help {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("enter", "confirm", "Confirm", show=True),
        Binding("s", "skip", "Skip", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("r", "retry", "Retry", show=False),
    ]

    def __init__(
        self,
        skip: set[str] | None = None,
        only: set[str] | None = None,
        auto_yes: bool = False,
        dry_run: bool = False,
        notify: bool = True,
        log_path: str | None = None,
        list_only: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        managers = get_managers(skip=skip, only=only)
        self.executor = Executor.from_managers(managers)
        self.auto_yes = auto_yes
        self.dry_run = dry_run
        self.notifier = Notifier(log_path=log_path, notify=notify)
        self.list_only = list_only
        self.cards: dict[str, ManagerCard] = {}
        self._confirm_queue: list[str] = []
        self._current_confirm: str | None = None
        self._start_time: float = 0.0
        self._phase = "checking"

    def compose(self) -> ComposeResult:
        today = date.today().strftime("%d %b %Y")
        yield Static(f"🚀 mac-upgrade                                           {today}", id="header-bar")
        with VerticalScroll(id="managers-container"):
            for mgr in self.executor.all_managers():
                card = ManagerCard(
                    icon=mgr.icon,
                    manager_name=mgr.name,
                    manager_key=mgr.key,
                    id=f"card-{mgr.key}",
                )
                self.cards[mgr.key] = card
                yield card
        yield LiveLogPanel(id="log-panel")
        yield Static("[Enter] Confirm  [S] Skip  [Q] Quit", id="footer-help")

    async def on_mount(self) -> None:
        self._start_time = time.monotonic()
        if self.list_only:
            self.run_worker(self._list_and_exit())
            return
        self.run_worker(self._run_check_phase())

    async def _list_and_exit(self) -> None:
        for mgr in self.executor.all_managers():
            available = await mgr.is_available()
            self.cards[mgr.key].status = "done" if available else "unavailable"
            self._log(mgr.key, "Available" if available else "Not installed")
        self.set_timer(1.5, self.exit)

    async def _run_check_phase(self) -> None:
        async def on_update(key: str, state: ManagerState) -> None:
            card = self.cards[key]
            card.total = len(state.outdated)
            card.status = state.status
            if state.status == "checking":
                self._log(key, "Checking for updates...")
            elif state.status == "awaiting_confirm":
                count = len(state.outdated)
                self._log(key, f"Found {count} outdated package{'s' if count != 1 else ''}")
                for pkg in state.outdated:
                    self._log(key, f"  {pkg}")
                if self.dry_run:
                    self.executor.skip_manager(key)
                    card.status = "done"
                    self._log(key, "Dry run — no changes made")
                    await self._maybe_finish()
                elif self.auto_yes:
                    self.run_worker(self._run_upgrade(key))
                else:
                    self._confirm_queue.append(key)
                    self._advance_confirm()
            elif state.status == "unavailable":
                self._log(key, "Not installed — skipping")
            elif state.status == "done" and not state.outdated:
                self._log(key, "All packages up to date")

        await self.executor.check_all(on_update=on_update)
        self._phase = "confirming"
        await self._maybe_finish()

    def _advance_confirm(self) -> None:
        if self._current_confirm is not None:
            return
        if not self._confirm_queue:
            return
        key = self._confirm_queue.pop(0)
        self._current_confirm = key
        self.cards[key].add_class("-highlight")

    async def _run_upgrade(self, key: str) -> None:
        async def on_update(k: str, state: ManagerState) -> None:
            c = self.cards[k]
            c.total = len(state.outdated)
            c.upgraded = sum(1 for r in state.results if r.success)
            c.failed = sum(1 for r in state.results if not r.success)
            c.status = state.status

        async def on_result(k: str, result: Result) -> None:
            if result.success:
                self._log(k, f"✓ Upgraded {result.package}")
            else:
                self._log(k, f"✗ Failed {result.package.name}: {result.message}")

        self._log(key, "Starting upgrades...")
        await self.executor.upgrade_manager(
            key, on_update=on_update, on_result=on_result,
        )
        await self._maybe_finish()

    async def action_confirm(self) -> None:
        if self._current_confirm is None:
            return
        key = self._current_confirm
        self.cards[key].remove_class("-highlight")
        self._current_confirm = None
        self.run_worker(self._run_upgrade(key))
        self._advance_confirm()

    async def action_skip(self) -> None:
        if self._current_confirm is None:
            return
        key = self._current_confirm
        self.executor.skip_manager(key)
        self.cards[key].remove_class("-highlight")
        self.cards[key].status = "skipped"
        self._log(key, "Skipped by user")
        self._current_confirm = None
        self._advance_confirm()
        await self._maybe_finish()

    def action_quit_app(self) -> None:
        self.exit()

    async def action_retry(self) -> None:
        # For now: quit on retry (future enhancement)
        self.exit()

    async def _maybe_finish(self) -> None:
        # Finish once no manager is still active
        active_statuses = {"pending", "checking", "awaiting_confirm", "upgrading"}
        if self._current_confirm is not None:
            return
        if self._confirm_queue:
            return
        for state in self.executor.states.values():
            if state.status in active_statuses:
                return
        await self._finish()

    async def _finish(self) -> None:
        if self._phase == "summary":
            return
        self._phase = "summary"

        elapsed = time.monotonic() - self._start_time
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        duration = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
        self._log("done", f"Completed in {duration}")

        total_upgraded = sum(
            1
            for s in self.executor.states.values()
            for r in s.results
            if r.success
        )
        total_failed = sum(
            1
            for s in self.executor.states.values()
            for r in s.results
            if not r.success
        )
        total_skipped = sum(
            1 for s in self.executor.states.values() if s.status == "skipped"
        )

        summary = f"{total_upgraded} upgraded"
        if total_failed:
            summary += f", {total_failed} failed"
        if total_skipped:
            summary += f", {total_skipped} skipped"

        title = (
            "mac-upgrade complete"
            if total_failed == 0
            else "mac-upgrade finished with errors"
        )
        await self.notifier.send_notification(title, summary)

        footer = self.query_one("#footer-help", Static)
        footer.update(f"Done — {summary}  |  [Q] Quit")

    def _log(self, key: str, message: str) -> None:
        panel = self.query_one("#log-panel", LiveLogPanel)
        panel.add_line(key, message)
        self.notifier.log(key, message)
```

- [ ] **Step 2: Run the list-only mode to verify it starts**

Run: `cd /Users/liskeee/Projects/Liskeee/mac-upgrade && python3 -m mac_upgrade.cli --list`
Expected: App launches, shows all managers, then exits after ~1.5 seconds.

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/mac_upgrade/app.py
git commit -m "feat: add main Textual dashboard app"
```

---

### Task 17: Integration Testing

**Files:** none — manual verification

- [ ] **Step 1: Test dry run**

Run: `cd /Users/liskeee/Projects/Liskeee/mac-upgrade && python3 -m mac_upgrade.cli --dry-run --yes`
Expected: App checks all managers, shows outdated packages, skips actual upgrades, then exits cleanly.

- [ ] **Step 2: Test --skip**

Run: `python3 -m mac_upgrade.cli --dry-run --yes --skip brew,cask`
Expected: Homebrew managers absent; only pip, npm, gem, system appear.

- [ ] **Step 3: Test --only**

Run: `python3 -m mac_upgrade.cli --dry-run --yes --only npm,gem`
Expected: Only npm and gem cards appear.

- [ ] **Step 4: Test live confirmation flow**

Run: `python3 -m mac_upgrade.cli --only npm` (if npm has outdated packages) or `python3 -m mac_upgrade.cli --only gem`
Expected: Cards show "updates found", pressing Enter triggers real upgrade, pressing S skips.

- [ ] **Step 5: Verify log file**

Run: `cat ~/mac-upgrade-$(date +%Y-%m-%d).log`
Expected: Log contains timestamped entries per manager.

- [ ] **Step 6: Run full test suite one last time**

Run: `python3 -m pytest -v`
Expected: All tests pass.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: mac-upgrade v0.1.0 complete"
```
