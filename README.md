# USD Version Manager

A small cross-platform (Windows + Linux) desktop app for managing sequential versions of USD assets. Built with Python + PySide6.

UVM does **not** require a full USD installation to manage, version, or write USD wrapper files. Optional USD inspection and `usdview` support are provided through a standalone USD distribution.

## How it works

### On disk

Each project is a root folder with one subfolder per asset, and one `v###` subfolder per version:

```text
my_project/
├── .usdvm/
│   └── usdvm.db                  <- metadata database (auto-created)
│
└── hero_character/
    ├── hero_character.usd        <- wrapper; always points to current version
    │
    ├── v001/
    │   └── hero_character_v001.usd
    │
    ├── v002/
    │   └── hero_character_v002.usd
    │
    └── v003/
        └── hero_character_v003.usd
```

The wrapper file (`<asset>.usd`) is a tiny plain-text `.usda` stage whose `subLayers` points at the current version:

```usda
#usda 1.0

(
    subLayers = [
        @./v003/hero_character_v003.usd@
    ]
)
```

Anything downstream — a shot, a render, another asset, etc. — references:

```text
hero_character.usd
```

and therefore always gets whichever version has been marked **current**.

This means downstream references do not need to be changed when an asset is bumped to a new version.

### No USD Python bindings required for version management

Writing the wrapper file does **not** require the USD Python bindings (`pxr`).

The wrapper is simply a plain-text `.usda` file, so UVM can create and update it without having USD installed.

The database and filesystem operations also do not depend on `pxr`.

## Quick-start workflow

The basic UVM workflow is:

```text
Create/Open Project
       │
       ▼
    Add Asset
       │
       ▼
   Add Version
       │
       ▼
    v001/
       │
       ▼
 Set v001 Current
       │
       ▼
 asset.usd ──────► v001/asset_v001.usd
       │
       ▼
   Work on v002
       │
       ▼
   Add Version
       │
       ▼
    v002/
       │
       ▼
 Set v002 Current
       │
       ▼
 asset.usd ──────► v002/asset_v002.usd
```

### 1. Create or open a project

Choose the root folder that will contain your assets.

For example:

```text
U:\projects\my_project
```

UVM automatically creates:

```text
U:\projects\my_project\.usdvm\usdvm.db
```

if the project has not been opened before.

### 2. Add an asset

Create an asset in UVM, for example:

```text
hero_character
```

This creates the asset directory:

```text
my_project/
└── hero_character/
```

### 3. Add the first version

Use **New Version** and select the USD file you want to publish.

For example, select:

```text
hero_character.usd
```

UVM copies it into:

```text
hero_character/
└── v001/
    └── hero_character_v001.usd
```

An optional comment can be added to describe the version:

```text
Initial sculpt and materials
```

### 4. Set the version as current

Select `v001` and choose **Set Current**.

UVM updates both:

```text
.usdvm/usdvm.db
```

and:

```text
hero_character/hero_character.usd
```

The wrapper now points to:

```text
./v001/hero_character_v001.usd
```

### 5. Reference the wrapper downstream

In Houdini, Maya, another USD application, or a render pipeline, reference:

```text
hero_character/hero_character.usd
```

rather than referencing:

```text
hero_character/v001/hero_character_v001.usd
```

The wrapper is the stable asset reference.

### 6. Publish another version

After making changes to the asset, export the new USD file and add it through **New Version**.

UVM creates:

```text
hero_character/
├── hero_character.usd
├── v001/
│   └── hero_character_v001.usd
└── v002/
    └── hero_character_v002.usd
```

The existing downstream references do not need to change.

### 7. Set the new version as current

Select `v002` and choose **Set Current**.

The wrapper changes from:

```usda
subLayers = [
    @./v001/hero_character_v001.usd@
]
```

to:

```usda
subLayers = [
    @./v002/hero_character_v002.usd@
]
```

Anything referencing `hero_character.usd` now receives `v002`.

### 8. Inspect or open the version

Select a version in UVM and use **Inspect** to view information about the file.

If the standalone USD runtime is available, UVM can also launch `usdview` for the selected file.

Without USD Python bindings, Inspect falls back to basic file information.

## Typical VFX workflow

UVM is intended to sit between the application where an asset is created and the applications that consume it:

```text
Houdini / Maya / Blender
          │
          │ Export USD
          ▼
     USD Version Manager
          │
       Publish
          │
     ┌────┴────┐
     ▼         ▼
   v001      v002
     │         │
     └────┬────┘
          ▼
    asset.usd
     (wrapper)
          │
          ▼
   ┌──────┼──────┐
   ▼      ▼      ▼
 Shot   Render  Other Asset
```

The important concept is that **the wrapper remains stable while the version it points to changes**.

This allows an asset to be updated without manually replacing references throughout a project.

## Features

* Open or create an asset root
* Browse assets and their versions
* Add new assets
* Add new versions

  * Copies an existing `.usd`, `.usda`, `.usdc` or `.usdz` file
  * Automatically assigns the next version number
  * Optional version comment
* Set any version as **current**

  * Updates the database
  * Updates the on-disk wrapper's sublayer
* Reveal a version's folder in Windows Explorer or the Linux file manager
* Inspect versions

  * Shows basic file information on all supported machines
  * Shows real USD stage information when USD Python bindings are available
