from __future__ import annotations

from typing import Protocol

_SPECIALS = {
    "\r": "enter",
    "\n": "enter",
    "\x1b": "esc",
    "\x03": "ctrl-c",
    "\x7f": "backspace",
    "\x08": "backspace",
    "\t": "tab",
    " ": "space",
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
}


def normalize_key(raw: str) -> str:
    if raw in _SPECIALS:
        return _SPECIALS[raw]
    if len(raw) == 1 and raw.isprintable():
        return raw
    return raw


class KeyInput(Protocol):
    def read_key(self) -> str: ...


class RealInput:
    def read_key(self) -> str:
        import readchar  # noqa: PLC0415
        return normalize_key(readchar.readkey())


class FakeInput:
    def __init__(self, keys: list[str]) -> None:
        self._keys = iter(keys)

    def read_key(self) -> str:
        return next(self._keys)
