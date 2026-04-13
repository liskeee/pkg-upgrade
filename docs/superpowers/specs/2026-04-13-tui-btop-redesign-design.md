# TUI redesign: btop/yazi-inspired dashboard

**Date:** 2026-04-13
**Status:** Design approved, ready for implementation planning
**Scope:** `src/pkg_upgrade/ui/rich_dashboard.py` and `src/pkg_upgrade/ui/_glyphs.py`. No changes to executor, managers, or `plain_dashboard.py`.

## Goal

Replace the current single-panel table in `rich_dashboard.py` with a layered btop/yazi-style dashboard: summary bar, rich manager rows with two-tone progress bars, keybind footer. Terminal-native ANSI colors only — no hardcoded palette. The UI must feel *alive* during upgrades (ticking spinners, live progress) and remain quiet-but-legible when idle.

## Non-goals

- No split-pane focus/detail view. Expanded log stays inline under the focused row.
- No user-facing theme configuration. Semantic ANSI colors + `NO_COLOR` fallback only.
- No changes to `plain_dashboard.py` (degraded renderer for dumb terminals).
- No changes to `executor.py`, managers, `_model.py`, `_input.py`, or `status.py` semantics. The renderer consumes the existing `UIModel` / `Row` shapes.

## Layout

Single rounded outer `Panel` containing a Rich `Layout` split into three regions, with a dim keybind hint line rendered below the panel.

```
╭─ pkg-upgrade ─────────────── 01:23 elapsed ────╮
│  ▰▰▰▰▰▰▰▰▱▱▱▱   12/20 packages   3 mgrs left  │   summary bar
├────────────────────────────────────────────────┤
│ ▸ 🍺 brew     upgrading   ████████░░  8/10    │
│   🍺 cask     pending     ░░░░░░░░░░  0/3     │   manager rows
│   📦 pip      done        ██████████  5/5  ✓  │   (focus = ▸)
│   📦 npm      failed      ████░░░░░░  2/5  ✗  │
│                                                │
│   [brew] log:                                  │   inline expand
│     ok wget                                    │
│     ok curl                                    │
╰────────────────────────────────────────────────╯
  j/k move  enter expand  y confirm  s skip  q quit
```

### Summary bar

- App title + elapsed clock (reuses `_fmt_duration`).
- Overall progress bar: sum of `done` / sum of `total` across all managers, two-tone (bright accent filled, dim unfilled).
- Counts: `N/M packages`, `K mgrs left` (managers not in a terminal status).

### Manager rows

One row per manager, columns:

1. Focus marker: `▸` if focused, space otherwise.
2. Icon (from `manager.icon`, already present).
3. Name, left-padded to 15 chars.
4. Status: spinner frame (animated, for active statuses) + status label from `GlyphTable.status()`.
5. Two-tone inline progress bar, fixed width ~10 cells.
6. `done/total` counts.
7. Duration (reuses `_fmt_duration`).
8. Terminal-state glyph suffix: `✓` done, `✗` failed, blank otherwise.

When a row is the `expanded_key`, a blank line + `[key] log:` header + last 8 log lines render beneath it, indented two spaces, inside the same panel region.

### Keybind footer

Dim, single line, below the outer panel: `j/k move  enter expand  y confirm  s skip  q quit`. Uses `dim` style; rendered via `Console.print` after the `Live` renderable if placing inside the panel complicates the `Layout` (decision deferred to implementation).

## Colors (semantic, ANSI only)

