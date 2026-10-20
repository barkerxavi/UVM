"""Application identity, bundled artwork and per-user GNOME integration."""
import os
import shutil
import sys
from pathlib import Path

from PySide6.QtGui import QIcon

APP_ID = 'com.xavitools.UVM'
ASSETS = Path(__file__).resolve().parent / 'assets'


def application_icon():
    return QIcon(str(ASSETS / 'uvm.png'))


def configure_application(app):
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName('USD Version Manager')
    app.setOrganizationName('XaviTools')
    app.setWindowIcon(application_icon())
    if sys.platform.startswith('linux'):
        app.setDesktopFileName(APP_ID)


def configure_windows_identity():
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


def _quote_exec(argument):
    # Desktop Entry Exec quoting, including field-code and string-value escapes.
    escaped = str(argument).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        escaped = escaped.replace(char, '\\' + char)
    return '"' + escaped.replace('\\', '\\\\') + '"'


def install_linux_shortcut():
    """Register the current executable and a persistent icon, never a temp path."""
    if not sys.platform.startswith('linux'):
        raise ValueError('Desktop entry registration is only needed on Linux.')
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share')))
    if not data_home.is_absolute():
        raise ValueError('XDG_DATA_HOME must be an absolute path.')
    applications = data_home / 'applications'
    icons = data_home / 'icons' / 'hicolor' / '256x256' / 'apps'
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSETS / 'uvm.png', icons / (APP_ID + '.png'))
    command = [str(Path(sys.executable).resolve())]
    if not getattr(sys, 'frozen', False):
        command.extend(['-m', 'usdvm.app'])
    entry = applications / (APP_ID + '.desktop')
    entry.write_text(
        '[Desktop Entry]\nType=Application\nVersion=1.0\n'
        'Name=USD Version Manager\nComment=Manage and inspect USD asset versions\n'
        'Exec=' + ' '.join(_quote_exec(arg) for arg in command) + '\n'
        f'Icon={APP_ID}\nTerminal=false\nCategories=Graphics;3DGraphics;\n'
        f'StartupWMClass={APP_ID}\n', encoding='utf-8',
    )
    return entry
