"""BC1 (DXT1) and BC3 (DXT5) block encoder for full-size textures.

Colour: endpoints along the principal axis of the block's visible pixels, then
least-squares refinement of the endpoints for the chosen indices; the candidate
with the lowest error wins. Pixels are weighted by alpha, so hidden colour
under transparent pixels does not pull the endpoints.
Alpha: both BC3 modes are tried (8 interpolated levels, or 6 levels plus exact
0 and 255) and the one with the lower error wins.
"""
from __future__ import annotations

Pixel = tuple[int, int, int, int]


def _pack565(c: tuple[float, float, float]) -> int:
    r = min(31, max(0, round(c[0] * 31 / 255)))
    g = min(63, max(0, round(c[1] * 63 / 255)))
    b = min(31, max(0, round(c[2] * 31 / 255)))
    return r << 11 | g << 5 | b


def _unpack565(v: int) -> tuple[float, float, float]:
    r, g, b = v >> 11 & 31, v >> 5 & 63, v & 31
    return ((r << 3 | r >> 2), (g << 2 | g >> 4), (b << 3 | b >> 2))


def _palette(c0: int, c1: int) -> list[tuple[float, float, float]]:
    a, b = _unpack565(c0), _unpack565(c1)
    return [a, b, tuple((2 * x + y) / 3 for x, y in zip(a, b)), tuple((x + 2 * y) / 3 for x, y in zip(a, b))]


def _fit(colors, weights, c0: int, c1: int) -> tuple[float, list[int]]:
    """Error and indices for 4-colour mode with endpoints c0 > c1."""
    pal = _palette(c0, c1)
    error, indices = 0.0, []
    for (r, g, b), w in zip(colors, weights):
        best, best_i = None, 0
        for i, (pr, pg, pb) in enumerate(pal):
            d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if best is None or d < best:
                best, best_i = d, i
        error += best * w
        indices.append(best_i)
    return error, indices


def _order(c0: int, c1: int) -> tuple[int, int, bool]:
    """4-colour mode needs c0 > c1; swapping endpoints swaps index meaning."""
    if c0 > c1:
        return c0, c1, False
    if c0 < c1:
        return c1, c0, True
    return (c0, c0 - 1, False) if c0 > 0 else (1, 0, True)


_WEIGHT = {0: 1.0, 1: 0.0, 2: 2 / 3, 3: 1 / 3}  # share of endpoint 0 per index


def _refine(colors, weights, indices) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    """Least-squares endpoints for fixed indices."""
    aa = bb = ab = 0.0
    ax, bx = [0.0] * 3, [0.0] * 3
    for (c, w, i) in zip(colors, weights, indices):
        t = _WEIGHT[i]
        s = 1 - t
        aa += w * t * t
        bb += w * s * s
        ab += w * t * s
        for k in range(3):
            ax[k] += w * t * c[k]
            bx[k] += w * s * c[k]
    det = aa * bb - ab * ab
    if abs(det) < 1e-9:
        return None
    e0 = tuple((ax[k] * bb - bx[k] * ab) / det for k in range(3))
    e1 = tuple((bx[k] * aa - ax[k] * ab) / det for k in range(3))
    return e0, e1


