"""
Reader/writer for classic TT Games PC .FNT resources.

Confirmed by an actual LEGOIndy crash dump and successful live launch:
  0x00 u32: relative pointer to relocation footer (not magic/version)
  0x04 u32: relative pointer to resource header
  0x08 u32: relative pointer to DDS
  0x18 u32: end of real mapping entries in observed files
  0x1c u32: metrics record count, including trailing unmapped record
  0x20 u32: mapping slot count, including sentinel pairs
  0x24 f32: shared glyph height
  0x28 f32: baseline
  0x44 u32: relative pointer to metrics (observed target 0x60)
  0x48 u32: relative pointer to Unicode mapping

Metrics: (x, y, width), three float32 values per record.
Mapping: (codepoint, glyph index), two uint16 values per slot.
The 128 bytes immediately BEFORE DDS are the engine texture descriptor.
AFTER DDS is a relocation count and signed relative pointers to pointer
fields. Each pointer field itself stores an offset relative to that field.
Growing the file must preserve and adjust BOTH engine structures.
See docs/research/font2-crash-investigation.md for evidence and limits.
"""
from __future__ import annotations
import struct
from pathlib import Path
from dataclasses import dataclass


SENTINEL = 0xFFFF

GLYPH_METRICS_BASE = 0x60
GLYPH_METRICS_STRIDE = 12


@dataclass
class MappingEntry:
    codepoint: int
    glyph_index: int


@dataclass
class GlyphMetrics:
    x: float
    y: float
    width: float


