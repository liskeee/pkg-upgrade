from __future__ import annotations

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from pkg_upgrade.ui._glyphs import GlyphTable
from pkg_upgrade.ui._model import UIModel


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
    return Panel(Group(*rows_renderables), title=title, border_style="cyan")
