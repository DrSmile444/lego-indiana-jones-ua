"""Validate the file pointers consumed by LEGOIndy's FNT loader."""
import struct
import sys
from pathlib import Path


def validate_layout(data: bytes) -> dict:
    def u32(offset):
        if not 0 <= offset <= len(data) - 4:
            raise ValueError(f"field outside file: 0x{offset:x}")
        return struct.unpack_from("<I", data, offset)[0]

    relocation = u32(0)
    count = u32(relocation)
    if count > (len(data) - relocation - 4) // 4:
        raise ValueError("relocation table extends outside file")
    locations = []
    for i in range(count):
        entry = relocation + 4 + i * 4
        location = entry + struct.unpack_from("<i", data, entry)[0]
        u32(location)
        relative = struct.unpack_from("<i", data, location)[0]
        if relative and not 0 <= location + relative < len(data):
            raise ValueError(f"pointer at 0x{location:x} targets outside file")
        locations.append(location)
    dds = 8 + u32(8)
    if data[dds:dds + 4] != b"DDS ":
        raise ValueError("DDS pointer does not point at DDS header")
    width, height = u32(dds + 16), u32(dds + 12)
    mips = u32(dds + 28)
    if data[dds + 84:dds + 88] != b"DXT5":
        raise ValueError("validator supports only PC DXT5 textures")
    if not width or not height or not 1 <= mips <= max(width, height).bit_length():
        raise ValueError("invalid DDS dimensions or mip count")
    size = 128 + sum(max(1, ((width >> level) + 3) // 4) *
                     max(1, ((height >> level) + 3) // 4) * 16
                     for level in range(mips))
    if relocation != dds + size:
        raise ValueError("DDS mip chain does not end at relocation footer")
    descriptor = dds - 128
    if (u32(descriptor), u32(descriptor + 4), u32(descriptor + 64),
            u32(descriptor + 68)) != (width, height, mips, size):
        raise ValueError("texture descriptor disagrees with DDS")
    glyph_count, map_count = u32(0x1c), u32(0x20)
    metrics, mapping = 0x44 + u32(0x44), 0x48 + u32(0x48)
    if metrics + glyph_count * 12 > mapping:
        raise ValueError("glyph metrics overlap mapping table")
    if mapping + map_count * 4 > descriptor:
        raise ValueError("mapping table overlaps texture descriptor")
    real_pairs = []
    for i in range(map_count):
        cp, gi = struct.unpack_from("<HH", data, mapping + i * 4)
        if (cp, gi) != (0xffff, 0xffff):
            if gi >= glyph_count:
                raise ValueError(f"glyph {gi} outside declared metrics table")
            real_pairs.append((cp, gi))
    return dict(relocation_offset=relocation, relocation_count=count,
                dds_offset=dds, glyph_count=glyph_count,
                mapping_offset=mapping, mapping_slots=map_count,
                real_mapping_entries=len(real_pairs), width=width, height=height)


if __name__ == "__main__":
    for name in sys.argv[1:]:
        try:
            print(name, validate_layout(Path(name).read_bytes()))
        except (ValueError, struct.error) as error:
            print(f"{name}: INVALID: {error}")
            sys.exit(1)
