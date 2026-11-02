"""
Renders a static PNG of the atlas with a colored rectangle drawn around
every glyph's rect (from the metrics table), color-coded by category --
same categories/colors as viewer.html. Quicker than opening the HTML tool
when you just want a screenshot to look at (e.g. to compare how the Latin
and Cyrillic ranges are boxed).

Requires atlas.png + glyphs.json in this folder (run export_glyph_atlas.py
first if they're missing or stale).

Run from repo root:
    python tools/glyph_viewer/render_boxes_png.py
    python tools/glyph_viewer/render_boxes_png.py --scale 2 --labels
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parents[3] / "build" / "glyph_viewer"

CAT_COLOR = {
    "patched": (255, 59, 59),
    "cyrillic": (78, 161, 255),
    "latinUpper": (255, 210, 78),
    "latinLower": (200, 255, 78),
    "digit": (78, 255, 210),
    "extended": (193, 78, 255),
    "other": (153, 153, 153),
}


def categorize(g: dict) -> str:
    if g["patched"]:
        return "patched"
    cp = g["codepoint"]
    if 0x30 <= cp <= 0x39:
        return "digit"
    if 0x41 <= cp <= 0x5A:
        return "latinUpper"
    if 0x61 <= cp <= 0x7A:
        return "latinLower"
    if 0x0400 <= cp <= 0x04FF:
        return "cyrillic"
    if 0x00A0 <= cp <= 0x02FF:
        return "extended"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=3, help="upscale factor for the output PNG (default 3)")
    ap.add_argument("--labels", action="store_true", help="draw each glyph's character above its box")
    ap.add_argument("--out", default=None, help="output path (default: <this folder>/atlas_boxes<suffix>.png)")
    ap.add_argument("--suffix", default="", help='matches export_glyph_atlas.py --suffix, e.g. "2" -> reads atlas2.png/glyphs2.json')
    args = ap.parse_args()

    atlas_path = HERE / f"atlas{args.suffix}.png"
    glyphs_path = HERE / f"glyphs{args.suffix}.json"
    if not atlas_path.exists() or not glyphs_path.exists():
        raise SystemExit(f"Missing {atlas_path} or {glyphs_path} -- run export_glyph_atlas.py first.")

    data = json.loads(glyphs_path.read_text(encoding="utf-8"))
    atlas = Image.open(atlas_path).convert("RGBA")

    scale = args.scale
    big = atlas.resize((atlas.width * scale, atlas.height * scale), Image.NEAREST)
    draw = ImageDraw.Draw(big)

    counts = {}
    for g in data["glyphs"]:
        cat = categorize(g)
        counts[cat] = counts.get(cat, 0) + 1
        color = CAT_COLOR[cat]
        x0, y0 = g["x"] * scale, g["y"] * scale
        x1, y1 = (g["x"] + g["width"]) * scale, (g["y"] + g["height"]) * scale
        draw.rectangle([x0, y0, x1, y1], outline=color, width=1 if cat != "patched" else 2)
        if args.labels:
            label = (g["char"].strip() or "␣")
            draw.text((x0, y0 - 10), label, fill=color)

    out_path = Path(args.out) if args.out else HERE / f"atlas_boxes{args.suffix}.png"
    big.save(out_path)
    print(f"wrote {out_path} ({big.size[0]}x{big.size[1]}, scale={scale}x)")
    print("glyph counts by category:", counts)


if __name__ == "__main__":
    main()
