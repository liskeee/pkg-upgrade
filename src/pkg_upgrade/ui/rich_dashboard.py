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


def _fmt_duration(s: int) -> str:
    if s <= 0:
        return "--"
    m, sec = divmod(s, 60)
    return f"{m}:{sec:02d}"


def _fmt_progress(done: int, total: int) -> str:
    if total <= 0:
        return "--"
    return f"{done}/{total}"


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
    return Panel(Group(*rows_renderables), title=title, border_style="cyan", box=box.ROUNDED)


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
