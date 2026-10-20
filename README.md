# USD Version Manager

UVM is a Python/PySide6 desktop application for publishing sequential USD asset versions, inspecting stages, and switching a stable wrapper to the current version.

Licensed under the [MIT License](LICENSE).

## Release targets

| Platform | Python | Architecture |
| --- | --- | --- |
| Rocky Linux 9.6, GNOME 40.4.0 | 3.9.12 | x86_64 |
| Windows 11 | 3.11 | x86_64 |

These are release acceptance targets, not a claim that native desktop acceptance has already passed. See [release validation](docs/RELEASING.md). The pinned runtime is PySide6 6.6.3.1, NumPy 1.26.4, and usd-core 25.5.1. These versions have binary wheels for both target Python versions. Avoid unbounded upgrades: newer Qt, NumPy and USD releases may drop Python 3.9 or require a newer glibc. The Linux Qt wheels require glibc 2.28 or later; Rocky 9 uses glibc 2.34.

## Install from source

Use a fresh virtual environment and the system Python specified above. Do not replace Rocky's system interpreter. A supported distribution update to Python 3.9 keeps important vendor security fixes; Python 3.9.12 itself is old and must be assessed under your deployment policy.

### Rocky Linux 9.6

Install desktop runtime libraries with an administrator account (many are already installed by GNOME):

```bash
sudo dnf install python3-pip mesa-libGL mesa-libEGL libxkbcommon libxkbcommon-x11 \
  libxcb xcb-util-cursor xcb-util-wm xcb-util-image xcb-util-keysyms \
  xcb-util-renderutil dbus-libs fontconfig libXcursor libXi libXrandr \
  libXrender libXfixes libSM libICE
python3 --version  # check your required Python 3.9.12 installation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m usdvm.app
```

Run from your GNOME desktop session. Qt selects Wayland or X11 from the session. If a Wayland-specific issue occurs, test XWayland with `QT_QPA_PLATFORM=xcb python -m usdvm.app`. Do not set `offscreen` for interactive use. OpenGL preview requires a working OpenGL 3.2 core context and suitable Mesa/vendor drivers.

### Windows 11

Install 64-bit Python 3.11, then use PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m usdvm.app
```

Activation is optional. This avoids changing PowerShell execution policy. The installed `uvm` command also starts the app. If a DLL dependency is missing on a clean machine, install Microsoft's supported Visual C++ 2015–2022 x64 runtime.

For development, use `python -m pip install -e ".[dev]"` instead. `requirements.txt` contains the same runtime pins for existing source workflows; `pip install .` also installs package metadata and the desktop entry point.

## Asset workflow

1. Open or create a project folder.
2. Add an asset (portable names use letters, numbers, `_` and `-`; Windows device names are rejected).
3. Add a USD file as a new version. UVM copies the selected file to `hero/v001/hero.usda`, preserving its extension.
4. Set a version current. UVM atomically replaces `hero/hero.usd` with a text sublayer wrapper pointing at that version.
5. Reference `hero/hero.usd` in downstream applications. Later version changes keep this reference stable.

```text
project/
├── .usdvm/usdvm.db
└── hero/
    ├── hero.usd             # stable wrapper
    ├── v001/hero.usda
    └── v002/hero.usda
```

The scanner also recognizes the earlier `hero_v001.usda` naming convention. Existing version directories are never overwritten. SQLite stores comments, version numbers and the current-version index. Rescan imports on-disk asset/version folders and reconciles current versions from wrappers. Removing an asset from the index removes its metadata, leaves files intact, and Rescan can register it again.

USD files with relative references, payloads or texture dependencies must retain a valid dependency layout after copying. UVM copies the selected file only; it does not collect or rewrite a stage's dependencies. Package a self-contained USDZ or prepare the dependency layout yourself. This is a local, single-user tool; simultaneous publishing and shared production databases are not supported.

## Inspection and viewers

The pinned `usd-core` wheel supplies `pxr` for stage inspection and in-app mesh loading. It does **not** supply `usdview`. The preview handles polygon meshes and uses fan triangulation; it is not a full Hydra renderer, does not render textures/materials, and is not a fidelity check for concave polygons or animated scenes.

Standalone `usdview` is optional and runs in its own Python environment. Set `UVM_USD_ROOT` to a complete distribution built for the destination operating system:

- Windows: `bin/usdview`, `python/python.exe`, and the distribution's libraries.
- Linux: `bin/usdview`, `python/bin/python3` (or `bin/python3`), and the distribution's libraries.

The launcher uses only this runtime and does not search unrelated DCC installations on PATH. Its Python can differ from UVM's Python. Without `UVM_USD_ROOT`, the legacy Windows NVIDIA directory beside the source checkout or frozen executable is tried. Do not copy Windows USD binaries onto Linux. The optional Windows download helper requires an independently obtained SHA-256 checksum.

## Checks and distribution

```bash
python -m pip install -e ".[dev,bundle]"
python -m pytest -q
python -m pip check
python -m build
python -m twine check dist/*
```

For a headless functional check:

```bash
QT_QPA_PLATFORM=offscreen python -m usdvm.app --smoke-test
```

PowerShell equivalent:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
python -m usdvm.app --smoke-test
Remove-Item Env:QT_QPA_PLATFORM
```

The smoke test exercises USD composition, mesh loading, SQLite/project rescan and Qt startup/shutdown. Headless checks cannot validate OpenGL rendering, native file dialogs or GNOME integration.

Build the single-file executable on each target platform with `python -m PyInstaller --clean --noconfirm run.spec`. The output is one file: `dist/uvm.exe` on Windows or `dist/uvm` on Linux. You can copy that file alone to the desktop or another folder; no adjacent `_internal` directory or Python installation is needed. On Linux, retain executable permission (`chmod +x uvm`). The application extracts its bundled runtime into a temporary directory at startup, so the temporary filesystem must be writable and allow execution. Linux desktop/OpenGL libraries and drivers listed above are still system prerequisites. The optional standalone `usdview` runtime remains external. Build Linux binaries on Rocky 9.6; binaries built on newer Linux systems may require a newer glibc. See [RELEASING.md](docs/RELEASING.md) for acceptance checks and known release gates.
