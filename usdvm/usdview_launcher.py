"""Launch an explicitly configured, isolated standalone USD runtime."""

import os
import subprocess
import sys
from pathlib import Path


def installation_dir():
    configured = os.environ.get("UVM_USD_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    return base / "usd.py312.windows-x86_64.usdview.release-v25.08.71e038c1"


def _python(root):
    candidates = (root / "python" / "python.exe",) if sys.platform == "win32" else (
        root / "python" / "bin" / "python3", root / "bin" / "python3",
    )
    return next((path for path in candidates if path.is_file()), None)


def find_usdview():
    """Never select an unrelated DCC's runtime from PATH."""
    root = installation_dir()
    script = root / "bin" / "usdview"
    return script if script.is_file() and _python(root) else None


def _usd_environment():
    root = installation_dir()
    env = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
        env.pop(name, None)
    env["PATH"] = os.pathsep.join(str(path) for path in (
        root / "python", root / "python" / "bin", root / "pip-packages" / "bin",
        root / "lib", root / "plugin" / "usd", root / "bin",
    )) + os.pathsep + env.get("PATH", "")
    env["PYTHONPATH"] = os.pathsep.join((str(root / "lib" / "python"), str(root / "pip-packages")))
    if sys.platform != "win32":
        env["LD_LIBRARY_PATH"] = str(root / "lib") + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    env["PXR_MTLX_STDLIB_SEARCH_PATHS"] = str(root / "libraries")
    return env


def launch(path: Path, extra_args=None):
    root = installation_dir()
    script = find_usdview()
    if script is None:
        raise FileNotFoundError(
            f"Standalone usdview and its Python interpreter were not found in {root}. "
            "Set UVM_USD_ROOT to a complete, platform-compatible USD distribution. "
            "The usd-core wheel does not include usdview."
        )
    target = Path(path).resolve(strict=True)
    return subprocess.Popen(
        [str(_python(root)), str(script), str(target), *(extra_args or [])],
        env=_usd_environment(), cwd=str(root),
        # CREATE_NO_WINDOW keeps the optional Python-based viewer console-free too.
        creationflags=0x08000000 if sys.platform == 'win32' else 0,
    )
