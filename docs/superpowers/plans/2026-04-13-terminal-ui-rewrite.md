# Terminal UI Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Textual TUI with a keyboard-only `rich` + `readchar` dashboard and onboarding wizard behind a narrow Protocol seam.

**Architecture:** Two `typing.Protocol` UIs (`DashboardUI`, `OnboardingUI`). `RichDashboardUI` drives a single `rich.live.Live` region at 10 Hz, polling `executor.states`. `PlainDashboardUI` streams one line per state transition for non-TTY. `RichOnboardingUI` is a linear 5-step Q&A using `console.clear()` + `console.print()`. All key input goes through a single normalization layer (`_input.py`) so tests feed a `FakeInput` of key names.

**Tech Stack:** Python 3.12+, `rich` (promoted from transitive to direct), `readchar` (new), pytest + pytest-asyncio. Textual is removed.

**Spec:** `docs/superpowers/specs/2026-04-13-terminal-ui-rewrite-design.md`

---

## File Structure

- Create:
  - `src/pkg_upgrade/ui/__init__.py` — exports Protocols + factories
  - `src/pkg_upgrade/ui/_input.py` — `read_key()`, `KeyInput` protocol, `RealInput`, `FakeInput`
  - `src/pkg_upgrade/ui/_glyphs.py` — unicode/ascii glyph tables
  - `src/pkg_upgrade/ui/_model.py` — `UIModel` pure render state
  - `src/pkg_upgrade/ui/plain_dashboard.py` — non-TTY fallback
  - `src/pkg_upgrade/ui/rich_dashboard.py` — rich.live dashboard
  - `src/pkg_upgrade/ui/rich_onboarding.py` — linear Q&A wizard
  - `tests/test_ui_input.py`
  - `tests/test_ui_model.py`
  - `tests/test_rich_dashboard_frame.py` (+ `tests/fixtures/rich_ui/*.txt` goldens)
  - `tests/test_rich_dashboard_input.py`
  - `tests/test_plain_dashboard.py`
  - `tests/test_rich_onboarding.py`
  - `tests/test_ui_contract.py`
- Modify:
  - `pyproject.toml` — drop `textual`, add `rich`, `readchar`
  - `src/pkg_upgrade/cli.py` — factory-based UI selection
  - `README.md` — update features + keybindings
- Delete:
  - `src/pkg_upgrade/app.py`
  - `src/pkg_upgrade/onboarding.py`
  - `src/pkg_upgrade/widgets.py`
  - `tests/test_onboarding.py`
  - Textual CSS / assets

---

## Task 1: Dependency swap

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Edit dependencies**

In `[project].dependencies`: remove any `textual...` entry; ensure `rich>=13.7` and `readchar>=4.0` are listed. Leave `pyyaml` and other deps alone.

- [ ] **Step 2: Install and verify import**

```bash
python -m pip install -e ".[dev]"
python -c "import rich, readchar; print(rich.__version__, readchar.__version__)"
```

Expected: prints two versions, no ImportError.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build(deps): swap textual for rich+readchar"
```

---

## Task 2: Input normalization layer

**Files:**
- Create: `src/pkg_upgrade/ui/__init__.py` (empty stub for now — `"""pkg_upgrade terminal UI."""`)
- Create: `src/pkg_upgrade/ui/_input.py`
- Test: `tests/test_ui_input.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_input.py
from pkg_upgrade.ui._input import FakeInput, normalize_key


def test_fake_input_returns_scripted_keys() -> None:
    fi = FakeInput(["j", "k", "enter", "q"])
    assert fi.read_key() == "j"
    assert fi.read_key() == "k"
    assert fi.read_key() == "enter"
    assert fi.read_key() == "q"


def test_fake_input_raises_when_exhausted() -> None:
    fi = FakeInput(["q"])
    fi.read_key()
    import pytest
    with pytest.raises(StopIteration):
        fi.read_key()


def test_normalize_key_arrows_and_specials() -> None:
    assert normalize_key("\x1b[A") == "up"
    assert normalize_key("\x1b[B") == "down"
    assert normalize_key("\x1b[C") == "right"
    assert normalize_key("\x1b[D") == "left"
    assert normalize_key("\r") == "enter"
    assert normalize_key("\n") == "enter"
    assert normalize_key("\x1b") == "esc"
    assert normalize_key("\x03") == "ctrl-c"
    assert normalize_key("\x7f") == "backspace"
    assert normalize_key("j") == "j"
    assert normalize_key("/") == "/"
```

- [ ] **Step 2: Run to fail**

`pytest tests/test_ui_input.py -v` — expect ImportError.

- [ ] **Step 3: Implement**

```python
# src/pkg_upgrade/ui/_input.py
from __future__ import annotations

from typing import Protocol


_SPECIALS = {
    "\r": "enter",
    "\n": "enter",
    "\x1b": "esc",
    "\x03": "ctrl-c",
    "\x7f": "backspace",
    "\x08": "backspace",
    "\t": "tab",
    " ": "space",
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
}


def normalize_key(raw: str) -> str:
    if raw in _SPECIALS:
        return _SPECIALS[raw]
    if len(raw) == 1 and raw.isprintable():
        return raw
    return raw


