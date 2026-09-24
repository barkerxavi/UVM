import os
import subprocess
from pathlib import Path


USD_INSTALL_DIR = Path(
    r"C:\Users\xbarker\tmp\usd.py312.windows-x86_64.usdview.release-v25.08.71e038c1"
)


def find_usdview():
    """Return the standalone USD usdview script."""
    usdview = USD_INSTALL_DIR / "bin" / "usdview"

    if usdview.is_file():
        return usdview

    return None


def _usd_environment():
    """Build the environment required by the standalone USD distribution."""

    env = os.environ.copy()

    python_dir = USD_INSTALL_DIR / "python"
    pip_packages = USD_INSTALL_DIR / "pip-packages"
    lib_dir = USD_INSTALL_DIR / "lib"
    plugin_dir = USD_INSTALL_DIR / "plugin" / "usd"
    bin_dir = USD_INSTALL_DIR / "bin"

    # Match NVIDIA's set_usd_python_env.bat
    env["PATH"] = os.pathsep.join([
        str(python_dir),
        str(pip_packages / "bin"),
        env.get("PATH", ""),
    ])

    env["PYTHONPATH"] = os.pathsep.join([
        str(pip_packages),
        env.get("PYTHONPATH", ""),
    ])

    # Match NVIDIA's set_usd_env.bat
    env["PATH"] = os.pathsep.join([
        str(lib_dir),
        str(plugin_dir),
        str(bin_dir),
        env.get("PATH", ""),
        str(bin_dir),
        str(plugin_dir),
        str(lib_dir),
    ])

    env["PYTHONPATH"] = os.pathsep.join([
        str(lib_dir / "python"),
        env.get("PYTHONPATH", ""),
    ])

    env["PXR_MTLX_STDLIB_SEARCH_PATHS"] = str(
        USD_INSTALL_DIR / "libraries"
    )

    return env


def launch(path: Path, extra_args=None):
    """Launch standalone USD usdview on a USD file."""

    usdview = find_usdview()

    if usdview is None:
        raise FileNotFoundError(
            f"Standalone USD usdview not found:\n"
            f"{USD_INSTALL_DIR / 'bin' / 'usdview'}"
        )

    python = USD_INSTALL_DIR / "python" / "python.exe"

    if not python.is_file():
        raise FileNotFoundError(
            f"Standalone USD Python not found:\n{python}"
        )

    args = [
        str(python),
        str(usdview),
        str(path),
    ]

    if extra_args:
        args.extend(extra_args)

    return subprocess.Popen(
        args,
        env=_usd_environment(),
        cwd=str(USD_INSTALL_DIR),
    )