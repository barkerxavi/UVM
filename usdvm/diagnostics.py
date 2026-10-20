"""Functional readiness check for installed and frozen distributions."""
from pathlib import Path
from tempfile import TemporaryDirectory


def smoke_test():
    from PySide6.QtCore import QSettings, QTimer
    from PySide6.QtWidgets import QApplication
    from pxr import Usd, UsdGeom
    from . import scanner, usd_writer
    from .app import MainWindow
    from .gl_viewer import build_mesh_buffer

    with TemporaryDirectory(prefix='uvm-smoke-') as tmp:
        root = Path(tmp)
        QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(root / 'settings'))
        source = root / 'input.usda'
        stage = Usd.Stage.CreateNew(str(source))
        mesh = UsdGeom.Mesh.Define(stage, '/Triangle')
        mesh.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
        mesh.CreateFaceVertexCountsAttr([3])
        mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
        stage.GetRootLayer().Save()
        del stage
        dest = scanner.create_version_from_file(root, 'hero', 1, source)
        wrapper = scanner.wrapper_path(root, 'hero')
        usd_writer.write_sublayer_wrapper(wrapper, dest.relative_to(wrapper.parent).as_posix())
        info = usd_writer.try_inspect_stage(wrapper)
        if info.get('prims') != ['/Triangle']:
            raise RuntimeError(f'USD composition/inspection failed: {info}')
        data, count = build_mesh_buffer(str(wrapper))
        if count != 3 or len(data) != 72:
            raise RuntimeError('USD mesh triangulation failed')
        app = QApplication.instance() or QApplication([])
        win = MainWindow()
        win.open_root(root)
        win.asset_list.setCurrentRow(0)
        if win.asset_list.count() != 1 or win.version_table.rowCount() != 1:
            raise RuntimeError('Project rescan/UI population failed')
        win.show()
        QTimer.singleShot(50, win.close)
        QTimer.singleShot(100, app.quit)
        code = app.exec()
        if code:
            raise RuntimeError(f'Qt event loop returned {code}')
    print('PASS: USD composition, inspection, mesh loading, SQLite/project rescan, Qt startup/shutdown')
    return 0