class KeyInput(Protocol):
    def read_key(self) -> str: ...


class RealInput:
    def read_key(self) -> str:
        import readchar  # noqa: PLC0415
        return normalize_key(readchar.readkey())


class FakeInput:
    def __init__(self, keys: list[str]) -> None:
        self._keys = iter(keys)

    def read_key(self) -> str:
        return next(self._keys)
```

Also create `src/pkg_upgrade/ui/__init__.py`:

```python
"""pkg_upgrade terminal UI."""
```

- [ ] **Step 4: Run to pass**

`pytest tests/test_ui_input.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/__init__.py src/pkg_upgrade/ui/_input.py tests/test_ui_input.py
git commit -m "feat(ui): add key input normalization layer"
```

---

## Task 3: Glyph tables (unicode/ascii)

**Files:**
- Create: `src/pkg_upgrade/ui/_glyphs.py`
- Test: `tests/test_ui_input.py` (extend) or new `tests/test_ui_glyphs.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_ui_glyphs.py
from pkg_upgrade.ui._glyphs import GlyphTable, pick_glyph_table
from pkg_upgrade.status import ManagerStatus


def test_unicode_table_has_all_statuses() -> None:
    t = GlyphTable.unicode()
    for s in ManagerStatus:
        assert t.status(s) != ""


def test_ascii_table_has_all_statuses_and_is_ascii() -> None:
    t = GlyphTable.ascii()
    for s in ManagerStatus:
        g = t.status(s)
        assert g != ""
        assert g.encode("ascii")


def test_pick_glyph_table_falls_back_for_ascii_encoding() -> None:
    assert pick_glyph_table("utf-8").status(ManagerStatus.DONE) == GlyphTable.unicode().status(ManagerStatus.DONE)
    assert pick_glyph_table("ascii").status(ManagerStatus.DONE) == GlyphTable.ascii().status(ManagerStatus.DONE)
```

- [ ] **Step 2: Run to fail**

`pytest tests/test_ui_glyphs.py -v`

- [ ] **Step 3: Implement**

```python
# src/pkg_upgrade/ui/_glyphs.py
from __future__ import annotations

from dataclasses import dataclass

from pkg_upgrade.status import ManagerStatus


@dataclass(frozen=True)
class GlyphTable:
    statuses: dict[ManagerStatus, str]

    def status(self, s: ManagerStatus) -> str:
        return self.statuses[s]

    @classmethod
    def unicode(cls) -> "GlyphTable":
        return cls({
            ManagerStatus.PENDING: "⏳ queued",
            ManagerStatus.CHECKING: "⧗ checking",
            ManagerStatus.AWAITING_CONFIRM: "⏸ awaiting confirm",
            ManagerStatus.UPGRADING: "▶ upgrading",
            ManagerStatus.DONE: "✓ done",
            ManagerStatus.SKIPPED: "⏭ skipped",
            ManagerStatus.UNAVAILABLE: "∅ unavailable",
            ManagerStatus.ERROR: "⚠ error",
        })

    @classmethod
    def ascii(cls) -> "GlyphTable":
        return cls({
            ManagerStatus.PENDING: ". queued",
            ManagerStatus.CHECKING: "- checking",
            ManagerStatus.AWAITING_CONFIRM: "P awaiting confirm",
            ManagerStatus.UPGRADING: "> upgrading",
            ManagerStatus.DONE: "v done",
            ManagerStatus.SKIPPED: "s skipped",
            ManagerStatus.UNAVAILABLE: "x unavailable",
            ManagerStatus.ERROR: "! error",
        })


def pick_glyph_table(encoding: str | None) -> GlyphTable:
    enc = (encoding or "").lower()
    if "utf" in enc:
        return GlyphTable.unicode()
    return GlyphTable.ascii()
```

- [ ] **Step 4: Run to pass**

`pytest tests/test_ui_glyphs.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/_glyphs.py tests/test_ui_glyphs.py
git commit -m "feat(ui): add unicode/ascii glyph tables"
```

---

## Task 4: UIModel (pure render state)

**Files:**
- Create: `src/pkg_upgrade/ui/_model.py`
- Test: `tests/test_ui_model.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_ui_model.py
from pkg_upgrade.status import ManagerStatus
from pkg_upgrade.ui._model import Row, UIModel


def _rows() -> list[Row]:
    return [
        Row(key="brew", name="Homebrew", icon="🍺", status=ManagerStatus.UPGRADING, done=3, total=12, duration_s=18, log=[]),
        Row(key="cask", name="Casks", icon="🍻", status=ManagerStatus.PENDING, done=0, total=0, duration_s=0, log=[]),
        Row(key="pip", name="pip", icon="🐍", status=ManagerStatus.DONE, done=4, total=4, duration_s=9, log=[]),
    ]


def test_move_focus_wraps_within_bounds() -> None:
    m = UIModel(rows=_rows())
    assert m.focus_key == "brew"
    m.move_focus(1)
    assert m.focus_key == "cask"
    m.move_focus(1)
    m.move_focus(1)
    assert m.focus_key == "pip"  # clamped


