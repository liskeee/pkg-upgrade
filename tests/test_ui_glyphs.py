from pkg_upgrade.status import ManagerStatus
from pkg_upgrade.ui._glyphs import GlyphTable, pick_glyph_table


def test_unicode_table_has_all_statuses() -> None:
    t = GlyphTable.unicode()
    for s in ManagerStatus:
        assert t.status(s) != ""


def test_ascii_table_has_all_statuses_and_is_ascii() -> None:
    t = GlyphTable.ascii()
    for s in ManagerStatus:
        g = t.status(s)
        assert g != ""
        assert g.encode("ascii")


def test_pick_glyph_table_falls_back_for_ascii_encoding() -> None:
    assert pick_glyph_table("utf-8").status(ManagerStatus.DONE) == GlyphTable.unicode().status(
        ManagerStatus.DONE
    )
    assert pick_glyph_table("ascii").status(ManagerStatus.DONE) == GlyphTable.ascii().status(
        ManagerStatus.DONE
    )


def test_unicode_spinner_frames_present() -> None:
    t = GlyphTable.unicode()
    assert t.spinner_frames == ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def test_ascii_spinner_frames_present() -> None:
    t = GlyphTable.ascii()
    assert t.spinner_frames == ("|", "/", "-", "\\")


def test_pick_glyph_table_ascii_has_ascii_spinner() -> None:
    assert pick_glyph_table("ascii").spinner_frames[0] == "|"
