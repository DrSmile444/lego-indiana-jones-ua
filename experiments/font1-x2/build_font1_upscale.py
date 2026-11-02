"""Build an experimental high-resolution Font 1 without changing release files.

python tools/build_font1_upscale.py --atlas tools/glyph_viewer/atlasx2.png
"""
import argparse
import io
import json
import struct
import sys
from pathlib import Path

from PIL import Image

from ua.formats.bc_gray import encode_block as encode_gray
from ua.formats.bc_color import encode_block as encode_color
from check_fnt_layout import validate_layout
from ua.formats.fnt import FntFile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ua import paths  # noqa: E402
ALIASES = ("FONT_PC.FNT", "PC_FONT.FNT", "PC_FONT_PC.FNT", "PC_FONT_NGC.FNT")


def encode_level(image):
    width, height = image.size
    chunks = []
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            block = image.crop((x, y, x + 4, y + 4))
            if block.getchannel("A").getbbox() is None:
                chunks.append(bytes(16))
                continue
            pixels = list(block.getdata())
            colored = any(max(p[:3]) - min(p[:3]) > 8 for p in pixels if p[3] > 8)
            chunks.append((encode_color if colored else encode_gray)(pixels))
    return b"".join(chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=paths.BUILD / "uap-unpacked/STUFF/TEXT/PC_FONT_PC.FNT")
    parser.add_argument("--output", type=Path, default=paths.BUILD / "experiments/font1-x2")
    args = parser.parse_args()
    font = FntFile(str(args.source))
    # The working donor has a stale out-of-file optional pointer at 0x4c.
    # The original game's FONT_PC has NULL here; use that for the rebuilt file.
    optional = struct.unpack_from("<i", font.data, 0x4c)[0]
    if optional and not 0 <= 0x4c + optional < len(font.data):
        struct.pack_into("<I", font.data, 0x4c, 0)
    old = validate_layout(font.data)
    atlas = Image.open(args.atlas).convert("RGBA")
    scale = atlas.width / old["width"]
    if scale <= 1 or atlas.height != old["height"] * scale or atlas.width & (atlas.width - 1):
        raise ValueError("Use a larger power-of-two atlas with unchanged aspect ratio")
    count = max(atlas.size).bit_length()
    header = bytearray(font.data[font.dds_offset:font.dds_offset + 128])
    struct.pack_into("<III", header, 12, atlas.height, atlas.width, atlas.width * atlas.height)
    struct.pack_into("<I", header, 28, count)
    chunks = []
    for level in range(count):
        size = (max(1, atlas.width >> level), max(1, atlas.height >> level))
        image = atlas if level == 0 else atlas.resize(size, Image.Resampling.BOX)
        chunks.append(encode_level(image))
        print(f"mip{level}: {size}", flush=True)
    dds = bytes(header) + b"".join(chunks)
    mapping_before = [(e.codepoint, e.glyph_index) for e in font.list_mapping()]
    metrics_before = [font.get_glyph_metrics(i) for i in range(old["glyph_count"])]
    # Reuse the existing writer to rebuild the descriptor and relocation footer.
    font.append_glyphs_and_mappings([], [], dds)
    # The engine also uses these metrics for screen geometry. Keep the
    # original logical coordinate system; the experimental DLL gives this
    # font texture logical 1024x1024 dimensions after its 2048 GPU upload.
    layout = validate_layout(font.data)
    assert mapping_before == [(e.codepoint, e.glyph_index) for e in font.list_mapping()]
    for i, before in enumerate(metrics_before):
        after = font.get_glyph_metrics(i)
        assert (after.x, after.y, after.width) == (before.x, before.y, before.width)
    original = FntFile(str(args.source))
    assert font.data[0x24:0x30] == original.data[0x24:0x30]
    decoded = Image.open(io.BytesIO(dds)).convert("RGBA")
    assert decoded.size == atlas.size
    args.output.mkdir(parents=True, exist_ok=True)
    decoded.save(args.output / "atlas-decoded.png")
    for name in ALIASES:
        font.save(str(args.output / name))
    report = dict(source=str(args.source), atlas=str(args.atlas), scale=scale,
                  height=font.height, baseline=font.base, layout=layout,
                  status="Experimental; screen size and inline button alignment require live verification")
    (args.output / "build.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
