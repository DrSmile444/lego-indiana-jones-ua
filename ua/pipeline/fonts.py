"""Level 1: rebuild Font 1 and Font 2 from our glyph sources.

Inputs (see manifests/inputs.json and docs/setup.md):
  Font 1: third-party Cyrillic font patch PC_FONT_PC.FNT (local/donors/cyrillic-font-patch/)
          + Franklin Gothic Medium (local/fonts/) + assets/fonts/font1/overrides.json
  Font 2: original game FONT2_PC.FNT (game/GAME/STUFF/TEXT/) + fan font "Adventure"
          (local/donors/) + assets/fonts/font2/overrides.json
The scripts in tools/fonts/ do the actual work; this module runs them in order.
Intermediates and results live in build/fonts/.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys

from PIL import Image

from .. import paths
from ..formats.fnt import FntFile
from ..util import UaError, say

FONT_TOOLS = paths.REPO / "tools/fonts"
WORK = paths.BUILD / "fonts"


def _run(script: str, *args: str) -> None:
    env = dict(os.environ, PYTHONPATH=str(paths.REPO))
    result = subprocess.run([sys.executable, str(FONT_TOOLS / script), *args], cwd=paths.REPO, env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise UaError(f"{script} failed:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")


def _prepare_font1_atlas() -> None:
    """Slice the donor DDS chunk and decode its mip 0 — the Font 1 painting canvas."""
    donor = paths.DONORS / "cyrillic-font-patch/PC_FONT_PC.FNT"
    font = FntFile(str(donor))
    chunk = bytes(font.data[font.dds_offset:])
    (WORK / "pcfont_0.dds").write_bytes(chunk)
    Image.open(io.BytesIO(chunk)).convert("RGBA").save(WORK / "pcfont_0.png")


def build() -> dict[str, bytes]:
    """Return {resource path in UAP: bytes} for all seven FNT files."""
    WORK.mkdir(parents=True, exist_ok=True)
    say("  Font 1: donor atlas -> Franklin Gothic glyphs -> DXT5 -> FNT")
    _prepare_font1_atlas()
    _run("build_font1_atlas.py")
    _run("build_font1_dds.py")
    _run("build_font1_ukrainian.py", str(WORK / "pcfont_patched_safe.dds"))
    say("  Font 2: original FONT2_PC.FNT -> Adventure glyphs -> DXT5 -> FNT")
    _run("build_font2_atlas.py")
    _run("build_font2_dds.py")
    _run("build_font2_ukrainian.py")
    result = {}
    for folder, names in (("font1", paths.FONT1_FILES), ("font2", paths.FONT2_FILES)):
        for name in names:
            path = WORK / folder / name
            if not path.exists():
                raise UaError(f"Font build did not produce {path}")
            result[f"{paths.TEXT_DIR}/{name}"] = path.read_bytes()
    return result
