"""Regression checks for the actual Font 2 resource and its loader metadata."""
import struct
import unittest
from collections import Counter
import sys
from pathlib import Path
from check_fnt_layout import validate_layout
from ua.formats.fnt import FntFile, GlyphMetrics

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ua import paths  # noqa: E402
FONT = paths.BUILD / "fonts/font2/FONT2_PC.FNT"
ORIGINAL = paths.GAME / "GAME/STUFF/TEXT/FONT2_PC.FNT"


class Font2LayoutTests(unittest.TestCase):
    def setUp(self):
        self.data = FONT.read_bytes()

    def test_generated_font_is_loadable_and_covers_ukrainian(self):
        info = validate_layout(self.data)
        self.assertEqual(info["relocation_count"], 16)
        self.assertEqual((info["width"], info["height"]), (1024, 1024))
        mapping = {entry.codepoint: entry.glyph_index for entry in FntFile(str(FONT)).list_mapping()}
        for ch in "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ":
            self.assertEqual(mapping[ord(ch)], mapping[ord(ch.lower())])

    def test_missing_footer_is_rejected(self):
        footer = struct.unpack_from("<I", self.data)[0]
        with self.assertRaises(ValueError):
            validate_layout(self.data[:footer])

    def test_stale_footer_pointer_reproduces_legacy_failure(self):
        data = bytearray(self.data)
        struct.pack_into("<I", data, 0, 0x56170)
        with self.assertRaises(ValueError):
            validate_layout(data)

    def test_missing_texture_descriptor_is_rejected(self):
        data = bytearray(self.data)
        dds = 8 + struct.unpack_from("<I", data, 8)[0]
        data[dds - 128:dds] = bytes(128)
        with self.assertRaisesRegex(ValueError, "texture descriptor"):
            validate_layout(data)

    def test_stale_mapping_pointer_is_rejected(self):
        data = bytearray(self.data)
        struct.pack_into("<I", data, 0x48, 2080 - 0x48)
        with self.assertRaises(ValueError):
            validate_layout(data)

    @unittest.skipUnless(ORIGINAL.exists(), "Requires extracted original game resource")
    def test_growing_original_with_unchanged_dds_preserves_loader_structures(self):
        font = FntFile(str(ORIGINAL))
        original = bytes(font.data)
        old_info = validate_layout(original)
        dds = original[font.dds_offset:old_info["relocation_offset"]]
        entries = font.list_mapping()
        indices = font.append_glyphs_and_mappings([GlyphMetrics(0, 0, 20)], [(0x0406, 164)], dds)
        self.assertEqual(indices, [164])
        info = validate_layout(font.data)
        self.assertEqual(info["glyph_count"], old_info["glyph_count"] + 1)
        self.assertEqual(info["mapping_slots"], old_info["mapping_slots"] + 1)
        self.assertEqual(bytes(font.data[info["dds_offset"]:info["relocation_offset"]]), dds)
        old_pairs = Counter((e.codepoint, e.glyph_index) for e in entries)
        grown_pairs = Counter((e.codepoint, e.glyph_index) for e in font.list_mapping())
        self.assertEqual(grown_pairs - old_pairs, Counter({(0x0406, 164): 1}))
        self.assertFalse(old_pairs - grown_pairs)


if __name__ == "__main__":
    unittest.main()
