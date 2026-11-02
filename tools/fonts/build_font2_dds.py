"""
Builds the brand-new DDS mip chain for Font 2's grown 1024x1024 atlas (up
from the pristine original's 512x512) and writes the final, resized
FONT2_PC.FNT.

Unlike Font 1's pipeline (which only ever SPLICES a few changed blocks into
an otherwise byte-identical, same-size mip chain), this one has to build an
ENTIRELY NEW mip chain top to bottom, because the canvas itself grew. Still,
the existing 164 Latin/symbol glyphs (unchanged, sitting at the same
relative position -- the top-left quadrant of every mip level, since the
whole canvas simply doubled) don't need to be recompressed at all: every
block fully inside that quadrant is copied VERBATIM from the pristine Font
2's own mip chain, at every level down to mip4. Only the genuinely new
territory (our 33 painted Cyrillic glyphs, and the rest of the now-empty
canvas) gets freshly encoded, via bc_color_encoder.py (NOT
bc_gray_encoder.py -- Font 2's glyphs are a real orange/yellow gradient,
not grayscale like Font 1's).

Run from repo root:
    python tools/build_font2_dds.py
"""
import struct
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from ua.formats.fnt import FntFile  # noqa: E402
from ua.formats.bc_color import encode_block  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
ORIG_FONT2 = paths.GAME / "GAME/STUFF/TEXT/FONT2_PC.FNT"
PATCHED_PNG = paths.BUILD / "fonts/font2_patched_ukrainian.png"
OUT_DDS = paths.BUILD / "fonts/font2_patched.dds"

OLD_SIZE = 512
NEW_SIZE = 1024
BLOCK = 4
BLOCK_BYTES = 16
DDS_HEADER_SIZE = 128
NUM_PATCHED_LEVELS = 5  # mip0 (1024) .. mip4 (64); smaller levels are fresh-encoded whole, see main()


def mip_levels(base: int, count: int):
    """Yields (level, size, offset, nbytes) for a standard DXT5 mip chain
    starting at `base`x`base`, down to 1x1 (`count` = number of levels)."""
    offset = 0
    for level in range(count):
        size = max(1, base >> level)
        blocks = max(1, (size + 3) // 4)
        nbytes = blocks * blocks * BLOCK_BYTES
        yield level, size, offset, nbytes
        offset += nbytes


def encode_full_level(image: Image.Image) -> bytes:
    """Fresh full-image DXT5 encode, block by block, via bc_color_encoder."""
    size = image.width
    blocks_per_row = max(1, size // BLOCK)
    out = bytearray(blocks_per_row * blocks_per_row * BLOCK_BYTES)
    for by in range(blocks_per_row):
        for bx in range(blocks_per_row):
            box = (bx * BLOCK, by * BLOCK, bx * BLOCK + BLOCK, by * BLOCK + BLOCK)
            pixels = list(image.crop(box).getdata())
            off = (by * blocks_per_row + bx) * BLOCK_BYTES
            out[off:off + BLOCK_BYTES] = encode_block(pixels)
    return bytes(out)


def splice_old_quadrant(new_bytes: bytearray, old_level_bytes: bytes, old_size: int, new_size: int):
    """Overwrites, in-place, every block of `new_bytes` (a NEW_size x
    NEW_size level) that falls fully inside the top-left old_size x old_size
    quadrant with the corresponding block copied verbatim from
    `old_level_bytes` (an old_size x old_size level from the PRISTINE Font 2
    file) -- so none of the 164 original glyphs are ever recompressed."""
    old_blocks_per_row = max(1, old_size // BLOCK)
    new_blocks_per_row = max(1, new_size // BLOCK)
    for by in range(old_blocks_per_row):
        for bx in range(old_blocks_per_row):
            old_off = (by * old_blocks_per_row + bx) * BLOCK_BYTES
            new_off = (by * new_blocks_per_row + bx) * BLOCK_BYTES
            new_bytes[new_off:new_off + BLOCK_BYTES] = old_level_bytes[old_off:old_off + BLOCK_BYTES]


def main():
    orig = FntFile(str(ORIG_FONT2))
    orig_dds_off = orig.dds_offset
    orig_levels = list(mip_levels(OLD_SIZE, 10))  # 512 down to 1

    patched = Image.open(PATCHED_PNG).convert("RGBA")
    assert patched.size == (NEW_SIZE, NEW_SIZE), patched.size

    new_levels = list(mip_levels(NEW_SIZE, 11))  # 1024 down to 1
    chunks = []
    for level, size, _offset, nbytes in new_levels:
        level_image = patched if level == 0 else patched.resize((size, size), Image.BOX)
        fresh = bytearray(encode_full_level(level_image))

        if level < NUM_PATCHED_LEVELS:
            old_level, old_size, old_offset, old_nbytes = orig_levels[level]
            assert old_size * 2 == size, (old_size, size)
            old_level_bytes = bytes(orig.data[orig_dds_off + DDS_HEADER_SIZE + old_offset:
                                               orig_dds_off + DDS_HEADER_SIZE + old_offset + old_nbytes])
            splice_old_quadrant(fresh, old_level_bytes, old_size, size)

        assert len(fresh) == nbytes, (level, len(fresh), nbytes)
        chunks.append(bytes(fresh))
        print(f"mip{level} ({size}x{size}): {'spliced old quadrant + ' if level < NUM_PATCHED_LEVELS else ''}fresh-encoded")

    # DDS header: reuse the pristine file's own 128-byte header, just patch
    # width/height/pitch/mip-count for the new size (standard DDS fields).
    header = bytearray(orig.data[orig_dds_off:orig_dds_off + DDS_HEADER_SIZE])
    struct.pack_into("<I", header, 12, NEW_SIZE)  # height
    struct.pack_into("<I", header, 16, NEW_SIZE)  # width
    # pitchOrLinearSize for a DXT5 (block-compressed) surface: total byte size of mip0
    struct.pack_into("<I", header, 20, new_levels[0][3])
    struct.pack_into("<I", header, 28, len(new_levels))  # mip count

    out = bytes(header) + b"".join(chunks)
    OUT_DDS.write_bytes(out)
    print(f"wrote {OUT_DDS} ({len(out)} bytes, {len(new_levels)} mip levels)")


if __name__ == "__main__":
    main()
