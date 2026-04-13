import pytest

from pkg_upgrade.parsers import get_parser, register_parser
from pkg_upgrade.parsers.generic import generic_regex


def test_registry_lookup():
    assert get_parser("generic_regex") is generic_regex


def test_register_and_lookup():
    def custom(stdout, **_):
        return []

    register_parser("custom_x", custom)
    assert get_parser("custom_x") is custom


def test_unknown_parser_raises():
    with pytest.raises(KeyError):
        get_parser("no_such_preset")


def test_generic_regex_parses_named_groups():
    stdout = "foo 1.0 -> 1.1\nbar 2.0 -> 2.5\n"
    packages = generic_regex(
        stdout,
        regex=r"^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$",
    )
    assert [(p.name, p.current_version, p.latest_version) for p in packages] == [
        ("foo", "1.0", "1.1"),
        ("bar", "2.0", "2.5"),
    ]


def test_generic_regex_skip_lines():
    stdout = "HEADER\nfoo 1 -> 2\n"
    packages = generic_regex(
        stdout,
        regex=r"^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$",
        skip_first_line=True,
    )
    assert [p.name for p in packages] == ["foo"]


def test_generic_regex_ignores_non_matching_lines():
    stdout = "garbage\nfoo 1 -> 2\nmore garbage\n"
    packages = generic_regex(
        stdout,
        regex=r"^(?P<name>\S+) (?P<current>\S+) -> (?P<latest>\S+)$",
    )
    assert [p.name for p in packages] == ["foo"]