Status → color map (used for both status label and the row's progress-bar fill):

| Status | Color |
|---|---|
| `CHECKING` | `blue` |
| `OUTDATED` / `AWAITING_CONFIRM` | `magenta` |
| `UPGRADING` | `yellow` |
| `DONE` | `green` |
| `FAILED` | `red` |
| `PENDING` / `SKIPPED` / `UP_TO_DATE` | `dim` |

Chrome (panel border, unfilled bar cells, keybind hints, separators): `dim`. No hex codes anywhere. `NO_COLOR` env var disables all styling and is respected by Rich automatically when set; the existing `pick_glyph_table` already falls back to ASCII glyphs when the encoding can't render Unicode.

## Animation

- Persistent render loop via `rich.live.Live(refresh_per_second=8)`.
- A monotonically increasing `tick: int` counter is passed into `build_frame`. The spinner frame for active rows is `SPINNER_FRAMES[tick % len(SPINNER_FRAMES)]`.
- Spinner frames: `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` (Unicode), fallback `|/-\` (ASCII) when glyphs unavailable.
- Elapsed clock and overall progress bar re-render every tick; per-manager rows only animate spinners for rows whose status is in `ACTIVE_STATUSES`.
- The render loop runs for the entire session (not hybrid) — simpler, and 8 Hz of pure-function frame builds is negligible.

## Code shape

Refactor `rich_dashboard.py` into small pure helpers, each independently testable:

```python
def render_summary(model: UIModel, elapsed_s: int, tick: int) -> RenderableType: ...
def render_rows(model: UIModel, glyphs: GlyphTable, tick: int) -> RenderableType: ...
def render_row(
    row: Row, glyphs: GlyphTable, tick: int, *, focused: bool, expanded: bool
) -> RenderableType: ...
def render_progress_bar(done: int, total: int, width: int, color: str) -> Text: ...
def render_footer() -> RenderableType: ...

def build_frame(
    model: UIModel, glyphs: GlyphTable, *, elapsed_seconds: int, tick: int
) -> RenderableType: ...
```

`build_frame` composes the three region helpers into a `Layout` wrapped in an outer rounded `Panel` (using `rich.box.ROUNDED`, not `ASCII`). Signature gains a required `tick` parameter — callers (and tests) must pass it.

`_glyphs.py` additions:

- `SPINNER_FRAMES_UNICODE: tuple[str, ...]` and `SPINNER_FRAMES_ASCII: tuple[str, ...]`.
- `GlyphTable` gains a `spinner_frames: tuple[str, ...]` field, selected by `pick_glyph_table` the same way as the existing tables.
- `STATUS_COLORS: dict[ManagerStatus, str]` mapping (defined in `rich_dashboard.py` since it's a renderer concern, not a glyph concern).

`RichDashboardUI.run` changes:

- Wrap the interactive key-read loop in `Live(build_frame(...), refresh_per_second=8, screen=False)`.
- Maintain a `tick` counter incremented on each refresh (via a small background task or `Live.refresh` hook).
- On each key event or tick, rebuild the model + frame and call `live.update(frame)`.
- The `auto_yes` and `dry_run` paths do not use `Live` — they stay headless as today.

## Testing

All rendering helpers are pure functions of their inputs — straightforward snapshot tests using Rich's recording console:

```python
console = Console(record=True, width=80, color_system="truecolor", force_terminal=True)
console.print(build_frame(model, glyphs, elapsed_seconds=83, tick=3))
assert console.export_text() == EXPECTED
```

Scenarios to cover (one snapshot each):

1. Idle — all managers `PENDING`, nothing to do.
2. Mid-upgrade — mixed `CHECKING` / `UPGRADING` / `DONE` rows, one focused and expanded with log lines.
3. All done — every row `DONE`, overall bar full.
4. Failed — one row `FAILED`, rest `DONE`.
5. Awaiting confirm — one row `AWAITING_CONFIRM`, focused.
6. Filter active — `model.filter_text` set, hidden rows excluded.
7. ASCII fallback — `pick_glyph_table` forced to ASCII table, spinner and bars render with ASCII glyphs.

Tick is injected as a parameter, so animated frames are deterministic. No sleep or timing in tests.

Existing tests for `rich_dashboard` (if any) get updated for the new `build_frame` signature; the `tick=0` default in tests keeps most call sites terse.

## Migration / risk

- `build_frame` signature changes (adds `tick`). Only internal callers exist; update `RichDashboardUI.run` and tests.
- `Live` render loop adds a persistent asyncio task. Ensure clean shutdown on `q` / `ctrl-c` / `SIGINT` — use `Live` as a context manager and cancel any background tick task in `finally`.
- Rounded box glyphs require Unicode. When `pick_glyph_table` returns the ASCII table, `build_frame` also selects `rich.box.ASCII` to avoid mojibake.
- `NO_COLOR` is handled by Rich natively; verify the snapshot tests run green with `NO_COLOR=1` set, too.

## Open questions

None at design time. Implementation-time decisions (exact bar width, whether the footer lives inside the outer panel or below it, exact `Layout` ratios) are left to the implementation plan and can be iterated on via snapshot tests.
