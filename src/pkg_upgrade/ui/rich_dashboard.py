from __future__ import annotations

import asyncio
import contextlib
import sys
import time
from typing import Any

from rich import box
from rich.console import Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
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

_BAR_WIDTH = 12
_NAME_WIDTH = 18
_STATUS_WIDTH = 22


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


def _status_label(row: Row, glyphs: GlyphTable, tick: int) -> str:
    if row.status in ACTIVE_STATUSES and row.status != ManagerStatus.PENDING:
        return f"{glyphs.spinner(tick)} {glyphs.status(row.status)}"
    return glyphs.status(row.status)


def _suffix_glyph(row: Row, glyphs: GlyphTable) -> str:
    if row.status == ManagerStatus.DONE:
        return "✓" if glyphs.use_unicode else "v"
    if row.status == ManagerStatus.ERROR:
        return "✗" if glyphs.use_unicode else "x"
    return ""


def render_row(
    row: Row,
    glyphs: GlyphTable,
    tick: int,
    *,
    focused: bool,
    expanded: bool,
) -> Text:
    _ = expanded
    """Legacy single-line row renderer kept for unit tests. build_frame uses a Table."""
    marker = ">" if focused else " "
    color = STATUS_COLORS[row.status]
    status_label = _status_label(row, glyphs, tick)
    suffix = _suffix_glyph(row, glyphs)

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


def _rows_table(model: UIModel, glyphs: GlyphTable, tick: int) -> Table:
    focus_key = model.focus_key
    table = Table(
        show_header=True,
        show_edge=False,
        show_lines=False,
        box=None,
        pad_edge=False,
        expand=True,
        header_style="bold dim",
    )
    table.add_column("", width=1, no_wrap=True)
    table.add_column("", width=2, no_wrap=True)
    table.add_column("MANAGER", min_width=_NAME_WIDTH, overflow="ellipsis", no_wrap=True)
    table.add_column("STATUS", width=_STATUS_WIDTH, no_wrap=True)
    table.add_column("PROGRESS", width=_BAR_WIDTH, no_wrap=True)
    table.add_column("PKGS", width=8, justify="right", no_wrap=True)
    table.add_column("DUR", width=6, justify="right", no_wrap=True)
    table.add_column("", width=1, no_wrap=True)

    for r in model.visible_rows:
        color = STATUS_COLORS[r.status]
        focused = r.key == focus_key
        marker = (
            Text("▸" if glyphs.use_unicode else ">", style="bold cyan") if focused else Text(" ")
        )
        icon = Text(r.icon)
        name_style = "bold" if focused else ""
        name = Text(r.name, style=name_style)
        status_text = _status_label(r, glyphs, tick)
        status = Text(status_text, style=color)
        progress = render_progress_bar(r.done, r.total, _BAR_WIDTH, color)
        pkgs = Text(_fmt_progress(r.done, r.total), style="dim" if r.total == 0 else "")
        dur = Text(_fmt_duration(r.duration_s), style="dim")
        suffix = Text(_suffix_glyph(r, glyphs), style=color)
        table.add_row(marker, icon, name, status, progress, pkgs, dur, suffix)
    return table


def render_summary(model: UIModel, elapsed_s: int) -> Text:
    done = sum(r.done for r in model.rows)
    total = sum(r.total for r in model.rows)
    active_left = sum(1 for r in model.rows if r.status in ACTIVE_STATUSES)
    ok = sum(1 for r in model.rows if r.status == ManagerStatus.DONE)
    failed = sum(1 for r in model.rows if r.status == ManagerStatus.ERROR)
    skipped = sum(1 for r in model.rows if r.status == ManagerStatus.SKIPPED)

    t = Text()
    t.append_text(render_progress_bar(done, total, _BAR_WIDTH, "cyan"))
    t.append(f"  {done}/{total} packages  ", style="bold")
    t.append(f"{active_left} mgrs left  ", style="dim")
    t.append(f"{_fmt_duration(elapsed_s)} elapsed", style="dim")
    t.append("\n")
    t.append(f"  {ok} ok", style="green")
    t.append(" · ", style="dim")
    t.append(f"{failed} failed", style="red" if failed else "dim")
    t.append(" · ", style="dim")
    t.append(f"{skipped} skipped", style="dim")
    return t