def test_focus_top_and_bottom() -> None:
    m = UIModel(rows=_rows())
    m.focus_bottom()
    assert m.focus_key == "pip"
    m.focus_top()
    assert m.focus_key == "brew"


def test_filter_narrows_visible_rows() -> None:
    m = UIModel(rows=_rows())
    m.set_filter("ca")
    assert [r.key for r in m.visible_rows] == ["cask"]
    m.set_filter("")
    assert [r.key for r in m.visible_rows] == ["brew", "cask", "pip"]


def test_toggle_expand_sets_expanded_key() -> None:
    m = UIModel(rows=_rows())
    m.toggle_expand()
    assert m.expanded_key == "brew"
    m.toggle_expand()
    assert m.expanded_key is None


def test_append_log_appends_to_focused_row() -> None:
    m = UIModel(rows=_rows())
    m.append_log("brew", "upgraded wget")
    assert m.rows[0].log == ["upgraded wget"]


def test_all_done_true_when_terminal() -> None:
    rows = _rows()
    for r in rows:
        r.status = ManagerStatus.DONE
    m = UIModel(rows=rows)
    assert m.all_done() is True


def test_all_done_false_when_any_active() -> None:
    m = UIModel(rows=_rows())
    assert m.all_done() is False
```

- [ ] **Step 2: Run to fail**

`pytest tests/test_ui_model.py -v`

- [ ] **Step 3: Implement**

```python
# src/pkg_upgrade/ui/_model.py
from __future__ import annotations

from dataclasses import dataclass, field

from pkg_upgrade.status import ACTIVE_STATUSES, ManagerStatus


@dataclass
class Row:
    key: str
    name: str
    icon: str
    status: ManagerStatus
    done: int
    total: int
    duration_s: int
    log: list[str] = field(default_factory=list)


@dataclass
class UIModel:
    rows: list[Row]
    focus_index: int = 0
    expanded_key: str | None = None
    filter_text: str = ""

    @property
    def focus_key(self) -> str | None:
        vis = self.visible_rows
        if not vis:
            return None
        idx = min(self.focus_index, len(vis) - 1)
        return vis[idx].key

    @property
    def visible_rows(self) -> list[Row]:
        if not self.filter_text:
            return list(self.rows)
        f = self.filter_text.lower()
        return [r for r in self.rows if f in r.key.lower() or f in r.name.lower()]

    def move_focus(self, delta: int) -> None:
        n = len(self.visible_rows)
        if n == 0:
            return
        self.focus_index = max(0, min(self.focus_index + delta, n - 1))

    def focus_top(self) -> None:
        self.focus_index = 0

    def focus_bottom(self) -> None:
        self.focus_index = max(0, len(self.visible_rows) - 1)

    def set_filter(self, text: str) -> None:
        self.filter_text = text
        self.focus_index = 0

    def toggle_expand(self) -> None:
        key = self.focus_key
        if key is None:
            return
        self.expanded_key = None if self.expanded_key == key else key

    def append_log(self, key: str, line: str) -> None:
        for r in self.rows:
            if r.key == key:
                r.log.append(line)
                return

    def all_done(self) -> bool:
        return all(r.status not in ACTIVE_STATUSES for r in self.rows)

    def focused_row(self) -> Row | None:
        key = self.focus_key
        if key is None:
            return None
        for r in self.rows:
            if r.key == key:
                return r
        return None
```

- [ ] **Step 4: Run to pass**

`pytest tests/test_ui_model.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/_model.py tests/test_ui_model.py
git commit -m "feat(ui): add UIModel render state"
```

---

## Task 5: UI protocols + factory

**Files:**
- Modify: `src/pkg_upgrade/ui/__init__.py`

- [ ] **Step 1: Implement (no tests yet — will be covered by contract tests in Task 10)**

```python
# src/pkg_upgrade/ui/__init__.py
"""pkg_upgrade terminal UI."""
from __future__ import annotations

import sys
from typing import Any, Protocol


class DashboardUI(Protocol):
    async def run(
        self,
        executor: "Executor",  # type: ignore[name-defined]  # noqa: F821
        *,
        auto_yes: bool,
        dry_run: bool,
    ) -> None: ...


class OnboardingUI(Protocol):
    def run(self, initial: dict[str, Any]) -> dict[str, Any] | None: ...


def select_dashboard() -> DashboardUI:
    if sys.stdout.isatty():
        from pkg_upgrade.ui.rich_dashboard import RichDashboardUI  # noqa: PLC0415
        return RichDashboardUI()
    from pkg_upgrade.ui.plain_dashboard import PlainDashboardUI  # noqa: PLC0415
    return PlainDashboardUI()


def select_onboarding() -> OnboardingUI | None:
    if not sys.stdout.isatty():
        return None
    from pkg_upgrade.ui.rich_onboarding import RichOnboardingUI  # noqa: PLC0415
    return RichOnboardingUI()
```

- [ ] **Step 2: Commit**

```bash
git add src/pkg_upgrade/ui/__init__.py
git commit -m "feat(ui): add DashboardUI/OnboardingUI protocols + factory"
```

---

## Task 6: Plain dashboard (non-TTY)

**Files:**
- Create: `src/pkg_upgrade/ui/plain_dashboard.py`
- Test: `tests/test_plain_dashboard.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_plain_dashboard.py
from __future__ import annotations

