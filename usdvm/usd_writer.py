"""Writes the tiny .usda 'wrapper' file that makes version switching
real from USD's point of view - no pxr/USD install required for this
part, since .usda is just plain text.

If the pxr (USD) Python bindings ARE installed, try_inspect_stage() will
use them to show real stage contents; otherwise it degrades gracefully
to basic file info.
"""

import re
from pathlib import Path

SUBLAYER_RE = re.compile(r"@\.?/?([^@]+)@")


def read_current_target(wrapper_path: Path):
    """Parse a wrapper .usda file's subLayers entry back out as a plain
    string path, so disk can be treated as the source of truth for
    'what's current' when reconciling with the database."""
    wrapper_path = Path(wrapper_path)
    if not wrapper_path.is_file():
        return None
    text = wrapper_path.read_text(encoding="utf-8", errors="ignore")
    m = SUBLAYER_RE.search(text)
    return m.group(1) if m else None


def write_sublayer_wrapper(wrapper_path: Path, target_relative_path: str):
    content = (
        "#usda 1.0\n"
        "(\n"
        "    subLayers = [\n"
        f"        @./{target_relative_path}@\n"
        "    ]\n"
        ")\n"
    )
    Path(wrapper_path).write_text(content, encoding="utf-8")


def try_inspect_stage(usd_path: Path) -> dict:
    try:
        from pxr import Usd
    except ImportError:
        return {
            "available": False,
            "note": "USD Python bindings (pxr) aren't installed here - showing file info only.",
        }
    try:
        stage = Usd.Stage.Open(str(usd_path))
        if stage is None:
            return {"available": True, "error": "Could not open stage."}
        prims = [str(p.GetPath()) for p in stage.Traverse()]
        default_prim = stage.GetDefaultPrim()
        return {
            "available": True,
            "prim_count": len(prims),
            "prims": prims[:25],
            "default_prim": str(default_prim.GetPath()) if default_prim else None,
            "up_axis": stage.GetMetadata("upAxis") if stage.HasMetadata("upAxis") else None,
        }
    except Exception as e:  # pxr can raise a range of things on bad files
        return {"available": True, "error": str(e)}
