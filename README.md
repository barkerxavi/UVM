# USD Version Manager

A small cross-platform (Windows + Linux) desktop app for managing sequential
versions of USD assets. Built with Python + PySide6.

## How it works

**On disk**, each project is just a root folder with one subfolder per asset,
and one `v###` subfolder per version:

```
my_project/
  .usdvm/usdvm.db          <- metadata database (auto-created)
  hero_character/
    hero_character.usd     <- the "wrapper" - always sublayers whatever is current
    v001/hero_character_v001.usd
    v002/hero_character_v002.usd
    v003/hero_character_v003.usd
```

The wrapper file (`<asset>.usd`) is a tiny plain-text `.usda` stage whose
`subLayers` points at the current version, e.g.:

```usda
#usda 1.0
(
    subLayers = [
        @./v003/hero_character_v003.usd@
    ]
)
```

Anything downstream (a shot, a render, another asset) references
`hero_character.usd` and always gets whatever version you've marked
current — no need to update those references when you bump a version.
Writing this file doesn't require the USD Python bindings (`pxr`) at
all, since `.usda` is just text, so the app works even on a machine
without a full USD install.

**In the database** (`.usdvm/usdvm.db`, plain SQLite, lives inside the
project folder so it travels with it), every version is tracked with its
number, file path, author, comment and timestamp, and each asset records
which version is current. The disk layout stays the source of truth for
the files themselves; the database just makes browsing/searching fast
and lets you attach notes without touching the USD files.

## Features

- Open/create an asset root, browse assets and their versions
- Add a new asset, add a new version (copies in a `.usd`/`.usda`/`.usdc`/`.usdz`
  file you pick, with an optional comment)
- Set any version as "current" - updates both the database and the
  on-disk wrapper file's sublayer
- Reveal a version's folder in Explorer / your Linux file manager
- Inspect a version - shows real stage contents (prims, default prim, up
  axis) if the `pxr` USD Python bindings are installed; otherwise falls
  back to basic file info

## Running it

Requires Python 3.9+.

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python run.py
```

Optional: if you want the "Inspect" panel to show real stage contents
(prim counts, default prim, etc.) rather than just file size, install
the USD Python bindings in the same environment, e.g. `pip install usd-core`.

## Notes / things you'll likely want to extend

- "New Version" currently copies in an existing file rather than creating
  a blank stage — that matches most VFX workflows where you're publishing
  something you already built in Houdini/Maya/etc.
- There's no locking/multi-user support; the SQLite file is fine for one
  person working locally, but if you want this shared across a team
  you'd want a proper server (or point everyone's DB at a synced/shared
  location and accept last-write-wins).
- `author` is stored per version but the UI never sets it yet — an easy
  first addition would be pulling `getpass.getuser()` as a default.
