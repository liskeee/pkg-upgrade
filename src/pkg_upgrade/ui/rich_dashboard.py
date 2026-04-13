from __future__ import annotations

import asyncio
import sys
import time
from typing import Any

from rich import box
from rich.console import Group, RenderableType
from rich.live import Live
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
        suffix = "v" if not glyphs.use_unicode else "✓"
    elif row.status == ManagerStatus.ERROR:
        suffix = "x" if not glyphs.use_unicode else "✗"

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
    tick: int = 0,
) -> RenderableType:
    focus_key = model.focus_key
    use_rounded = glyphs.use_unicode

    header = Text(
        f"  {'MANAGER':<{_NAME_WIDTH + 3}} {'STATUS':<{_STATUS_WIDTH}} "
        f"{'PROGRESS':<{_BAR_WIDTH + 2}}  {'PKGS':<8}{'DUR':>6}",
        style="bold",
    )

    row_items: list[RenderableType] = [
        render_summary(model, elapsed_seconds),
        Text(""),
        header,
    ]
    for r in model.visible_rows:
        row_items.append(
            render_row(
                r,
                glyphs,
                tick,
                focused=r.key == focus_key,
                expanded=r.key == model.expanded_key,
            )
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

        model = self._build_model(executor)

        if self._quiet:
            if auto_yes:
                for key, s in list(executor.states.items()):
                    if s.outdated:
                        await executor.upgrade_manager(key)
                return
            while not model.all_done():
                key = await self._read_key_soft()
                if key is None:
                    break
                result = await self._handle_key(key, model, executor)
                if result is None:
                    break
                model = result
            return

        tick = 0
        start_time = time.monotonic()

        def _frame() -> Any:
            return build_frame(
                self._build_model(executor),
                self._glyphs,
                elapsed_seconds=int(time.monotonic() - start_time),
                tick=tick,
            )

        with Live(
            _frame(),
            refresh_per_second=8,
            transient=False,
        ) as live:
            if auto_yes:
                pending = [k for k, s in executor.states.items() if s.outdated]
                for key in pending:
                    task = asyncio.create_task(executor.upgrade_manager(key))
                    while not task.done():
                        await asyncio.sleep(0.125)
                        tick += 1
                        live.update(_frame())
                    await task
                tick += 1
                live.update(_frame())
                return

            while not model.all_done():
                key = await self._read_key_soft()
                if key is None:
                    break
                result = await self._handle_key(key, model, executor)
                if result is None:
                    break
                model = result
                tick += 1
                live.update(_frame())
