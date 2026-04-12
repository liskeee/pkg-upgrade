from unittest.mock import patch

import pytest

from pkg_upgrade.platform import current_os, is_windows_admin, linux_distro


def test_current_os_macos():
    with patch("sys.platform", "darwin"):
        assert current_os() == "macos"


def test_current_os_linux():
    with patch("sys.platform", "linux"):
        assert current_os() == "linux"


def test_current_os_windows():
    with patch("sys.platform", "win32"):
        assert current_os() == "windows"


def test_current_os_unknown_raises():
    with patch("sys.platform", "freebsd"):
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            current_os()


def test_linux_distro_reads_id_like(tmp_path):
    os_release = tmp_path / "os-release"
    os_release.write_text('ID=ubuntu\nID_LIKE="debian"\n')
    assert linux_distro(os_release) == "debian"


def test_linux_distro_falls_back_to_id(tmp_path):
    os_release = tmp_path / "os-release"
    os_release.write_text("ID=fedora\n")
    assert linux_distro(os_release) == "fedora"


def test_linux_distro_missing_file_returns_none(tmp_path):
    assert linux_distro(tmp_path / "nope") is None


def test_is_windows_admin_non_windows_returns_false():
    with patch("pkg_upgrade.platform.current_os", return_value="macos"):
        assert is_windows_admin() is False
