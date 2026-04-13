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
