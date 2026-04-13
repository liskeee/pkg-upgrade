# TUI btop-redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current flat single-panel TUI with a btop/yazi-style layered dashboard (summary bar, rich manager rows with two-tone progress bars, animated spinners, keybind footer) using terminal-native ANSI colors only.

**Architecture:** Refactor `rich_dashboard.py` into small pure render helpers composed by `build_frame`, extend `_glyphs.py` with spinner frames, add a status→color map, and wrap `RichDashboardUI.run` in a `rich.live.Live` loop ticking at 8 Hz. No changes to executor, managers, model, or `plain_dashboard.py`.

**Tech Stack:** Python 3.12+, Rich (`rich.live.Live`, `rich.layout.Layout`, `rich.panel.Panel`, `rich.text.Text`, `rich.box.ROUNDED`/`ASCII`), pytest + asyncio.

**Spec:** `docs/superpowers/specs/2026-04-13-tui-btop-redesign-design.md`

---

## File Structure

**Modify:**
- `src/pkg_upgrade/ui/_glyphs.py` — add `spinner_frames` field + unicode/ascii frame tuples.
- `src/pkg_upgrade/ui/rich_dashboard.py` — refactor into pure helpers, add `STATUS_COLORS`, new `build_frame(tick=...)` signature, `Live`-wrapped `run`.
- `tests/test_rich_dashboard_frame.py` — update existing goldens for new signature + layout; add snapshots for new scenarios.
- `tests/test_ui_glyphs.py` — add spinner-frame tests.
- `tests/fixtures/rich_ui/*.txt` — regenerate golden fixtures (delete + re-record via first test run).

**No new files.**

---

## Task 1: Add spinner frames to GlyphTable

**Files:**
- Modify: `src/pkg_upgrade/ui/_glyphs.py`
- Test: `tests/test_ui_glyphs.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui_glyphs.py`:

```python
def test_unicode_spinner_frames_present() -> None:
    t = GlyphTable.unicode()
    assert t.spinner_frames == ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def test_ascii_spinner_frames_present() -> None:
    t = GlyphTable.ascii()
    assert t.spinner_frames == ("|", "/", "-", "\\")


def test_pick_glyph_table_ascii_has_ascii_spinner() -> None:
    assert pick_glyph_table("ascii").spinner_frames[0] == "|"
```

Ensure the test module imports `pick_glyph_table` at the top. If a `test_ui_glyphs.py` import block doesn't include it, add:

```python
from pkg_upgrade.ui._glyphs import GlyphTable, pick_glyph_table
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_glyphs.py -v`
Expected: FAIL — `GlyphTable` has no attribute `spinner_frames`.

- [ ] **Step 3: Implement**

Replace the contents of `src/pkg_upgrade/ui/_glyphs.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from pkg_upgrade.status import ManagerStatus

SPINNER_FRAMES_UNICODE: tuple[str, ...] = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
SPINNER_FRAMES_ASCII: tuple[str, ...] = ("|", "/", "-", "\\")


@dataclass(frozen=True)
class GlyphTable:
    statuses: dict[ManagerStatus, str]
    spinner_frames: tuple[str, ...]

    def status(self, s: ManagerStatus) -> str:
        return self.statuses[s]

    def spinner(self, tick: int) -> str:
        return self.spinner_frames[tick % len(self.spinner_frames)]

    @classmethod
    def unicode(cls) -> GlyphTable:
        return cls(
            statuses={
                ManagerStatus.PENDING: "⏳ queued",
                ManagerStatus.CHECKING: "⧗ checking",
                ManagerStatus.AWAITING_CONFIRM: "⏸ awaiting confirm",
                ManagerStatus.UPGRADING: "▶ upgrading",
                ManagerStatus.DONE: "✓ done",
                ManagerStatus.SKIPPED: "⏭ skipped",
                ManagerStatus.UNAVAILABLE: "∅ unavailable",
                ManagerStatus.ERROR: "⚠ error",
            },
            spinner_frames=SPINNER_FRAMES_UNICODE,
        )

    @classmethod
    def ascii(cls) -> GlyphTable:
        return cls(
            statuses={
                ManagerStatus.PENDING: ". queued",
                ManagerStatus.CHECKING: "- checking",
                ManagerStatus.AWAITING_CONFIRM: "P awaiting confirm",
                ManagerStatus.UPGRADING: "> upgrading",
                ManagerStatus.DONE: "v done",
                ManagerStatus.SKIPPED: "s skipped",
                ManagerStatus.UNAVAILABLE: "x unavailable",
                ManagerStatus.ERROR: "! error",
            },
            spinner_frames=SPINNER_FRAMES_ASCII,
        )


def pick_glyph_table(encoding: str | None) -> GlyphTable:
    enc = (encoding or "").lower()
    if "utf" in enc:
        return GlyphTable.unicode()
    return GlyphTable.ascii()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui_glyphs.py -v`
