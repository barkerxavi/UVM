import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope='session')
def qapp(tmp_path_factory):
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path_factory.mktemp('settings')))
    app = QApplication.instance() or QApplication([])
    yield app