def render_footer(*, end_of_run: bool = False) -> Text:
    if end_of_run:
        return Text("  press any key to exit", style="dim")
    return Text(
        "  j/k move • enter expand • y confirm • s skip • q quit",
        style="dim",
    )


def _expansion_block(row: Row) -> list[RenderableType]:
    items: list[RenderableType] = [Text("")]
    items.append(Text(f"  [{row.key}] log:", style="bold"))
    if row.error:
        items.append(Text(f"    ! {row.error}", style="red"))
    for log_line in row.log[-8:]:
        style = "red" if log_line.startswith("FAIL") else "dim"
        items.append(Text(f"    {log_line}", style=style))
    items.append(Text(""))
    return items


def _error_hint(row: Row) -> Text:
    return Text(f"    ! {row.error}", style="red")


def build_frame(
    model: UIModel,
    glyphs: GlyphTable,
    *,
    elapsed_seconds: int = 0,
    tick: int = 0,
    end_of_run: bool = False,
) -> RenderableType:
    use_rounded = glyphs.use_unicode

    body_items: list[RenderableType] = [
        render_summary(model, elapsed_seconds),
        Text(""),
    ]

    expanded_key = model.expanded_key
    if expanded_key is None:
        body_items.append(_rows_table(model, glyphs, tick))
        for r in model.visible_rows:
            if r.status == ManagerStatus.ERROR and r.error:
                body_items.append(_error_hint(r))
    else:
        body_items.append(_rows_table(model, glyphs, tick))
        for r in model.visible_rows:
            if r.key == expanded_key:
                body_items.extend(_expansion_block(r))
            elif r.status == ManagerStatus.ERROR and r.error:
                body_items.append(_error_hint(r))

    if model.filter_text:
        body_items.append(Text(""))
        body_items.append(Text(f"  filter: /{model.filter_text}", style="magenta"))

    clock = _fmt_duration(elapsed_seconds) if elapsed_seconds > 0 else "0:00"
    title = f"pkg-upgrade · {clock}"
    panel = Panel(
        Group(*body_items),
        title=title,
        border_style="cyan" if end_of_run else "dim",
        box=box.ROUNDED if use_rounded else box.ASCII,
        padding=(0, 1),
    )
    return Group(panel, render_footer(end_of_run=end_of_run))


def build_summary_frame(
    model: UIModel,
    glyphs: GlyphTable,
    *,
    elapsed_seconds: int,
) -> RenderableType:
    use_rounded = glyphs.use_unicode
    total = sum(r.total for r in model.rows)
    done = sum(r.done for r in model.rows)
    ok = sum(1 for r in model.rows if r.status == ManagerStatus.DONE)
    failed = sum(1 for r in model.rows if r.status == ManagerStatus.ERROR)
    skipped = sum(1 for r in model.rows if r.status == ManagerStatus.SKIPPED)

    clock = _fmt_duration(elapsed_seconds) if elapsed_seconds > 0 else "0:00"
    header = Text()
    header.append("Upgrade complete", style="bold green" if not failed else "bold yellow")
    header.append(f"  in {clock}\n", style="dim")

    stats = Text()
    stats.append(f"  {done}/{total} packages upgraded", style="bold")
    stats.append("\n")
    stats.append(f"  {ok} managers ok", style="green")
    stats.append(" · ", style="dim")
    stats.append(f"{failed} failed", style="red" if failed else "dim")
    stats.append(" · ", style="dim")
    stats.append(f"{skipped} skipped", style="dim")

    failures: list[RenderableType] = []
    for r in model.rows:
        if r.status == ManagerStatus.ERROR:
            failures.append(Text(""))
            failures.append(Text(f"  ✗ {r.name}", style="bold red"))
            if r.error:
                failures.append(Text(f"    {r.error}", style="red"))
            for log_line in r.log[-5:]:
                if log_line.startswith("FAIL"):
                    failures.append(Text(f"    {log_line}", style="red"))

    body = Group(header, stats, *failures)
    panel = Panel(
        body,
        title=f"pkg-upgrade · {_fmt_duration(elapsed_seconds)}",
        border_style="green" if not failed else "yellow",
        box=box.ROUNDED if use_rounded else box.ASCII,
        padding=(0, 1),
    )
    return Group(panel, render_footer(end_of_run=True))