from pkg_upgrade.ui.plain_dashboard import PlainDashboardUI
from tests._ui_fakes import FakeExecutor, canned_states_all_outdated


async def test_plain_ui_streams_lines_and_completes(capsys) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = PlainDashboardUI()
    await ui.run(ex, auto_yes=True, dry_run=False)
    out = capsys.readouterr().out
    assert "[brew]" in out
    assert "done" in out
    assert ex.all_done()


async def test_plain_ui_dry_run_does_not_upgrade(capsys) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = PlainDashboardUI()
    await ui.run(ex, auto_yes=True, dry_run=True)
    assert ex.upgrade_calls == 0
```

Also create `tests/_ui_fakes.py`:

```python
# tests/_ui_fakes.py
from __future__ import annotations

from collections.abc import Awaitable, Callable

from pkg_upgrade.status import ManagerStatus


class _FakeManager:
    def __init__(self, key: str, name: str, icon: str) -> None:
        self.key = key
        self.name = name
        self.icon = icon


class _FakeState:
    def __init__(self, manager: _FakeManager, outdated: list[str]) -> None:
        self.manager = manager
        self.outdated = list(outdated)
        self.results: list[tuple[str, bool]] = []
        self.status = ManagerStatus.PENDING
        self.error: str | None = None


class FakeExecutor:
    def __init__(self, states: dict[str, _FakeState]) -> None:
        self.states = states
        self.upgrade_calls = 0

    def all_managers(self) -> list[_FakeManager]:
        return [s.manager for s in self.states.values()]

    async def check_all(self, on_update: Callable[[str], Awaitable[None]] | None = None) -> None:
        for k, s in self.states.items():
            s.status = ManagerStatus.CHECKING
            if on_update:
                await on_update(k)
            s.status = ManagerStatus.AWAITING_CONFIRM if s.outdated else ManagerStatus.DONE
            if on_update:
                await on_update(k)

    async def upgrade_manager(
        self,
        key: str,
        on_update: Callable[[str], Awaitable[None]] | None = None,
        on_result: Callable[[str, str, bool], Awaitable[None]] | None = None,
    ) -> None:
        self.upgrade_calls += 1
        s = self.states[key]
        s.status = ManagerStatus.UPGRADING
        if on_update:
            await on_update(key)
        for pkg in s.outdated:
            s.results.append((pkg, True))
            if on_result:
                await on_result(key, pkg, True)
        s.status = ManagerStatus.DONE
        if on_update:
            await on_update(key)

    def skip_manager(self, key: str) -> None:
        self.states[key].status = ManagerStatus.SKIPPED

    def all_done(self) -> bool:
        from pkg_upgrade.status import ACTIVE_STATUSES  # noqa: PLC0415
        return all(s.status not in ACTIVE_STATUSES for s in self.states.values())


def canned_states_all_outdated() -> dict[str, _FakeState]:
    return {
        "brew": _FakeState(_FakeManager("brew", "Homebrew", "🍺"), ["wget", "jq"]),
        "pip": _FakeState(_FakeManager("pip", "pip", "🐍"), ["rich"]),
    }
```

- [ ] **Step 2: Run to fail**

`pytest tests/test_plain_dashboard.py -v`

- [ ] **Step 3: Implement**

```python
# src/pkg_upgrade/ui/plain_dashboard.py
from __future__ import annotations

import sys
from typing import Any


class PlainDashboardUI:
    async def run(self, executor: Any, *, auto_yes: bool, dry_run: bool) -> None:
        def say(key: str, msg: str) -> None:
            print(f"[{key}] {msg}", flush=True)

        async def on_update(key: str) -> None:
            s = executor.states[key]
            say(key, s.status.value)

        async def on_result(key: str, pkg: str, ok: bool) -> None:
            marker = "ok" if ok else "FAIL"
            say(key, f"{marker} {pkg}")

        await executor.check_all(on_update=on_update)

        if dry_run:
            for k, s in executor.states.items():
                if s.outdated:
                    say(k, f"dry-run: would upgrade {len(s.outdated)} package(s)")
                    from pkg_upgrade.status import ManagerStatus  # noqa: PLC0415
                    s.status = ManagerStatus.DONE
            return

        for key, s in executor.states.items():
            if not s.outdated:
                continue
            if not auto_yes:
                say(key, "skipped (no TTY and --yes not set)")
                executor.skip_manager(key)
                continue
            await executor.upgrade_manager(key, on_update=on_update, on_result=on_result)
        sys.stdout.flush()
