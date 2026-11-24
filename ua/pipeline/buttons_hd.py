"""Controller button icons at four times the resolution, from the game studio's own 2x art.

The game draws button icons (A B X Y, LB RB, LT RT, d-pad, arrows) from a small font,
STUFF/TEXT/BUTTONS_PC_PC.FNT (the EXE asks for stuff\text\buttons_PC and the engine adds
_PC.FNT): a 256x128 DXT5 atlas, cells 36 px tall. LEGO Star Wars III:
The Clone Wars ships the same icon set, same colours and same order, drawn at twice the
size (FRAMEWORK-DATA/GUI/FONT/BUTTONS_PC_NXG.FT2: 512x256, cells 72 px tall;
python -m ua extract --lsw3). tools/fonts/upscale_buttons.py enlarges that art four times
more with Real-ESRGAN, glyph by glyph (local/buttons/BUTTONS_PC_NXG_X4.png); the build
reduces it to K = 4 times this game's atlas.

Each icon is placed by its glyph rectangle: the 2x cell goes centre on centre over the 1x
cell, then moves by up to SHIFT pixels to where it, reduced to 1x, is closest to the
game's 1x cell. The K-times cell comes from the same place in the enlarged art. A glyph
whose mean error stays above MAX_ERROR stops the build. Atlas pixels outside the glyph
cells are the 1x atlas, enlarged.

Output: the FNT with its own 1x atlas and the UAHD mark (K, slot) in its DDS header, and
UKRAINIAN/BUTTONS_HD.DDS, the K-times atlas with a full mip chain. native/asi/font_hd.h
hands that atlas to D3DX when the game loads the marked one.
"""
from __future__ import annotations

import io
import struct
from dataclasses import dataclass

from PIL import Image, ImageChops

from .. import paths
from ..util import UaError
from .font_hd import MARK, _cached_dds, chain

RESOURCE = "STUFF/TEXT/BUTTONS_PC_PC.FNT"
HD_RESOURCE = "UKRAINIAN/BUTTONS_HD.DDS"
SLOT = 2  # font_hd.h atlas slot (0 = Font 1, 1 = Font 2)
K = 4
SOURCE = "GAME/FRAMEWORK-DATA/GUI/FONT/BUTTONS_PC_NXG.FT2"  # inside game/LSW3/
ART = "buttons/BUTTONS_PC_NXG_X4.png"  # inside local/: the 2x art enlarged 4 times
SHIFT = 4  # largest search offset, 2x pixels
MAX_ERROR = 16.0  # mean absolute RGBA difference (0-255) of a cell reduced to 1x


@dataclass(frozen=True)
class Cell:
    index: int
    x: int
    y: int
    width: int
    offset: tuple[int, int]
    error: float  # 2x art reduced to 1x against the game's cell
    error_hd: float  # K-times cell reduced to 1x against the game's cell


def _fnt(data: bytes) -> tuple[int, float, list[tuple[float, float, float]]]:
    """(DDS offset, cell height, glyph rectangles) of a button FNT."""
    dds = 8 + struct.unpack_from("<I", data, 0x08)[0]
    count = struct.unpack_from("<I", data, 0x1C)[0]
    height = struct.unpack_from("<f", data, 0x24)[0]
    metrics = 0x44 + struct.unpack_from("<I", data, 0x44)[0]
    if data[dds:dds + 4] != b"DDS " or data[dds + 84:dds + 88] != b"DXT5":
        raise UaError("Button font: atlas is not a DXT5 DDS")
    return dds, height, [struct.unpack_from("<fff", data, metrics + 12 * i) for i in range(count)]


def _ft2(data: bytes) -> tuple[float, list[tuple[float, float, float]], Image.Image]:
    """(cell height, glyph rectangles, atlas) of an NXG .FT2 font (big endian)."""
    if data[8:12] != b"TNFN":
        raise UaError("LEGO Star Wars III button font: not an FT2 file")
    height = struct.unpack_from(">f", data, 0x22)[0]
    count = struct.unpack_from(">I", data, 0x36)[0]
    glyphs = [struct.unpack_from(">fff", data, 0x3A + 12 * i) for i in range(count)]
    return height, glyphs, _image(data[data.index(b"DDS ", 0x3A + 12 * count):])