def _color_block(pixels: list[Pixel], weighted: bool) -> bytes:
    colors = [p[:3] for p in pixels]
    weights = [(p[3] / 255 if weighted else 1.0) for p in pixels]
    total = sum(weights)
    if total < 1e-6:
        weights = [1.0] * 16
        total = 16.0
    mean = [sum(c[k] * w for c, w in zip(colors, weights)) / total for k in range(3)]
    cov = [[0.0] * 3 for _ in range(3)]
    for c, w in zip(colors, weights):
        d = [c[k] - mean[k] for k in range(3)]
        for i in range(3):
            for j in range(3):
                cov[i][j] += w * d[i] * d[j]
    axis = [1.0, 1.0, 1.0]
    for _ in range(8):
        axis = [sum(cov[i][j] * axis[j] for j in range(3)) for i in range(3)]
        norm = max(abs(v) for v in axis)
        if norm < 1e-9:
            axis = [0.0, 0.0, 0.0]
            break
        axis = [v / norm for v in axis]
    projections = [sum((c[k] - mean[k]) * axis[k] for k in range(3)) for c, w in zip(colors, weights) if w > 0]
    lo, hi = (min(projections), max(projections)) if projections else (0.0, 0.0)
    length = sum(v * v for v in axis) or 1.0
    start = tuple(mean[k] + axis[k] * lo / length for k in range(3))
    end = tuple(mean[k] + axis[k] * hi / length for k in range(3))

    best = None
    candidates = [(end, start)]
    for _ in range(3):
        e0, e1 = candidates[-1]
        c0, c1, _ = _order(_pack565(e0), _pack565(e1))
        error, indices = _fit(colors, weights, c0, c1)
        if best is None or error < best[0]:
            best = (error, c0, c1, indices)
        refined = _refine(colors, weights, indices)
        if refined is None:
            break
        candidates.append(tuple(tuple(min(255.0, max(0.0, v)) for v in e) for e in refined))
    _, c0, c1, indices = best
    bits = 0
    for n, i in enumerate(indices):
        bits |= i << (2 * n)
    return c0.to_bytes(2, "little") + c1.to_bytes(2, "little") + bits.to_bytes(4, "little")


def _alpha_fit(alphas, a0: int, a1: int) -> tuple[float, list[int]]:
    if a0 > a1:
        levels = [a0, a1] + [((7 - k) * a0 + k * a1) / 7 for k in range(1, 7)]
    else:
        levels = [a0, a1] + [((5 - k) * a0 + k * a1) / 5 for k in range(1, 5)] + [0, 255]
    error, indices = 0.0, []
    for a in alphas:
        i = min(range(len(levels)), key=lambda k: abs(a - levels[k]))
        error += (a - levels[i]) ** 2
        indices.append(i)
    return error, indices


def _alpha_block(alphas: list[int]) -> bytes:
    hi, lo = max(alphas), min(alphas)
    candidates = [(hi, lo) if hi > lo else (hi, hi - 1) if hi > 0 else (1, 0)]
    inner = [a for a in alphas if 0 < a < 255]
    if inner:
        candidates.append((min(inner), max(inner)))
    best = min((_alpha_fit(alphas, a0, a1) + (a0, a1) for a0, a1 in candidates), key=lambda t: t[0])
    _, indices, a0, a1 = best
    bits = 0
    for n, i in enumerate(indices):
        bits |= i << (3 * n)
    return bytes((a0, a1)) + bits.to_bytes(6, "little")


def encode_bc1(pixels: list[Pixel]) -> bytes:
    """One opaque BC1 block; `pixels` are 16 RGBA tuples, row-major."""
    return _color_block(pixels, weighted=False)


def encode_bc3(pixels: list[Pixel]) -> bytes:
    """One BC3 block; `pixels` are 16 RGBA tuples, row-major."""
    return _alpha_block([p[3] for p in pixels]) + _color_block(pixels, weighted=True)


def encode(image, fourcc: str) -> bytes:
    """Encode a PIL RGBA image (any size) into BC1 or BC3 blocks."""
    width, height = image.size
    data = image.tobytes()
    block = encode_bc3 if fourcc == "DXT5" else encode_bc1
    out = bytearray()
    for by in range(0, max(height, 1), 4):
        for bx in range(0, max(width, 1), 4):
            pixels = []
            for dy in range(4):
                y = min(by + dy, height - 1)
                for dx in range(4):
                    x = min(bx + dx, width - 1)
                    o = (y * width + x) * 4
                    pixels.append(tuple(data[o:o + 4]))
            out += block(pixels)
    return bytes(out)
