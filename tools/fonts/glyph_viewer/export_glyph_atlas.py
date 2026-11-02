"""
Exports the data the glyph viewer/editor (viewer.html, in this same folder)
needs to visualize every glyph's rect directly on top of the real atlas
texture:
  - atlas<suffix>.png: the font's mip0 texture, decoded from DXT5 to a plain PNG.
  - glyphs<suffix>.json: one entry per mapped codepoint, with its character,
    glyph index, and (x, y, width, height) rect straight from the metrics
    table (see tools/fnt_tool.py / local/research/fnt-format-findings.md for
    how this table was decoded).
  - glyph_data<suffix>.js: same payload as glyphs<suffix>.json, assigned to
    `window.GLYPH_DATA<suffix upper>` -- viewer.html includes this via
    <script src>, not fetch() (fetching a local JSON file is blocked by CORS
    when the page is opened directly (file://) without a server; a <script>
    tag is not).

Supports Font 1 and Font 2 using their declared mapping pointer/count.
Their different initial bytes are relocation offsets, not format versions.

Run from repo root:
    python tools/glyph_viewer/export_glyph_atlas.py                                   # Font 1 (default)
    python tools/glyph_viewer/export_glyph_atlas.py path/to/some.FNT
    python tools/glyph_viewer/export_glyph_atlas.py path/to/FONT2_PC.FNT --suffix 2    # -> atlas2.png etc.
"""
import argparse
import io
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from ua.formats.fnt import FntFile  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
DEFAULT_FNT = paths.BUILD / "fonts/font1/PC_FONT_PC.FNT"
OUT_DIR = paths.BUILD / "glyph_viewer"  # generated data stays out of git
DDS_HEADER_SIZE = 128

# The 8 glyph indices this project's Ukrainian patch repaints in FONT 1 (see
# tools/build_font1_atlas.py TARGETS) -- flagged separately in glyphs.json so
# the viewer can highlight "ours" vs "everything else" by default. Font 2
# doesn't have an equivalent yet, so this is only ever passed for Font 1.
FONT1_PATCHED_GLYPH_INDICES = {160, 162, 164, 165, 166, 168, 169, 170}
DEFAULT_FONT2 = paths.BUILD / "fonts/font2/FONT2_PC.FNT"
# The 33 new Ukrainian glyph indices build_font2_ukrainian.py appends (see
# its own self-check print for the exact range) -- flagged the same way as
# FONT1_PATCHED_GLYPH_INDICES so the viewer can highlight "ours" for Font 2 too.
FONT2_PATCHED_GLYPH_INDICES = set(range(164, 197))


def decode_mip0_png(fnt: FntFile, out_path: Path):
    """Self-contained: the file's own embedded DDS chunk already has a
    complete, standard 128-byte DDS header (magic, DXT5 fourcc, width,
    height) right at dds_offset -- no need to borrow one from a separate
    reference file, and no need to hardcode the atlas size, so this works
    unchanged for Font 2's smaller 512x512 atlas too."""
    dds_off = fnt.dds_offset
    header = bytes(fnt.data[dds_off:dds_off + DDS_HEADER_SIZE])
    width = struct.unpack_from("<I", header, 16)[0]
    height = struct.unpack_from("<I", header, 12)[0]
    mip0_size = width * height  # DXT5 = 1 byte/pixel at mip0
    mip0 = bytes(fnt.data[dds_off + DDS_HEADER_SIZE:dds_off + DDS_HEADER_SIZE + mip0_size])

    from PIL import Image
    Image.open(io.BytesIO(header + mip0)).convert("RGBA").save(out_path)
    return width, height


def export(fnt_path: Path, suffix: str, patched_glyph_indices: set[int]):
    fnt = FntFile(str(fnt_path))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(Path(__file__).with_name("viewer.html"), OUT_DIR / "viewer.html")
    atlas_png = OUT_DIR / f"atlas{suffix}.png"
    width, height = decode_mip0_png(fnt, atlas_png)
    print(f"wrote {atlas_png} ({width}x{height})")

    glyphs = []
    for entry in fnt.list_mapping():
        m = fnt.get_glyph_metrics(entry.glyph_index)
        try:
            char = chr(entry.codepoint)
        except ValueError:
            char = ""
        glyphs.append({
            "codepoint": entry.codepoint,
            "char": char,
            "glyph_index": entry.glyph_index,
            "x": m.x,
            "y": m.y,
            "width": m.width,
            "height": fnt.height,
            "patched": entry.glyph_index in patched_glyph_indices,
        })

    payload = {
        "source": str(fnt_path), "font_height": fnt.height, "base": fnt.base,
        "atlas_width": width, "atlas_height": height, "glyphs": glyphs,
    }

    glyphs_json = OUT_DIR / f"glyphs{suffix}.json"
    glyphs_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {glyphs_json} ({len(glyphs)} glyphs, "
          f"{sum(g['patched'] for g in glyphs)} flagged as our Ukrainian patch)")

    var_name = "GLYPH_DATA" + (f"_{suffix.upper()}" if suffix else "")
    glyph_data_js = OUT_DIR / f"glyph_data{suffix}.js"
    glyph_data_js.write_text(
        f"window.{var_name} = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {glyph_data_js} (window.{var_name})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fnt_path", nargs="?", default=str(DEFAULT_FNT))
    ap.add_argument("--suffix", default="", help='output suffix, e.g. "2" -> atlas2.png/glyphs2.json/glyph_data2.js')
    args = ap.parse_args()

    given = Path(args.fnt_path).resolve()
    if given == DEFAULT_FNT.resolve():
        patched = FONT1_PATCHED_GLYPH_INDICES
    elif given == DEFAULT_FONT2.resolve():
        patched = FONT2_PATCHED_GLYPH_INDICES
    else:
        patched = set()
    export(Path(args.fnt_path), args.suffix, patched)


if __name__ == "__main__":
    main()
