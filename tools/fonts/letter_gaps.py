"""Visible gaps between neighbouring letters: the game font vs the x4 font as rendered now.

Each pair of neighbouring letters from the test words is drawn as the game draws it
(tools/fonts/text_sheet.py) at `--scale` screen pixels per font pixel; the gap is the run
of empty columns (alpha <= 128) between the two glyphs' ink. Prints every Latin pair
(game, x4, difference), the Latin means and the x4 Ukrainian mean. The x4 font is
rendered from build/fonts/ (`python -m ua build --level full`). `--font 2` measures
Font 2 on capitals. `--set` overrides a key of the font's style in
assets/fonts/font_hd.json for this run only.

    python tools/fonts/letter_gaps.py
    python tools/fonts/letter_gaps.py --scale 2.7 --set tighten=0.5 --set stretch=1.035
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ua import paths  # noqa: E402
from ua.pipeline import font_hd  # noqa: E402
from ua.pipeline.fonts import WORK  # noqa: E402
from tools.fonts.text_sheet import GameFont  # noqa: E402

LATIN = ("The quick brown fox jumps over the lazy dog New Game Load Options Quit to Windows "
         "PACK MY BOX WITH FIVE DOZEN LIQUOR JUGS").split()
UKRAINIAN = ("Чуєш їх доцю га Кумедна ж ти прощайся без ґольфів Нова гра Завантажити Налаштування "
             "Вийти ЧУЄШ ЇХ ДОЦЮ ГА КУМЕДНА ПРОЩАЙСЯ БЕЗ ҐОЛЬФІВ").split()


def pairs(words: list[str]) -> list[str]:
    return sorted({w[i:i + 2] for w in words for i in range(len(w) - 1) if w[i:i + 2].isalpha()})


def gap(font: GameFont, pair: str, scale: float) -> int:
    """Empty screen columns between the ink of the two glyphs of `pair`."""
    alpha = font.line(pair, scale).getchannel("A").point(lambda v: 255 if v > 128 else 0)
    split = round(font.font.get_glyph_metrics(font.glyphs[pair[0]]).width * scale)
    left = alpha.crop((0, 0, split, alpha.height)).getbbox()
    right = alpha.crop((split, 0, alpha.width, alpha.height)).getbbox()
    if not left or not right:
        return 0
    return max(0, split + right[0] - left[2])


def override(text: str) -> tuple[str, object]:
    key, _, value = text.partition("=")
    try:
        return key, json.loads(value)
    except json.JSONDecodeError:
        return key, value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--font", type=int, choices=(1, 2), default=1)
    parser.add_argument("--scale", type=float, default=1.8, help="screen pixels per font pixel (2560x1440: 1.8)")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="override a font_hd.json key of this font, e.g. tighten=0.5")
    args = parser.parse_args()
    changes = dict(override(s) for s in args.set)
    game = paths.GAME / "GAME" / paths.TEXT_DIR
    if args.font == 1:
        spec = {**font_hd.style(), **changes}
        font_hd.style = lambda: spec
        font, _, big, _ = font_hd.render((WORK / "font1" / paths.FONT1_FILES[0]).read_bytes())
        old = GameFont((game / "FONT_PC.FNT").read_bytes())
        latin, ukrainian = pairs(LATIN), pairs(UKRAINIAN)
    else:
        spec = {**font_hd.font2_style(), **changes}
        font_hd.font2_style = lambda: spec
        font, _, big, _ = font_hd.render2((WORK / "font2" / paths.FONT2_FILES[0]).read_bytes())
        old = GameFont((game / "FONT2_PC.FNT").read_bytes())
        latin, ukrainian = pairs([w.upper() for w in LATIN]), pairs([w.upper() for w in UKRAINIAN])
    built = GameFont.rendered(font, big, spec["scale"])
    rows = [(p, gap(old, p, args.scale), gap(built, p, args.scale)) for p in latin
            if p[0] in old.glyphs and p[1] in old.glyphs]
    print(f"{'pair':6}{'game':>6}{'x4':>6}{'diff':>6}")
    for p, a, b in sorted(rows, key=lambda r: (r[2] - r[1], r[0])):
        print(f"{p:6}{a:6}{b:6}{b - a:+6}")
    ua = [gap(built, p, args.scale) for p in ukrainian]
    mean = lambda values: sum(values) / len(values)
    shown = ", ".join(f"{k}={spec[k]}" for k in ("size", "stretch", "outline", "tighten") if k in spec)
    print(f"Font {args.font}, style: {shown}, scale {args.scale}")
    print(f"Latin mean gap: game {mean([r[1] for r in rows]):.2f} px, x4 {mean([r[2] for r in rows]):.2f} px "
          f"({len(rows)} pairs)")
    print(f"Ukrainian mean gap: x4 {mean(ua):.2f} px ({len(ua)} pairs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
