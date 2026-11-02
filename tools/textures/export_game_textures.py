"""Inventory and decode unique DDS textures from the extracted game archives."""
import argparse
import array
import hashlib
import io
import json
import math
import re
import struct
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402


def dds_length(data, offset):
    if len(data) < offset + 128 or struct.unpack_from("<I", data, offset + 4)[0] != 124:
        raise ValueError("Invalid DDS header")
    height, width = struct.unpack_from("<II", data, offset + 12)
    mips = struct.unpack_from("<I", data, offset + 28)[0] or 1
    fourcc = data[offset + 84:offset + 88]
    if not (0 < width <= 8192 and 0 < height <= 8192 and 1 <= mips <= 14):
        raise ValueError("Unexpected DDS dimensions or mip count")
    if fourcc in (b"DXT1", b"DXT3", b"DXT5"):
        block = 8 if fourcc == b"DXT1" else 16
        size = sum(max(1, (max(1, width >> i) + 3) // 4)
                   * max(1, (max(1, height >> i) + 3) // 4) * block for i in range(mips))
    elif fourcc == struct.pack("<I", 116):
        # D3DFMT_A32B32G32R32F: https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dformat
        size = sum(max(1, width >> i) * max(1, height >> i) * 16 for i in range(mips))
    elif fourcc == b"\0\0\0\0":
        bpp = struct.unpack_from("<I", data, offset + 88)[0]
        if bpp not in (8, 16, 24, 32):
            raise ValueError("Unsupported uncompressed DDS")
        size = sum(max(1, width >> i) * max(1, height >> i) * bpp // 8 for i in range(mips))
    else:
        raise ValueError(f"Unsupported DDS compression: {fourcc!r}")
    if offset + 128 + size > len(data):
        raise ValueError("Truncated DDS")
    return 128 + size, width, height, mips, fourcc.decode("ascii", errors="replace").strip("\0")


def decode_texture(payload, width, height):
    if payload[84:88] == struct.pack("<I", 116):
        pixels = array.array("f")
        pixels.frombytes(payload[128:128 + width * height * 16])
        rgba = bytes(round(max(0, min(1, v)) * 255) if math.isfinite(v) else 0 for v in pixels)
        return Image.frombytes("RGBA", (width, height), rgba)
    return Image.open(io.BytesIO(payload)).convert("RGBA")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=paths.GAME)
    parser.add_argument("--output", type=Path, default=paths.BUILD / "texture-catalog")
    args = parser.parse_args()
    image_dir = args.output / "all"
    image_dir.mkdir(parents=True, exist_ok=True)
    prior_path = args.output / "inventory.json"
    prior_ids = {}
    if prior_path.exists():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        prior_ids = {item["sha256"]: item["id"] for item in prior["textures"]}
    next_number = max((int(ident[1:]) for ident in prior_ids.values()), default=0) + 1
    unique, errors = {}, []
    paths = sorted(p for p in args.source.rglob("*") if p.is_file() and p.suffix.upper() in {".GSC", ".DDS"})
    total = 0
    for number, path in enumerate(paths, 1):
        data = path.read_bytes()
        relative = path.relative_to(args.source)
        for match in re.finditer(rb"DDS ", data):
            offset = match.start()
            try:
                length, width, height, mips, fourcc = dds_length(data, offset)
                payload = data[offset:offset + length]
                digest = hashlib.sha256(payload).hexdigest()
                occurrence = {"archive": relative.parts[0], "resource": Path(*relative.parts[1:]).as_posix(),
                              "offset": offset, "length": length}
                total += 1
                if digest in unique:
                    unique[digest]["occurrences"].append(occurrence)
                    continue
                image = decode_texture(payload, width, height)
                ident = prior_ids.get(digest)
                if ident is None:
                    ident = f"T{next_number:04}"
                    next_number += 1
                image.save(image_dir / f"{ident}.png")
                unique[digest] = {"id": ident, "sha256": digest, "width": width, "height": height,
                                  "mip_count": mips, "compression": fourcc, "occurrences": [occurrence]}
            except Exception as error:
                errors.append({"resource": relative.as_posix(), "offset": offset, "error": str(error)})
        if number % 50 == 0:
            print(f"Scanned {number}/{len(paths)} resources; {len(unique)} unique textures", flush=True)
    manifest = {"scanned_resource_files": len(paths), "dds_occurrences": total,
                "unique_textures": len(unique), "textures": list(unique.values()), "errors": errors}
    (args.output / "inventory.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Finished: {len(paths)} resources, {total} DDS occurrences, {len(unique)} unique textures, {len(errors)} errors")


if __name__ == "__main__":
    main()
