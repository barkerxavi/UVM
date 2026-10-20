from unittest.mock import patch

from PySide6.QtCore import QTimer
from usdvm import scanner, usd_writer
from usdvm.app import MainWindow


def test_window_rescan_and_event_loop(qapp, tmp_path):
    folder = tmp_path / 'hero' / 'v001'
    folder.mkdir(parents=True)
    (folder / 'hero.usda').write_text('#usda 1.0\n')
    usd_writer.write_sublayer_wrapper(folder.parent / 'hero.usd', 'v001/hero.usda')
    win = MainWindow()
    win.open_root(tmp_path)
    assert win.asset_list.count() == 1
    win.asset_list.setCurrentRow(0)
    assert win.version_table.rowCount() == 1
    assert win.version_table.item(0, 5).text() == 'Yes'
    win.show()
    QTimer.singleShot(10, win.close)
    QTimer.singleShot(20, qapp.quit)
    assert qapp.exec() == 0


def test_new_version_sets_new_row_current(qapp, tmp_path):
    from PySide6.QtWidgets import QMessageBox
    src = tmp_path / 'input.usda'
    src.write_text('#usda 1.0\n')
    win = MainWindow()
    win.open_root(tmp_path)
    win.db.add_asset('hero')
    win.refresh_assets()
    win.asset_list.setCurrentRow(0)
    with patch('usdvm.app.QFileDialog.getOpenFileName', return_value=(str(src), '')), \
         patch('usdvm.app.QInputDialog.getText', return_value=('publish', True)), \
         patch('usdvm.app.QMessageBox.question', return_value=QMessageBox.Yes):
        win.new_version()
        win.new_version()
    asset = win.db.get_asset('hero')
    current = win.db.get_version(asset['current_version_id'])
    assert current['version_num'] == 2
    assert usd_writer.read_current_target(scanner.wrapper_path(tmp_path, 'hero')) == 'v002/hero.usda'
    win.close()


def test_failed_project_open_retains_previous_project(qapp, tmp_path):
    win = MainWindow()
    win.open_root(tmp_path)
    original = win.db
    with patch('usdvm.app.QMessageBox.warning') as warning:
        win.open_root(tmp_path / 'missing' / 'child')
    warning.assert_called_once()
    assert win.db is original
    assert win.db.list_assets() == []
    win.close()


def test_close_during_loading_is_deferred(qapp):
    from unittest.mock import Mock
    win = MainWindow()
    worker = Mock()
    worker.isRunning.return_value = True
    win._mesh_loaders.append(worker)
    event = Mock()
    win.closeEvent(event)
    event.ignore.assert_called_once()
    win._mesh_loaders.clear()
    win.close()