Expected: PASS (all, including spinner tests).

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/_glyphs.py tests/test_ui_glyphs.py
git commit -m "feat(ui): add spinner frames to GlyphTable"
```

---

## Task 2: Add status→color map and pure render helpers

**Files:**
- Modify: `src/pkg_upgrade/ui/rich_dashboard.py`
- Test: `tests/test_rich_dashboard_frame.py` (new unit tests, goldens come later)

- [ ] **Step 1: Write failing unit tests**

Append to `tests/test_rich_dashboard_frame.py`:

```python
from pkg_upgrade.ui.rich_dashboard import (
    STATUS_COLORS,
    render_progress_bar,
)


def test_status_colors_cover_every_status() -> None:
    for s in ManagerStatus:
        assert s in STATUS_COLORS


def test_progress_bar_full() -> None:
    bar = render_progress_bar(10, 10, width=10, color="green").plain
    assert bar == "██████████"


def test_progress_bar_half() -> None:
    bar = render_progress_bar(5, 10, width=10, color="green").plain
    assert bar == "█████░░░░░"


def test_progress_bar_zero_total_is_all_dim() -> None:
    bar = render_progress_bar(0, 0, width=6, color="green").plain
    assert bar == "░░░░░░"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rich_dashboard_frame.py::test_status_colors_cover_every_status tests/test_rich_dashboard_frame.py::test_progress_bar_full -v`
Expected: FAIL — `STATUS_COLORS` / `render_progress_bar` not importable.

- [ ] **Step 3: Add `STATUS_COLORS` and `render_progress_bar` to `rich_dashboard.py`**

At the top of `src/pkg_upgrade/ui/rich_dashboard.py`, below existing imports, add:

```python
from pkg_upgrade.status import ManagerStatus

STATUS_COLORS: dict[ManagerStatus, str] = {
    ManagerStatus.PENDING: "dim",
    ManagerStatus.CHECKING: "blue",
    ManagerStatus.AWAITING_CONFIRM: "magenta",
    ManagerStatus.UPGRADING: "yellow",
    ManagerStatus.DONE: "green",
    ManagerStatus.SKIPPED: "dim",
    ManagerStatus.UNAVAILABLE: "dim",
    ManagerStatus.ERROR: "red",
}


def render_progress_bar(done: int, total: int, width: int, color: str) -> Text:
    if total <= 0:
        return Text("░" * width, style="dim")
    filled = min(width, max(0, round(width * done / total)))
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * (width - filled), style="dim")
    return t
```

(`Text` is already imported.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rich_dashboard_frame.py -v -k "status_colors or progress_bar"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/rich_dashboard.py tests/test_rich_dashboard_frame.py
git commit -m "feat(ui): add status colors and progress bar helper"
```

---

## Task 3: Add row/summary/footer render helpers

**Files:**
- Modify: `src/pkg_upgrade/ui/rich_dashboard.py`
- Test: `tests/test_rich_dashboard_frame.py`

- [ ] **Step 1: Write failing unit tests**

Append to `tests/test_rich_dashboard_frame.py`:

