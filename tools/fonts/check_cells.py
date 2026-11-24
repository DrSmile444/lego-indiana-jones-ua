"""Checks the x4 font cells: no glyph drawn anew loses visible ink at its cell edges.

Runs ua.pipeline.font_hd.render (Font 1) and render2 (Font 2) on the fonts in build/fonts/
(`python -m ua build --level full` writes them) and measures every cell they draw. Visible
ink is alpha > 16 (font_hd.visible). Font 1: a Latin cell may cut up to font_hd.OVERHANG
x1 px of it, split over both sides; a Cyrillic cell cuts none; glyphs that keep the game's
pixels are not checked; the top and bottom pixel rows of every cell stay clear. Font 2: its
Latin glyphs follow the game's pixels, which touch their cell edges, so only the Ukrainian
letters are measured, and their losses are warnings that leave the exit code. Also writes a contact
sheet of every cell of each k-times atlas, cell box in red, to build/screens/cells-font1.png
and cells-font2.png. Exit code 1 when a glyph breaks the rule.

    python tools/fonts/check_cells.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ua import paths  # noqa: E402
from ua.pipeline import font_hd  # noqa: E402
from ua.pipeline.fonts import WORK  # noqa: E402

SCREENS = paths.BUILD / "screens"


def measure(whole: Image.Image, alpha: Image.Image, k: int) -> tuple[float, float, bool]:
    """(visible width cut in x1 px, ink lost in x1 px², ink in the top or bottom row) of a cell
    whose undivided alpha is `whole`."""
    full, kept = font_hd.visible(whole), font_hd.visible(alpha)
    cut = ((full[2] - full[0]) - (kept[2] - kept[0] if kept else 0)) / k if full else 0.0
    lost = (ImageStat.Stat(whole).sum[0] - ImageStat.Stat(alpha).sum[0]) / 255 / k / k
    edge_rows = bool(kept) and (kept[1] < k or kept[3] > alpha.height - k)
    return cut, lost, edge_rows


def contact_sheet(cells: list[Image.Image], path: Path, zoom: float = 0.5, columns: int = 16) -> None:
    cells = [c.resize((max(1, round(c.width * zoom)), round(c.height * zoom))) for c in cells]
    pad = 6
    cw, ch = max(c.width for c in cells) + pad, max(c.height for c in cells) + pad
    sheet = Image.new("RGB", (columns * cw, -(-len(cells) // columns) * ch), (40, 70, 120))
    draw = ImageDraw.Draw(sheet)
    for i, c in enumerate(cells):
        x, y = (i % columns) * cw + 3, (i // columns) * ch + 3
        sheet.paste(c, (x, y), c)
        draw.rectangle((x - 1, y - 1, x + c.width, y + c.height), outline=(255, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def report(name: str, records: dict, allowed, kept: set[str]) -> list[str]:
    checked = {c: r for c, r in records.items() if c and c not in kept}
    bad = [f"  {c} U+{ord(c):04X} w={w} cut {cut:.2f} px (allowed {allowed(c)}), ink lost {lost:.2f} px², "
           f"edge row {'yes' if rows else 'no'}"
           for c, (w, (cut, lost, rows)) in sorted(checked.items()) if cut > allowed(c) + 1e-6 or rows]
    worst = max((r[1][0] for r in checked.values()), default=0.0)
    print(f"{name}: {len(checked)} drawn cells, widest cut {worst:.2f} px, {len(kept)} keep game pixels")
    print("\n".join(bad) if bad else "  every cell holds its visible ink")
    return bad


def sheet(name: str, font, big: Image.Image, k: int) -> None:
    h = int(font.height)
    cells = []
    for index in sorted({e.glyph_index for e in font.list_mapping()}):
        g = font.get_glyph_metrics(index)
        if round(g.width) > 0:
            cells.append(big.crop((round(g.x * k), round(g.y * k), round((g.x + g.width) * k), round((g.y + h) * k))))
    path = SCREENS / f"cells-{name}.png"
    contact_sheet(cells, path)
    print(" ", path)


def main() -> int:
    font1, font2 = {}, {}
    draw, paint = font_hd.Renderer.cell, font_hd._paint2

    def cell(self, char, width, centre=None):
        out = draw(self, char, width, centre)
        whole = ImageChops.lighter(*self.masks(char))
        font1[char] = (width, measure(whole, out.getchannel("A"), self.k))  # the last call is the atlas cell
        return out

    def paint2(fill, spec, k):
        out = paint(fill, spec, k)
        r = round(spec["outline"] * k) + 2
        wide = Image.new("L", (fill.width + 2 * r, fill.height + 2 * r), 0)
        wide.paste(fill, (r, r))
        whole = ImageChops.lighter(font_hd._dilate(wide, r - 2), wide)
        char = sys._getframe(1).f_locals.get("char", "")  # render2's loop variable
        if "Ѐ" <= char <= "ӿ":
            font2[char] = (fill.width // k, measure(whole, out.getchannel("A"), k))
        return out

    font_hd.Renderer.cell, font_hd._paint2 = cell, paint2
    bad = []
    f1, _, big1, notes = font_hd.render((WORK / "font1" / paths.FONT1_FILES[0]).read_bytes())
    kept = {chr(int(n.split("U+")[1][:4], 16)) for n in notes if n.startswith("kept game pixels")}
    bad += report("Font 1", font1, lambda c: 0.0 if "Ѐ" <= c <= "ӿ" else font_hd.OVERHANG, kept)
    sheet("font1", f1, big1, font_hd.style()["scale"])
    f2, _, big2, _ = font_hd.render2((WORK / "font2" / paths.FONT2_FILES[0]).read_bytes())
    report("Font 2 (warnings)", font2, lambda c: 0.0, set())
    sheet("font2", f2, big2, font_hd.font2_style()["scale"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