* Launch standalone `usdview` when the bundled USD distribution is installed

## Running from source

UVM requires Python 3.9+.

Create a virtual environment:

```bash
python -m venv .venv
```

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Install the application dependencies:

```bash
pip install -r requirements.txt
```

Run UVM from the project root:

```bash
python -m usdvm.app
```

Running it as a module is recommended because the application uses package-relative imports.

## USD inspection

UVM itself does **not** require `pxr`.

If the Python environment contains the USD Python bindings, the Inspect panel can read actual USD stage information such as:

* Prim count
* Default prim
* Up axis
* Stage information

Without `pxr`, UVM falls back to basic file information rather than failing.

### Standalone USD

For `usdview` and full USD inspection, UVM uses a standalone NVIDIA USD distribution rather than relying on another application such as Gaffer or Houdini.

The current distribution is:

```text
usd.py312.windows-x86_64.usdview.release-v25.08.71e038c1
```

It contains its own:

```text
python/
    python.exe

lib/
    python/
        pxr/

bin/
    usdview
    usdview.cmd

pip-packages/
plugin/
libraries/
```

The bundled Python runtime is **Python 3.12**, and the `pxr` bindings belong to this USD installation.

UVM therefore does **not** install `pxr` into its own Python virtual environment.

The architecture is:

```text
UVM
├── .venv
│   └── Python 3.11
│       ├── PySide6
│       └── UVM
│
└── Standalone USD
    └── Python 3.12
        ├── pxr
        └── usdview
```

This separation avoids Python-version conflicts with other applications that may provide their own USD installation.

## Standalone USD layout

When running from source, the standalone USD distribution is expected alongside the UVM project:

```text
UVM/
├── usdvm/
├── .venv/
├── run.py
├── requirements.txt
└── usd.py312.windows-x86_64.usdview.release-v25.08.71e038c1/
    ├── bin/
    ├── lib/
    ├── python/
    ├── pip-packages/
    ├── plugin/
    └── libraries/
```

The launcher explicitly uses:

```text
usd...\python\python.exe
```

to run:

```text
usd...\bin\usdview
```

and constructs the required `PATH`, `PYTHONPATH` and MaterialX environment for the standalone USD distribution.

It does **not** use:

```python
shutil.which("usdview")
```

because another application may provide a different `usdview` on the system `PATH`.

For example, Gaffer can provide its own USD environment, which may not contain the Python modules required by this particular USD distribution.

## PyInstaller builds

UVM can be packaged as a standalone executable using PyInstaller.

Build with:

```powershell
pyinstaller --onefile run.py
```

For development/debugging, avoid `--noconsole` so that Python errors remain visible:

```powershell
pyinstaller --onefile run.py
```

Once the build is working correctly, a windowed build can be produced with:

```powershell
pyinstaller --onefile --noconsole run.py
```

### Important: USD is external to the executable

The standalone USD distribution should **not** be bundled into the PyInstaller executable.

A portable distribution should look like:

```text
dist/
├── run.exe
│
└── usd.py312.windows-x86_64.usdview.release-v25.08.71e038c1/
    ├── bin/
    ├── lib/
    ├── python/
    ├── pip-packages/
    ├── plugin/
    └── libraries/
```

The UVM launcher detects whether it is running from source or from a frozen PyInstaller executable.

When running from source, it resolves the USD installation relative to the UVM project.

When running as an executable, it resolves the USD installation relative to the executable.

This allows the executable and USD distribution to be moved together without hard-coding a user's development path.

### Why `pxr` is not packaged by PyInstaller

`pxr` is part of the standalone USD distribution, not a dependency that needs to be installed into UVM's `.venv`.

The executable therefore launches the standalone USD Python interpreter when starting `usdview`.

Conceptually:

```text
run.exe
   │
   └── launches
         │
         ├── standalone USD python.exe
         │
         └── standalone USD bin/usdview
                    │
                    └── lib/python/pxr
```

This keeps the UVM application and USD runtime separate.

## Getting the standalone USD package

The standalone NVIDIA USD distribution is distributed separately from this project.

The required package is:

```text
usd.py312.windows-x86_64.usdview.release-v25.08.71e038c1
```

The extracted directory should be placed alongside the UVM project when developing from source, or alongside `run.exe` when using the packaged application.

The USD distribution itself should generally **not be committed to Git**, since it is a large third-party binary package.

A setup script can download and extract the required NVIDIA distribution automatically.

## Notes / things you'll likely want to extend

* **New Version** currently copies an existing file rather than creating a blank stage. This matches most VFX workflows where you are publishing something already built in Houdini, Maya, Blender, etc.
* There is currently no locking or multi-user support. SQLite is suitable for local/single-user workflows, but a shared production system would eventually benefit from a proper server/database architecture.
* `author` is stored per version, but the UI does not currently set it automatically. A simple improvement would be using `getpass.getuser()` as the default author.
* The filesystem remains the source of truth; the database should not be treated as the authoritative location of the USD files.
* The standalone USD runtime is deliberately kept separate from UVM's Python environment to avoid conflicts with Houdini, Gaffer, or other USD installations.
* The USD version can be updated independently by replacing the standalone USD distribution and updating the configured distribution name/path.
