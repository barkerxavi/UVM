from unittest.mock import patch

import pytest
from usdvm import usdview_launcher as launcher


@pytest.mark.parametrize('platform,python', [('win32', 'python/python.exe'), ('linux', 'python/bin/python3')])
def test_launch_uses_own_runtime(tmp_path, monkeypatch, platform, python):
    root = tmp_path / 'USD runtime'
    for rel in ('bin/usdview', python):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    asset = tmp_path / 'asset with spaces.usda'
    asset.touch()
    monkeypatch.setenv('UVM_USD_ROOT', str(root))
    monkeypatch.setenv('PYTHONPATH', '/unrelated/dcc')
    monkeypatch.setenv('QT_PLUGIN_PATH', '/unrelated/qt')
    monkeypatch.setattr(launcher.sys, 'platform', platform)
    with patch.object(launcher.subprocess, 'Popen') as popen:
        launcher.launch(asset)
    args, kwargs = popen.call_args
    assert args[0] == [str(root / python), str(root / 'bin/usdview'), str(asset)]
    assert '/unrelated/dcc' not in kwargs['env']['PYTHONPATH']
    assert 'QT_PLUGIN_PATH' not in kwargs['env']


def test_frozen_location(tmp_path, monkeypatch):
    monkeypatch.delenv('UVM_USD_ROOT', raising=False)
    monkeypatch.setattr(launcher.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(launcher.sys, 'executable', str(tmp_path / 'uvm.exe'))
    assert launcher.installation_dir().parent == tmp_path


def test_missing_interpreter_disables_viewer(tmp_path, monkeypatch):
    monkeypatch.setenv('UVM_USD_ROOT', str(tmp_path))
    (tmp_path / 'bin').mkdir()
    (tmp_path / 'bin/usdview').touch()
    assert launcher.find_usdview() is None
    with pytest.raises(FileNotFoundError, match='UVM_USD_ROOT'):
        launcher.launch(tmp_path / 'asset.usda')
