from __future__ import annotations

from pathlib import Path

from rich.console import Console

from pkg_upgrade.status import ManagerStatus
from pkg_upgrade.ui._glyphs import GlyphTable
from pkg_upgrade.ui._model import Row, UIModel
from pkg_upgrade.ui.rich_dashboard import (
    STATUS_COLORS,
    build_frame,
    render_footer,
    render_progress_bar,
    render_row,
    render_summary,
)

FIXTURES = Path(__file__).parent / "fixtures" / "rich_ui"


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


def _assert_golden(name: str, output: str) -> None:
    path = FIXTURES / f"{name}.txt"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    assert output == path.read_text(encoding="utf-8")


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