```python
from pkg_upgrade.ui.rich_dashboard import (
    render_footer,
    render_row,
    render_summary,
)


def test_render_row_shows_focus_marker_and_counts() -> None:
    row = Row("brew", "Homebrew", "H", ManagerStatus.UPGRADING, 3, 10, 5, [])
    out = render_row(row, GlyphTable.ascii(), tick=0, focused=True, expanded=False).plain
    assert out.lstrip().startswith(">")
    assert "Homebrew" in out
    assert "3/10" in out


def test_render_row_unfocused_has_no_marker() -> None:
    row = Row("brew", "Homebrew", "H", ManagerStatus.PENDING, 0, 0, 0, [])
    out = render_row(row, GlyphTable.ascii(), tick=0, focused=False, expanded=False).plain
    assert not out.lstrip().startswith(">")


def test_render_row_done_has_check_suffix() -> None:
    row = Row("pip", "pip", "P", ManagerStatus.DONE, 4, 4, 9, [])
    out = render_row(row, GlyphTable.ascii(), tick=0, focused=False, expanded=False).plain
    assert out.rstrip().endswith("v")


def test_render_row_failed_has_cross_suffix() -> None:
    row = Row("npm", "npm", "N", ManagerStatus.ERROR, 1, 3, 2, [])
    out = render_row(row, GlyphTable.ascii(), tick=0, focused=False, expanded=False).plain
    assert out.rstrip().endswith("x")


def test_render_summary_counts_totals() -> None:
    rows = [
        Row("a", "a", "", ManagerStatus.DONE, 2, 2, 0, []),
        Row("b", "b", "", ManagerStatus.UPGRADING, 1, 5, 0, []),
    ]
    out = render_summary(UIModel(rows=rows), elapsed_s=65, tick=0).plain
    assert "3/7" in out
    assert "1:05" in out


def test_render_footer_contains_keybinds() -> None:
    out = render_footer().plain
    for key in ("j/k", "enter", "y", "s", "q"):
        assert key in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rich_dashboard_frame.py -v -k "render_row or render_summary or render_footer"`
Expected: FAIL — helpers not defined.

- [ ] **Step 3: Implement helpers in `rich_dashboard.py`**

Add these functions below `render_progress_bar`:

```python
_BAR_WIDTH = 10
_NAME_WIDTH = 12
_STATUS_WIDTH = 20


def render_row(
    row: Row,
    glyphs: GlyphTable,
    tick: int,
    *,
    focused: bool,
    expanded: bool,  # noqa: ARG001 — reserved; expansion block rendered by render_rows
) -> Text:
    marker = ">" if focused else " "
    color = STATUS_COLORS[row.status]

    from pkg_upgrade.status import ACTIVE_STATUSES

    if row.status in ACTIVE_STATUSES and row.status != ManagerStatus.PENDING:
        status_label = f"{glyphs.spinner(tick)} {glyphs.status(row.status)}"
    else:
        status_label = glyphs.status(row.status)

    suffix = ""
    if row.status == ManagerStatus.DONE:
        suffix = "v" if glyphs.spinner_frames[0] == "|" else "✓"
    elif row.status == ManagerStatus.ERROR:
        suffix = "x" if glyphs.spinner_frames[0] == "|" else "✗"

    line = Text()
    line.append(f"{marker} ")
    line.append(f"{row.icon} ")
    line.append(f"{row.name:<{_NAME_WIDTH}} ", style="bold" if focused else "")
    line.append(f"{status_label:<{_STATUS_WIDTH}} ", style=color)
    line.append_text(render_progress_bar(row.done, row.total, _BAR_WIDTH, color))
    line.append(f"  {_fmt_progress(row.done, row.total):<8}")
    line.append(f"{_fmt_duration(row.duration_s):>6}")
    if suffix:
        line.append(f"  {suffix}", style=color)
    return line


def render_summary(model: UIModel, elapsed_s: int, tick: int) -> Text:  # noqa: ARG001
    done = sum(r.done for r in model.rows)
    total = sum(r.total for r in model.rows)
    active_left = sum(1 for r in model.rows if r.status in ACTIVE_STATUSES)

    t = Text()
    t.append_text(render_progress_bar(done, total, _BAR_WIDTH, "cyan"))
    t.append(f"  {done}/{total} packages  ", style="bold")
    t.append(f"{active_left} mgrs left  ", style="dim")
    t.append(f"{_fmt_duration(elapsed_s)} elapsed", style="dim")
    return t


def render_footer() -> Text:
    return Text(
        "  j/k move   enter expand   y confirm   s skip   q quit",
        style="dim",
    )
```

