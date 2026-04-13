# pkg-upgrade: New Managers + Tri-OS CI (Plan 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the nine Linux/Windows/macOS declarative managers (apt, dnf, pacman, flatpak, snap, winget, scoop, choco, mas) plus their parser presets, sudo/admin gating, and a tri-OS CI matrix with per-OS smoke jobs.

**Architecture:** Each Linux/Windows/macOS CLI-wrapping manager is a pure YAML manifest at `src/pkg_upgrade/managers/declarative/*.yaml` backed by a named parser preset in `src/pkg_upgrade/parsers/`. `DeclarativeManager` gains optional `requires_sudo` (Linux: probes `sudo -n true` via `run_command`) and `requires_admin` (Windows: probes `ctypes.windll.shell32.IsUserAnAdmin()`); unmet → `is_available()` returns False. CI fans out to ubuntu/macos/windows × py3.12/3.13 with subprocess-stubbed unit tests; smoke jobs exercise the native binary on each runner.

**Tech Stack:** Python 3.12+, PyYAML, `ctypes` (stdlib) for Windows admin probe, GitHub Actions matrix.

**Spec:** [`docs/superpowers/specs/2026-04-13-pkg-upgrade-cross-platform-design.md`](../specs/2026-04-13-pkg-upgrade-cross-platform-design.md)

---

## File Structure

**Created:**
- `src/pkg_upgrade/parsers/apt.py`, `dnf.py`, `pacman.py`, `flatpak.py`, `snap.py`, `winget.py`, `scoop.py`, `choco.py`, `mas.py` — one function per preset, registered in module.
- `src/pkg_upgrade/managers/declarative/{apt,dnf,pacman,flatpak,snap,winget,scoop,choco,mas}.yaml` — nine manifests.
- `tests/fixtures/parsers/{apt,dnf,pacman,flatpak,snap,winget,scoop,choco,mas}.txt` — real-world stdout captures.
- `tests/test_parsers_presets.py` — table-driven parser tests.
- `tests/test_declarative_gating.py` — sudo/admin gating tests.
- `tests/test_manifests.py` — loads every shipped manifest and asserts schema.
- `tests/test_cross_os_discovery.py` — OS-specific discovery regression guard.

**Modified:**
- `src/pkg_upgrade/parsers/__init__.py` — eager-import new parser modules so registration fires.
- `src/pkg_upgrade/declarative.py` — extend `_Manifest` with `requires_admin`; extend `DeclarativeManager.is_available()` with sudo/admin probes.
- `src/pkg_upgrade/platform.py` — add `sudo_available_noninteractive()` helper.
- `.github/workflows/ci.yml` — expand jobs to tri-OS matrix; add per-OS smoke jobs.

---

## Parser preset conventions

All preset functions share this signature:

```python
def parse(stdout: str, **_: Any) -> list[Package]: ...
```

Packages with unknown current version use `current_version=""`. Unparseable lines are skipped silently. Every preset is registered via `register_parser(name, fn)` at module import time. New modules are imported from `parsers/__init__.py` so registration happens whenever the parsers package is touched.

---

### Task 1: apt_upgradable parser

**Files:**
- Create: `tests/fixtures/parsers/apt.txt`
- Create: `src/pkg_upgrade/parsers/apt.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create real-world fixture**

Write `tests/fixtures/parsers/apt.txt`:

```
Listing... Done
curl/jammy-updates 7.81.0-1ubuntu1.15 amd64 [upgradable from: 7.81.0-1ubuntu1.14]
git/jammy-updates 1:2.34.1-1ubuntu1.11 amd64 [upgradable from: 1:2.34.1-1ubuntu1.10]
libc6/jammy-updates,jammy-security 2.35-0ubuntu3.7 amd64 [upgradable from: 2.35-0ubuntu3.6]
```

- [ ] **Step 2: Write failing test**

Create `tests/test_parsers_presets.py`:

```python
from __future__ import annotations

from pathlib import Path

from pkg_upgrade.parsers import get_parser

FIXTURES = Path(__file__).parent / "fixtures" / "parsers"