```

- [ ] **Step 4: Run to pass**

`pytest tests/test_plain_dashboard.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/plain_dashboard.py tests/test_plain_dashboard.py tests/_ui_fakes.py
git commit -m "feat(ui): add PlainDashboardUI for non-TTY"
```

---

## Task 7: Rich dashboard frame renderer

**Files:**
- Create: `src/pkg_upgrade/ui/rich_dashboard.py` (partial — just `build_frame` for now)
- Test: `tests/test_rich_dashboard_frame.py`
- Fixtures: `tests/fixtures/rich_ui/*.txt`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rich_dashboard_frame.py
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from pkg_upgrade.status import ManagerStatus
from pkg_upgrade.ui._glyphs import GlyphTable
from pkg_upgrade.ui._model import Row, UIModel
from pkg_upgrade.ui.rich_dashboard import build_frame

FIXTURES = Path(__file__).parent / "fixtures" / "rich_ui"


def _render(model: UIModel) -> str:
    c = Console(width=80, height=24, record=True, force_terminal=True, color_system=None)
    c.print(build_frame(model, GlyphTable.ascii(), elapsed_seconds=42))
    return c.export_text()


def _assert_golden(name: str, output: str) -> None:
    path = FIXTURES / f"{name}.txt"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)
    assert output == path.read_text()


def _base_rows() -> list[Row]:
    return [
        Row("brew", "Homebrew", "H", ManagerStatus.UPGRADING, 3, 12, 18, ["ok wget", "ok jq"]),
        Row("cask", "Casks", "C", ManagerStatus.PENDING, 0, 0, 0, []),
        Row("pip", "pip", "P", ManagerStatus.DONE, 4, 4, 9, []),
    ]


def test_frame_mixed_states() -> None:
    m = UIModel(rows=_base_rows())
    _assert_golden("mixed", _render(m))


def test_frame_expanded_row() -> None:
    m = UIModel(rows=_base_rows())
    m.toggle_expand()
    _assert_golden("expanded", _render(m))


def test_frame_filter_active() -> None:
    m = UIModel(rows=_base_rows())
    m.set_filter("br")
    _assert_golden("filter_br", _render(m))


def test_frame_awaiting_confirm() -> None:
    rows = _base_rows()
    rows[0].status = ManagerStatus.AWAITING_CONFIRM
    _assert_golden("awaiting_confirm", _render(UIModel(rows=rows)))
```

- [ ] **Step 2: Run to fail**

`pytest tests/test_rich_dashboard_frame.py -v` — expect ImportError.

- [ ] **Step 3: Implement `build_frame`**

```python
# src/pkg_upgrade/ui/rich_dashboard.py
from __future__ import annotations

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pkg_upgrade.ui._glyphs import GlyphTable
from pkg_upgrade.ui._model import UIModel


def _fmt_duration(s: int) -> str:
    if s <= 0:
        return "—"
    m, sec = divmod(s, 60)
    return f"{m}:{sec:02d}"


def _fmt_progress(done: int, total: int) -> str:
    if total <= 0:
        return "—"
    return f"{done}/{total}"


def build_frame(
    model: UIModel,
    glyphs: GlyphTable,
    *,
    elapsed_seconds: int = 0,
) -> RenderableType:
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(width=2)
    table.add_column("KEY", ratio=1)
    table.add_column("MANAGER", ratio=2)
    table.add_column("STATUS", ratio=2)
    table.add_column("PROGRESS", ratio=1)
    table.add_column("DURATION", ratio=1)

    header = Text("  KEY     MANAGER           STATUS         PROGRESS    DURATION", style="bold")

    rows_renderables: list[RenderableType] = [header]
    focus_key = model.focus_key
    for r in model.visible_rows:
        marker = ">" if r.key == focus_key else " "
        line = Text(
            f"{marker} {r.key:<7} {r.icon} {r.name:<15} {glyphs.status(r.status):<18} "
            f"{_fmt_progress(r.done, r.total):<10} {_fmt_duration(r.duration_s)}"
        )
        rows_renderables.append(line)

    if model.expanded_key:
        for r in model.rows:
            if r.key == model.expanded_key:
                rows_renderables.append(Text(""))
                rows_renderables.append(Text(f"  - {r.key} - (expanded)"))
                for line in r.log[-8:]:
                    rows_renderables.append(Text(f"  {line}"))
                break

    if model.filter_text:
        rows_renderables.append(Text(""))
        rows_renderables.append(Text(f"  filter: /{model.filter_text}"))

    title = f"pkg-upgrade - {_fmt_duration(elapsed_seconds)} elapsed"
    return Panel(Group(*rows_renderables), title=title, border_style="cyan")
```

- [ ] **Step 4: Generate goldens + run**

```bash
pytest tests/test_rich_dashboard_frame.py -v
```

First run creates goldens; second run verifies. Inspect `tests/fixtures/rich_ui/*.txt` and confirm they look right.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/rich_dashboard.py tests/test_rich_dashboard_frame.py tests/fixtures/rich_ui
git commit -m "feat(ui): add rich dashboard frame renderer with snapshot tests"
```

---

## Task 8: RichDashboardUI event loop

**Files:**
- Modify: `src/pkg_upgrade/ui/rich_dashboard.py`
- Test: `tests/test_rich_dashboard_input.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_rich_dashboard_input.py
from __future__ import annotations

from pkg_upgrade.ui._input import FakeInput
from pkg_upgrade.ui.rich_dashboard import RichDashboardUI
from tests._ui_fakes import FakeExecutor, canned_states_all_outdated


async def test_quit_immediately() -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = RichDashboardUI(input=FakeInput(["q"]), quiet=True)
    await ui.run(ex, auto_yes=True, dry_run=False)
    # quit short-circuits; may or may not have run upgrades


async def test_auto_yes_runs_all_and_exits() -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = RichDashboardUI(input=FakeInput([]), quiet=True)
    await ui.run(ex, auto_yes=True, dry_run=False)
    assert ex.all_done()
    assert ex.upgrade_calls >= 1


async def test_manual_confirm_then_skip() -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    ui = RichDashboardUI(input=FakeInput(["y", "j", "s"]), quiet=True)
    await ui.run(ex, auto_yes=False, dry_run=False)
    assert ex.all_done()
```

- [ ] **Step 2: Run to fail**

`pytest tests/test_rich_dashboard_input.py -v`

- [ ] **Step 3: Implement RichDashboardUI**

Append to `src/pkg_upgrade/ui/rich_dashboard.py`:

```python
from __future__ import annotations

import asyncio
import sys
from typing import Any

from pkg_upgrade.status import ACTIVE_STATUSES, ManagerStatus
from pkg_upgrade.ui._glyphs import GlyphTable, pick_glyph_table
from pkg_upgrade.ui._input import FakeInput, KeyInput, RealInput
from pkg_upgrade.ui._model import Row, UIModel


class RichDashboardUI:
    def __init__(self, input: KeyInput | None = None, quiet: bool = False) -> None:
        self._input: KeyInput = input if input is not None else RealInput()
        self._quiet = quiet
        self._glyphs: GlyphTable = pick_glyph_table(sys.stdout.encoding)

    def _build_model(self, executor: Any) -> UIModel:
        rows: list[Row] = []
        for key, s in executor.states.items():
            rows.append(
                Row(
                    key=key,
                    name=s.manager.name,
                    icon=getattr(s.manager, "icon", ""),
                    status=s.status,
                    done=len(s.results),
                    total=len(s.outdated),
                    duration_s=0,
                    log=[f"{'ok' if ok else 'FAIL'} {pkg}" for pkg, ok in s.results],
                )
            )
        return UIModel(rows=rows)

    async def _read_key_soft(self) -> str | None:
        if isinstance(self._input, FakeInput):
            try:
                return self._input.read_key()
            except StopIteration:
                return None
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._input.read_key)

    async def run(self, executor: Any, *, auto_yes: bool, dry_run: bool) -> None:
        await executor.check_all()

        if dry_run:
            for s in executor.states.values():
                s.status = ManagerStatus.DONE
            return

        if auto_yes:
            for key, s in list(executor.states.items()):
                if s.outdated:
                    await executor.upgrade_manager(key)
            return

        model = self._build_model(executor)

        while not model.all_done():
            key = await self._read_key_soft()
            if key is None:
                break
            if key in {"q", "ctrl-c"}:
                break
            if key in {"j", "down"}:
                model.move_focus(1)
            elif key in {"k", "up"}:
                model.move_focus(-1)
            elif key == "g":
                model.focus_top()
            elif key == "G":
                model.focus_bottom()
            elif key in {"enter", "right"}:
                model.toggle_expand()
            elif key == "y":
                fk = model.focus_key
                if fk and executor.states[fk].status == ManagerStatus.AWAITING_CONFIRM:
                    await executor.upgrade_manager(fk)
                    model = self._build_model(executor)
            elif key == "s":
                fk = model.focus_key
                if fk and executor.states[fk].status in ACTIVE_STATUSES:
                    executor.skip_manager(fk)
                    model = self._build_model(executor)
```

- [ ] **Step 4: Run to pass**

`pytest tests/test_rich_dashboard_input.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/rich_dashboard.py tests/test_rich_dashboard_input.py
git commit -m "feat(ui): add RichDashboardUI event loop with keybindings"
```

---

## Task 9: Rich onboarding wizard

**Files:**
- Create: `src/pkg_upgrade/ui/rich_onboarding.py`
- Test: `tests/test_rich_onboarding.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_rich_onboarding.py
from __future__ import annotations

from pkg_upgrade.config import DEFAULT_CONFIG
from pkg_upgrade.ui._input import FakeInput
from pkg_upgrade.ui.rich_onboarding import RichOnboardingUI


def test_onboarding_cancel_returns_none() -> None:
    ui = RichOnboardingUI(input=FakeInput(["q"]), quiet=True)
    assert ui.run(dict(DEFAULT_CONFIG)) is None


def test_onboarding_happy_path_saves_defaults() -> None:
    # step 1: managers (enter accepts discovered selection)
    # step 2: confirm mode (enter = ask)
    # step 3: notify (enter accepts)
    # step 4: logging (enter accepts both checkbox and path)
    # step 5: review (enter saves)
    keys = ["enter", "enter", "enter", "enter", "enter", "enter"]
    ui = RichOnboardingUI(input=FakeInput(keys), quiet=True)
    result = ui.run(dict(DEFAULT_CONFIG))
    assert result is not None
    assert "managers" in result
    assert "auto_yes" in result
    assert "notify" in result
    assert "log" in result
    assert "log_dir" in result


def test_onboarding_back_navigates() -> None:
    keys = ["enter", "b", "enter", "enter", "enter", "enter", "enter"]
    ui = RichOnboardingUI(input=FakeInput(keys), quiet=True)
    result = ui.run(dict(DEFAULT_CONFIG))
    assert result is not None
```

- [ ] **Step 2: Run to fail**

`pytest tests/test_rich_onboarding.py -v`

- [ ] **Step 3: Implement**

```python
# src/pkg_upgrade/ui/rich_onboarding.py
from __future__ import annotations

import asyncio
import json
from typing import Any

from rich.console import Console

from pkg_upgrade.ui._input import KeyInput, RealInput


_BACK = object()
_QUIT = object()


class RichOnboardingUI:
    def __init__(self, input: KeyInput | None = None, quiet: bool = False) -> None:
        self._input: KeyInput = input if input is not None else RealInput()
        self._console = Console(quiet=quiet)

    def _read(self) -> str:
        try:
            return self._input.read_key()
        except StopIteration:
            return "q"

    def _render(self, title: str, body: str) -> None:
        self._console.clear()
        self._console.print(f"[bold]{title}[/bold]")
        self._console.print(body)

    def _step_managers(self, cfg: dict[str, Any]) -> object:
        from pkg_upgrade.registry import discover_managers  # noqa: PLC0415
        mgrs = discover_managers()
        available: dict[str, bool] = {}
        try:
            loop = asyncio.new_event_loop()
            try:
                async def _probe() -> dict[str, bool]:
                    return {m.key: bool(await m.is_available()) for m in mgrs}
                available = loop.run_until_complete(_probe())
            finally:
                loop.close()
        except Exception:
            available = {m.key: True for m in mgrs}

        selected = {m.key for m in mgrs if available.get(m.key, False) and m.key in set(cfg.get("managers") or [])}
        if not selected:
            selected = {m.key for m in mgrs if available.get(m.key, False)}
        idx = 0
        while True:
            lines = ["Which package managers do you want to upgrade? (space toggles, a=all, n=none, enter=next, b=back, q=quit)"]
            for i, m in enumerate(mgrs):
                mark = "[x]" if m.key in selected else "[ ]"
                avail = "" if available.get(m.key, False) else " (not found)"
                cursor = ">" if i == idx else " "
                lines.append(f"{cursor} {mark} {m.icon} {m.key} - {m.name}{avail}")
            self._render("Step 1/5: Managers", "\n".join(lines))
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k in {"j", "down"}:
                idx = min(idx + 1, len(mgrs) - 1)
            elif k in {"k", "up"}:
                idx = max(idx - 1, 0)
            elif k == "space":
                m = mgrs[idx]
                if available.get(m.key, False):
                    if m.key in selected:
                        selected.discard(m.key)
                    else:
                        selected.add(m.key)
            elif k == "a":
                selected = {m.key for m in mgrs if available.get(m.key, False)}
            elif k == "n":
                selected = set()
            elif k == "enter":
                cfg["managers"] = sorted(selected)
                return None

    def _step_confirm(self, cfg: dict[str, Any]) -> object:
        idx = 1 if cfg.get("auto_yes") else 0
        while True:
            options = [("Ask before each manager (recommended)", False), ("Upgrade everything automatically (--yes)", True)]
            lines = ["How should upgrades be confirmed? (j/k move, enter select, b back, q quit)"]
            for i, (label, _) in enumerate(options):
                cursor = ">" if i == idx else " "
                lines.append(f"{cursor} ( ) {label}" if i != idx else f"{cursor} (*) {label}")
            self._render("Step 2/5: Confirmation", "\n".join(lines))
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k in {"j", "down"}:
                idx = min(idx + 1, 1)
            elif k in {"k", "up"}:
                idx = max(idx - 1, 0)
            elif k == "enter":
                cfg["auto_yes"] = options[idx][1]
                return None

    def _step_notify(self, cfg: dict[str, Any]) -> object:
        val = bool(cfg.get("notify", True))
        while True:
            mark = "[x]" if val else "[ ]"
            self._render("Step 3/5: Notifications", f"{mark} Show a notification when upgrades complete\n(space toggles, enter next, b back, q quit)")
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k == "space":
                val = not val
            elif k == "enter":
                cfg["notify"] = val
                return None

    def _step_log(self, cfg: dict[str, Any]) -> object:
        log_on = bool(cfg.get("log", True))
        log_dir = str(cfg.get("log_dir", "~/"))
        phase = "toggle"
        buf = log_dir
        while True:
            if phase == "toggle":
                mark = "[x]" if log_on else "[ ]"
                self._render("Step 4/5: Logging", f"{mark} Write a log file for each run\n(space toggles, enter next, b back, q quit)")
                k = self._read()
                if k in {"q", "ctrl-c"}:
                    return _QUIT
                if k == "b":
                    return _BACK
                if k == "space":
                    log_on = not log_on
                elif k == "enter":
                    if log_on:
                        phase = "path"
                    else:
                        cfg["log"] = False
                        cfg["log_dir"] = log_dir
                        return None
            else:
                self._render("Step 4/5: Log directory", f"Path: {buf}_\n(type to edit, backspace to delete, enter to accept, b back, q quit)")
                k = self._read()
                if k in {"q", "ctrl-c"}:
                    return _QUIT
                if k == "b":
                    phase = "toggle"
                    continue
                if k == "backspace":
                    buf = buf[:-1]
                elif k == "enter":
                    cfg["log"] = True
                    cfg["log_dir"] = buf or "~/"
                    return None
                elif len(k) == 1 and k.isprintable():
                    buf += k

    def _step_review(self, cfg: dict[str, Any]) -> object:
        self._render("Step 5/5: Review", json.dumps(cfg, indent=2, sort_keys=True) + "\n\n(enter=save, b=back, q=cancel)")
        while True:
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k == "enter":
                return None

    def run(self, initial: dict[str, Any]) -> dict[str, Any] | None:
        cfg = dict(initial)
        steps = [self._step_managers, self._step_confirm, self._step_notify, self._step_log, self._step_review]
        i = 0
        while i < len(steps):
            outcome = steps[i](cfg)
            if outcome is _QUIT:
                return None
            if outcome is _BACK:
                i = max(0, i - 1)
            else:
                i += 1
        return cfg
```

- [ ] **Step 4: Run to pass**

`pytest tests/test_rich_onboarding.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/rich_onboarding.py tests/test_rich_onboarding.py
git commit -m "feat(ui): add RichOnboardingUI linear 5-step wizard"
```

---

## Task 10: Wire CLI + delete Textual

**Files:**
- Modify: `src/pkg_upgrade/cli.py`
- Delete: `src/pkg_upgrade/app.py`, `src/pkg_upgrade/onboarding.py`, `src/pkg_upgrade/widgets.py`, `tests/test_onboarding.py`

- [ ] **Step 1: Write contract test first**

```python
# tests/test_ui_contract.py
from __future__ import annotations

import pytest

from pkg_upgrade.ui._input import FakeInput
from pkg_upgrade.ui.plain_dashboard import PlainDashboardUI
from pkg_upgrade.ui.rich_dashboard import RichDashboardUI
from tests._ui_fakes import FakeExecutor, canned_states_all_outdated


@pytest.fixture(params=["plain", "rich"])
def ui(request):
    if request.param == "plain":
        return PlainDashboardUI()
    return RichDashboardUI(input=FakeInput([]), quiet=True)


async def test_ui_completes_with_auto_yes(ui) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    await ui.run(ex, auto_yes=True, dry_run=False)
    assert ex.all_done()


async def test_ui_respects_dry_run(ui) -> None:
    ex = FakeExecutor(canned_states_all_outdated())
    await ui.run(ex, auto_yes=True, dry_run=True)
    assert ex.upgrade_calls == 0
```

Run: `pytest tests/test_ui_contract.py -v` — should pass already (both UIs are done).

- [ ] **Step 2: Rewrite cli.py**

Replace the Textual-specific parts of `cli.py`. Key changes:
- Delete imports: `from textual ...`, `from pkg_upgrade.app import PkgUpgradeApp`, `from pkg_upgrade.onboarding import OnboardingScreen`.
- Delete `_run_onboarding_wizard` function entirely.
- Replace onboarding launch: use `select_onboarding()`; if `None`, print error and exit 2 when config is missing.
- Replace `PkgUpgradeApp(...).run()` with:

```python
import asyncio  # already imported
from pkg_upgrade.executor import Executor
from pkg_upgrade.registry import discover_managers, select_managers
from pkg_upgrade.ui import select_dashboard, select_onboarding

# in main() — replacing the app.run() block:
managers = discover_managers()
managers = select_managers(managers, skip=settings["skip"], only=settings["only"])
executor = Executor.from_managers(managers, max_parallel=args.max_parallel)
ui = select_dashboard()
asyncio.run(ui.run(executor, auto_yes=settings["auto_yes"], dry_run=settings["dry_run"]))
```

And the onboarding path:

```python
if args.onboard or not config_exists():
    ob = select_onboarding()
    if ob is None:
        print("error: onboarding requires an interactive terminal. Re-run in a TTY, or create ~/.mac-upgrade manually.", file=sys.stderr)
        return 2
    existing, _ = load_config_dict() if config_exists() else (dict(DEFAULT_CONFIG), None)
    saved = ob.run(existing)
    if saved is None:
        print("Onboarding cancelled - no changes written.")
        return 0
    save_config(saved)
    if args.onboard:
        print(f"Saved configuration to {Path.home() / '.mac-upgrade'}")
        return 0
    cfg = saved
    warning = None
```

- [ ] **Step 3: Delete files**

```bash
git rm src/pkg_upgrade/app.py src/pkg_upgrade/onboarding.py src/pkg_upgrade/widgets.py tests/test_onboarding.py
```

- [ ] **Step 4: Run full suite**

```bash
pytest
ruff check .
ruff format --check .
mypy
```

Fix any failures inline.

- [ ] **Step 5: Smoke test**

```bash
pkg-upgrade --list
pkg-upgrade --version
```

Both should work without Textual.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(ui): wire rich UIs into cli; remove Textual app"
```

---

## Task 11: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update features + keybindings**

Remove "Textual TUI" phrasing; replace with "keyboard-only terminal UI (rich)". Add keybinding table matching the spec. Update any screenshots reference to a note saying they're pending.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for rich terminal UI"
```
