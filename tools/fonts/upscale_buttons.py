"""Upscale the 2x button icon atlases of LEGO Star Wars III four times with Real-ESRGAN.

    python tools/fonts/upscale_buttons.py [FT2 ...]

Default input: the button fonts that `python -m ua extract --lsw3` puts in game/LSW3/.
Output: local/buttons/<FONT>_X4.png (RGBA, four times the FT2 atlas) for ua/pipeline/buttons_hd.py.
The SHA-256 of each output goes to manifests/inputs.json by hand after a check.

Each glyph is upscaled alone, with a transparent border, so no ink runs into the next cell;
the colour under transparent pixels is the nearest ink colour, so edges get no dark fringe.
Tool: realesrgan-ncnn-vulkan, model realesr-animevideov3, scale 4; folder from UA_REALESRGAN
(default E:\\AI-Tools\\Real-ESRGAN-Full). It is third-party and stays outside the repository.
"""
from __future__ import annotations

import hashlib
import io
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402

TOOL = Path(os.environ.get("UA_REALESRGAN", r"E:\AI-Tools\Real-ESRGAN-Full"))
MODEL = "realesr-animevideov3"
SCALE = 4
MARGIN = 3  # px left and right of each glyph cell that may hold its ink (2x atlas)
BORDER = 8  # transparent px around each glyph before upscaling
FAINT = 6  # alpha at or below this after upscaling is noise and becomes 0
FONTS = ("BUTTONS_PC_NXG.FT2",)
SOURCE = paths.GAME / "LSW3" / "GAME" / "FRAMEWORK-DATA" / "GUI" / "FONT"
OUTPUT = paths.LOCAL / "buttons"


def parse(data: bytes) -> tuple[float, list[tuple[float, float, float]], Image.Image]:
    """(cell height, glyph rectangles, atlas) of an NXG .FT2 font (big endian)."""
    if data[8:12] != b"TNFN":
        raise SystemExit("not an FT2 font")
    height = struct.unpack_from(">f", data, 0x22)[0]
    count = struct.unpack_from(">I", data, 0x36)[0]
    glyphs = [struct.unpack_from(">fff", data, 0x3A + 12 * i) for i in range(count)]
    image = Image.open(io.BytesIO(data[data.index(b"DDS ", 0x3A + 12 * count):]))
    image.load()
    return height, glyphs, image.convert("RGBA")


def bleed(image: Image.Image) -> Image.Image:
    """Colour of fully transparent pixels grown in from the nearest ink; alpha unchanged."""
    alpha = image.getchannel("A")
    known = alpha.point(lambda a: 255 if a else 0)
    rgb = Image.composite(image.convert("RGB"), Image.new("RGB", image.size), known)
    while known.getextrema()[0] < 255 and known.getextrema()[1] == 255:
        weight = known.filter(ImageFilter.BoxBlur(1)).tobytes()
        sums = [c.filter(ImageFilter.BoxBlur(1)).tobytes() for c in rgb.split()]
        grown = Image.merge("RGB", [Image.frombytes("L", rgb.size, bytes(
            min(255, v * 255 // w) if w else 0 for v, w in zip(band, weight))) for band in sums])
        reach = known.filter(ImageFilter.MaxFilter(3))
        rgb = Image.composite(rgb, grown, known)
        rgb = Image.composite(rgb, Image.new("RGB", rgb.size), reach)
        known = reach
    out = rgb.copy()
    out.putalpha(alpha)
    return out


def error(a: Image.Image, b: Image.Image) -> float:
    pixels = ImageChops.difference(a.convert("RGBa"), b.convert("RGBa")).tobytes()
    return sum(pixels) / len(pixels)


def upscale(ft2: Path) -> Path:
    height, glyphs, atlas = parse(ft2.read_bytes())
    exe = TOOL / "realesrgan-ncnn-vulkan.exe"
    if not exe.exists():
        raise SystemExit(f"{exe} not found; set UA_REALESRGAN to the Real-ESRGAN folder")
    boxes = {}
    for index, (x, y, w) in enumerate(glyphs):
        if w > 0:
            boxes[index] = (max(0, int(x) - MARGIN), int(y), min(atlas.width, int(x + w) + MARGIN), int(y + height))
    big = Image.new("RGBA", (atlas.width * SCALE, atlas.height * SCALE))
    with tempfile.TemporaryDirectory() as work:
        src, dst = Path(work, "in"), Path(work, "out")
        src.mkdir()
        dst.mkdir()
        for index, box in boxes.items():
            cell = atlas.crop(box)
            padded = Image.new("RGBA", (cell.width + 2 * BORDER, cell.height + 2 * BORDER))
            padded.paste(cell, (BORDER, BORDER))
            bleed(padded).save(src / f"{index:02d}.png")
        result = subprocess.run([str(exe), "-i", str(src), "-o", str(dst), "-n", MODEL, "-s", str(SCALE),
                                 "-f", "png", "-m", str(TOOL / "models")], capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"Real-ESRGAN failed:\n{result.stdout[-1500:]}{result.stderr[-1500:]}")
        for index, box in boxes.items():
            up = Image.open(dst / f"{index:02d}.png").convert("RGBA")
            b = BORDER * SCALE
            up = up.crop((b, b, b + (box[2] - box[0]) * SCALE, b + (box[3] - box[1]) * SCALE))
            alpha = up.getchannel("A").point(lambda a: 0 if a <= FAINT else a)
            up.putalpha(alpha)
            big.paste(up, (box[0] * SCALE, box[1] * SCALE))
    for index, box in boxes.items():
        cell = big.crop(tuple(v * SCALE for v in box)).convert("RGBa").resize(
            (box[2] - box[0], box[3] - box[1]), Image.Resampling.BOX)
        print(f"  glyph {index:2d}: mean error {error(cell, atlas.crop(box)):5.2f} against the 2x art")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    out = OUTPUT / (ft2.stem + "_X4.png")
    big.save(out, optimize=False)
    print(f"{out}  SHA-256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    return out


def main() -> None:
    sources = [Path(a) for a in sys.argv[1:]] or [SOURCE / name for name in FONTS]
    for ft2 in sources:
        if not ft2.exists():
            raise SystemExit(f"{ft2} not found. Run: python -m ua extract --lsw3 <LEGO Star Wars III Steam folder>")
        print(ft2.name)
        upscale(ft2)


if __name__ == "__main__":
    main()
