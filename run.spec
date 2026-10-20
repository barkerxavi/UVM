# Build on each target OS: python -m PyInstaller --clean --noconfirm run.spec
from PyInstaller.utils.hooks import collect_all
import sys
from pathlib import Path

usd_data, usd_binaries, usd_imports = collect_all('pxr')
assets = Path(SPECPATH) / 'usdvm' / 'assets'
usd_data.extend([(str(assets / 'uvm.png'), 'usdvm/assets')])
a = Analysis(
    ['run.py'], pathex=[], binaries=usd_binaries, datas=usd_data,
    hiddenimports=usd_imports, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name='uvm',
    debug=False, strip=False, upx=False, console=sys.platform != 'win32',
    icon=str(assets / 'uvm.ico') if sys.platform == 'win32' else None,
)
