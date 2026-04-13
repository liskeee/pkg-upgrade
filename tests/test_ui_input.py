# tests/test_ui_input.py
import pytest

from pkg_upgrade.ui._input import FakeInput, normalize_key


def test_fake_input_returns_scripted_keys() -> None:
    fi = FakeInput(["j", "k", "enter", "q"])
    assert fi.read_key() == "j"
    assert fi.read_key() == "k"
    assert fi.read_key() == "enter"
    assert fi.read_key() == "q"


def test_fake_input_raises_when_exhausted() -> None:
    fi = FakeInput(["q"])
    fi.read_key()
    with pytest.raises(StopIteration):
        fi.read_key()


def test_normalize_key_arrows_and_specials() -> None:
    assert normalize_key("\x1b[A") == "up"
    assert normalize_key("\x1b[B") == "down"
    assert normalize_key("\x1b[C") == "right"
    assert normalize_key("\x1b[D") == "left"
    assert normalize_key("\r") == "enter"
    assert normalize_key("\n") == "enter"
    assert normalize_key("\x1b") == "esc"
    assert normalize_key("\x03") == "ctrl-c"
    assert normalize_key("\x7f") == "backspace"
    assert normalize_key("j") == "j"
    assert normalize_key("/") == "/"