Ensure `ACTIVE_STATUSES` is imported at module top: add `from pkg_upgrade.status import ACTIVE_STATUSES, ManagerStatus` (merge with existing import line).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rich_dashboard_frame.py -v -k "render_row or render_summary or render_footer"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pkg_upgrade/ui/rich_dashboard.py tests/test_rich_dashboard_frame.py
git commit -m "feat(ui): add row, summary, and footer render helpers"
```

---

## Task 4: Refactor `build_frame` to use Layout + new helpers

**Files:**
- Modify: `src/pkg_upgrade/ui/rich_dashboard.py`
- Modify: `tests/test_rich_dashboard_frame.py`
- Delete + regenerate: `tests/fixtures/rich_ui/*.txt`

- [ ] **Step 1: Update existing goldens test helper to pass `tick`**

In `tests/test_rich_dashboard_frame.py`, change `_render` to:

```python
def _render(model: UIModel) -> str:
    c = Console(
        width=80,
        height=30,
        record=True,
        force_terminal=True,
        color_system=None,
        legacy_windows=False,
    )
    c.print(build_frame(model, GlyphTable.ascii(), elapsed_seconds=42, tick=0))
    return c.export_text()
```

Add two new golden scenarios at the bottom of the file:

```python
def test_frame_all_done() -> None:
    rows = [
        Row("brew", "Homebrew", "H", ManagerStatus.DONE, 12, 12, 30, []),
        Row("pip", "pip", "P", ManagerStatus.DONE, 4, 4, 9, []),
    ]
    _assert_golden("all_done", _render(UIModel(rows=rows)))


def test_frame_failed_row() -> None:
    rows = _base_rows()
    rows[0].status = ManagerStatus.ERROR
    _assert_golden("failed", _render(UIModel(rows=rows)))
```

- [ ] **Step 2: Delete stale goldens so they regenerate**

```bash
rm -f tests/fixtures/rich_ui/*.txt
```

- [ ] **Step 3: Refactor `build_frame` in `rich_dashboard.py`**

Replace the existing `build_frame` with:

```python
def build_frame(
    model: UIModel,
    glyphs: GlyphTable,
    *,
    elapsed_seconds: int = 0,
    tick: int = 0,
) -> RenderableType:
    focus_key = model.focus_key
    use_rounded = glyphs.spinner_frames[0] != "|"  # unicode => rounded, ascii => ascii box

    header = Text(
        f"  {'MANAGER':<{_NAME_WIDTH + 3}} {'STATUS':<{_STATUS_WIDTH}} "
        f"{'PROGRESS':<{_BAR_WIDTH + 2}}  {'PKGS':<8}{'DUR':>6}",
        style="bold",
    )

    row_items: list[RenderableType] = [
        render_summary(model, elapsed_seconds, tick),
        Text(""),
        header,
    ]
    for r in model.visible_rows:
        row_items.append(
            render_row(r, glyphs, tick, focused=r.key == focus_key, expanded=r.key == model.expanded_key)
        )
        if r.key == model.expanded_key:
            row_items.append(Text(""))
            row_items.append(Text(f"  [{r.key}] log:", style="bold"))
            for log_line in r.log[-8:]:
                row_items.append(Text(f"    {log_line}", style="dim"))
            row_items.append(Text(""))

    if model.filter_text:
        row_items.append(Text(""))
        row_items.append(Text(f"  filter: /{model.filter_text}", style="magenta"))

    body = Group(*row_items)
    panel = Panel(
        body,
        title="pkg-upgrade",
        border_style="dim",
        box=box.ROUNDED if use_rounded else box.ASCII,
        padding=(0, 1),
    )
    return Group(panel, render_footer())
```

Remove the old `header` / `rows_renderables` block entirely.

- [ ] **Step 4: Run goldens tests to regenerate fixtures**

Run: `pytest tests/test_rich_dashboard_frame.py -v`
Expected: PASS (first run writes new fixtures; subsequent runs compare).

- [ ] **Step 5: Re-run to verify goldens are stable**

Run: `pytest tests/test_rich_dashboard_frame.py -v`
Expected: PASS with no fixture writes.

- [ ] **Step 6: Inspect one fixture manually and sanity-check layout**

Run: `cat tests/fixtures/rich_ui/mixed.txt`
Expected: summary line with progress bar + counts, rounded-equivalent ASCII panel border, manager rows with `█`/`░` bars, footer keybinds below the panel.

- [ ] **Step 7: Commit**

```bash
git add src/pkg_upgrade/ui/rich_dashboard.py tests/test_rich_dashboard_frame.py tests/fixtures/rich_ui/
git commit -m "feat(ui): btop-style layered dashboard frame"
```

---

## Task 5: Wrap `RichDashboardUI.run` in a ticking `Live` loop

**Files:**
- Modify: `src/pkg_upgrade/ui/rich_dashboard.py`
- Test: `tests/test_rich_dashboard_input.py` (verify tests still pass with the new loop)

- [ ] **Step 1: Read current input tests**

Run: `cat tests/test_rich_dashboard_input.py` — confirm they drive `run()` with `FakeInput`. If they construct `RichDashboardUI(input=FakeInput(...))` and call `run`, the new loop must still let `FakeInput` drive keys to completion without requiring a real TTY.

- [ ] **Step 2: Update `RichDashboardUI.run` to use `Live`**

Replace the existing `run` method with:

```python
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
        tick = 0

        from rich.live import Live

        with Live(
            build_frame(model, self._glyphs, elapsed_seconds=0, tick=tick),
            refresh_per_second=8,
            transient=False,
            auto_refresh=False,
        ) as live:
            while not model.all_done():
                key = await self._read_key_soft()
                if key is None:
                    break
                result = await self._handle_key(key, model, executor)
                if result is None:
                    break
                model = result
                tick += 1
                live.update(
                    build_frame(model, self._glyphs, elapsed_seconds=0, tick=tick),
                    refresh=True,
                )
```

Note: `auto_refresh=False` + manual `live.update(..., refresh=True)` keeps the existing deterministic input-driven test behavior (tests don't rely on wall-clock ticking). A follow-up can add a background tick task; for this plan, animation advances on each key event, which is sufficient for the visible "alive" feel during user interaction.

If `quiet` is truthy, skip `Live` entirely and fall back to the previous simple loop. Add at the top of the interactive branch:

```python
        if self._quiet:
            while not model.all_done():
                key = await self._read_key_soft()
                if key is None:
                    break
                result = await self._handle_key(key, model, executor)
                if result is None:
                    break
                model = result
            return
```

- [ ] **Step 3: Run dashboard input tests**

Run: `pytest tests/test_rich_dashboard_input.py -v`
Expected: PASS (interactive behavior unchanged).

- [ ] **Step 4: Run full test suite**

Run: `pytest -x`
Expected: PASS.

- [ ] **Step 5: Manual smoke test**

Run: `pkg-upgrade --dry-run` and then `pkg-upgrade` (interactive). Visually confirm:
- Summary bar shows overall progress and elapsed/managers counts.
- Rows have two-tone bars with status-colored fills.
- Focus marker `>` (or `▸` on unicode) follows `j`/`k`.
- Keybind footer renders below the panel.
- `q` exits cleanly.

- [ ] **Step 6: Commit**

```bash
git add src/pkg_upgrade/ui/rich_dashboard.py
git commit -m "feat(ui): drive interactive dashboard with rich Live loop"
```

---

## Task 6: Lint, typecheck, coverage sweep

- [ ] **Step 1: Ruff**

Run: `ruff check . && ruff format --check .`
Expected: clean. Fix anything flagged; commit as `chore: ruff fixes`.

- [ ] **Step 2: Mypy**

Run: `mypy`
Expected: no errors under strict mode. Fix with precise types (no `Any` unless unavoidable); commit as `chore: mypy fixes`.

- [ ] **Step 3: Full pytest with coverage**

Run: `pytest --cov --cov-report=term-missing`
Expected: all green. Confirm `rich_dashboard.py` coverage is ≥ prior baseline.

- [ ] **Step 4: Pre-commit**

Run: `pre-commit run --all-files`
Expected: clean.

- [ ] **Step 5: Final commit if anything moved**

```bash
git status
# commit any outstanding formatting
```

---

## Self-Review Notes

- **Spec coverage:** summary bar ✓ (Task 3 `render_summary`), manager rows with two-tone bars ✓ (Tasks 2–3), inline expanded log ✓ (Task 4 `build_frame`), keybind footer ✓ (Task 3 `render_footer`), status→color map ✓ (Task 2), spinner + tick ✓ (Tasks 1, 3, 5), ASCII fallback ✓ (Task 4 `use_rounded`), goldens cover the 5+ required scenarios ✓ (Task 4). `NO_COLOR` is implicitly covered — Rich's renderer disables styles when set; the tests already use `color_system=None` which mirrors that path.
- **Placeholders:** none. Every code step shows the actual code.
- **Type consistency:** `build_frame` signature `(model, glyphs, *, elapsed_seconds, tick)` used consistently in Tasks 4 and 5 and tests. `render_progress_bar(done, total, width, color) -> Text` used consistently in Tasks 2, 3. `STATUS_COLORS` is `dict[ManagerStatus, str]` throughout.
- **Scope:** single subsystem (interactive Rich dashboard renderer). No executor or manager changes. One plan is appropriate.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-13-tui-btop-redesign.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks.
2. **Inline Execution** — Execute tasks in this session with checkpoints.

Which approach?