def _image(dds: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(dds))
    image.load()
    return image.convert("RGBA")


def _reduce(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.convert("RGBa").resize(size, Image.Resampling.BOX).convert("RGBA")


def error(a: Image.Image, b: Image.Image) -> float:
    """Mean absolute difference of premultiplied RGBA, 0-255."""
    pixels = ImageChops.difference(a.convert("RGBa"), b.convert("RGBa")).tobytes()
    return sum(pixels) / len(pixels)


def source() -> bytes:
    path = paths.GAME / "LSW3" / SOURCE
    if not path.exists():
        raise UaError(f"{path} not found. The button icons come from LEGO Star Wars III: The Clone Wars. "
                      "Run: python -m ua extract --lsw3 <LEGO Star Wars III Steam folder>")
    return path.read_bytes()


def art() -> Image.Image:
    path = paths.LOCAL / ART
    if not path.exists():
        raise UaError(f"{path} not found. Run: python tools/fonts/upscale_buttons.py (needs Real-ESRGAN)")
    return Image.open(path).convert("RGBA")


def render(original: bytes, donor: bytes, enlarged: Image.Image) -> tuple[Image.Image, Image.Image, list[Cell]]:
    """(1x atlas, K-times atlas, placed cells)."""
    dds, height, glyphs = _fnt(original)
    small = _image(original[dds:])
    donor_height, donor_glyphs, donor_art = _ft2(donor)
    d = round(donor_height / height)  # the donor's scale against this game
    if d != 2 or donor_height != height * d or donor_art.size != (small.width * d, small.height * d):
        raise UaError("LEGO Star Wars III button font is not the 2x twin of the game's button font")
    if enlarged.width % donor_art.width or enlarged.width * donor_art.height != enlarged.height * donor_art.width:
        raise UaError(f"{ART}: not an enlargement of the LEGO Star Wars III button atlas")
    hd_art = _reduce(enlarged, (small.width * K, small.height * K))
    big = small.convert("RGBa").resize(hd_art.size, Image.Resampling.LANCZOS).convert("RGBA")
    cells = []
    for index, (x, y, w) in enumerate(glyphs):
        if w <= 0 or index >= len(donor_glyphs) or donor_glyphs[index][2] <= 0:
            continue
        sx, sy, sw = donor_glyphs[index]
        x, y, w = int(x), int(y), int(w)
        target = small.crop((x, y, x + w, y + int(height)))
        size = (w * d, int(height) * d)
        left = int(sx) - round((size[0] - sw) / 2)  # centre on centre
        best = None
        for dy in range(-SHIFT, SHIFT + 1):
            for dx in range(-SHIFT, SHIFT + 1):
                box = (left + dx, int(sy) + dy, left + dx + size[0], int(sy) + dy + size[1])
                if box[0] < 0 or box[1] < 0 or box[2] > donor_art.width or box[3] > donor_art.height:
                    continue
                e = error(_reduce(donor_art.crop(box), target.size), target)
                if best is None or e < best[0]:
                    best = (e, dx, dy, box)
        if best is None:
            raise UaError(f"Button glyph {index}: no 2x cell inside the LEGO Star Wars III atlas")
        e, dx, dy, box = best
        cell = hd_art.crop(tuple(v * K // d for v in box))
        e_hd = error(_reduce(cell, target.size), target)
        if max(e, e_hd) > MAX_ERROR:
            raise UaError(f"Button glyph {index}: the new art differs from the game's icon "
                          f"(mean error {e:.1f} at 2x, {e_hd:.1f} at {K}x)")
        big.paste(cell, (x * K, y * K))
        cells.append(Cell(index, x, y, w, (dx, dy), e, e_hd))
    return small, big, cells


def build(original: bytes, donor: bytes, enlarged: Image.Image) -> tuple[bytes, bytes, list[Cell]]:
    """Return (marked FNT, BUTTONS_HD.DDS, cells)."""
    _, big, cells = render(original, donor, enlarged)
    dds, _, _ = _fnt(original)
    data = bytearray(original)
    header = data[dds:dds + 128]
    header[32:36] = MARK
    struct.pack_into("<II", header, 36, K, SLOT)
    data[dds:dds + 128] = header
    hd = _cached_dds(big, bytes(original[dds:dds + 128]), len(chain(*big.size)))
    return bytes(data), hd, cells