class RichDashboardUI:
    def __init__(self, input: KeyInput | None = None, quiet: bool = False) -> None:
        self._input: KeyInput = input if input is not None else RealInput()
        self._quiet = quiet
        self._glyphs: GlyphTable = pick_glyph_table(sys.stdout.encoding)

    def _build_model(self, executor: Any) -> UIModel:
        rows: list[Row] = []
        for key, s in executor.states.items():
            log_lines: list[str] = []
            failed = 0
            for item in s.results:
                name, ok = _coerce_result(item)
                log_lines.append(f"{'ok' if ok else 'FAIL'} {name}")
                if not ok:
                    failed += 1
            rows.append(
                Row(
                    key=key,
                    name=s.manager.name,
                    icon=getattr(s.manager, "icon", ""),
                    status=s.status,
                    done=len(s.results),
                    total=len(s.outdated),
                    duration_s=0,
                    log=log_lines,
                    error=getattr(s, "error", None),
                    failed=failed,
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

        if self._quiet:
            await self._run_quiet(executor, auto_yes=auto_yes)
            return

        await self._run_live(executor, auto_yes=auto_yes)

    async def _run_quiet(self, executor: Any, *, auto_yes: bool) -> None:
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

    async def _run_live(self, executor: Any, *, auto_yes: bool) -> None:
        start_time = time.monotonic()
        tick = 0

        def elapsed() -> int:
            return int(time.monotonic() - start_time)

        def build_running_frame() -> RenderableType:
            return build_frame(
                self._build_model(executor),
                self._glyphs,
                elapsed_seconds=elapsed(),
                tick=tick,
            )

        upgrade_task: asyncio.Task[None] | None = None
        if auto_yes:
            upgrade_task = asyncio.create_task(self._auto_upgrade(executor))

        aborted = False
        with Live(
            build_running_frame(),
            refresh_per_second=8,
            transient=False,
        ) as live:
            # Main loop: tick the spinner, race key reads against ticks.
            while True:
                model = self._build_model(executor)
                if model.all_done() and (upgrade_task is None or upgrade_task.done()):
                    break

                key_task = asyncio.create_task(self._read_key_soft())
                sleep_task: asyncio.Task[Any] = asyncio.create_task(asyncio.sleep(0.125))
                pending_tasks: list[asyncio.Task[Any]] = [key_task, sleep_task]
                if upgrade_task is not None:
                    pending_tasks.append(upgrade_task)
                done_tasks, _ = await asyncio.wait(
                    pending_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if key_task in done_tasks:
                    key = key_task.result()
                    if key is not None:
                        result = await self._handle_key(key, model, executor)
                        if result is None:
                            aborted = True
                            break
                else:
                    key_task.cancel()

                if sleep_task not in done_tasks:
                    sleep_task.cancel()

                tick += 1
                live.update(build_running_frame())

            if upgrade_task is not None and not upgrade_task.done():
                upgrade_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await upgrade_task

            # Final summary — keep Live open until user presses a key.
            if not aborted:
                final_model = self._build_model(executor)
                live.update(
                    build_summary_frame(final_model, self._glyphs, elapsed_seconds=elapsed())
                )
                await self._read_key_soft()

    async def _auto_upgrade(self, executor: Any) -> None:
        # Keep auto-confirming any manager that reaches AWAITING_CONFIRM.
        while True:
            pending = [
                k for k, s in executor.states.items() if s.status == ManagerStatus.AWAITING_CONFIRM
            ]
            if not pending:
                if all(s.status not in ACTIVE_STATUSES for s in executor.states.values()):
                    return
                await asyncio.sleep(0.1)
                continue
            for key in pending:
                if executor.states[key].status == ManagerStatus.AWAITING_CONFIRM:
                    await executor.upgrade_manager(key)


def _coerce_result(item: Any) -> tuple[str, bool]:
    """Normalize both real Result dataclasses and legacy (name, ok) tuples."""
    if hasattr(item, "package") and hasattr(item, "success"):
        return (item.package.name, bool(item.success))
    if isinstance(item, tuple) and len(item) == 2:
        return (str(item[0]), bool(item[1]))
    return (str(item), True)
