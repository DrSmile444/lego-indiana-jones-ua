"""
Converts the patched atlas PNG (from build_font1_atlas.py) into the DDS
mip chain matching the original donor's exact byte layout, by re-using the
original's header + untouched mip data verbatim and only replacing the
specific DXT5 blocks our 8 glyph rects actually touch, at EVERY mip level
where that rect is still big enough to matter (mip0 through mip4, i.e. down
to 64x64 -- smaller than that the rect is a handful of pixels and any
leftover old content would be imperceptible even blended in). This
guarantees the output file size matches exactly (needed since
build_font1_ukrainian.py splices this into a fixed-size region of the .FNT).

IMPORTANT (10th real bug, found in real gameplay testing): the first version
of this script replaced the ENTIRE mip0 with a fresh full-image DXT5
re-encode of the composited PNG. DXT5 compresses in fixed 4x4-pixel blocks,
and none of our 8 rects' edges land on a 4px boundary -- so several blocks
straddle the line between a freshly-painted glyph and an untouched
neighboring glyph a few pixels away. Recompressing those shared blocks lets
DXT5's block-level color/alpha interpolation blend the two together (DXT5's
color endpoints are shared per-block regardless of alpha). Fixed: encode the
full patched image once, then copy back the ORIGINAL bytes for every block
outside our 8 rects (expanded to the enclosing 4px block boundary).

IMPORTANT (11th real bug, found via direct in-game observation -- user could
see it on their own monitor even though it was too subtle to show up in any
screenshot, lossless or not): a faint halo/shadow remained even after the
10th fix. Root cause was the ALREADY-DOCUMENTED "texture is only patched at
mip0" limitation (see README.md) -- mip1 (512x512) and smaller still contain
the OLD Polish donor letters byte-for-byte, because nothing ever touched
them. Decoding mip1 and looking at our 8 glyphs' (halved) coordinates
confirmed this directly: "Ą ą Ć ć" / "Ś ś" still clearly visible there. Any
GPU trilinear/anisotropic filtering that blends mip0 with mip1 at the scale
this text is actually drawn at will show a faint, reduced ghost of the OLD
Polish letterform right where our new glyph is -- exactly a small, easy-to-
miss "halo" that traces a rectangle (the old glyph's own shape) rather than
anything resembling a compression artifact. Fixed: extended the same
block-preserving splice technique (mip0's TARGETS rects, block-aligned) down
through mip1-mip4, using a resized coverage MASK (rather than re-deriving
per-level pixel math, which would need separate rounding for every level)
to decide which blocks at each level are "ours".

Run from repo root:
    python tools/build_font1_dds.py
"""
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from build_font1_atlas import TARGETS, BLOCK, clear_rect_for, KILL_RECTS, kill_rect_for  # noqa: E402
from ua.formats.bc_gray import encode_block  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
PATCHED_PNG = paths.BUILD / "fonts/pcfont_patched_ukrainian.png"
ORIG_DDS = paths.BUILD / "fonts/pcfont_0.dds"  # pristine full DDS chunk (header + all mips), extracted earlier
OUT_DDS = paths.BUILD / "fonts/pcfont_patched_safe.dds"

HEADER = 128
ATLAS_SIZE = 1024
BLOCK_BYTES = 16  # 8 bytes alpha + 8 bytes color per block

# Patch mip0 (1024) through mip4 (64). Verified empirically: this mip chain's
# per-level byte offsets/sizes follow the standard DXT5 rule (blocks_w *
# blocks_h * 16, blocks = ceil(dim/4)) for at least these top 5 levels --
# confirmed by decoding mip1 at the offset this formula predicts and finding
# exactly the expected (still-unpatched) donor glyphs at the expected
# position. Levels 5-10 (32px and below) are left untouched: unverified
# whether the same simple offset formula holds all the way to the 1x1 tail
# (the file's total size is a few dozen bytes off from this formula's
# theoretical total, likely some padding/rounding in that tail), and at
# =<32px our 8 glyphs are a handful of pixels -- not worth the risk.
NUM_PATCHED_LEVELS = 5


