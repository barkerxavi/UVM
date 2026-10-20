import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtGui import QImage

from usdvm import desktop


def test_packaged_icons_and_window_identity(qapp):
    desktop.configure_application(qapp)
    assert not qapp.windowIcon().isNull()
    assert not QImage(str(desktop.ASSETS / 'uvm.png')).isNull()
    assert (desktop.ASSETS / 'uvm.ico').read_bytes()[:4] == b'\x00\x00\x01\x00'
    if sys.platform.startswith('linux'):
        assert qapp.desktopFileName() == desktop.APP_ID


def test_linux_shortcut_has_persistent_icon_and_no_terminal(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop.sys, 'platform', 'linux')
    monkeypatch.setattr(desktop.sys, 'frozen', True, raising=False)
    executable = tmp_path / 'folder with spaces' / 'uvm'
    monkeypatch.setattr(desktop.sys, 'executable', str(executable))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'user data'))
    entry = desktop.install_linux_shortcut()
    text = entry.read_text()
    assert 'Exec=' + desktop._quote_exec(executable) + '\n' in text
    assert 'Terminal=false\n' in text
    assert f'Icon={desktop.APP_ID}\n' in text
    icon = tmp_path / 'user data/icons/hicolor/256x256/apps' / (desktop.APP_ID + '.png')
    assert icon.read_bytes() == (desktop.ASSETS / 'uvm.png').read_bytes()
    assert str(desktop.ASSETS) not in text
    assert desktop.install_linux_shortcut() == entry


def test_source_shortcut_uses_installed_module(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop.sys, 'platform', 'linux')
    monkeypatch.setattr(desktop.sys, 'frozen', False, raising=False)
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    entry = desktop.install_linux_shortcut()
    assert '"-m" "usdvm.app"' in entry.read_text()


def test_shortcut_rejects_relative_xdg_path(monkeypatch):
    monkeypatch.setattr(desktop.sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_DATA_HOME', 'relative')
    with pytest.raises(ValueError, match='absolute'):
        desktop.install_linux_shortcut()


def test_windows_taskbar_identity(monkeypatch):
    monkeypatch.setattr(desktop.sys, 'platform', 'win32')
    library = Mock()
    with patch('ctypes.windll', library, create=True):
        desktop.configure_windows_identity()
    library.shell32.SetCurrentProcessExplicitAppUserModelID.assert_called_once_with(desktop.APP_ID)
