"""Launches usdview (https://docs.omniverse.nvidia.com/usd/latest/usdview/index.html)
as its own process.

usdview is a full standalone Qt application with its own event loop and a
Hydra/OpenGL viewport - it can't be embedded as a child widget inside another
PySide6 app in the same process on Windows or Linux, so the practical
integration is: launch it pointed at the file you care about, and it opens
in its own window alongside ours.
"""

import shutil
import subprocess
from pathlib import Path


def find_usdview():
    """Path to the usdview executable, or None if it's not on PATH."""
    return shutil.which("usdview")


def launch(path: Path, extra_args=None):
    """Start usdview on `path`. Returns the subprocess.Popen so callers can
    keep a reference (and optionally check on / terminate it later)."""
    exe = find_usdview()
    if not exe:
        raise FileNotFoundError(
            "usdview wasn't found on PATH. It ships with a USD install - e.g. "
            "'pip install usd-core' in this environment, or add your USD "
            "build's bin/ folder to PATH."
        )
    args = [exe, str(path)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.Popen(args)
