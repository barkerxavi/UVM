"""Disk-side conventions: one folder per asset, one v### subfolder per
version. This module only touches the filesystem; the database in db.py
is the fast index on top of it."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

VERSION_DIR_RE = re.compile(r"^v(\d+)$")
USD_EXTS = (".usd", ".usda", ".usdc", ".usdz")


def asset_dir(root: Path, asset_name: str) -> Path:
    return Path(root) / asset_name


def discover_asset_names(root: Path):
    """Folder names directly under root, skipping hidden/system folders
    like .usdvm. Used to pick up assets that exist on disk but aren't
    in the database yet (e.g. an existing pipeline you're importing)."""
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(
        p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")
    )


def discover_versions(root: Path, asset_name: str):
    """v### subfolders under this asset that contain a usd-like file.
    Returns a list of (version_num, path_relative_to_root), sorted."""
    found = []
    adir = asset_dir(root, asset_name)
    if not adir.is_dir():
        return found
    for vdir in adir.iterdir():
        if not vdir.is_dir():
            continue
        m = VERSION_DIR_RE.match(vdir.name)
        if not m:
            continue
        usd_files = sorted(
            f for f in vdir.iterdir() if f.is_file() and f.suffix.lower() in USD_EXTS
        )
        if not usd_files:
            continue
        found.append((int(m.group(1)), usd_files[0].relative_to(root)))
    return sorted(found)


def version_dir(root: Path, asset_name: str, version_num: int) -> Path:
    return asset_dir(root, asset_name) / f"v{version_num:03d}"


def wrapper_path(root: Path, asset_name: str) -> Path:
    """The stable, always-there file other USD stages should reference,
    e.g. `@./character/character.usd@`. Its sublayer is repointed at
    whichever version is 'current'."""
    return asset_dir(root, asset_name) / f"{asset_name}.usd"


def create_version_from_file(root: Path, asset_name: str, version_num: int, source_file: Path) -> Path:
    vdir = version_dir(root, asset_name, version_num)
    vdir.mkdir(parents=True, exist_ok=True)
    ext = source_file.suffix or ".usd"
    dest = vdir / f"{asset_name}_v{version_num:03d}{ext}"
    shutil.copy2(source_file, dest)
    return dest


def reveal_in_file_manager(path: Path):
    path = Path(path)
    target = path if path.is_dir() else path.parent
    if sys.platform.startswith("win"):
        subprocess.run(["explorer", str(target)])
    elif sys.platform == "darwin":
        subprocess.run(["open", str(target)])
    else:
        subprocess.run(["xdg-open", str(target)])
