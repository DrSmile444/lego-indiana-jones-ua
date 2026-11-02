"""Export the two title logo textures without modifying game resources."""
import argparse
import hashlib
import io
import json
import re
import shutil
import struct
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
GAME = paths.GAME


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=GAME / "LEVELS/TITLES/TITLES_US_PC.GSC")
    parser.add_argument("--output", type=Path, default=paths.BUILD / "title-logo")
    args = parser.parse_args()
    data = args.source.read_bytes()
    textures = []
    for match in re.finditer(rb"DDS ", data):
        offset = match.start()
        height, width = struct.unpack_from("<II", data, offset + 12)
        mip_count = struct.unpack_from("<I", data, offset + 28)[0] or 1
        fourcc = data[offset + 84:offset + 88]
        if (width, height) not in {(1024, 256), (512, 64)}:
            continue
        if fourcc != b"DXT5":
            raise ValueError("Unexpected logo texture compression")
        length = 128 + sum(
            max(1, (max(1, width >> level) + 3) // 4)
            * max(1, (max(1, height >> level) + 3) // 4) * 16
            for level in range(mip_count)
        )
        payload = data[offset:offset + length]
        if len(payload) != length:
            raise ValueError("Truncated DDS texture")
        image = Image.open(io.BytesIO(payload)).convert("RGBA")
        name = "indiana-jones-logo" if width == 1024 else "original-adventures-subtitle"
        textures.append((name, payload, image, {
            "name": name, "offset": offset, "length": length,
            "width": width, "height": height, "mip_count": mip_count,
            "compression": "DXT5", "dds_sha256": hashlib.sha256(payload).hexdigest(),
        }))
    if len(textures) != 2 or len({item[0] for item in textures}) != 2:
        raise ValueError("Expected exactly one logo and one subtitle texture")
    args.output.mkdir(parents=True, exist_ok=True)
    originals = args.output / "originals"
    originals.mkdir(exist_ok=True)
    shutil.copyfile(args.source, originals / args.source.name)
    manifest = {
        "game_resource": f"LEVELS/TITLES/{args.source.name}",
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "textures": [],
    }
    for name, payload, image, entry in textures:
        (originals / f"{name}.dds").write_bytes(payload)
        image.save(args.output / f"{name}.png")
        manifest["textures"].append(entry)
        print(f"Exported {name}.png: {image.width}x{image.height}, RGBA")
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