def mip_levels(base=ATLAS_SIZE, count=11):
    """Yields (level, size, offset, nbytes) for a standard DXT5 mip chain."""
    offset = 0
    for level in range(count):
        size = max(1, base >> level)
        blocks = max(1, (size + 3) // 4)
        nbytes = blocks * blocks * BLOCK_BYTES
        yield level, size, offset, nbytes
        offset += nbytes


def coverage_mask() -> Image.Image:
    """1024x1024 'L' image: 255 over the exact area build_font1_atlas.py
    clears/repaints for every TARGETS entry (clear_rect_for, block-aligned
    and widened per CLEAR_X_OVERRIDE) and erases for every KILL_RECTS entry
    (kill_rect_for -- unused donor glyphs removed outright, see the 14th-bug
    note in build_font1_atlas.py), 0 elsewhere."""
    mask = Image.new("L", (ATLAS_SIZE, ATLAS_SIZE), 0)
    for _ch, name, (x0, y0, x1, y1) in TARGETS:
        ex0, ey0, ex1, ey1 = clear_rect_for(name, x0, y0, x1, y1)
        mask.paste(255, (ex0, ey0, ex1, ey1))
    for name, (x0, y0, x1, y1) in KILL_RECTS:
        ex0, ey0, ex1, ey1 = kill_rect_for(name, x0, y0, x1, y1)
        mask.paste(255, (ex0, ey0, ex1, ey1))
    return mask


def splice_level(pristine_bytes: bytes, level_image: Image.Image, mask: Image.Image, size: int) -> tuple[bytes, int]:
    """Re-encodes and splices in ONLY the blocks the mask flags as ours,
    using our own gray-safe BC3 encoder (bc_gray_encoder.py) instead of
    Pillow's generic DXT5 encoder -- see that module's docstring for why:
    Pillow's encoder was found to bake a visible magenta/purple tint into
    our (pure grayscale) glyph outlines. Encoding block-by-block here, only
    for the handful of blocks we actually touch, also means we never run
    the full image through Pillow's encoder at all."""
    level_rgba = level_image.convert("RGBA")
    blocks_per_row = max(1, size // BLOCK)
    out = bytearray(pristine_bytes)
    changed = 0
    for by in range(blocks_per_row):
        for bx in range(blocks_per_row):
            box = (bx * BLOCK, by * BLOCK, bx * BLOCK + BLOCK, by * BLOCK + BLOCK)
            if mask.crop(box).getbbox() is None:
                continue  # this block is all-zero in the mask -- not ours
            pixels = list(level_rgba.crop(box).getdata())
            off = (by * blocks_per_row + bx) * BLOCK_BYTES
            out[off:off + BLOCK_BYTES] = encode_block(pixels)
            changed += 1
    return bytes(out), changed


def main():
    orig = bytearray(Path(ORIG_DDS).read_bytes())
    patched_mip0 = Image.open(PATCHED_PNG).convert("RGBA")
    assert patched_mip0.size == (ATLAS_SIZE, ATLAS_SIZE), patched_mip0.size

    mask0 = coverage_mask()

    levels = list(mip_levels())
    out_chunks = {}
    for level, size, offset, nbytes in levels[:NUM_PATCHED_LEVELS]:
        # BOX, not LANCZOS: LANCZOS has a wide filter kernel (~3px radius,
        # i.e. it samples several pixels beyond the exact 2x/4x/8x/16x
        # footprint a real mip level averages) and some of our 8 glyphs sit
        # only ~5-6px from an unrelated neighboring glyph (e.g. "ł" next to
        # i_lower) -- close enough for LANCZOS to blend a faint trace of
        # that neighbor into our own glyph's mip1-mip4 pixels even though
        # the splice step only takes blocks inside our own coverage mask.
        # BOX matches what GPU mipmap generation actually does: each output
        # texel is the average of exactly its corresponding source block,
        # nothing beyond it.
        level_image = patched_mip0 if level == 0 else patched_mip0.resize((size, size), Image.BOX)
        level_mask = mask0 if level == 0 else mask0.resize((size, size), Image.BOX)

        pristine_level = bytes(orig[HEADER + offset:HEADER + offset + nbytes])
        assert len(pristine_level) == nbytes, (level, len(pristine_level), nbytes)

        spliced, changed = splice_level(pristine_level, level_image, level_mask, size)
        total_blocks = max(1, size // BLOCK) ** 2
        print(f"mip{level} ({size}x{size}): re-encoded {changed}/{total_blocks} DXT5 blocks")
        out_chunks[level] = spliced

    patched_head = b"".join(out_chunks[level] for level, *_ in levels[:NUM_PATCHED_LEVELS])
    tail_offset = levels[NUM_PATCHED_LEVELS][2]  # offset where the untouched tail starts
    tail = bytes(orig[HEADER + tail_offset:])

    out = bytes(orig[:HEADER]) + patched_head + tail
    assert len(out) == len(orig), (len(out), len(orig))

    OUT_DDS.write_bytes(out)
    print(f"wrote {OUT_DDS} ({len(out)} bytes, matches original size: {len(out) == len(orig)})")


if __name__ == "__main__":
    main()
