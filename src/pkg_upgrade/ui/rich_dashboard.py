from __future__ import annotations

import asyncio
import sys
from typing import Any

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from pkg_upgrade.status import ACTIVE_STATUSES, ManagerStatus
from pkg_upgrade.ui._glyphs import GlyphTable, pick_glyph_table
from pkg_upgrade.ui._input import FakeInput, KeyInput, RealInput
from pkg_upgrade.ui._model import Row, UIModel

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


def _fmt_duration(s: int) -> str:
    if s <= 0:
        return "--"
    m, sec = divmod(s, 60)
    return f"{m}:{sec:02d}"


def _fmt_progress(done: int, total: int) -> str:
    if total <= 0:
        return "--"
    return f"{done}/{total}"


_BAR_WIDTH = 10
_NAME_WIDTH = 12
_STATUS_WIDTH = 20


def render_row(
    row: Row,
    glyphs: GlyphTable,
    tick: int,
    *,
    focused: bool,
    # `expanded` is accepted for API symmetry; the expansion block is rendered
    # by build_frame, not by this helper.
    expanded: bool,
) -> Text:
    marker = ">" if focused else " "
    color = STATUS_COLORS[row.status]

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


def render_summary(
    model: UIModel,
    elapsed_s: int,
    # `tick` is reserved for Task 4/5 consumers.
    tick: int,
) -> Text:
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


def build_frame(
    model: UIModel,
    glyphs: GlyphTable,
    *,
    elapsed_seconds: int = 0,
) -> RenderableType:
    header = Text(
        f"{'':2}{'KEY':<8}{'MANAGER':<17}{'STATUS':<20}{'PROGRESS':<12}{'DURATION'}",
        style="bold",
    )

    rows_renderables: list[RenderableType] = [header]
    focus_key = model.focus_key

    for r in model.visible_rows:
        marker = ">" if r.key == focus_key else " "
        line = Text(
            f"{marker} {r.key:<7} {r.icon} {r.name:<15} "
            f"{glyphs.status(r.status):<20}"
            f"{_fmt_progress(r.done, r.total):<12}"
            f"{_fmt_duration(r.duration_s)}"
        )
        rows_renderables.append(line)
        if r.key == model.expanded_key:
            rows_renderables.append(Text(""))
            rows_renderables.append(Text(f"  [{r.key}] log:", style="bold"))
            for log_line in r.log[-8:]:
                rows_renderables.append(Text(f"    {log_line}"))
            rows_renderables.append(Text(""))

    if model.filter_text:
        rows_renderables.append(Text(""))
        rows_renderables.append(Text(f"  filter: /{model.filter_text}"))

    title = f"pkg-upgrade  {_fmt_duration(elapsed_seconds)} elapsed"
    return Panel(Group(*rows_renderables), title=title, border_style="cyan", box=box.ASCII)


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

    async def _handle_key(self, key: str, model: UIModel, executor: Any) -> UIModel | None:
        """Handle one keypress; return updated model or None to exit."""
        if key in {"q", "ctrl-c"}:
            return None
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
        return model

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
            result = await self._handle_key(key, model, executor)
            if result is None:
                break
            model = result