def _load(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text()


def test_apt_upgradable_parses_three_packages() -> None:
    parser = get_parser("apt_upgradable")
    pkgs = parser(_load("apt"))
    names = [(p.name, p.current_version, p.latest_version) for p in pkgs]
    assert names == [
        ("curl", "7.81.0-1ubuntu1.14", "7.81.0-1ubuntu1.15"),
        ("git", "1:2.34.1-1ubuntu1.10", "1:2.34.1-1ubuntu1.11"),
        ("libc6", "2.35-0ubuntu3.6", "2.35-0ubuntu3.7"),
    ]
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_parsers_presets.py::test_apt_upgradable_parses_three_packages -v`
Expected: FAIL — `KeyError: "Unknown parser preset: 'apt_upgradable'"`.

- [ ] **Step 4: Implement parser**

Create `src/pkg_upgrade/parsers/apt.py`:

```python
from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser

_LINE = re.compile(
    r"^(?P<name>[^/\s]+)/\S+\s+(?P<latest>\S+)\s+\S+\s+\[upgradable from: (?P<current>[^\]]+)\]"
)


def apt_upgradable(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        pkgs.append(
            Package(
                name=gd["name"],
                current_version=gd["current"],
                latest_version=gd["latest"],
            )
        )
    return pkgs


register_parser("apt_upgradable", apt_upgradable)
```

- [ ] **Step 5: Wire module import**

Edit `src/pkg_upgrade/parsers/__init__.py` — replace the final `from pkg_upgrade.parsers import generic` line with:

```python
from pkg_upgrade.parsers import (  # noqa: E402, F401
    apt,
    generic,
)
```

- [ ] **Step 6: Run test to verify PASS**

Run: `pytest tests/test_parsers_presets.py::test_apt_upgradable_parses_three_packages -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/apt.txt src/pkg_upgrade/parsers/apt.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add apt_upgradable preset"
```

---

### Task 2: dnf_check_update parser

**Files:**
- Create: `tests/fixtures/parsers/dnf.txt`
- Create: `src/pkg_upgrade/parsers/dnf.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/dnf.txt`:

```

Last metadata expiration check: 0:05:12 ago on Sun Apr 13 06:00:00 2026.

bash.x86_64                       5.2.15-1.fc39            updates
kernel.x86_64                     6.6.13-200.fc39          updates
vim-enhanced.x86_64               2:9.1.0-1.fc39           updates

Obsoleting Packages
old-thing.noarch                  1.0-1.fc38               @anaconda
```

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_dnf_check_update_parses_packages_and_stops_at_obsoletes() -> None:
    parser = get_parser("dnf_check_update")
    pkgs = parser(_load("dnf"))
    names = [(p.name, p.latest_version) for p in pkgs]
    assert names == [
        ("bash", "5.2.15-1.fc39"),
        ("kernel", "6.6.13-200.fc39"),
        ("vim-enhanced", "2:9.1.0-1.fc39"),
    ]
```

- [ ] **Step 3: Run to verify FAIL**

Run: `pytest tests/test_parsers_presets.py::test_dnf_check_update_parses_packages_and_stops_at_obsoletes -v`
Expected: FAIL — unknown parser.

- [ ] **Step 4: Implement parser**

Create `src/pkg_upgrade/parsers/dnf.py`:

```python
from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser

_LINE = re.compile(r"^(?P<name>[^\s.]+)\.\S+\s+(?P<latest>\S+)\s+\S+\s*$")


def dnf_check_update(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for raw in stdout.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("Obsoleting Packages"):
            break
        if line.startswith("Last metadata"):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        pkgs.append(
            Package(name=gd["name"], current_version="", latest_version=gd["latest"])
        )
    return pkgs


register_parser("dnf_check_update", dnf_check_update)
```

- [ ] **Step 5: Add to parsers/__init__.py import tuple**

Update `src/pkg_upgrade/parsers/__init__.py` to include `dnf` alphabetically:

```python
from pkg_upgrade.parsers import (  # noqa: E402, F401
    apt,
    dnf,
    generic,
)
```

- [ ] **Step 6: Run test to verify PASS**

Run: `pytest tests/test_parsers_presets.py::test_dnf_check_update_parses_packages_and_stops_at_obsoletes -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/dnf.txt src/pkg_upgrade/parsers/dnf.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add dnf_check_update preset"
```

---

### Task 3: pacman_qu parser

**Files:**
- Create: `tests/fixtures/parsers/pacman.txt`
- Create: `src/pkg_upgrade/parsers/pacman.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/pacman.txt`:

```
linux 6.6.10.arch1-1 -> 6.7.2.arch1-1
firefox 122.0-1 -> 123.0.1-1
python 3.11.7-1 -> 3.12.2-1
```

(Source: `pacman -Qu` — one line per outdated package: `name current -> latest`.)

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_pacman_qu_parses_arrows() -> None:
    parser = get_parser("pacman_qu")
    pkgs = parser(_load("pacman"))
    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [
        ("linux", "6.6.10.arch1-1", "6.7.2.arch1-1"),
        ("firefox", "122.0-1", "123.0.1-1"),
        ("python", "3.11.7-1", "3.12.2-1"),
    ]
```

- [ ] **Step 3: Run FAIL**

Run: `pytest tests/test_parsers_presets.py::test_pacman_qu_parses_arrows -v`
Expected: FAIL.

- [ ] **Step 4: Implement**

Create `src/pkg_upgrade/parsers/pacman.py`:

```python
from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser

_LINE = re.compile(r"^(?P<name>\S+)\s+(?P<current>\S+)\s+->\s+(?P<latest>\S+)\s*$")


def pacman_qu(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        pkgs.append(
            Package(name=gd["name"], current_version=gd["current"], latest_version=gd["latest"])
        )
    return pkgs


register_parser("pacman_qu", pacman_qu)
```

- [ ] **Step 5: Wire import** — add `pacman,` to the tuple in `src/pkg_upgrade/parsers/__init__.py` (alphabetical).

- [ ] **Step 6: Run PASS**

Run: `pytest tests/test_parsers_presets.py::test_pacman_qu_parses_arrows -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/pacman.txt src/pkg_upgrade/parsers/pacman.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add pacman_qu preset"
```

---

### Task 4: flatpak_remote_ls_updates parser

**Files:**
- Create: `tests/fixtures/parsers/flatpak.txt`
- Create: `src/pkg_upgrade/parsers/flatpak.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/flatpak.txt` — tab-separated from `flatpak remote-ls --updates --columns=application,version`:

```
org.mozilla.firefox	123.0.1
org.gimp.GIMP	2.10.36
com.github.tchx84.Flatseal	2.2.0
```

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_flatpak_parses_tab_columns() -> None:
    parser = get_parser("flatpak_remote_ls_updates")
    pkgs = parser(_load("flatpak"))
    assert [(p.name, p.latest_version) for p in pkgs] == [
        ("org.mozilla.firefox", "123.0.1"),
        ("org.gimp.GIMP", "2.10.36"),
        ("com.github.tchx84.Flatseal", "2.2.0"),
    ]
```

- [ ] **Step 3: Run FAIL.** `pytest tests/test_parsers_presets.py::test_flatpak_parses_tab_columns -v`

- [ ] **Step 4: Implement**

Create `src/pkg_upgrade/parsers/flatpak.py`:

```python
from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def flatpak_remote_ls_updates(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        pkgs.append(Package(name=cols[0], current_version="", latest_version=cols[1]))
    return pkgs


register_parser("flatpak_remote_ls_updates", flatpak_remote_ls_updates)
```

- [ ] **Step 5: Wire import** — add `flatpak,` alphabetically.

- [ ] **Step 6: Run PASS.**

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/flatpak.txt src/pkg_upgrade/parsers/flatpak.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add flatpak_remote_ls_updates preset"
```

---

### Task 5: snap_refresh_list parser

**Files:**
- Create: `tests/fixtures/parsers/snap.txt`
- Create: `src/pkg_upgrade/parsers/snap.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/snap.txt` (output of `snap refresh --list`):

```
Name       Version        Rev    Size   Publisher   Notes
core22     20240111       1122   77MB   canonical*  -
firefox    123.0.1-1      3626   247MB  mozilla*    -
snapd      2.61.2         21184  39MB   canonical*  -
```

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_snap_refresh_list_skips_header() -> None:
    parser = get_parser("snap_refresh_list")
    pkgs = parser(_load("snap"))
    assert [(p.name, p.latest_version) for p in pkgs] == [
        ("core22", "20240111"),
        ("firefox", "123.0.1-1"),
        ("snapd", "2.61.2"),
    ]
```

- [ ] **Step 3: Run FAIL.**

- [ ] **Step 4: Implement**

Create `src/pkg_upgrade/parsers/snap.py`:

```python
from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def snap_refresh_list(stdout: str, **_: Any) -> list[Package]:
    lines = stdout.splitlines()
    if lines and lines[0].lower().startswith("name"):
        lines = lines[1:]
    pkgs: list[Package] = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        pkgs.append(Package(name=parts[0], current_version="", latest_version=parts[1]))
    return pkgs


register_parser("snap_refresh_list", snap_refresh_list)
```

- [ ] **Step 5: Wire import** — add `snap,` alphabetically.

- [ ] **Step 6: Run PASS.**

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/snap.txt src/pkg_upgrade/parsers/snap.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add snap_refresh_list preset"
```

---

### Task 6: winget_upgrade parser

**Files:**
- Create: `tests/fixtures/parsers/winget.txt`
- Create: `src/pkg_upgrade/parsers/winget.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/winget.txt`:

```
Name                        Id                          Version      Available    Source
-------------------------------------------------------------------------------------------
Git                         Git.Git                     2.43.0       2.44.0       winget
Microsoft PowerShell        Microsoft.PowerShell        7.4.0.0      7.4.1.0      winget
Python 3.12                 Python.Python.3.12          3.12.1150.0  3.12.2150.0  winget
3 upgrades available.
```

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_winget_upgrade_parses_fixed_width_table() -> None:
    parser = get_parser("winget_upgrade")
    pkgs = parser(_load("winget"))
    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [
        ("Git.Git", "2.43.0", "2.44.0"),
        ("Microsoft.PowerShell", "7.4.0.0", "7.4.1.0"),
        ("Python.Python.3.12", "3.12.1150.0", "3.12.2150.0"),
    ]
```

- [ ] **Step 3: Run FAIL.**

- [ ] **Step 4: Implement**

Create `src/pkg_upgrade/parsers/winget.py`:

```python
from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def winget_upgrade(stdout: str, **_: Any) -> list[Package]:
    lines = [line.rstrip() for line in stdout.splitlines()]
    header_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("Name ") and "Id" in line and "Version" in line and "Available" in line:
            header_idx = i
            break
    if header_idx is None:
        return []
    header = lines[header_idx]
    id_start = header.index("Id")
    ver_start = header.index("Version")
    avail_start = header.index("Available")
    src_start = header.index("Source")
    pkgs: list[Package] = []
    for line in lines[header_idx + 1 :]:
        if not line or set(line) <= {"-"}:
            continue
        if "upgrades available." in line:
            break
        id_ = line[id_start:ver_start].strip()
        current = line[ver_start:avail_start].strip()
        latest = line[avail_start:src_start].strip()
        if not id_ or not current or not latest:
            continue
        pkgs.append(Package(name=id_, current_version=current, latest_version=latest))
    return pkgs


register_parser("winget_upgrade", winget_upgrade)
```

- [ ] **Step 5: Wire import** — add `winget,` alphabetically.

- [ ] **Step 6: Run PASS.**

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/winget.txt src/pkg_upgrade/parsers/winget.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add winget_upgrade preset"
```

---

### Task 7: scoop_status parser

**Files:**
- Create: `tests/fixtures/parsers/scoop.txt`
- Create: `src/pkg_upgrade/parsers/scoop.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/scoop.txt`:

```
Scoop is up to date.

Name    Installed Version Latest Version Missing Dependencies Info
----    ----------------- -------------- -------------------- ----
git     2.43.0            2.44.0
ripgrep 14.1.0            14.1.1
nodejs  20.11.0           20.11.1
```

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_scoop_status_parses_fixed_width() -> None:
    parser = get_parser("scoop_status")
    pkgs = parser(_load("scoop"))
    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [
        ("git", "2.43.0", "2.44.0"),
        ("ripgrep", "14.1.0", "14.1.1"),
        ("nodejs", "20.11.0", "20.11.1"),
    ]
```

- [ ] **Step 3: Run FAIL.**

- [ ] **Step 4: Implement**

Create `src/pkg_upgrade/parsers/scoop.py`:

```python
from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def scoop_status(stdout: str, **_: Any) -> list[Package]:
    lines = [line.rstrip() for line in stdout.splitlines()]
    header_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("Name") and "Installed Version" in line and "Latest Version" in line:
            header_idx = i
            break
    if header_idx is None:
        return []
    header = lines[header_idx]
    installed_start = header.index("Installed Version")
    latest_start = header.index("Latest Version")
    missing_start = (
        header.index("Missing Dependencies")
        if "Missing Dependencies" in header
        else len(header)
    )
    pkgs: list[Package] = []
    for line in lines[header_idx + 2 :]:  # skip header + ruler
        if not line.strip():
            continue
        name = line[:installed_start].strip()
        current = line[installed_start:latest_start].strip()
        latest = line[latest_start:missing_start].strip()
        if not name or not current or not latest:
            continue
        pkgs.append(Package(name=name, current_version=current, latest_version=latest))
    return pkgs


register_parser("scoop_status", scoop_status)
```

- [ ] **Step 5: Wire import** — add `scoop,` alphabetically.

- [ ] **Step 6: Run PASS.**

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/scoop.txt src/pkg_upgrade/parsers/scoop.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add scoop_status preset"
```

---

### Task 8: choco_outdated parser

**Files:**
- Create: `tests/fixtures/parsers/choco.txt`
- Create: `src/pkg_upgrade/parsers/choco.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/choco.txt` (output of `choco outdated --limit-output`):

```
git|2.43.0|2.44.0|false
nodejs|20.11.0|20.11.1|false
vscode|1.86.0|1.87.0|false
```

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_choco_outdated_parses_pipes() -> None:
    parser = get_parser("choco_outdated")
    pkgs = parser(_load("choco"))
    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [
        ("git", "2.43.0", "2.44.0"),
        ("nodejs", "20.11.0", "20.11.1"),
        ("vscode", "1.86.0", "1.87.0"),
    ]
```

- [ ] **Step 3: Run FAIL.**

- [ ] **Step 4: Implement**

Create `src/pkg_upgrade/parsers/choco.py`:

```python
from __future__ import annotations

from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser


def choco_outdated(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        name, current, latest = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not name:
            continue
        pkgs.append(Package(name=name, current_version=current, latest_version=latest))
    return pkgs


register_parser("choco_outdated", choco_outdated)
```

- [ ] **Step 5: Wire import** — add `choco,` alphabetically.

- [ ] **Step 6: Run PASS.**

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/choco.txt src/pkg_upgrade/parsers/choco.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add choco_outdated preset"
```

---

### Task 9: mas_outdated parser

**Files:**
- Create: `tests/fixtures/parsers/mas.txt`
- Create: `src/pkg_upgrade/parsers/mas.py`
- Modify: `src/pkg_upgrade/parsers/__init__.py`
- Test: `tests/test_parsers_presets.py`

- [ ] **Step 1: Create fixture**

Write `tests/fixtures/parsers/mas.txt`:

```
497799835 Xcode (15.1 -> 15.3)
1333542190 1Password 7 (7.9.11 -> 7.9.12)
409183694 Keynote (13.2 -> 14.0)
```

- [ ] **Step 2: Write failing test**

Append to `tests/test_parsers_presets.py`:

```python
def test_mas_outdated_parses_lines() -> None:
    parser = get_parser("mas_outdated")
    pkgs = parser(_load("mas"))
    assert [(p.name, p.current_version, p.latest_version) for p in pkgs] == [
        ("497799835", "15.1", "15.3"),
        ("1333542190", "7.9.11", "7.9.12"),
        ("409183694", "13.2", "14.0"),
    ]
```

Note: `mas upgrade <id>` takes the numeric ID, so we use the ID as `name`. The human-readable app name is not needed for the upgrade command.

- [ ] **Step 3: Run FAIL.**

- [ ] **Step 4: Implement**

Create `src/pkg_upgrade/parsers/mas.py`:

```python
from __future__ import annotations

import re
from typing import Any

from pkg_upgrade.models import Package
from pkg_upgrade.parsers import register_parser

_LINE = re.compile(
    r"^(?P<id>\d+)\s+.*\((?P<current>[^\s]+)\s*->\s*(?P<latest>[^\s)]+)\)\s*$"
)


def mas_outdated(stdout: str, **_: Any) -> list[Package]:
    pkgs: list[Package] = []
    for line in stdout.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        pkgs.append(
            Package(name=gd["id"], current_version=gd["current"], latest_version=gd["latest"])
        )
    return pkgs


register_parser("mas_outdated", mas_outdated)
```

- [ ] **Step 5: Wire import** — add `mas,` alphabetically.

- [ ] **Step 6: Run PASS.**

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/parsers/mas.txt src/pkg_upgrade/parsers/mas.py \
        src/pkg_upgrade/parsers/__init__.py tests/test_parsers_presets.py
git commit -m "feat(parsers): add mas_outdated preset"
```

---

### Task 10: Sudo/admin gating in DeclarativeManager

**Files:**
- Modify: `src/pkg_upgrade/platform.py`
- Modify: `src/pkg_upgrade/declarative.py`
- Test: `tests/test_declarative_gating.py`

**Context:** Linux managers with `requires_sudo: true` should report `is_available() == False` unless the user has a live sudo credential (`sudo -n true` returns 0). Windows managers with `requires_admin: true` (choco) should report `False` unless `is_windows_admin()` returns True. Manifests already pass `requires_sudo` through `_Manifest`; add `requires_admin`. Shell calls go through `run_command` per project convention (CLAUDE.md).

- [ ] **Step 1: Add sudo probe helper to platform.py**

Edit `src/pkg_upgrade/platform.py` — append:

```python
import shutil

from pkg_upgrade._subprocess import run_command


async def sudo_available_noninteractive() -> bool:
    """True if `sudo -n true` succeeds (cached sudo credential)."""
    if shutil.which("sudo") is None:
        return False
    rc, _, _ = await run_command(["sudo", "-n", "true"])
    return rc == 0
```

If `shutil` is already imported at the top of the file, skip the duplicate. If a circular-import ImportError occurs from the `run_command` import, move it inside the function body.

- [ ] **Step 2: Write failing test for sudo/admin gating**

Create `tests/test_declarative_gating.py`:

```python
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
    with patch(
        "pkg_upgrade.declarative.sudo_available_noninteractive",
        AsyncMock(return_value=False),
    ), patch("pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"):
        assert await mgr.is_available() is False


async def test_is_available_true_with_sudo_credential() -> None:
    mgr = _mk(requires_sudo=True)
    with patch(
        "pkg_upgrade.declarative.sudo_available_noninteractive",
        AsyncMock(return_value=True),
    ), patch("pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"):
        assert await mgr.is_available() is True


async def test_is_available_false_without_admin_on_windows() -> None:
    mgr = _mk(requires_admin=True)
    with patch("pkg_upgrade.declarative.is_windows_admin", return_value=False), patch(
        "pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"
    ):
        assert await mgr.is_available() is False


async def test_is_available_true_with_admin_on_windows() -> None:
    mgr = _mk(requires_admin=True)
    with patch("pkg_upgrade.declarative.is_windows_admin", return_value=True), patch(
        "pkg_upgrade.declarative.shutil.which", return_value="/usr/bin/echo"
    ):
        assert await mgr.is_available() is True
```

- [ ] **Step 3: Run FAIL**

Run: `pytest tests/test_declarative_gating.py -v`
Expected: FAIL — `_Manifest` lacks `requires_admin`; `sudo_available_noninteractive` / `is_windows_admin` not imported into `declarative`.

- [ ] **Step 4: Extend `_Manifest` and `DeclarativeManager`**

Edit `src/pkg_upgrade/declarative.py`:

Add imports at the top:

```python
from pkg_upgrade.platform import is_windows_admin, sudo_available_noninteractive
```

In the `_Manifest` dataclass, add `requires_admin: bool` directly after `requires_sudo: bool`.

In `_Manifest.from_dict`, add this keyword to the `cls(...)` call (directly after `requires_sudo=...`):

```python
requires_admin=bool(data.get("requires_admin", False)),
```

Replace `DeclarativeManager.is_available` with:

```python
async def is_available(self) -> bool:
    binary = self._m.check_cmd[0]
    if binary == "sudo" and len(self._m.check_cmd) > 1:
        binary = self._m.check_cmd[1]
    if shutil.which(binary) is None:
        return False
    if self._m.requires_sudo and not await sudo_available_noninteractive():
        return False
    if self._m.requires_admin and not is_windows_admin():
        return False
    return True
```

- [ ] **Step 5: Run PASS**

Run: `pytest tests/test_declarative_gating.py -v`
Expected: all 4 pass.

- [ ] **Step 6: Run full suite to catch regressions**

Run: `pytest`
Expected: all pass (pre-existing declarative tests may need `requires_admin=False` added if they construct `_Manifest` directly; update as needed).

- [ ] **Step 7: Commit**

```bash
git add src/pkg_upgrade/platform.py src/pkg_upgrade/declarative.py \
        tests/test_declarative_gating.py tests/test_declarative.py
git commit -m "feat(declarative): gate is_available by sudo credential and Windows admin"
```

---

### Task 11: Ship nine YAML manifests + schema test

**Files:**
- Create: `src/pkg_upgrade/managers/declarative/{apt,dnf,pacman,flatpak,snap,winget,scoop,choco,mas}.yaml`
- Test: `tests/test_manifests.py`

- [ ] **Step 1: Write the failing schema test**

Create `tests/test_manifests.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pkg_upgrade.declarative import _Manifest
from pkg_upgrade.parsers import get_parser

DECL_DIR = (
    Path(__file__).parent.parent / "src" / "pkg_upgrade" / "managers" / "declarative"
)

EXPECTED_KEYS = {
    "apt", "dnf", "pacman", "flatpak", "snap",
    "winget", "scoop", "choco", "mas",
}


def _all_yaml() -> list[Path]:
    return sorted(DECL_DIR.glob("*.yaml"))


def test_all_expected_manifests_shipped() -> None:
    keys = {p.stem for p in _all_yaml()}
    assert EXPECTED_KEYS <= keys, f"Missing: {EXPECTED_KEYS - keys}"


@pytest.mark.parametrize("path", _all_yaml(), ids=lambda p: p.stem)
def test_manifest_schema_valid(path: Path) -> None:
    data = yaml.safe_load(path.read_text())
    manifest = _Manifest.from_dict(data)
    assert manifest.key == path.stem
    assert manifest.platforms  # non-empty
    get_parser(manifest.check_parser)  # must resolve
```

- [ ] **Step 2: Run FAIL** — `pytest tests/test_manifests.py -v` fails because YAML files don't exist.

- [ ] **Step 3: Write apt.yaml**

Create `src/pkg_upgrade/managers/declarative/apt.yaml`:

```yaml
name: APT
key: apt
icon: "📦"
platforms: [linux]
install_hint: "Debian/Ubuntu ships APT by default."
requires_sudo: true

check:
  cmd: [apt, list, --upgradable]
  parser: apt_upgradable

upgrade:
  cmd: [sudo, apt-get, install, --only-upgrade, -y, "{name}"]
```

- [ ] **Step 4: Write dnf.yaml**

Create `src/pkg_upgrade/managers/declarative/dnf.yaml`:

```yaml
name: DNF
key: dnf
icon: "🎩"
platforms: [linux]
install_hint: "Fedora/RHEL ships DNF by default."
requires_sudo: true

check:
  cmd: [dnf, check-update, --quiet]
  parser: dnf_check_update

upgrade:
  cmd: [sudo, dnf, upgrade, -y, "{name}"]
```

- [ ] **Step 5: Write pacman.yaml**

Create `src/pkg_upgrade/managers/declarative/pacman.yaml`:

```yaml
name: Pacman
key: pacman
icon: "🏛️"
platforms: [linux]
install_hint: "Ships with Arch Linux and derivatives."
requires_sudo: true

check:
  cmd: [pacman, -Qu]
  parser: pacman_qu

upgrade:
  cmd: [sudo, pacman, -S, --noconfirm, "{name}"]
```

- [ ] **Step 6: Write flatpak.yaml**

Create `src/pkg_upgrade/managers/declarative/flatpak.yaml`:

```yaml
name: Flatpak
key: flatpak
icon: "📦"
platforms: [linux]
install_hint: "Install via your distro package manager: flatpak."

check:
  cmd: [flatpak, remote-ls, --updates, --columns=application,version]
  parser: flatpak_remote_ls_updates

upgrade:
  cmd: [flatpak, update, -y, "{name}"]
```

- [ ] **Step 7: Write snap.yaml**

Create `src/pkg_upgrade/managers/declarative/snap.yaml`:

```yaml
name: Snap
key: snap
icon: "⚡"
platforms: [linux]
install_hint: "Install snapd via your distro package manager."
requires_sudo: true

check:
  cmd: [snap, refresh, --list]
  parser: snap_refresh_list

upgrade:
  cmd: [sudo, snap, refresh, "{name}"]
```

- [ ] **Step 8: Write winget.yaml**

Create `src/pkg_upgrade/managers/declarative/winget.yaml`:

```yaml
name: winget
key: winget
icon: "🪟"
platforms: [windows]
install_hint: "Install 'App Installer' from the Microsoft Store."

check:
  cmd: [winget, upgrade]
  parser: winget_upgrade

upgrade:
  cmd: [winget, upgrade, --silent, --accept-source-agreements, --accept-package-agreements, --id, "{name}"]
```

- [ ] **Step 9: Write scoop.yaml**

Create `src/pkg_upgrade/managers/declarative/scoop.yaml`:

```yaml
name: Scoop
key: scoop
icon: "🥄"
platforms: [windows]
install_hint: "See https://scoop.sh for install instructions."

check:
  cmd: [scoop, status]
  parser: scoop_status

upgrade:
  cmd: [scoop, update, "{name}"]
```

- [ ] **Step 10: Write choco.yaml**

Create `src/pkg_upgrade/managers/declarative/choco.yaml`:

```yaml
name: Chocolatey
key: choco
icon: "🍫"
platforms: [windows]
install_hint: "See https://chocolatey.org/install. Must run as Administrator."
requires_admin: true

check:
  cmd: [choco, outdated, --limit-output]
  parser: choco_outdated

upgrade:
  cmd: [choco, upgrade, "{name}", -y]
```

- [ ] **Step 11: Write mas.yaml**

Create `src/pkg_upgrade/managers/declarative/mas.yaml`:

```yaml
name: Mac App Store
key: mas
icon: "🛍️"
platforms: [macos]
install_hint: "brew install mas"

check:
  cmd: [mas, outdated]
  parser: mas_outdated

upgrade:
  cmd: [mas, upgrade, "{name}"]
```

- [ ] **Step 12: Run all manifest tests**

Run: `pytest tests/test_manifests.py -v`
Expected: 10 tests pass (1 inventory + 9 parametrized).

- [ ] **Step 13: Commit**

```bash
git add src/pkg_upgrade/managers/declarative tests/test_manifests.py
git commit -m "feat(managers): ship apt/dnf/pacman/flatpak/snap/winget/scoop/choco/mas manifests"
```

---

### Task 12: Tri-OS CI matrix

**Files:**
- Modify: `.github/workflows/ci.yml`

**Context:** Currently every job is `runs-on: macos-latest`. Expand `lint`, `typecheck`, `test`, `build` to an OS matrix. Keep `pre-commit` on ubuntu only (mypy pre-commit hook paths are fussy on Windows), and `security` and `brew` on macOS.

- [ ] **Step 1: Rewrite `lint` job**

Replace the `lint:` block with:

```yaml
  lint:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .
```

- [ ] **Step 2: Rewrite `typecheck` job**

```yaml
  typecheck:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: mypy
```

- [ ] **Step 3: Rewrite `test` job**

```yaml
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.12", "3.13"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: pytest --cov --cov-report=xml
      - uses: actions/upload-artifact@v7
        if: matrix.python-version == '3.12' && matrix.os == 'ubuntu-latest'
        with:
          name: coverage-xml
          path: coverage.xml
```

- [ ] **Step 4: Keep `build` on ubuntu (fastest)**

Change `build:` `runs-on: macos-latest` → `runs-on: ubuntu-latest`. No matrix — one wheel is universal.

- [ ] **Step 5: Pin `pre-commit` job to ubuntu**

Change `pre-commit:` `runs-on: macos-latest` → `runs-on: ubuntu-latest`.

- [ ] **Step 6: Validate YAML locally**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: no output, exit 0.

- [ ] **Step 7: Run pytest locally**

Run: `pytest`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: fan lint/typecheck/test out to ubuntu/macos/windows matrix"
```

---

### Task 13: Per-OS smoke jobs

**Files:**
- Modify: `.github/workflows/ci.yml`

**Context:** Smoke today runs on macOS only. Extend to all three OSes and exercise `--list` + `--show-graph` to catch OS-specific discovery bugs.

- [ ] **Step 1: Replace the `smoke:` block**

```yaml
  smoke:
    needs: build
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - uses: actions/download-artifact@v8
        with:
          name: dist
          path: dist/
      - name: Install built wheel in clean venv (POSIX)
        if: runner.os != 'Windows'
        run: |
          python -m venv .smoke
          .smoke/bin/pip install dist/*.whl
          .smoke/bin/pkg-upgrade --version
          .smoke/bin/pkg-upgrade --help
          .smoke/bin/pkg-upgrade --list
          .smoke/bin/pkg-upgrade --show-graph
      - name: Install built wheel in clean venv (Windows)
        if: runner.os == 'Windows'
        shell: pwsh
        run: |
          python -m venv .smoke
          .smoke\Scripts\pip install (Get-ChildItem dist\*.whl)[0].FullName
          .smoke\Scripts\pkg-upgrade.exe --version
          .smoke\Scripts\pkg-upgrade.exe --help
          .smoke\Scripts\pkg-upgrade.exe --list
          .smoke\Scripts\pkg-upgrade.exe --show-graph
```

- [ ] **Step 2: Validate YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run smoke on ubuntu/macos/windows and exercise --list/--show-graph"
```

---

### Task 14: OS-specific discovery regression guard

**Files:**
- Test: `tests/test_cross_os_discovery.py`

**Context:** Guard against future regressions where a manifest leaks onto the wrong OS.

- [ ] **Step 1: Write the test**

Create `tests/test_cross_os_discovery.py`:

```python
from __future__ import annotations

from unittest.mock import patch

import pytest

from pkg_upgrade.registry import clear_registry, discover_managers

MACOS_DECL = {"mas"}
LINUX_DECL = {"apt", "dnf", "pacman", "flatpak", "snap"}
WINDOWS_DECL = {"winget", "scoop", "choco"}


@pytest.fixture(autouse=True)
def _fresh_registry():
    clear_registry()
    yield
    clear_registry()


@pytest.mark.parametrize(
    ("os_name", "expected_decl"),
    [("macos", MACOS_DECL), ("linux", LINUX_DECL), ("windows", WINDOWS_DECL)],
)
def test_discover_includes_declared_managers_for_os(
    os_name: str, expected_decl: set[str]
) -> None:
    with patch("pkg_upgrade.registry.current_os", return_value=os_name):
        managers = discover_managers(load_entry_points=False)
    keys = {m.key for m in managers}
    assert expected_decl <= keys, f"OS {os_name} missing: {expected_decl - keys}"
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_cross_os_discovery.py -v`
Expected: 3 tests pass.

- [ ] **Step 3: If `clear_registry` breaks subsequent tests** in the full suite, copy the `_repopulate_builtins()` teardown pattern from `tests/test_registry.py` / `tests/test_declarative.py` and add it to the `_fresh_registry` fixture.

- [ ] **Step 4: Commit**

```bash
git add tests/test_cross_os_discovery.py
git commit -m "test: guard OS-specific manager discovery against regressions"
```

---

### Task 15: Final regression + PR

- [ ] **Step 1: Run full suite + lints**

```bash
pytest
ruff check .
ruff format --check .
mypy
```

All must pass.

- [ ] **Step 2: Push branch**

```bash
git push -u origin feat/pkg-upgrade-managers
```

- [ ] **Step 3: Open PR**

Base: `main` if Plan 1 is merged; else `feat/pkg-upgrade-foundation` (stacked PR).

```bash
gh pr create --title "feat: pkg-upgrade managers + tri-OS CI (Plan 2)" \
  --body "Ships 9 declarative managers (apt/dnf/pacman/flatpak/snap/winget/scoop/choco/mas), their parser presets with real-world fixtures, sudo/admin gating, tri-OS CI matrix, and per-OS smoke jobs. See docs/superpowers/plans/2026-04-13-pkg-upgrade-managers.md."
```

---

## Self-Review

**Spec coverage** (against `2026-04-13-pkg-upgrade-cross-platform-design.md`):
- Built-in managers table (apt, dnf, pacman, flatpak, snap, winget, scoop, choco, mas) → Task 11 ✓
- Parser presets list (9 presets) → Tasks 1–9 ✓
- Every preset has fixtures → each task ships `tests/fixtures/parsers/<key>.txt` ✓
- Linux sudo gating (`sudo -n true`) → Task 10 ✓
- Windows admin gating (`IsUserAnAdmin`) → Task 10 (uses existing `is_windows_admin` from Plan 1) ✓
- CI matrix `{ubuntu, macos, windows} × {3.12, 3.13}` with ruff/format/mypy/pytest → Task 12 ✓
- Per-OS smoke jobs → Task 13 ✓
- Parser preset tests table-driven with fixtures → Tasks 1–9 ✓
- Declarative schema validated → Task 11 schema test ✓

**Explicitly deferred (out of scope for Plan 2):**
- `creationflags=CREATE_NO_WINDOW` Windows console suppression — deferred until a console-flash is observed in practice.
- `linux_distro()`-based auto-routing of apt vs dnf vs pacman — unnecessary; runtime `is_available()` already selects the right manager.

**Placeholder scan:** no TBDs, no "similar to Task N", every code block is complete.

**Type consistency:** `Package(name, current_version, latest_version)` used identically in every parser. `_Manifest.requires_admin` introduced in Task 10 and consumed in Task 11's `choco.yaml`. Every parser name used in a manifest (`apt_upgradable`, etc.) is registered in the matching parser task.
