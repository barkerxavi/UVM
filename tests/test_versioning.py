from pathlib import Path
from unittest.mock import patch

import pytest
from pxr import Usd, UsdGeom

from usdvm import scanner, usd_writer
from usdvm.db import ProjectDB
from usdvm.gl_viewer import build_mesh_buffer


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'input.usda'
    stage = Usd.Stage.CreateNew(str(path))
    mesh = UsdGeom.Mesh.Define(stage, '/Triangle')
    mesh.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    mesh.CreateFaceVertexCountsAttr([3])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
    stage.GetRootLayer().Save()
    return path


def test_publish_switch_and_reopen(tmp_path, source):
    db = ProjectDB(tmp_path)
    asset = db.add_asset('hero')
    for num in (1, 2):
        assert db.next_version_num(asset['id']) == num
        dest = scanner.create_version_from_file(tmp_path, 'hero', num, source)
        vid = db.add_version(asset['id'], num, dest.relative_to(tmp_path))
        wrapper = scanner.wrapper_path(tmp_path, 'hero')
        target = dest.relative_to(wrapper.parent).as_posix()
        usd_writer.write_sublayer_wrapper(wrapper, target)
        db.set_current_version(asset['id'], vid)
        assert usd_writer.read_current_target(wrapper) == target
        stage = Usd.Stage.Open(str(wrapper))
        assert stage.GetPrimAtPath('/Triangle')
        del stage
    db.close()
    db = ProjectDB(tmp_path)
    assert db.get_asset('hero')['current_version_id'] == vid
    assert len(db.list_versions(asset['id'])) == 2
    assert [n for n, _ in scanner.discover_versions(tmp_path, 'hero')] == [1, 2]
    db.close()


def test_existing_version_cannot_be_overwritten(tmp_path, source):
    dest = scanner.create_version_from_file(tmp_path, 'hero', 1, source)
    before = dest.read_bytes()
    with pytest.raises(FileExistsError):
        scanner.create_version_from_file(tmp_path, 'hero', 1, source)
    assert dest.read_bytes() == before


def test_failed_copy_cleans_only_new_version(tmp_path, source):
    with patch('usdvm.scanner.shutil.copy2', side_effect=OSError('disk full')):
        with pytest.raises(OSError):
            scanner.create_version_from_file(tmp_path, 'hero', 1, source)
    assert not scanner.version_dir(tmp_path, 'hero', 1).exists()


def test_read_legacy_version_names(tmp_path):
    folder = tmp_path / 'hero' / 'v001'
    folder.mkdir(parents=True)
    (folder / 'hero_v001.usda').write_text('#usda 1.0\n')
    (folder / 'unrelated.usda').write_text('#usda 1.0\n')
    assert scanner.discover_versions(tmp_path, 'hero') == [(1, Path('hero/v001/hero_v001.usda'))]


@pytest.mark.parametrize('name', ['CON', 'nul', 'COM1', 'LPT9', '../hero', '', 'a b', 'hero.'])
def test_portable_asset_names(name):
    with pytest.raises(ValueError):
        scanner.validate_asset_name(name)


def test_atomic_wrapper_failure_preserves_current(tmp_path):
    wrapper = tmp_path / 'hero.usd'
    usd_writer.write_sublayer_wrapper(wrapper, 'v001/hero.usda')
    before = wrapper.read_bytes()
    with patch('usdvm.usd_writer.os.replace', side_effect=OSError('access denied')):
        with pytest.raises(OSError):
            usd_writer.write_sublayer_wrapper(wrapper, 'v002/hero.usda')
    assert wrapper.read_bytes() == before
    assert list(tmp_path.iterdir()) == [wrapper]


def test_remove_metadata_does_not_leave_orphans(tmp_path):
    db = ProjectDB(tmp_path)
    asset = db.add_asset('hero')
    db.add_version(asset['id'], 1, 'hero/v001/hero.usda')
    db.remove_asset(asset['id'])
    assert db.list_assets() == []
    assert db.list_versions(asset['id']) == []
    db.close()


def test_usd_inspection_and_mesh_buffer(source):
    info = usd_writer.try_inspect_stage(source)
    assert info['available'] and info['prims'] == ['/Triangle']
    data, count = build_mesh_buffer(str(source))
    assert count == 3
    assert len(data) == count * 6 * 4


def test_database_paths_are_portable_and_legacy_paths_migrate(tmp_path):
    db = ProjectDB(tmp_path)
    asset = db.add_asset('hero')
    vid = db.add_version(asset['id'], 1, r'hero\v001\hero.usda')
    assert db.get_version(vid)['file_path'] == 'hero/v001/hero.usda'
    db.conn.execute('UPDATE versions SET file_path=? WHERE id=?', (r'hero\v001\hero.usda', vid))
    db.conn.commit()
    db.close()
    db = ProjectDB(tmp_path)
    assert db.get_version(vid)['file_path'] == 'hero/v001/hero.usda'
    db.close()
