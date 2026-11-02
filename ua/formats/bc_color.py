"""
General-purpose (non-grayscale) BC3/DXT5 block encoder, for Font 2's newly
painted glyphs -- unlike Font 1's outline+solid-fill glyphs (pure grayscale,
see bc_gray_encoder.py), Font 2's own style is a real orange-to-yellow
vertical gradient, so forcing R=G=B is not an option here.

Avoids the same class of artifact bc_gray_encoder.py was written to fix
(Pillow's stock DXT5 encoder driving a color channel to a value that never
appears in the source, e.g. a near-gray pixel coming out tinted magenta) by
a different, still-simple means: instead of synthesizing each 565 endpoint
from independent per-channel min/max (which can produce a combination that
matches NO real pixel in the block), pick the two ACTUAL pixels with the
highest and lowest luminance as the endpoints. Every endpoint is therefore
always a real, observed color -- structurally safer than a synthesized
per-channel combination, at some cost in optimality vs. a full least-squares
fit (not needed here: these are small, new, generously-spaced glyphs, not a
dense photographic image).
"""


def _luminance(px: tuple[int, int, int, int]) -> float:
    r, g, b, _a = px
    return 0.299 * r + 0.587 * g + 0.114 * b


def _to565(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    r5 = round(r * 31 / 255)
    g6 = round(g * 63 / 255)
    b5 = round(b * 31 / 255)
    return (r5 << 11) | (g6 << 5) | b5


def _from565(packed: int) -> tuple[float, float, float]:
    r5 = (packed >> 11) & 0x1F
    g6 = (packed >> 5) & 0x3F
    b5 = packed & 0x1F
    return r5 * 255 / 31, g6 * 255 / 63, b5 * 255 / 31


def _nearest_index(px: tuple[float, float, float], refs: list[tuple[float, float, float]]) -> int:
    best_i, best_d = 0, None
    for i, ref in enumerate(refs):
        d = sum((a - b) ** 2 for a, b in zip(px, ref))
        if best_d is None or d < best_d:
            best_d, best_i = d, i
    return best_i


def encode_block(pixels: list[tuple[int, int, int, int]]) -> bytes:
    """Encodes one 4x4 BC3/DXT5 block. `pixels` is 16 RGBA tuples in
    row-major order (y*4+x), matching the standard BC index bit layout."""
    assert len(pixels) == 16, len(pixels)
    alphas = [p[3] for p in pixels]

    visible = [p for p, a in zip(pixels, alphas) if a > 8] or pixels
    lums = [(_luminance(p), p) for p in visible]
    lums.sort(key=lambda t: t[0])
    dark_px, bright_px = lums[0][1][:3], lums[-1][1][:3]

    c0 = _to565(bright_px)
    c1 = _to565(dark_px)
    if c0 <= c1:
        c1 = max(0, c0 - 1)

    ref0, ref1 = _from565(c0), _from565(c1)
    color_refs = [
        ref0, ref1,
        tuple((2 * a + b) / 3 for a, b in zip(ref0, ref1)),
        tuple((a + 2 * b) / 3 for a, b in zip(ref0, ref1)),
    ]
    color_bits = 0
    for i, p in enumerate(pixels):
        color_bits |= _nearest_index(p[:3], color_refs) << (2 * i)

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
        best_i, best_d = 0, None
        for j, ref in enumerate(alpha_refs):
            d = abs(a - ref)
            if best_d is None or d < best_d:
                best_d, best_i = d, j
        alpha_bits |= best_i << (3 * i)

    out = bytearray(16)
    out[0] = a0 & 0xFF
    out[1] = a1 & 0xFF
    out[2:8] = alpha_bits.to_bytes(6, "little")
    out[8:10] = c0.to_bytes(2, "little")
    out[10:12] = c1.to_bytes(2, "little")
    out[12:16] = color_bits.to_bytes(4, "little")
    return bytes(out)
