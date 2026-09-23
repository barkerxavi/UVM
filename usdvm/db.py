"""SQLite-backed metadata store. Lives at <root>/.usdvm/usdvm.db so the
whole project (disk files + db) stays portable and travels together."""

import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    current_version_id INTEGER
);
CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    version_num INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    author TEXT,
    comment TEXT,
    FOREIGN KEY(asset_id) REFERENCES assets(id),
    UNIQUE(asset_id, version_num)
);
"""


class ProjectDB:
    def __init__(self, root: Path):
        self.root = Path(root)
        db_dir = self.root / ".usdvm"
        db_dir.mkdir(exist_ok=True)
        self.db_path = db_dir / "usdvm.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ---- assets ----
    def add_asset(self, name: str):
        self.conn.execute("INSERT OR IGNORE INTO assets(name) VALUES (?)", (name,))
        self.conn.commit()
        return self.get_asset(name)

    def get_asset(self, name: str):
        return self.conn.execute("SELECT * FROM assets WHERE name=?", (name,)).fetchone()

    def get_asset_by_id(self, asset_id: int):
        return self.conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()

    def list_assets(self):
        return self.conn.execute("SELECT * FROM assets ORDER BY name").fetchall()

    def set_current_version(self, asset_id: int, version_id: int):
        self.conn.execute(
            "UPDATE assets SET current_version_id=? WHERE id=?", (version_id, asset_id)
        )
        self.conn.commit()

    # ---- versions ----
    def add_version(self, asset_id: int, version_num: int, file_path, author="", comment=""):
        now = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO versions(asset_id, version_num, file_path, created_at, author, comment) "
            "VALUES (?,?,?,?,?,?)",
            (asset_id, version_num, str(file_path), now, author, comment),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_versions(self, asset_id: int):
        return self.conn.execute(
            "SELECT * FROM versions WHERE asset_id=? ORDER BY version_num", (asset_id,)
        ).fetchall()

    def next_version_num(self, asset_id: int) -> int:
        row = self.conn.execute(
            "SELECT MAX(version_num) as m FROM versions WHERE asset_id=?", (asset_id,)
        ).fetchone()
        return (row["m"] or 0) + 1

    def get_version(self, version_id: int):
        return self.conn.execute("SELECT * FROM versions WHERE id=?", (version_id,)).fetchone()