class FntFile:
    def __init__(self, path: str):
        self.path = path
        self.data = bytearray(Path(path).read_bytes())

    # ---- header -----------------------------------------------------
    @property
    def dds_offset(self) -> int:
        ptr = struct.unpack_from("<I", self.data, 8)[0]
        return 8 + ptr

    @property
    def height(self) -> float:
        return struct.unpack_from("<f", self.data, 0x24)[0]

    @property
    def base(self) -> float:
        return struct.unpack_from("<f", self.data, 0x28)[0]

    def inspect(self) -> dict:
        dds_off = self.dds_offset
        found_dds = self.data.find(b"DDS ")
        info = {
            "path": self.path,
            "size": len(self.data),
            "relocation_offset": struct.unpack_from("<I", self.data, 0)[0],
            "dds_offset_from_header": dds_off,
            "dds_offset_found": found_dds,
            "header_math_ok": dds_off == found_dds,
            "height": self.height,
            "base": self.base,
        }
        if found_dds != -1:
            w = struct.unpack_from("<I", self.data, found_dds + 16)[0]
            h = struct.unpack_from("<I", self.data, found_dds + 12)[0]
            fourcc = bytes(self.data[found_dds + 84:found_dds + 88])
            info["dds_width"] = w
            info["dds_height"] = h
            info["dds_fourcc"] = fourcc
        return info

    # ---- mapping table ------------------------------------------------
    def find_mapping_table(self):
        """Read the declared mapping pointer/count, keeping duplicate entries.

        Font 2 has three sentinel slots, Font 1 one. No backward guessing
        is needed: 0x48 is a relative pointer, 0x20 the full slot count.
        """
        start = 0x48 + struct.unpack_from("<I", self.data, 0x48)[0]
        count = struct.unpack_from("<I", self.data, 0x20)[0]
        if start < GLYPH_METRICS_BASE or start + count * 4 > self.dds_offset - 128:
            raise ValueError("mapping pointer/count outside font data")
        entries = []
        for i in range(count):
            cp, gi = struct.unpack_from("<HH", self.data, start + i * 4)
            if (cp, gi) == (SENTINEL, SENTINEL):
                return start, start + (i + 1) * 4, entries
            entries.append(MappingEntry(cp, gi))
        raise ValueError("declared mapping table has no sentinel")

    def list_mapping(self):
        start, end, entries = self.find_mapping_table()
        return entries

    def remap_existing_codepoint(self, old_cp: int, new_cp: int):
        """In-place: change the codepoint of an EXISTING mapping entry to a
        new value, WITHOUT resizing the file. This breaks strict ascending
        sort order if new_cp doesn't belong at that position — only safe if
        the game's lookup does not require strict sort order (UNVERIFIED).
        Prefer remap_and_resort() for anything meant to actually ship."""
        start, end, entries = self.find_mapping_table()
        off = start
        for e in entries:
            cp, gi = struct.unpack_from("<HH", self.data, off)
            if cp == old_cp:
                struct.pack_into("<HH", self.data, off, new_cp, gi)
                return True
            off += 4
        return False

    def remap_and_resort(self, remap: dict[int, int]):
        """Like remap_existing_codepoint, but re-sorts the WHOLE mapping
        table by codepoint afterward and rewrites it in place (same start/end
        offsets, same entry count, same terminator/padding after it -- only
        the order and the remapped codepoint fields change).

        This exists because remap_existing_codepoint() leaves the table out
        of ascending order at the edited entries. That was later confirmed
        in a real game launch to break rendering for at least one remapped
        codepoint (U+0456 'i' rendered as a missing-glyph box) -- consistent
        with the engine doing a binary (not linear) search over this table.
        Re-sorting after editing is the fix.

        Operates on the entry LIST, not a dict keyed by codepoint: the real
        table has been observed to contain a few duplicate/near-duplicate
        codepoints (parser noise or genuine duplicates, unconfirmed) -- a
        dict would silently collapse those and shrink the table. We only
        remap the *first* entry matching each old codepoint, and otherwise
        preserve every entry, including duplicates, exactly once.
        """
        start, end, entries = self.find_mapping_table()
        pairs = [(e.codepoint, e.glyph_index) for e in entries]
        remaining = dict(remap)
        new_pairs = []
        for cp, gi in pairs:
            if cp in remaining:
                new_pairs.append((remaining.pop(cp), gi))
            else:
                new_pairs.append((cp, gi))
        if remaining:
            raise ValueError(f"codepoints not found in table: {[hex(c) for c in remaining]}")
        sorted_items = sorted(new_pairs, key=lambda kv: kv[0])
        if len(sorted_items) != len(entries):
            raise ValueError(f"entry count changed: {len(entries)} -> {len(sorted_items)}")
        off = start
        for cp, gi in sorted_items:
            struct.pack_into("<HH", self.data, off, cp, gi)
            off += 4
        # `end` (from find_mapping_table) points just past the sentinel entry,
        # which is not itself in `entries` -- rewrite it explicitly so the
        # span we fill exactly matches [start, end).
        struct.pack_into("<HH", self.data, off, SENTINEL, SENTINEL)
        off += 4
        assert off == end, f"wrote {off - start} bytes, expected {end - start}"
        return sorted_items

    # ---- glyph metrics table -------------------------------------------
    def get_glyph_metrics(self, glyph_index: int) -> GlyphMetrics:
        off = GLYPH_METRICS_BASE + glyph_index * GLYPH_METRICS_STRIDE
        x, y, w = struct.unpack_from("<fff", self.data, off)
        return GlyphMetrics(x, y, w)

    def set_glyph_metrics(self, glyph_index: int, x: float = None, y: float = None, w: float = None):
        """In-place: overwrite one or more fields of an existing glyph's
        metrics record. Fields left as None keep their current value. Never
        resizes the file (every record is a fixed 12 bytes)."""
        off = GLYPH_METRICS_BASE + glyph_index * GLYPH_METRICS_STRIDE
        cur = self.get_glyph_metrics(glyph_index)
        new_x = cur.x if x is None else x
        new_y = cur.y if y is None else y
        new_w = cur.width if w is None else w
        struct.pack_into("<fff", self.data, off, new_x, new_y, new_w)

    def add_mapping_alias(self, codepoint: int, existing_codepoint: int):
        """Add a sorted alias using zero padding before the texture descriptor.

        Keep the metrics, DDS, relocation footer and all relative pointers in
        place. Font 1 has spare mapping padding but donor-specific relocation
        fields, so rebuilding its whole container is unnecessary here.
        """
        start, end, entries = self.find_mapping_table()
        mapping = {entry.codepoint: entry.glyph_index for entry in entries}
        target = mapping[existing_codepoint]
        if codepoint in mapping:
            if mapping[codepoint] != target:
                raise ValueError("alias already maps to a different glyph")
            return
        slots = struct.unpack_from("<I", self.data, 0x20)[0]
        declared_end = start + slots * 4
        if struct.unpack_from("<I", self.data, 0x18)[0] != end - 4:
            raise ValueError("unexpected mapping end field")
        if declared_end + 4 > self.dds_offset - 128 or any(self.data[declared_end:declared_end + 4]):
            raise ValueError("no zero padding available for a mapping alias")
        pairs = sorted([(e.codepoint, e.glyph_index) for e in entries] + [(codepoint, target)])
        table = b"".join(struct.pack("<HH", cp, gi) for cp, gi in pairs)
        table += self.data[end - 4:declared_end]
        self.data[start:declared_end + 4] = table
        struct.pack_into("<I", self.data, 0x18, end)
        struct.pack_into("<I", self.data, 0x20, slots + 1)

    def save(self, out_path: str):
        Path(out_path).write_bytes(self.data)

    # ---- growing the file: new glyphs + new mapping entries -------------
    def append_glyphs_and_mappings(
        self,
        new_metrics: list[GlyphMetrics],
        new_mapping_entries: list[tuple[int, int]],
        new_dds: bytes,
    ) -> list[int]:
        """Grow tables while preserving the texture descriptor and relocation footer.

        The first DWORD is a relative pointer to the relocation table, NOT
        magic/version. All pointers listed there are relative to their own
        field. The engine relocates them before loading the DDS.
        """
        from check_fnt_layout import validate_layout

        validate_layout(self.data)
        source = bytes(self.data)
        mapping_start, _mapping_end, entries = self.find_mapping_table()
        old_glyph_count = struct.unpack_from("<I", source, 0x1c)[0]
        old_map_slots = struct.unpack_from("<I", source, 0x20)[0]
        metrics_end = GLYPH_METRICS_BASE + old_glyph_count * GLYPH_METRICS_STRIDE
        old_dds = self.dds_offset
        old_descriptor = old_dds - 128
        old_footer = struct.unpack_from("<I", source, 0)[0]
        relocation_count = struct.unpack_from("<I", source, old_footer)[0]
        locations = []
        for i in range(relocation_count):
            entry = old_footer + 4 + i * 4
            locations.append(entry + struct.unpack_from("<i", source, entry)[0])

        first_new = max(e.glyph_index for e in entries) + 1
        new_indices = list(range(first_new, first_new + len(new_metrics)))
        used_metrics_end = GLYPH_METRICS_BASE + first_new * GLYPH_METRICS_STRIDE
        metrics = source[GLYPH_METRICS_BASE:used_metrics_end]
        metrics += b"".join(struct.pack("<fff", m.x, m.y, m.width) for m in new_metrics)
        # Keep the unmapped trailing blank record(s) after the new glyphs.
        # Existing manual overrides use indices 164..196 for Font 2.
        metrics += source[used_metrics_end:metrics_end]
        metrics += source[metrics_end:mapping_start]
        pairs = [(e.codepoint, e.glyph_index) for e in entries] + list(new_mapping_entries)
        pairs.sort(key=lambda pair: pair[0])
        terminators = old_map_slots - len(entries)
        assert terminators > 0
        mapping = b"".join(struct.pack("<HH", cp, gi) for cp, gi in pairs)
        mapping += struct.pack("<HH", SENTINEL, SENTINEL) * terminators
        new_mapping_start = GLYPH_METRICS_BASE + len(metrics)
        prefix = bytearray(source[:GLYPH_METRICS_BASE] + metrics + mapping)
        # The 128-byte engine texture descriptor must survive; the old
        # implementation mistook this region for disposable zero padding.
        prefix += b"\x00" * ((-len(prefix)) % 128)
        new_descriptor = len(prefix)
        prefix += source[old_descriptor:old_dds]
        new_dds_offset = len(prefix)
        new_footer = new_dds_offset + len(new_dds)
        new_data = prefix + new_dds
        struct.pack_into("<I", new_data, 0, new_footer)
        struct.pack_into("<I", new_data, 8, new_dds_offset - 8)
        struct.pack_into("<I", new_data, 0x18, new_mapping_start + len(pairs) * 4)
        struct.pack_into("<I", new_data, 0x1c, old_glyph_count + len(new_metrics))
        struct.pack_into("<I", new_data, 0x20, len(pairs) + terminators)
        struct.pack_into("<I", new_data, 0x48, new_mapping_start - 0x48)
        width = struct.unpack_from("<I", new_dds, 16)[0]
        height = struct.unpack_from("<I", new_dds, 12)[0]
        mip_count = struct.unpack_from("<I", new_dds, 28)[0]
        struct.pack_into("<II", new_data, new_descriptor, width, height)
        struct.pack_into("<II", new_data, new_descriptor + 64, mip_count, len(new_dds))
        new_data += struct.pack("<I", relocation_count)
        for i, location in enumerate(locations):
            if old_descriptor <= location < old_dds:
                location += new_descriptor - old_descriptor
            elif location >= GLYPH_METRICS_BASE:
                raise ValueError(f"Unsupported relocation field: 0x{location:x}")
            entry = new_footer + 4 + i * 4
            new_data += struct.pack("<i", location - entry)
        validate_layout(new_data)
        self.data = new_data
        return new_indices



def inspect(path: str):
    f = FntFile(path)
    info = f.inspect()
    for k, v in info.items():
        print(f"  {k}: {v}")
    return info


def list_mapping(path: str):
    f = FntFile(path)
    entries = f.list_mapping()
    print(f"{len(entries)} mapping entries")
    for e in entries:
        print(f"  U+{e.codepoint:04X}  -> glyph_index {e.glyph_index}")
    return entries


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: fnt_tool.py <inspect|list_mapping> <path.fnt>")
        raise SystemExit(1)
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "inspect":
        inspect(path)
    elif cmd == "list_mapping":
        list_mapping(path)
    else:
        print("unknown command", cmd)
