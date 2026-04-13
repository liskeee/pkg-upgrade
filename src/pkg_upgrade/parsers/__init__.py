from __future__ import annotations

from collections.abc import Callable

from pkg_upgrade.models import Package

Parser = Callable[..., list[Package]]

_PARSERS: dict[str, Parser] = {}


def register_parser(name: str, fn: Parser) -> None:
    _PARSERS[name] = fn


def get_parser(name: str) -> Parser:
    try:
        return _PARSERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown parser preset: {name!r}") from exc


def known_parsers() -> list[str]:
    return sorted(_PARSERS)


from pkg_upgrade.parsers import (  # noqa: E402, F401
    apt,
    dnf,
    flatpak,
    generic,
    pacman,
)
