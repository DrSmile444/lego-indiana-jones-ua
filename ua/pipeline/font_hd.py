"""Font 1 (the main UI font) drawn from its typeface at k times the atlas resolution.

The glyphs are Franklin Gothic Medium in a white fill with a 3 px grey outline
(assets/fonts/font_hd.json holds the fitted style). Every glyph whose character the
typeface has is drawn again with FreeType at k times the size, in the same pixel model:
alpha = outline coverage, colour = white over the outline grey by fill coverage. Latin
glyphs keep their advance and ink centre, so English text keeps its layout. Cyrillic
glyphs get an advance sized from their own ink plus the side margin of the Latin glyphs.
Glyphs the typeface does not draw (button icons, arrows, aiming triangles) keep the
font's pixels, scaled up.

Input: Font 1 as fonts.py builds it (mapping with the Ukrainian code points). Output: the
same FNT with the original 1x atlas size (the k-times atlas reduced to 1x, glyphs repacked
with gaps so texture filtering never mixes neighbours; its DDS header carries the UAHD
mark and k; file size unchanged) and UKRAINIAN/FONT_HD.DDS, the k-times atlas with a full
mip chain. native/asi/font_hd.h hands that atlas to D3DX when the game loads the marked one.
"""
from __future__ import annotations

import hashlib
import io
import math
import os
import struct
import unicodedata
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .. import paths
from ..formats import bc_encode
from ..formats.fnt import FntFile
from ..util import UaError, read_json

STYLE = paths.ASSETS / "fonts" / "font_hd.json"
HD_RESOURCE = "UKRAINIAN/FONT_HD.DDS"
OUTLINE = (41, 40, 41)
MARK = b"UAHD"  # DDS dwReserved1[0] of the 1x atlas; dwReserved1[1] holds k
GAP = 4  # empty pixels between packed glyphs (x1)
# Visible ink (x1 px) a cell may cut, half on each side: the game's own glyphs touch their
# cell edges, and the typeface's ink is up to this much wider than they are.
OVERHANG = 0.75
# Latin glyphs that have the same shape in the typeface as a Cyrillic letter; their
# advance minus their ink gives the side margin for the Cyrillic cells.
TWINS = "ABEHKMOPCTXaeopcx"
# A glyph is drawn from the typeface when it resembles the typeface's character: letters,
# digits and text punctuation differ only in details (flattened accents, the ear of g),
# so their bar is lower; icons mapped to text codepoints stay game pixels.
SIMILARITY = 0.55
TEXT_SIMILARITY = 0.25
TEXT_PUNCTUATION = ",.:;!?'\"-()&%/“”‘’ªº²³§™"


def style() -> dict:
    return read_json(STYLE)


