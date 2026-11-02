"""Build English title containers with the supplied Ukrainian PNG textures.

Only the two DDS pixel payloads change; container size, DDS headers and
all other resources stay intact. Does not write to the game installation.
"""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image

from ua.formats.bc_color import encode_block

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
GRAPHICS = paths.ASSETS / "logo"
GAME = paths.GAME


def encode_dds(image, original, mip_count):
    chunks = [original[:128]]
    for level in range(mip_count):
        width, height = max(1, image.width >> level), max(1, image.height >> level)
        mip = image if level == 0 else image.resize((width, height), Image.Resampling.LANCZOS)
        pixels = list(mip.get_flattened_data())
        for y in range(0, height, 4):
            for x in range(0, width, 4):
                block = [
                    pixels[min(y + dy, height - 1) * width + min(x + dx, width - 1)]
                    for dy in range(4) for dx in range(4)
                ]
                chunks.append(encode_block(block))
    result = b"".join(chunks)
    if len(result) != len(original):
        raise ValueError("Encoded DDS length differs from original")
    decoded = Image.open(io.BytesIO(result)).convert("RGBA")
    if decoded.size != image.size:
        raise ValueError("Encoded DDS dimensions differ from PNG")
    return result, decoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-path", type=Path, default=GAME)
    args = parser.parse_args()
    manifest = json.loads((GRAPHICS / "manifest.json").read_text(encoding="utf-8"))
    replacements = []
    built = GRAPHICS / "built"
    built.mkdir(exist_ok=True)
    for item in manifest["textures"]:
        png = GRAPHICS / f"{item['name']}-ukrainian.png"
        image = Image.open(png)
        if image.size != (item["width"], item["height"]) or image.mode != "RGBA":
            raise ValueError(f"Expected RGBA {item['width']}x{item['height']}: {png}")
        original = (GRAPHICS / "originals" / f"{item['name']}.dds").read_bytes()
        if hashlib.sha256(original).hexdigest() != item["dds_sha256"]:
            raise ValueError("Original DDS checksum mismatch")
        payload, decoded = encode_dds(image, original, item["mip_count"])
        (built / f"{item['name']}-ukrainian.dds").write_bytes(payload)
        decoded.save(built / f"{item['name']}-compressed-preview.png")
        replacements.append((item, original, payload))
        print(f"Encoded {png.name}: {item['mip_count']} mip levels, {len(payload)} bytes")
    report = {"resources": []}
    for variant in ("US", "UK"):
        relative = Path(f"LEVELS/TITLES/TITLES_{variant}_PC.GSC")
        backup = GRAPHICS / "originals" / relative.name
        source = backup if backup.exists() else args.game_path / relative
        before = source.read_bytes()
        after = bytearray(before)
        cursor = 0
        for item, original, payload in sorted(replacements, key=lambda r: r[0]["offset"]):
            start, end = item["offset"], item["offset"] + item["length"]
            if before[start:end] != original:
                raise ValueError(f"Unexpected original logo in {source}; refusing to patch")
            after[start:end] = payload
            assert after[cursor:start] == before[cursor:start]
            assert after[start:start + 128] == before[start:start + 128]
            cursor = end
        assert after[cursor:] == before[cursor:]
        assert len(after) == len(before)
        destination = paths.BUILD / "title-logo" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(after)
        if backup.exists() and backup.read_bytes() != before:
            raise ValueError(f"Saved original differs: {backup}")
        if not backup.exists():
            backup.write_bytes(before)
        report["resources"].append({
            "path": relative.as_posix(), "size": len(after),
            "original_sha256": hashlib.sha256(before).hexdigest(),
            "patched_sha256": hashlib.sha256(after).hexdigest(),
        })
        print(f"Built {destination.relative_to(REPO)}; only logo DDS pixels changed")
    (built / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
