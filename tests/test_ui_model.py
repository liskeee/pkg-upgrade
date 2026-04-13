from pkg_upgrade.status import ManagerStatus
from pkg_upgrade.ui._model import Row, UIModel


def _rows() -> list[Row]:
    return [
        Row(
            key="brew",
            name="Homebrew",
            icon="🍺",
            status=ManagerStatus.UPGRADING,
            done=3,
            total=12,
            duration_s=18,
            log=[],
        ),
        Row(
            key="cask",
            name="Casks",
            icon="🍻",
            status=ManagerStatus.PENDING,
            done=0,
            total=0,
            duration_s=0,
            log=[],
        ),
        Row(
            key="pip",
            name="pip",
            icon="🐍",
            status=ManagerStatus.DONE,
            done=4,
            total=4,
            duration_s=9,
            log=[],
        ),
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
