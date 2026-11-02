"""Level 1: rebuild the nine translated DDS textures from our PNG layers.

The original DDS is sliced from its GSC container in game/. Only 4x4 blocks
whose pixels changed (plus a Lanczos safety margin) are re-encoded; every other
compressed block, the header and the mip count stay byte-identical, so the
replacement keeps the original size and the ASI can swap it in memory.
"""
from __future__ import annotations

import io
import struct

from PIL import Image, ImageChops, ImageFilter

from .. import paths
from ..formats.bc_color import encode_block
from ..util import UaError, read_json, sha256

MANIFEST = paths.ASSETS / "textures/manifest.json"


def pack(image: Image.Image, original: bytes, compression: str, mip_count: int) -> tuple[bytes, int]:
    source = Image.open(io.BytesIO(original)).convert("RGBA")
    if image.size != source.size:
        raise UaError("PNG layer has different dimensions than the original texture")
    difference = ImageChops.difference(image, source)
    channels = difference.split()
    mask = channels[0]
    for channel in channels[1:]:
        mask = ImageChops.lighter(mask, channel)
    # Include Lanczos's neighbouring samples around changed pixels.
    mask = mask.point(lambda value: 255 if value else 0).filter(ImageFilter.MaxFilter(9))
    result = bytearray(original)
    position = 128
    block_size = 8 if compression == "DXT1" else 16
    changed = 0
    for level in range(mip_count):
        width, height = max(1, image.width >> level), max(1, image.height >> level)
        mip = image if level == 0 else image.resize((width, height), Image.Resampling.LANCZOS)
        mip_mask = mask if level == 0 else mask.resize((width, height), Image.Resampling.BOX)
        pixels = list(mip.get_flattened_data())
        start = position
        for y in range(0, height, 4):
            for x in range(0, width, 4):
                if mip_mask.crop((x, y, min(x + 4, width), min(y + 4, height))).getbbox():
                    block = [pixels[min(y + dy, height - 1) * width + min(x + dx, width - 1)]
                             for dy in range(4) for dx in range(4)]
                    if block_size == 8 and any(p[3] != 255 for p in block):
                        raise UaError("DXT1 translations must remain opaque")
                    encoded = encode_block(block)
                    result[position:position + block_size] = encoded[-8:] if block_size == 8 else encoded
                    changed += 1
                position += block_size
        # Decode each mip independently to validate its dimensions and payload.
        header = bytearray(original[:128])
        struct.pack_into("<II", header, 12, height, width)
        struct.pack_into("<I", header, 28, 1)
        decoded = Image.open(io.BytesIO(header + result[start:position]))
        decoded.load()
        if decoded.size != (width, height):
            raise UaError("Decoded mip has unexpected dimensions")
    if not position == len(original) == len(result) or result[:128] != original[:128]:
        raise UaError("Rebuilt DDS changed size or header")
    return bytes(result), changed


def original(item: dict) -> bytes:
    occurrence = item["occurrences"][0]
    container = paths.GAME / occurrence["archive"] / occurrence["resource"]
    if not container.exists():
        raise UaError(f"{container} missing. Run: python -m ua extract --game <Steam folder>")
    data = container.read_bytes()[occurrence["offset"]:occurrence["offset"] + occurrence["length"]]
    if sha256(data) != item["original_sha256"]:
        raise UaError(f"{item['id']}: original texture in {container.name} has a different SHA-256")
    return data


def build() -> tuple[list[tuple[str, bytes]], list[str]]:
    """Return UAP texture resources in manifest order and a list of differences."""
    resources, differences = [], []
    for item in read_json(MANIFEST)["textures"]:
        if item["compression"] not in ("DXT1", "DXT5"):
            raise UaError(f"{item['id']}: unsupported compression {item['compression']}")
        source = original(item)
        image = Image.open(paths.ASSETS / "textures" / item["png"]).convert("RGBA")
        payload, _ = pack(image, source, item["compression"], item["mip_count"])
        if sha256(payload) != item["dds_sha256"]:
            differences.append(f"{item['id']}: rebuilt DDS differs from the reviewed build")
        if sha256(source[128:]).upper() != item["uap_key"]:
            raise UaError(f"{item['id']}: UAP key mismatch")
        resources.append((f"UKRAINIAN/TEXTURES/{item['uap_key']}.DDS", payload))
    return resources, differences
