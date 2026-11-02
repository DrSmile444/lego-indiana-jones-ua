"""
Custom, guaranteed-grayscale BC3 (DXT5) block encoder for the handful of
glyph blocks this project repaints (see build_font1_dds.py).

WHY THIS EXISTS: after the "our new glyphs look dirty" report, diffing the
pre-compression composited PNG against the post-compression (DXT5-decoded)
atlas pixel-by-pixel found real color corruption introduced by Pillow's
built-in DXT5 encoder (Image.save(..., pixel_format="DXT5")) -- e.g. atlas
pixel (176,540) is neutral gray (41,40,41,251) in the source PNG but came out
(54,0,54,200) after Pillow's round-trip: the green channel collapsed to 0
while red/blue stayed up, baking a visible magenta/purple tint into the
glyph's own outline pixels. Our 8 patched glyphs are provably pure grayscale
(FILL_COLOR/STROKE_COLOR in build_font1_atlas.py are both R=G=B, and
LANCZOS-resizing/compositing a grayscale image against transparency keeps R,
G, B equal or within a unit of each other everywhere) -- so this artifact is
compressor-introduced, not present in our own render.

Fix: for every block we control, pick BOTH BC1 color endpoints as an actual
gray value (R=G=B) taken from the block's own min/max luminance, instead of
letting a generic encoder fit each channel independently. Interpolating
between two grayscale endpoints is always exactly grayscale, so this class
of color-channel decorrelation artifact is structurally impossible here,
regardless of the source encoder's general quality.
"""


def _luminance(px: tuple[int, int, int, int]) -> float:
    r, g, b, _a = px
    return (r + g + b) / 3.0


def _to565_gray(gray: float) -> int:
    v = round(gray)
    r5 = round(v * 31 / 255)
    g6 = round(v * 63 / 255)
    b5 = round(v * 31 / 255)
    return (r5 << 11) | (g6 << 5) | b5


def _from565_gray(packed: int) -> float:
    r5 = (packed >> 11) & 0x1F
    g6 = (packed >> 5) & 0x3F
    b5 = packed & 0x1F
    r = r5 * 255 / 31
    g = g6 * 255 / 63
    b = b5 * 255 / 31
    return (r + g + b) / 3.0


def _nearest_index(value: float, refs: list[float]) -> int:
    best_i, best_d = 0, None
    for i, ref in enumerate(refs):
        d = abs(value - ref)
        if best_d is None or d < best_d:
            best_d, best_i = d, i
    return best_i


def encode_block(pixels: list[tuple[int, int, int, int]]) -> bytes:
    """Encodes one 4x4 BC3/DXT5 block. `pixels` is 16 RGBA tuples in
    row-major order (y*4+x), matching the standard BC index bit layout."""
    assert len(pixels) == 16, len(pixels)
    grays = [_luminance(p) for p in pixels]
    alphas = [p[3] for p in pixels]

    # --- color block: force both endpoints onto the gray axis (R=G=B) ---
    # Pick the endpoint RANGE only from pixels that are actually visible
    # (alpha above a small threshold). Fully/near-transparent pixels keep
    # whatever RGB the source render happened to leave behind (usually
    # (0,0,0) from the "clear" step in build_font1_atlas.py) -- letting
    # those drag the block's gray range down to pure black would waste an
    # endpoint on a color nobody sees and quantize the real, visible ink
    # (e.g. the ~41-gray outline) further from its true value than needed.
    visible_grays = [g for g, a in zip(grays, alphas) if a > 8] or grays
    g_max, g_min = max(visible_grays), min(visible_grays)
    c0 = _to565_gray(g_max)
    c1 = _to565_gray(g_min)
    if c0 <= c1:
        c1 = max(0, c0 - 1)  # keep c0 > c1 so the decoder uses 4-opaque-color mode

    ref0, ref1 = _from565_gray(c0), _from565_gray(c1)
    color_refs = [ref0, ref1, (2 * ref0 + ref1) / 3, (ref0 + 2 * ref1) / 3]
    color_bits = 0
    for i, g in enumerate(grays):
        color_bits |= _nearest_index(g, color_refs) << (2 * i)

    # --- alpha block: standard 8-level BC3 alpha (a0 > a1) ---
    a0, a1 = max(alphas), min(alphas)
    if a0 <= a1:
        a1 = max(0, a0 - 1)
    alpha_refs = [
        a0, a1,
        (6 * a0 + 1 * a1) / 7, (5 * a0 + 2 * a1) / 7, (4 * a0 + 3 * a1) / 7,
        (3 * a0 + 4 * a1) / 7, (2 * a0 + 5 * a1) / 7, (1 * a0 + 6 * a1) / 7,
    ]
    alpha_bits = 0
    for i, a in enumerate(alphas):
        alpha_bits |= _nearest_index(a, alpha_refs) << (3 * i)

    out = bytearray(16)
    out[0] = a0 & 0xFF
    out[1] = a1 & 0xFF
    out[2:8] = alpha_bits.to_bytes(6, "little")
    out[8:10] = c0.to_bytes(2, "little")
    out[10:12] = c1.to_bytes(2, "little")
    out[12:16] = color_bits.to_bytes(4, "little")
    return bytes(out)


def _self_test():
    """Round-trips a synthetic block through a minimal DDS file and PIL's own
    DXT5 reader, to catch layout mistakes (byte order, index bit packing)."""
    import io
    from PIL import Image

    # A block with a clean gray gradient + a partial alpha edge -- close to
    # what real glyph-edge blocks look like.
    pixels = [
        (255, 255, 255, 255), (255, 255, 255, 255), (41, 40, 41, 255), (0, 0, 0, 0),
        (255, 255, 255, 255), (255, 255, 255, 255), (41, 40, 41, 200), (0, 0, 0, 0),
        (41, 40, 41, 255), (41, 40, 41, 255), (41, 40, 41, 100), (0, 0, 0, 0),
        (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0),
    ]
    block = encode_block(pixels)
    assert len(block) == 16

    ref_dds = __import__("pathlib").Path(__file__).parent.parent / "local/research/pcfont_0.dds"
    header = bytearray(ref_dds.read_bytes()[:128])
    # Patch header dims down to 4x4, single mip, so PIL only reads our block.
    import struct
    header[12:16] = struct.pack("<I", 4)   # height
    header[16:20] = struct.pack("<I", 4)   # width
    header[28:32] = struct.pack("<I", 1)   # mip count

    buf = io.BytesIO(bytes(header) + block)
    decoded = Image.open(buf).convert("RGBA")
    got = list(decoded.getdata())
    max_err = max(
        max(abs(g[i] - p[i]) for i in range(4))
        for g, p in zip(got, pixels)
    )
    print("self-test decoded pixels:", got)
    print("max per-channel error vs source:", max_err)
    assert max_err <= 60, f"unexpectedly large round-trip error: {max_err}"
    # The key property this whole module exists for: no color-channel split.
    for r, g, b, _a in got:
        assert abs(r - g) <= 1 and abs(g - b) <= 1, f"non-gray output pixel: {(r, g, b)}"
    print("self-test OK: round-trip stays on the gray axis for every pixel")


if __name__ == "__main__":
    _self_test()
