# Release procedure

The initial package version is 0.1.0. No release has been published by this cleanup.

## Current validation evidence

The cleanup was validated on the cloud Linux host with CPython 3.9.12 and 3.11.17: all 24 regression tests passed on each. Wheel/sdist builds and metadata checks passed. A fresh wheel installation outside the checkout and an earlier PyInstaller directory bundle both passed the functional headless smoke check. Runtime dependency wheels were successfully resolved/downloaded for Windows x64/Python 3.11; those binaries were not executed on Windows.

Rocky 9.6 container startup succeeded, but its dependency installation was blocked by the cloud network policy denying Rocky package mirrors. The required mirror domains were saved in the cloud configuration draft; that does not activate network changes. Rocky runtime checks, native GNOME 40.4.0/OpenGL checks, Windows 11 execution, and remote CI execution remain unverified. The local bundle is a Linux-host validation artifact, not a Rocky release binary.

The subsequent single-file build also passed the headless smoke check after copying only the executable into an otherwise empty directory whose path contains spaces. This check was run on the Linux cloud host; the Windows and Rocky single-file builds still need their CI/native checks.

The icon/windowed-launch update passed all 29 tests on Python 3.9.12 and 3.11.17. Both PNG/ICO assets were verified in the wheel. The relocated Linux single-file executable passed its icon-aware smoke check, installed its persistent desktop icon/entry, and that entry passed desktop-file-validate. Windows GUI subsystem verification is included in CI; visual Windows taskbar and GNOME shell acceptance still require native testing.

## Automated checks

The GitHub workflow tests Python 3.9.12 on Ubuntu and Python 3.11 on Windows Server, plus the Rocky Linux 9.6 container's vendor Python 3.9. These checks complement, rather than replace, native testing on the exact desktop targets. It builds wheels/sdists, collects the USD runtime/plugins in PyInstaller bundles and runs a functional smoke check against the bundled executable. CI configuration is not evidence of a completed CI run.

1. Keep the version in `pyproject.toml` and `usdvm/__init__.py` synchronized. Keep dependency pins in `requirements.txt` and `pyproject.toml` synchronized.
2. In a clean virtual environment run `python -m pip install ".[dev,bundle]"`, `python -m pip check`, and `python -m pytest -q`.
3. Run `python -m build` and `python -m twine check dist/*` before building the native bundle.
4. Install the wheel into a second fresh environment, outside the checkout. Run `python -m usdvm.app --version` and `--smoke-test` with `QT_QPA_PLATFORM=offscreen`.
5. Build `python -m PyInstaller --clean --noconfirm run.spec` on Windows 11/Python 3.11 and Rocky 9.6/Python 3.9.12 separately. Windows builds are windowed (`console=False`); CI uses Start-Process -Wait and checks ExitCode so the GUI process must finish successfully. Linux builds retain CLI diagnostics, while the GNOME desktop entry specifies Terminal=false. Do not ship an Ubuntu-built executable as the Rocky candidate.
6. Copy only `dist/uvm` (Windows: `dist\uvm.exe`) to an otherwise empty directory outside the checkout and run `./uvm --smoke-test` (Windows: `.\uvm.exe`) with `QT_QPA_PLATFORM=offscreen` and no source checkout on PYTHONPATH. Verify plugins and inspection still work without an adjacent `_internal` folder. CI performs this relocation check. Distribute the single executable per OS and record SHA-256 hashes. Linux archive packaging must preserve the executable permission bit.

Single-file builds include Python, Qt and the USD inspection runtime. PyInstaller extracts bundled libraries at startup; writable executable temporary storage is required (a `noexec` temporary mount needs an administrator-approved executable location via TMPDIR). System desktop/OpenGL libraries and drivers remain prerequisites. Optional standalone usdview and user asset dependencies remain external.

## Native desktop acceptance gates

Record the OS, Python, GNOME session type, GPU/driver and candidate hashes for each run. The following checks must pass on Rocky 9.6/GNOME 40.4.0/Python 3.9.12 and Windows 11/Python 3.11 before claiming those platforms supported:

- Launch both installed wheel and portable bundle from a clean user account. Verify the window/taskbar icon and the Windows executable/shortcut icon. Double-click the Windows executable and confirm no terminal appears. On GNOME install the application shortcut from the Application menu, launch it from Applications, pin it to Favorites, and verify its icon and absence of a terminal.
- On GNOME, test both the normal Wayland session and X11/XWayland where supported; verify scaling, fonts, dialogs and window closing.
- Create/reopen a project whose parent path contains spaces and non-ASCII characters. Publish two versions; set each current and confirm the wrapper stage resolves the intended content.
- Cancel file/comment dialogs; try a read-only project, a missing source file, an existing version directory and Windows reserved names. Failures must preserve previous files/current version and show usable messages.
- Rescan existing projects, including legacy version filenames. Check metadata/comments persist after reopening.
- Inspect a representative real production stage. Preview proxy/render mesh representations, orbit/pan/zoom, and close during loading. Confirm clean shutdown and OpenGL 3.2 support.
- Reveal files in GNOME Files/Windows Explorer. If distributing standalone usdview, test the selected platform-specific runtime separately and check no other DCC Python/Qt paths are imported.
- Test USD stages with dependencies using the intended publishing layout; UVM does not collect those dependencies.

## Publication gates

The project uses the MIT license in LICENSE. Review redistribution terms/notices for Qt/PySide6, NumPy, OpenUSD, PyInstaller and any optional NVIDIA runtime. Include required third-party notices with binary archives. Decide Windows signing and download hosting before publication. No credentials, asset databases, virtual environments or downloaded standalone USD runtimes belong in source releases.

Only tag and publish after these gates pass. CI uploads candidate artifacts and does not create public releases.