def typeface_path(names: list[str]) -> Path:
    """The typeface file: local/fonts/ or local/donors/ (pinned in manifests/inputs.json), UA_FONT_DIR, Windows Fonts."""
    folders = [str(paths.LOCAL / "fonts"), str(paths.DONORS), os.environ.get("UA_FONT_DIR"),
               os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
               os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    for folder in folders:
        for name in names:
            if folder and (Path(folder) / name).exists():
                return Path(folder) / name
    raise UaError(f"Typeface {names[0]} not found (local/fonts/, UA_FONT_DIR or the Windows Fonts folder)")


class Renderer:
    def __init__(self, scale: int, spec: dict, cell: int):
        self.k = scale
        self.cell_height = cell
        self.ss = 2  # supersampling before the horizontal stretch
        self.font = ImageFont.truetype(str(typeface_path(spec["files"])), round(spec["size"] * scale * self.ss))
        self.stretch = spec["stretch"]
        self.outline = spec["outline"] * scale
        self.baseline = spec["baseline"]
        self._masks: dict[str, tuple[Image.Image, Image.Image]] = {}

    def _probe(self, char: str) -> bytes:
        image = Image.new("L", (600, 600), 0)
        ImageDraw.Draw(image).text((50, 450), char, font=self.font, fill=255, anchor="ls")
        return image.tobytes()

    def has(self, char: str) -> bool:
        """The typeface draws `char` itself (not its missing-glyph box)."""
        probe = self._probe(char)
        return any(probe) and probe != self._probe("\uffff")

    def masks(self, char: str) -> tuple[Image.Image, Image.Image]:
        """(fill, outline) coverage at k-scale, one cell tall, ink starting near x = 0."""
        if char in self._masks:
            return self._masks[char]
        ss, k = self.ss, self.k
        stroke = round(self.outline * ss)
        box = self.font.getbbox(char, anchor="ls", stroke_width=stroke)
        width = box[2] - box[0] + 4 * ss
        pad = self.cell_height * k * ss  # a free cell above and below: marks stay whole until fitted
        origin = (2 * ss - box[0], pad + round(self.baseline * k * ss))
        fill = Image.new("L", (width, 3 * pad), 0)
        ImageDraw.Draw(fill).text(origin, char, font=self.font, fill=255, anchor="ls")
        outline = Image.new("L", (width, 3 * pad), 0)
        ImageDraw.Draw(outline).text(origin, char, font=self.font, fill=255, anchor="ls",
                                     stroke_width=stroke, stroke_fill=255)
        size = (max(1, round(width * self.stretch / ss)), 3 * self.cell_height * k)
        result = self._fit_height(fill.resize(size, Image.Resampling.LANCZOS),
                                  outline.resize(size, Image.Resampling.LANCZOS))
        self._masks[char] = result
        return result

    def _fit_height(self, fill: Image.Image, outline: Image.Image) -> tuple[Image.Image, Image.Image]:
        """Crop the cell; marks and descenders it cannot hold are pulled in with one clear row.

        Fill and outline take the same transform, from the outline's visible ink."""
        k, cell = self.k, self.cell_height
        top0 = cell * k
        base = top0 + round(self.baseline * k)
        masks = [fill, outline]
        box = visible(outline)
        if box and box[1] < top0 + k:
            for i, m in enumerate(masks):
                above = m.crop((0, box[1], m.width, base)).resize((m.width, base - top0 - k), Image.Resampling.LANCZOS)
                m = m.copy()
                m.paste(0, (0, 0, m.width, base))
                m.paste(above, (0, top0 + k))
                masks[i] = m
        if box and box[3] > top0 + (cell - 1) * k:
            for i, m in enumerate(masks):
                below = m.crop((0, base, m.width, box[3])).resize((m.width, top0 + (cell - 1) * k - base),
                                                                   Image.Resampling.LANCZOS)
                m = m.copy()
                m.paste(0, (0, base, m.width, m.height))
                m.paste(below, (0, base))
                masks[i] = m
        fill, outline = (m.crop((0, top0, m.width, top0 + cell * k)) for m in masks)
        return fill, outline

    def cell(self, char: str, width: int, centre: float | None = None) -> Image.Image:
        """RGBA cell `width` x1 pixels wide at k-scale; the ink centre goes to `centre` (x1 px)."""
        fill, outline = self.masks(char)
        box, edge = ink(outline), visible(outline)
        target = (centre if centre is not None else width / 2) * self.k
        dx = round(target - (box[0] + box[2]) / 2)
        room = width * self.k
        if edge[2] - edge[0] <= room:  # shift into the cell rather than cut the soft edge
            dx = min(max(dx, -edge[0]), room - edge[2])
        else:  # only the faint edge is wider than the cell: cut it evenly on both sides
            dx = round((room - edge[0] - edge[2]) / 2)
        size = (width * self.k, self.cell_height * self.k)
        f = Image.new("L", size, 0)
        a = Image.new("L", size, 0)
        f.paste(fill, (dx, 0))
        a.paste(outline, (dx, 0))
        a = ImageChops.lighter(a, f)
        colour = Image.composite(Image.new("RGB", size, (255, 255, 255)), Image.new("RGB", size, OUTLINE),
                                 _share(f, a))
        colour.putalpha(a)
        return colour

    def min_width(self, char: str, overhang: float = 0.0) -> int:
        """Narrowest cell, in x1 pixels, for the visible ink of `char`, `overhang` split over both edges."""
        edge = visible(self.masks(char)[1])
        return max(1, math.ceil((edge[2] - edge[0]) / self.k - overhang)) if edge else 1

    def ink_width(self, char: str) -> float:
        """Width of the outlined ink in x1 pixels."""
        box = ink(self.masks(char)[1])
        return (box[2] - box[0]) / self.k


def ink(mask: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box of the visible ink (faint anti-aliasing and filter ringing left out)."""
    return mask.point(lambda v: 255 if v > 64 else 0).getbbox()


def visible(mask: Image.Image) -> tuple[int, int, int, int] | None:
    """Bounding box of every pixel that shows on screen, soft edges included."""
    return mask.point(lambda v: 255 if v > 16 else 0).getbbox()


def _share(fill: Image.Image, alpha: Image.Image) -> Image.Image:
    """Fill coverage relative to the outline coverage (white share of the colour)."""
    f, a = fill.tobytes(), alpha.tobytes()
    return Image.frombytes("L", fill.size, bytes(min(255, x * 255 // y) if y else 0 for x, y in zip(f, a)))


def _fill_coverage(cell: Image.Image) -> Image.Image:
    level = cell.convert("L").point(lambda v: max(0, min(255, round((v - OUTLINE[0]) * 255 / (255 - OUTLINE[0])))))
    return ImageChops.multiply(level, cell.getchannel("A"))


def _similarity(a: Image.Image, b: Image.Image) -> float:
    """Intersection over union of two coverage masks cut at 50 %."""
    pa = a.point(lambda v: 255 if v >= 128 else 0).tobytes()
    pb = b.point(lambda v: 255 if v >= 128 else 0).tobytes()
    inter = sum(1 for x, y in zip(pa, pb) if x and y)
    union = sum(1 for x, y in zip(pa, pb) if x or y)
    return inter / union if union else 0.0


def chain(width: int, height: int) -> list[tuple[int, int]]:
    out = [(width, height)]
    while out[-1] != (1, 1):
        w, h = out[-1]
        out.append((max(1, w // 2), max(1, h // 2)))
    return out


def dds(image: Image.Image, template: bytes, levels: int) -> bytes:
    """DXT5 DDS of `image` with `levels` mip levels (premultiplied box filter)."""
    width, height = image.size
    header = bytearray(template[:128])
    struct.pack_into("<IIII", header, 12, height, width, width * height, 0)
    struct.pack_into("<I", header, 28, levels)
    flags, caps = struct.unpack_from("<I", header, 8)[0], struct.unpack_from("<I", header, 108)[0]
    if levels > 1:
        flags, caps = flags | 0x20000, caps | 0x400008  # MIPMAPCOUNT; COMPLEX | MIPMAP
    struct.pack_into("<I", header, 8, flags)
    struct.pack_into("<I", header, 108, caps)
    header[32:44] = bytes(12)
    source = image.convert("RGBa")
    body = []
    for size in chain(width, height)[:levels]:
        mip = image.convert("RGBA") if size == (width, height) else \
            source.resize(size, Image.Resampling.BOX).convert("RGBA")
        body.append(bc_encode.encode(mip, "DXT5"))
    return bytes(header) + b"".join(body)


def _cached_dds(image: Image.Image, template: bytes, levels: int) -> bytes:
    """dds() result, cached by its inputs and the code that makes it."""
    key = hashlib.sha256(struct.pack("<III", *image.size, levels) + image.tobytes() + bytes(template[:128]) +
                         Path(bc_encode.__file__).read_bytes() + Path(__file__).read_bytes()).hexdigest()[:24]
    cache = paths.BUILD / "cache" / f"dds-{key}.bin"
    if cache.exists():
        return cache.read_bytes()
    data = dds(image, template, levels)
    cache.parent.mkdir(parents=True, exist_ok=True)
    partial = cache.with_suffix(".tmp")
    partial.write_bytes(data)
    os.replace(partial, cache)
    return data


def _font(data: bytes) -> FntFile:
    font = FntFile.__new__(FntFile)
    font.path, font.data = "<memory>", bytearray(data)
    return font


def _atlas(font: FntFile) -> Image.Image:
    image = Image.open(io.BytesIO(bytes(font.data[font.dds_offset:])))
    image.load()
    return image.convert("RGBA")


def _shown(font: FntFile) -> dict[int, str]:
    """Glyph index -> the character it shows (the lowest code point mapped to it)."""
    shown: dict[int, str] = {}
    for entry in sorted(font.list_mapping(), key=lambda e: e.codepoint):
        shown.setdefault(entry.glyph_index, chr(entry.codepoint))
    return shown


def render(data: bytes) -> tuple[FntFile, Image.Image, Image.Image, list[str]]:
    """(font with repacked metrics, 1x atlas, k-times atlas, notes)."""
    spec = style()
    k = spec["scale"]
    font = _font(data)
    cell_h = int(font.height)
    source = _atlas(font)
    width, height = source.size
    renderer = Renderer(k, spec, cell_h)
    by_char = {chr(e.codepoint): e.glyph_index for e in font.list_mapping()}
    tighten = spec.get("tighten", 0.0)

    def fit(char: str, index: int) -> tuple[int, float, Image.Image]:
        """(advance, ink centre, fill coverage) of a Latin glyph drawn from the typeface.

        The new ink gets the game glyph's side bearings, so the advance follows the drawn
        letter. The game atlas has soft edges that close up about one pixel between
        neighbours; the sharp k-times glyphs do not, so each bearing is `tighten` smaller."""
        g = font.get_glyph_metrics(index)
        w = int(round(g.width))
        cell = source.crop((int(g.x), int(g.y), int(g.x) + w, int(g.y) + cell_h))
        cover = _fill_coverage(cell)
        box = cover.getbbox()
        if not box:
            return w, w / 2, cover
        # side bearings of the game glyph's outlined ink (alpha > 128), less `tighten`
        edge = cell.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox() or box
        left = max(edge[0] - tighten, 0.0)
        right = max(w - edge[2] - tighten, 0.0)
        ink_w = renderer.ink_width(char)
        # never wider than the game glyph (English layout keeps fitting) unless the ink needs it
        tight = max(1, min(w, round(left + ink_w + right)), renderer.min_width(char, OVERHANG))
        return tight, left + ink_w / 2 + (tight - left - ink_w - right) / 2, cover

    margin = sum(fit(c, by_char[c])[0] - renderer.ink_width(c) for c in TWINS) / len(TWINS)
    notes = []
    cells: list[tuple[int, Image.Image]] = []
    widths: dict[int, int] = {}
    shown = _shown(font)
    for index in range(struct.unpack_from("<I", font.data, 0x1C)[0]):
        char = shown.get(index, "")  # records without a code point keep their pixels
        g = font.get_glyph_metrics(index)
        w = int(round(g.width))
        if w <= 0:
            continue
        original_cell = source.crop((int(g.x), int(g.y), int(g.x) + w, int(g.y) + cell_h))
        if "Ѐ" <= char <= "ӿ" and renderer.has(char):
            # Cyrillic cells came from other fonts; spacing follows the Latin glyphs.
            w = max(round(renderer.ink_width(char) + margin), renderer.min_width(char))
            cells.append((index, renderer.cell(char, w)))
            widths[index] = w
            continue
        cover = _fill_coverage(original_cell)
        box = cover.getbbox()
        if char != " " and box and renderer.has(char):
            tight, centre, _ = fit(char, index)
            # similarity on the game's own cell; the tightened cell is what goes into the atlas
            score = _similarity(_fill_coverage(renderer.cell(char, w, (box[0] + box[2]) / 2)
                                               .resize((w, cell_h), Image.Resampling.BOX)), cover)
            text = unicodedata.category(char)[0] in "LN" or char in TEXT_PUNCTUATION
            if score >= (TEXT_SIMILARITY if text else SIMILARITY):
                cells.append((index, renderer.cell(char, tight, centre)))
                widths[index] = tight
                continue
            notes.append(f"kept game pixels for U+{ord(char):04X} ({score:.2f})")
        art = original_cell.convert("RGBa").resize((w * k, cell_h * k), Image.Resampling.LANCZOS)
        cells.append((index, art.convert("RGBA")))
        widths[index] = w
    big = Image.new("RGBA", (width * k, height * k), (0, 0, 0, 0))
    x = y = 0
    for index, cell in cells:
        w = widths[index]
        if x + w > width:
            x, y = 0, y + cell_h + GAP
        if y + cell_h > height:
            raise UaError("Font atlas is full")
        big.paste(cell, (x * k, y * k))
        font.set_glyph_metrics(index, float(x), float(y), float(w))
        x += w + GAP
    small = big.convert("RGBa").resize((width, height), Image.Resampling.BOX).convert("RGBA")
    return font, small, big, notes


def compose(data: bytes) -> tuple[bytes, bytes, list[str]]:
    """Return (FNT, FONT_HD.DDS, notes) for Font 1."""
    return _pack(*render(data), style()["scale"], 0)


def compose2(data: bytes) -> tuple[bytes, bytes, list[str]]:
    """Return (FNT, FONT2_HD.DDS, notes) for Font 2."""
    return _pack(*render2(data), font2_style()["scale"], 1)


def _pack(font: FntFile, small: Image.Image, big: Image.Image, notes: list[str], k: int,
          slot: int) -> tuple[bytes, bytes, list[str]]:
    """The FNT with the marked 1x atlas (same file size), and the k-times DDS."""
    at = font.dds_offset
    template = bytes(font.data[at:at + 128])
    if template[84:88] != b"DXT5":
        raise UaError("font atlas is not DXT5; the encoder writes DXT5 only")
    levels = struct.unpack_from("<I", template, 28)[0] or 1
    one_x = _cached_dds(small, template, levels)
    if len(one_x) > len(font.data) - at:
        raise UaError("New 1x atlas does not fit the original DDS")
    header = bytearray(one_x[:128])
    header[32:36] = MARK
    struct.pack_into("<II", header, 36, k, slot)
    font.data[at:at + len(one_x)] = bytes(header) + one_x[128:]
    hd = _cached_dds(big, template, len(chain(*big.size)))
    return bytes(font.data), hd, notes


# --- Font 2 -----------------------------------------------------------------------------------
# Font 2 is a brush-style capital font: a vertical orange-to-yellow gradient fill (by row of the
# 50-pixel cell, the same for every glyph) inside a 2 px dark outline. Its Latin glyphs are
# not a typeface we have, so their shapes come from the game's pixels: the fill coverage is
# enlarged k times, smoothed and cut sharp again, then the outline and the gradient are drawn
# anew at k times the size. The Ukrainian letters are drawn from the "Adventure" typeface, as
# in fonts.py, at k times the size.
HD2_RESOURCE = "UKRAINIAN/FONT2_HD.DDS"


def font2_style() -> dict:
    return read_json(STYLE)["font2"]


def _gradient(spec: dict, row: float) -> tuple[int, int, int]:
    (y0, *top), (y1, *bottom) = spec["gradient"]
    t = min(1.0, max(0.0, (row - y0) / (y1 - y0)))
    return tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))


def _dilate(mask: Image.Image, radius: int) -> Image.Image:
    """Grey-level dilation by a disc of `radius` pixels (a round outline around the fill)."""
    out = mask.copy()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if (dx or dy) and dx * dx + dy * dy <= radius * radius + radius // 2:
                shifted = Image.new("L", mask.size, 0)
                shifted.paste(mask, (dx, dy))
                out = ImageChops.lighter(out, shifted)
    return out


def _paint2(fill: Image.Image, spec: dict, k: int) -> Image.Image:
    """RGBA cell at k-scale from a fill coverage mask: gradient fill inside a dark outline."""
    outline = ImageChops.lighter(_dilate(fill, round(spec["outline"] * k)), fill)
    gradient = Image.new("RGB", fill.size)
    for y in range(fill.height):
        gradient.paste(_gradient(spec, (y + 0.5) / k), (0, y, fill.width, y + 1))
    colour = Image.composite(gradient, Image.new("RGB", fill.size, tuple(spec["outline_colour"])),
                             _share(fill, outline))
    colour.putalpha(outline)
    return colour


def _fill_share2(cell: Image.Image, spec: dict) -> Image.Image:
    """Fill coverage of a game Font 2 cell: brightness between the outline and the gradient."""
    out = Image.new("L", cell.size, 0)
    src, dst = cell.load(), out.load()
    dark = sum(spec["outline_colour"]) / 3
    for y in range(cell.height):
        bright = sum(_gradient(spec, y + 0.5)) / 3
        for x in range(cell.width):
            r, g, b, a = src[x, y]
            share = min(1.0, max(0.0, ((r + g + b) / 3 - dark) / (bright - dark)))
            dst[x, y] = round(255 * share * a / 255)
    return out


def _sharpen_up(fill: Image.Image, k: int) -> Image.Image:
    """Fill coverage enlarged k times with smooth, sharp edges (no pixel steps, no blur)."""
    big = fill.resize((fill.width * k, fill.height * k), Image.Resampling.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(k * 0.45))
    return big.point(lambda v: max(0, min(255, round((v - 128) * 3.2 + 128))))


class Adventure:
    """Ukrainian Font 2 letters from the Adventure typeface: fill mask at k-scale."""

    def has(self, char: str) -> bool:
        """The typeface draws `char` itself (not its missing-glyph box)."""
        def probe(c):
            image = Image.new("L", (200, 200), 0)
            ImageDraw.Draw(image).text((20, 160), c, font=self.probe, fill=255, anchor="ls")
            return image.tobytes()
        drawn = probe(char)
        return any(drawn) and drawn != probe("￿")

    def __init__(self, spec: dict, k: int, cell: int):
        self.spec, self.k, self.cell_h, self.ss = spec, k, cell, 2
        path = typeface_path(spec["files"])
        probe = ImageFont.truetype(str(path), 400)
        self.probe = ImageFont.truetype(str(path), 100)
        box = probe.getbbox("Н", anchor="ls")
        # Cap height of the fill = baseline - cap top, minus the outline on both sides.
        target = spec["baseline"] - spec["cap_top"] - 2 * spec["outline"]
        self.size = 400 * target / (box[3] - box[1])
        self.font = ImageFont.truetype(str(path), round(self.size * k * self.ss))

    def fill(self, char: str) -> Image.Image:
        """Fill mask at k-scale, one cell tall, ink from x = 0."""
        k, ss = self.k, self.ss
        pad = self.cell_h * k  # a free cell above: marks stay whole until fitted
        base = round((self.spec["baseline"] - self.spec["outline"]) * k * ss)
        box = self.font.getbbox(char, anchor="ls")
        image = Image.new("L", (box[2] - box[0] + 2 * ss, 2 * pad * ss), 0)
        ImageDraw.Draw(image).text((ss - box[0], pad * ss + base), char, font=self.font, fill=255, anchor="ls")
        image = image.resize((max(1, image.width // ss), 2 * pad), Image.Resampling.LANCZOS)
        top, line = pad + round(self.spec["outline"] * k) + k, pad + base // ss
        bbox = visible(image)
        if bbox and bbox[1] < top:  # marks above capitals stay inside the cell
            above = image.crop((0, bbox[1], image.width, line))
            squeezed = above.resize((image.width, line - top), Image.Resampling.LANCZOS)
            image.paste(0, (0, 0, image.width, line))
            image.paste(squeezed, (0, top))
        return image.crop((0, pad, image.width, 2 * pad))


def render2(data: bytes) -> tuple[FntFile, Image.Image, Image.Image, list[str]]:
    """Font 2: (font with repacked metrics, 1x atlas, k-times atlas, notes)."""
    spec = font2_style()
    k = spec["scale"]
    font = _font(data)
    cell_h = int(font.height)
    source = _atlas(font)
    width, height = source.size
    adventure = Adventure(spec, k, cell_h)
    shown = _shown(font)
    count = struct.unpack_from("<I", font.data, 0x1C)[0]

    def ink_width(index: int) -> int:
        g = font.get_glyph_metrics(index)
        box = source.crop((int(g.x), int(g.y), int(g.x + g.width), int(g.y + cell_h))).getchannel("A").getbbox()
        return box[2] - box[0]

    # Side margin of the game's Latin capitals: advance minus outlined ink.
    latin = [i for i in range(count) if "A" <= shown.get(i, "") <= "Z"]
    margin = sum(font.get_glyph_metrics(i).width - ink_width(i) for i in latin) / len(latin)
    cells, widths = [], {}
    for index in range(count):
        g = font.get_glyph_metrics(index)
        w = int(round(g.width))
        if w <= 0:
            continue
        char = shown.get(index, "")
        if "Ѐ" <= char <= "ӿ":
            fill = adventure.fill(char)
            ink = fill.getbbox()
            if not adventure.has(char) or not ink:
                raise UaError(f"Font 2: the Adventure typeface has no {char!r}")
            w = round((ink[2] - ink[0]) / k + 2 * spec["outline"] + margin)
            canvas = Image.new("L", (w * k, cell_h * k), 0)
            canvas.paste(fill, (round((w * k - (ink[2] - ink[0])) / 2) - ink[0], 0))
            cells.append((index, _paint2(canvas, spec, k)))
        else:
            original = source.crop((int(g.x), int(g.y), int(g.x) + w, int(g.y) + cell_h))
            fill = _fill_share2(original, spec)
            if fill.getbbox():
                cells.append((index, _paint2(_sharpen_up(fill, k), spec, k)))
            else:
                art = original.convert("RGBa").resize((w * k, cell_h * k), Image.Resampling.LANCZOS)
                cells.append((index, art.convert("RGBA")))
        widths[index] = w
    big = Image.new("RGBA", (width * k, height * k), (0, 0, 0, 0))
    x = y = 0
    for index, cell in cells:
        w = widths[index]
        if x + w > width:
            x, y = 0, y + cell_h + GAP
        if y + cell_h > height:
            raise UaError("Font 2 atlas is full")
        big.paste(cell, (x * k, y * k))
        font.set_glyph_metrics(index, float(x), float(y), float(w))
        x += w + GAP
    small = big.convert("RGBa").resize((width, height), Image.Resampling.BOX).convert("RGBA")
    return font, small, big, []
