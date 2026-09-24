import re
import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QFileDialog, QInputDialog, QMessageBox,
    QAbstractItemView, QHeaderView, QSplitter, QTextEdit,
)

from .db import ProjectDB
from . import scanner
from . import usd_writer
from . import usdview_launcher

ORG = "XaviTools"
APP = "USDVersionManager"
ASSET_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")

ORANGE = "#ff7a1a"
ORANGE_DARK = "#cc5f0f"
BG = "#1b1b1b"
BG_ALT = "#242424"
BG_FIELD = "#262626"
BORDER = "#3a3a3a"
TEXT = "#f0f0f0"
TEXT_DIM = "#8a8a8a"

THEME_QSS = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-size: 10pt;
}}
QMainWindow, QStatusBar {{
    background-color: {BG};
    color: {TEXT};
}}
QLineEdit, QTextEdit {{
    background-color: {BG_FIELD};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 4px;
    color: {TEXT};
    selection-background-color: {ORANGE};
    selection-color: {BG};
}}
QPushButton {{
    background-color: {BG_FIELD};
    border: 1px solid {ORANGE};
    border-radius: 4px;
    padding: 6px 12px;
    color: {ORANGE};
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {ORANGE};
    color: {BG};
}}
QPushButton:pressed {{
    background-color: {ORANGE_DARK};
    color: {BG};
    border-color: {ORANGE_DARK};
}}
QPushButton:disabled {{
    border-color: {BORDER};
    color: {TEXT_DIM};
}}
QListWidget, QTableWidget {{
    background-color: {BG_ALT};
    alternate-background-color: {BG_FIELD};
    border: 1px solid {BORDER};
    gridline-color: {BORDER};
    color: {TEXT};
}}
QListWidget::item:selected, QTableWidget::item:selected {{
    background-color: {ORANGE};
    color: {BG};
}}
QHeaderView::section {{
    background-color: {BG_FIELD};
    color: {ORANGE};
    padding: 5px;
    border: 1px solid {BORDER};
    font-weight: 600;
}}
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:hover {{
    background-color: {ORANGE};
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {BG_ALT};
}}
QScrollBar::handle {{
    background: {BORDER};
    border-radius: 3px;
}}
QScrollBar::handle:hover {{
    background: {ORANGE};
}}
QMessageBox, QInputDialog, QFileDialog {{
    background-color: {BG};
}}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USD Version Manager")
        self.resize(1350, 650)

        self.settings = QSettings(ORG, APP)
        self.root: Optional[Path] = None
        self.db: Optional[ProjectDB] = None
        self._usdview_procs = []  # keep references so Popen objects aren't GC'd

        self._build_ui()
        self._connect_signals()
        self._refresh_usdview_status()

        last_root = self.settings.value("last_root", "")
        if last_root and Path(last_root).is_dir():
            self.open_root(Path(last_root))

    # ---------------- UI ----------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        top = QHBoxLayout()
        self.root_edit = QLineEdit()
        self.root_edit.setPlaceholderText("Paste or type an asset root folder path, or click Browse...")
        self.btn_browse_root = QPushButton("Browse...")
        self.btn_go_root = QPushButton("Open")
        self.btn_new_asset = QPushButton("New Asset...")
        self.btn_delete_asset = QPushButton("Delete Asset...")
        self.btn_rescan = QPushButton("Rescan")
        top.addWidget(QLabel("Asset root:"))
        top.addWidget(self.root_edit, 1)
        top.addWidget(self.btn_go_root)
        top.addWidget(self.btn_browse_root)
        top.addWidget(self.btn_new_asset)
        top.addWidget(self.btn_delete_asset)
        top.addWidget(self.btn_rescan)
        outer.addLayout(top)

        splitter = QSplitter()
        outer.addWidget(splitter, 1)

        # ---- left: asset list ----
        self.asset_list = QListWidget()
        self.asset_list.setMinimumWidth(220)
        splitter.addWidget(self.asset_list)

        # ---- center: versions + details ----
        center = QWidget()
        center_layout = QVBoxLayout(center)

        self.version_table = QTableWidget(0, 6)
        self.version_table.setHorizontalHeaderLabels(
            ["Version", "Date", "Author", "Comment", "Size", "Current"]
        )
        self.version_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.version_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.version_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        center_layout.addWidget(self.version_table, 2)

        btn_row = QHBoxLayout()
        self.btn_new_version = QPushButton("New Version...")
        self.btn_set_current = QPushButton("Set as Current")
        self.btn_reveal = QPushButton("Reveal in File Manager")
        self.btn_inspect = QPushButton("Inspect")
        for b in (self.btn_new_version, self.btn_set_current, self.btn_reveal, self.btn_inspect):
            btn_row.addWidget(b)
        center_layout.addLayout(btn_row)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select a version and click Inspect to see details here.")
        center_layout.addWidget(self.details, 1)

        splitter.addWidget(center)

        # ---- right: usdview ----
        usdview_panel = QWidget()
        usdview_panel.setMinimumWidth(240)
        usdview_layout = QVBoxLayout(usdview_panel)

        title = QLabel("usdview")
        title.setStyleSheet(f"font-weight: bold; color: {ORANGE}; font-size: 11pt;")
        usdview_layout.addWidget(title)

        note = QLabel(
            "usdview is its own standalone application - this opens it in a "
            "separate window pointed at your selection, it isn't embedded here."
        )
        note.setWordWrap(True)
        usdview_layout.addWidget(note)

        self.usdview_status = QLabel()
        self.usdview_status.setWordWrap(True)
        usdview_layout.addWidget(self.usdview_status)

        self.btn_launch_usdview = QPushButton("Launch usdview on Selection")
        usdview_layout.addWidget(self.btn_launch_usdview)
        usdview_layout.addStretch(1)

        splitter.addWidget(usdview_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([220, 700, 260])

        self.statusBar().showMessage("Ready")

    def _connect_signals(self):
        self.btn_browse_root.clicked.connect(self.choose_root)
        self.btn_go_root.clicked.connect(self.open_root_from_edit)
        self.root_edit.returnPressed.connect(self.open_root_from_edit)
        self.btn_new_asset.clicked.connect(self.new_asset)
        self.btn_delete_asset.clicked.connect(self.delete_asset)
        self.btn_rescan.clicked.connect(self.rescan)
        self.asset_list.currentItemChanged.connect(self.on_asset_selected)
        self.btn_new_version.clicked.connect(self.new_version)
        self.btn_set_current.clicked.connect(self.set_current_version)
        self.btn_reveal.clicked.connect(self.reveal_selected)
        self.btn_inspect.clicked.connect(self.inspect_selected)
        self.btn_launch_usdview.clicked.connect(self.launch_usdview)

    # ---------------- project ----------------
    def choose_root(self):
        start = self.root_edit.text().strip() or ""
        path = QFileDialog.getExistingDirectory(self, "Choose or create an asset root folder", start)
        if path:
            self.open_root(Path(path))

    def open_root_from_edit(self):
        text = self.root_edit.text().strip().strip('"').strip("'")
        if not text:
            return
        path = Path(text).expanduser()
        if not path.is_dir():
            if path.exists():
                QMessageBox.warning(self, "Not a folder", f"'{path}' exists but isn't a folder.")
                return
            if QMessageBox.question(
                self, "Folder doesn't exist",
                f"'{path}' doesn't exist yet. Create it and use it as the asset root?",
            ) != QMessageBox.Yes:
                return
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self, "Couldn't create folder", str(e))
                return
        self.open_root(path)

    def open_root(self, root: Path):
        if self.db:
            self.db.close()
        self.root = root
        self.db = ProjectDB(root)
        self.settings.setValue("last_root", str(root))
        self.root_edit.setText(str(root))
        self.rescan()

    def rescan(self):
        """Reconcile the database with what's actually on disk: pick up
        asset folders and v### versions that were added outside the app,
        and figure out which version is current by reading each asset's
        wrapper file, then refresh the UI."""
        if not self.db or not self.root:
            return
        for name in scanner.discover_asset_names(self.root):
            self.db.add_asset(name)

        for asset in self.db.list_assets():
            name = asset["name"]
            known = {Path(v["file_path"]).as_posix() for v in self.db.list_versions(asset["id"])}
            for vnum, rel_path in scanner.discover_versions(self.root, name):
                if rel_path.as_posix() not in known:
                    self.db.add_version(asset["id"], vnum, rel_path, comment="(found on disk)")

            wrapper = scanner.wrapper_path(self.root, name)
            target = usd_writer.read_current_target(wrapper)
            if target:
                target_abs = (wrapper.parent / target).resolve()
                for v in self.db.list_versions(asset["id"]):
                    if (self.root / v["file_path"]).resolve() == target_abs:
                        self.db.set_current_version(asset["id"], v["id"])
                        break

        self.refresh_assets()

    def refresh_assets(self):
        if not self.db:
            return
        self.asset_list.clear()
        for row in self.db.list_assets():
            item = QListWidgetItem(row["name"])
            item.setData(Qt.UserRole, row["id"])
            self.asset_list.addItem(item)
        self.version_table.setRowCount(0)
        self.details.clear()
        self.statusBar().showMessage(f"{self.asset_list.count()} asset(s)")

    def new_asset(self):
        if not self.db:
            QMessageBox.information(self, "No project", "Open an asset root first.")
            return
        name, ok = QInputDialog.getText(self, "New Asset", "Asset name (letters, numbers, _ and - only):")
        if not ok or not name.strip():
            return
        name = name.strip()
        if not ASSET_NAME_RE.match(name):
            QMessageBox.warning(
                self, "Invalid name",
                "Asset names can only contain letters, numbers, underscores and hyphens "
                "(no spaces or slashes) - USD and file paths get unreliable otherwise.",
            )
            return
        if self.db.get_asset(name):
            QMessageBox.information(self, "Already exists", f"An asset named '{name}' already exists.")
            return
        adir = scanner.asset_dir(self.root, name)
        if adir.is_dir() and any(adir.iterdir()):
            if QMessageBox.question(
                self, "Folder already has content",
                f"'{name}' already exists on disk and isn't empty. Register it as an asset "
                "and scan it for existing v### versions?",
            ) != QMessageBox.Yes:
                return
        adir.mkdir(parents=True, exist_ok=True)
        self.db.add_asset(name)
        self.rescan()

    def delete_asset(self):
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.information(self, "No asset", "Select an asset first.")
            return
        if QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this asset and all its versions?"
        ) != QMessageBox.Yes:
            return
        self.db.remove_asset(asset_id)
        self.refresh_assets()

    # ---------------- assets / versions ----------------
    def on_asset_selected(self, current, previous):
        self.version_table.setRowCount(0)
        self.details.clear()
        if not current or not self.db:
            return
        self._load_versions(current.data(Qt.UserRole))

    def _load_versions(self, asset_id: int):
        asset = self.db.get_asset_by_id(asset_id)
        versions = self.db.list_versions(asset_id)
        self.version_table.setRowCount(len(versions))
        for r, v in enumerate(versions):
            is_current = asset["current_version_id"] == v["id"]
            size_path = self.root / v["file_path"]
            size_text = self._format_size(size_path.stat().st_size) if size_path.is_file() else ""

            self.version_table.setItem(r, 0, QTableWidgetItem(f"v{v['version_num']:03d}"))
            self.version_table.setItem(r, 1, QTableWidgetItem(v["created_at"]))
            self.version_table.setItem(r, 2, QTableWidgetItem(v["author"] or ""))
            self.version_table.setItem(r, 3, QTableWidgetItem(v["comment"] or ""))
            self.version_table.setItem(r, 4, QTableWidgetItem(size_text))
            self.version_table.setItem(r, 5, QTableWidgetItem("Yes" if is_current else ""))
            self.version_table.item(r, 0).setData(Qt.UserRole, v["id"])

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        size = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024

    def _selected_asset_id(self):
        item = self.asset_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _selected_version_id(self):
        row = self.version_table.currentRow()
        if row < 0:
            return None
        return self.version_table.item(row, 0).data(Qt.UserRole)

    def new_version(self):
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.information(self, "No asset", "Select an asset first.")
            return
        asset = self.db.get_asset_by_id(asset_id)
        src, _ = QFileDialog.getOpenFileName(
            self, "Choose USD file for new version", "",
            "USD Files (*.usd *.usda *.usdc *.usdz);;All Files (*)",
        )
        if not src:
            return
        comment, ok = QInputDialog.getText(self, "Version comment", "Comment (optional):")
        if not ok:
            comment = ""

        version_num = self.db.next_version_num(asset_id)
        dest = scanner.create_version_from_file(self.root, asset["name"], version_num, Path(src))
        rel_path = dest.relative_to(self.root)
        self.db.add_version(asset_id, version_num, rel_path, author="", comment=comment.strip())
        self._load_versions(asset_id)
        self.statusBar().showMessage(f"Added v{version_num:03d} for {asset['name']}")

        if QMessageBox.question(
            self, "Set as current?",
            f"Set v{version_num:03d} as the current version of {asset['name']}?",
        ) == QMessageBox.Yes:
            self.set_current_version()

    def set_current_version(self):
        asset_id = self._selected_asset_id()
        version_id = self._selected_version_id()
        if asset_id is None or version_id is None:
            QMessageBox.information(self, "Select a version", "Select an asset and a version first.")
            return
        asset = self.db.get_asset_by_id(asset_id)
        version = self.db.get_version(version_id)
        vfile = self.root / version["file_path"]
        wrapper = scanner.wrapper_path(self.root, asset["name"])
        rel = vfile.relative_to(wrapper.parent)
        usd_writer.write_sublayer_wrapper(wrapper, str(rel).replace("\\", "/"))
        self.db.set_current_version(asset_id, version_id)
        self._load_versions(asset_id)
        self.statusBar().showMessage(
            f"{asset['name']} -> v{version['version_num']:03d}  ({wrapper.name} updated)"
        )

    def reveal_selected(self):
        asset_id = self._selected_asset_id()
        version_id = self._selected_version_id()
        if version_id is not None:
            version = self.db.get_version(version_id)
            scanner.reveal_in_file_manager(self.root / version["file_path"])
        elif asset_id is not None:
            asset = self.db.get_asset_by_id(asset_id)
            scanner.reveal_in_file_manager(scanner.asset_dir(self.root, asset["name"]))

    def inspect_selected(self):
        version_id = self._selected_version_id()
        if version_id is None:
            QMessageBox.information(self, "Select a version", "Select a version to inspect.")
            return
        version = self.db.get_version(version_id)
        path = self.root / version["file_path"]
        info = usd_writer.try_inspect_stage(path)

        lines = [f"File: {path}", f"Size: {path.stat().st_size:,} bytes", ""]
        if not info.get("available"):
            lines.append(info.get("note", ""))
        elif "error" in info:
            lines.append(f"Error reading stage: {info['error']}")
        else:
            lines.append(f"Default prim: {info.get('default_prim')}")
            lines.append(f"Up axis: {info.get('up_axis')}")
            lines.append(f"Prim count: {info.get('prim_count')}")
            lines.append("")
            lines.append("Prims (first 25):")
            lines.extend(info.get("prims", []))
        self.details.setPlainText("\n".join(lines))

    # ---------------- usdview ----------------
    def _refresh_usdview_status(self):
        exe = usdview_launcher.find_usdview()
        if exe:
            self.usdview_status.setText(f"Found: {exe}")
            self.btn_launch_usdview.setEnabled(True)
        else:
            self.usdview_status.setText(
                "usdview not found on PATH. Install USD (e.g. 'pip install usd-core') "
                "or add your USD build's bin/ folder to PATH to enable this."
            )
            self.btn_launch_usdview.setEnabled(False)

    def launch_usdview(self):
        version_id = self._selected_version_id()
        asset_id = self._selected_asset_id()

        if version_id is not None:
            version = self.db.get_version(version_id)
            target = self.root / version["file_path"]
        elif asset_id is not None:
            asset = self.db.get_asset_by_id(asset_id)
            target = scanner.wrapper_path(self.root, asset["name"])
            if not target.is_file():
                QMessageBox.information(
                    self, "Nothing to open",
                    f"'{asset['name']}' doesn't have a current version set yet.",
                )
                return
        else:
            QMessageBox.information(self, "Nothing selected", "Select an asset or version first.")
            return

        try:
            proc = usdview_launcher.launch(target)
        except FileNotFoundError as e:
            QMessageBox.warning(self, "usdview not found", str(e))
            return
        self._usdview_procs.append(proc)
        self.statusBar().showMessage(f"Opened {target.name} in usdview")

    def closeEvent(self, event):
        if self.db:
            self.db.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(THEME_QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
