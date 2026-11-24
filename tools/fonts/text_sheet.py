"""Draws test texts with a game font the way the game draws them, outside the game.

Each glyph is a quad: the atlas rectangle (x, y, width, cell height) of its metric record,
stretched to `scale` screen pixels per font pixel, placed at the running sum of the
advances. A 1x atlas is magnified bilinearly (as the GPU does); a k-times atlas is reduced
with area filtering (as mip levels and trilinear filtering do). The sheet shows one text
block per font variant, so the original font and the new one can be compared line by line.

    python tools/fonts/text_sheet.py                       # the built package vs the game font
    python tools/fonts/text_sheet.py --scale 1.8 --out build/screens/text-sheet.png
"""
from __future__ import annotations

import argparse
import io
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ua import paths  # noqa: E402
from ua.formats import uap  # noqa: E402
from ua.pipeline import font_hd  # noqa: E402

LATIN = [
    "The quick brown fox jumps over the lazy dog.",
    "PACK MY BOX WITH FIVE DOZEN LIQUOR JUGS!",
    "New Game  Load Game  Options  Quit to Windows",
    "0123456789  % & ( ) + - = / : ; , . ! ? ’ “ ”",
]
UKRAINIAN = [
    "Чуєш їх, доцю, га? Кумедна ж ти, прощайся без ґольфів!",
    "ЧУЄШ ЇХ, ДОЦЮ, ГА? КУМЕДНА Ж ТИ, ПРОЩАЙСЯ БЕЗ ҐОЛЬФІВ!",
    "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя",
    "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ",
    "Нова гра  Завантажити гру  Налаштування  Вийти до Windows",
    "Їжак Євген, ґедзь, п’ять м’ячів — 100% «так»",
]


class GameFont:
    """A font as the game sees it: metrics from the FNT, pixels from its atlas or a k-times one."""

    def __init__(self, fnt: bytes, hd: bytes | None = None):
        self.font = font_hd._font(fnt)
        if hd and fnt[self.font.dds_offset + 32:self.font.dds_offset + 36] == b"UAHD":
            self.k = struct.unpack_from("<I", fnt, self.font.dds_offset + 36)[0]
            self.atlas = Image.open(io.BytesIO(hd)).convert("RGBA")
        else:
            self.k = 1
            self.atlas = Image.open(io.BytesIO(bytes(self.font.data[self.font.dds_offset:]))).convert("RGBA")
        self.height = int(self.font.height)
        self.glyphs = {chr(e.codepoint): e.glyph_index for e in self.font.list_mapping()}

    @classmethod
    def rendered(cls, font, atlas: Image.Image, k: int) -> GameFont:
        """The font as font_hd.render or render2 returns it: repacked metrics and the k-times atlas."""
        self = cls.__new__(cls)
        self.font, self.atlas, self.k, self.height = font, atlas.convert("RGBA"), k, int(font.height)
        self.glyphs = {chr(e.codepoint): e.glyph_index for e in font.list_mapping()}
        return self

    def chars(self) -> str:
        return "".join(sorted(c for c in self.glyphs if c.isprintable() and c != " "))

    def line(self, text: str, scale: float, colour=(255, 255, 255)) -> Image.Image:
        k, h = self.k, self.height
        out_h = round(h * scale)
        widths = [self.font.get_glyph_metrics(self.glyphs[c]).width if c in self.glyphs else 0 for c in text]
        out = Image.new("RGBA", (max(1, round(sum(widths) * scale) + 4), out_h), (0, 0, 0, 0))
        x = 0.0
        for c, w in zip(text, widths):
            if c in self.glyphs and w > 0 and c != " ":  # the game draws no quad for a space
                g = self.font.get_glyph_metrics(self.glyphs[c])
                cell = self.atlas.crop((round(g.x * k), round(g.y * k), round((g.x + w) * k), round((g.y + h) * k)))
                size = (max(1, round(w * scale)), out_h)
                method = Image.Resampling.BILINEAR if k * 1.0 < scale else Image.Resampling.BOX
                cell = cell.convert("RGBa").resize(size, method).convert("RGBA")
                if colour != (255, 255, 255):
                    r, gg, b, a = cell.split()
                    tint = [ch.point(lambda v, m=m: v * m // 255) for ch, m in zip((r, gg, b), colour)]
                    cell = Image.merge("RGBA", (*tint, a))
                out.alpha_composite(cell, (round(x * scale), 0))
            x += w
        return out


def sheet(variants: list[tuple[str, GameFont]], texts: list[str], scale: float, colour,
          background=(52, 44, 36)) -> Image.Image:
    label_font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
    blocks = []
    for name, font in variants:
        lines = [font.line(t, scale, colour) for t in texts]
        chars = font.chars()
        for i in range(0, len(chars), 48):
            lines.append(font.line(chars[i:i + 48], scale, colour))
        width = max(l.width for l in lines) + 24
        block = Image.new("RGB", (width, 40 + sum(l.height for l in lines)), background)
        ImageDraw.Draw(block).text((12, 8), name, font=label_font, fill=(235, 235, 235))
        y = 40
        for l in lines:
            block.paste(l, (12, y), l)
            y += l.height
        blocks.append(block)
    out = Image.new("RGB", (max(b.width for b in blocks), sum(b.height + 8 for b in blocks)), (20, 18, 16))
    y = 0
    for b in blocks:
        out.paste(b, (0, y))
        y += b.height + 8
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--uap", default=str(paths.BUILD / "UKRAINIAN.uap"))
    parser.add_argument("--scale", type=float, default=1.8, help="screen pixels per font pixel (2560x1440 menu: 1.8)")
    parser.add_argument("--out", default=str(paths.BUILD / "screens" / "text-sheet"))
    args = parser.parse_args()
    built = dict(uap.read(Path(args.uap).read_bytes()))
    game = paths.GAME / "GAME" / "STUFF" / "TEXT"
    pairs = [
        ("font1", "FONT_PC.FNT", "PC_FONT_PC.FNT", "UKRAINIAN/FONT_HD.DDS", (255, 255, 255)),
        ("font2", "FONT2_PC.FNT", "FONT2_PC.FNT", "UKRAINIAN/FONT2_HD.DDS", (255, 255, 255)),
    ]
    for tag, game_name, built_name, hd_name, colour in pairs:
        original = GameFont((game / game_name).read_bytes())
        new = GameFont(built[f"STUFF/TEXT/{built_name}"], built.get(hd_name))
        for lang, texts, variants in (
            ("en", LATIN, [("Оригінал гри", original), (f"Новий x{new.k}", new)]),
            ("ua", UKRAINIAN + LATIN, [(f"Новий x{new.k}", new)]),
        ):
            path = Path(f"{args.out}-{tag}-{lang}.png")
            path.parent.mkdir(parents=True, exist_ok=True)
            sheet(variants, texts, args.scale, colour).save(path)
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
