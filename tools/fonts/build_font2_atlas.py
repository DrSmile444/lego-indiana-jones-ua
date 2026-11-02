"""
Builds the patched Font 2 atlas texture: composites the EXISTING pristine
512x512 "Adventure" atlas (unchanged, top-left corner) into a fresh, larger
1024x1024 canvas, then renders 33 new Ukrainian Cyrillic uppercase glyphs
(Franklin-Gothic-style approach from Font 1, but styled to match Font 2's
own orange-gradient-with-black-outline look) into the newly available
space below/right of the original content.

Font 2 (`local/extracted/indy1-original/.../FONT2_PC.FNT`) had ZERO
Cyrillic before this -- confirmed by decoding its own mapping table (see
tools/fnt_tool.py; this file uses three sentinel slots in its mapping table).
Only 33 NEW glyph SHAPES
are needed, not 66: Font 2's own existing Latin lowercase codepoints (a-z)
already just point at the SAME glyph_index as their uppercase counterpart
(this font has no distinct lowercase artwork at all -- confirmed directly:
even the donor TTF itself renders Cyrillic lowercase as the same shape as
uppercase). build_font2_ukrainian.py mirrors that pattern: each of the 33
new glyphs gets TWO mapping entries (upper- and lower-case codepoint),
both pointing at the one new glyph_index.

Run from repo root:
    python tools/build_font2_atlas.py
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp1252, can't print Cyrillic

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
ORIG_FONT2 = paths.GAME / "GAME/STUFF/TEXT/FONT2_PC.FNT"
ADVENTURE_TTF = paths.DONORS / "Adventure_Indiana_Jones.ttf"
OUT_PNG = paths.BUILD / "fonts/font2_patched_ukrainian.png"

OLD_SIZE = 512
NEW_SIZE = 1024
ROW_HEIGHT = 50          # matches this font's shared `height` header field
ROW_PITCH = 60           # extra vertical gap between our own new rows -- generous, we have room to spare
COL_GAP = 8              # extra horizontal gap between our own new glyphs
NEW_AREA_Y0 = OLD_SIZE    # new glyphs start right below the untouched old 512x512 content

# 33 Ukrainian uppercase letters (Ukrainian alphabet only -- excluding non-Ukrainian
# Ы/Ъ/Э). name is just for logging. lower_cp is what build_font2_ukrainian.py
# additionally maps to the SAME new glyph (see module docstring).
TARGETS = [
    ("А", 0x0410, 0x0430), ("Б", 0x0411, 0x0431), ("В", 0x0412, 0x0432),
    ("Г", 0x0413, 0x0433), ("Ґ", 0x0490, 0x0491), ("Д", 0x0414, 0x0434),
    ("Е", 0x0415, 0x0435), ("Є", 0x0404, 0x0454), ("Ж", 0x0416, 0x0436),
    ("З", 0x0417, 0x0437), ("И", 0x0418, 0x0438), ("І", 0x0406, 0x0456),
    ("Ї", 0x0407, 0x0457), ("Й", 0x0419, 0x0439), ("К", 0x041A, 0x043A),
    ("Л", 0x041B, 0x043B), ("М", 0x041C, 0x043C), ("Н", 0x041D, 0x043D),
    ("О", 0x041E, 0x043E), ("П", 0x041F, 0x043F), ("Р", 0x0420, 0x0440),
    ("С", 0x0421, 0x0441), ("Т", 0x0422, 0x0442), ("У", 0x0423, 0x0443),
    ("Ф", 0x0424, 0x0444), ("Х", 0x0425, 0x0445), ("Ц", 0x0426, 0x0446),
    ("Ч", 0x0427, 0x0447), ("Ш", 0x0428, 0x0448), ("Щ", 0x0429, 0x0449),
    ("Ь", 0x042C, 0x044C), ("Ю", 0x042E, 0x044E), ("Я", 0x042F, 0x044F),
]

RENDER_SIZE = 300
RENDER_STROKE = 10
# Sampled directly off the existing "A" glyph's own vertical gradient (see
# investigation before this script existed): top color near the cap, bottom
# color near the baseline.
GRAD_TOP = (255, 80, 16)
GRAD_BOTTOM = (255, 195, 33)

# Measured directly off the existing "A" glyph (glyph_index 65, rect
# x=1,y=0,w=35, row height=50): ink spans y=4..45 within its row -- cap
# top at 4, baseline (incl. this font's own small serif flourish) at 45.
CAP_TOP = 4
BASELINE = 45
CAP_HEIGHT_TARGET = BASELINE - CAP_TOP  # 41


def _measure_scale() -> float:
    f = ImageFont.truetype(str(ADVENTURE_TTF), RENDER_SIZE)
    tmp = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((250, 250), "А", font=f, stroke_width=RENDER_STROKE)
    rendered_cap_height = bb[3] - bb[1]
    return CAP_HEIGHT_TARGET / rendered_cap_height


def render_char(ch: str, scale: float) -> Image.Image:
    """Renders one glyph in Font 2's own style: black outline + a vertical
    orange-to-yellow gradient fill, matching GRAD_TOP/GRAD_BOTTOM sampled
    from the existing atlas. See build_font1_atlas.py's render_char() for
    the (much simpler, flat-fill) sibling used by Font 1."""
    f = ImageFont.truetype(str(ADVENTURE_TTF), RENDER_SIZE)
    tmp = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((250, 250), ch, font=f, stroke_width=RENDER_STROKE)

    base = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    ImageDraw.Draw(base).text((250, 250), ch, font=f, fill=(0, 0, 0, 255),
                               stroke_width=RENDER_STROKE, stroke_fill=(0, 0, 0, 255))

    mask_img = Image.new("L", (900, 900), 0)
    ImageDraw.Draw(mask_img).text((250, 250), ch, font=f, fill=255)

    x0, y0, x1, y1 = bb
    w, h = x1 - x0, y1 - y0
    grad = Image.new("RGBA", (w, h))
    for row in range(h):
        t = row / max(h - 1, 1)
        color = (
            round(GRAD_TOP[0] + (GRAD_BOTTOM[0] - GRAD_TOP[0]) * t),
            round(GRAD_TOP[1] + (GRAD_BOTTOM[1] - GRAD_TOP[1]) * t),
            round(GRAD_TOP[2] + (GRAD_BOTTOM[2] - GRAD_TOP[2]) * t),
            255,
        )
        grad.paste(Image.new("RGBA", (w, 1), color), (0, row))

    fill_layer = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    fill_layer.paste(grad, (x0, y0), mask_img.crop((x0, y0, x1, y1)))

    result = base.copy()
    result.alpha_composite(fill_layer)
    glyph = result.crop(bb)

    new_w = max(1, round(glyph.width * scale))
    new_h = max(1, round(glyph.height * scale))
    return glyph.resize((new_w, new_h), Image.LANCZOS)


def compute_layout(scale: float) -> list[dict]:
    """Packs the 33 new glyphs left-to-right, wrapping rows, starting right
    below the untouched old 512x512 content. Returns one dict per TARGETS
    entry with everything main() and build_font2_ukrainian.py need."""
    results = []
    x, row_y = 0, NEW_AREA_Y0
    row_h_used = 0
    for name, upper_cp, lower_cp in TARGETS:
        glyph = render_char(name, scale)
        if x + glyph.width > NEW_SIZE:
            x = 0
            row_y += ROW_PITCH
            row_h_used = 0
        baseline_in_row = row_y + BASELINE
        px = x
        py = baseline_in_row - glyph.height
        declared_width = glyph.width + 4  # small side bearing, like Font 1's SIDE_BEARING
        results.append({
            "ch": name, "upper_cp": upper_cp, "lower_cp": lower_cp,
            "image": glyph, "x": px, "y": py,
            "width": glyph.width, "height": glyph.height,
            "declared_width": declared_width,
        })
        x += glyph.width + COL_GAP
        row_h_used = max(row_h_used, glyph.height)
    used_bottom = row_y + ROW_PITCH
    assert used_bottom <= NEW_SIZE, f"ran out of vertical room: needed up to y={used_bottom}"
    return results


def main():
    scale = _measure_scale()
    print(f"cap-height calibrated scale: {scale:.4f}")

    # decode the pristine Font 2's own mip0 directly (self-contained, same
    # technique as tools/glyph_viewer/export_glyph_atlas.py's decode_mip0_png)
    import struct
    sys.path.insert(0, str(Path(__file__).parent))
    from ua.formats.fnt import FntFile
    fnt = FntFile(str(ORIG_FONT2))
    dds_off = fnt.dds_offset
    header = bytes(fnt.data[dds_off:dds_off + 128])
    w = struct.unpack_from("<I", header, 16)[0]
    h = struct.unpack_from("<I", header, 12)[0]
    assert (w, h) == (OLD_SIZE, OLD_SIZE), (w, h)
    mip0 = bytes(fnt.data[dds_off + 128:dds_off + 128 + w * h])
    import io
    old_atlas = Image.open(io.BytesIO(header + mip0)).convert("RGBA")

    canvas = Image.new("RGBA", (NEW_SIZE, NEW_SIZE), (0, 0, 0, 0))
    canvas.paste(old_atlas, (0, 0))

    layout = compute_layout(scale)
    for g in layout:
        canvas.alpha_composite(g["image"], (g["x"], g["y"]))
        print(f"{g['ch']}: pos=({g['x']},{g['y']}) size={g['width']}x{g['height']} "
              f"declared_width={g['declared_width']}")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PNG)
    print(f"saved {OUT_PNG} {canvas.size}")


if __name__ == "__main__":
    main()
