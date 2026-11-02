"""Regression checks for the engine-generated bottom targeting triangle."""
import unittest
import sys
from pathlib import Path

from ua.formats.fnt import FntFile
from audit_runtime_ui_glyphs import audit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ua import paths  # noqa: E402
FONT = paths.BUILD / 'fonts/font1/FONT_PC.FNT'
DONOR = paths.DONORS / 'cyrillic-font-patch/PC_FONT_PC.FNT'


class TargetingGlyphTests(unittest.TestCase):
    def test_shipped_fonts_cover_all_four_targeting_markers(self):
        for folder in (paths.BUILD / 'fonts/font1', paths.BUILD / 'uap-unpacked/STUFF/TEXT'):
            for name in ('FONT_PC.FNT', 'PC_FONT.FNT', 'PC_FONT_PC.FNT', 'PC_FONT_NGC.FNT'):
                with self.subTest(folder=folder, name=name):
                    self.assertTrue(all(item['present'] for item in audit(folder / name)['targeting']))

    @unittest.skipUnless(DONOR.exists(), 'Requires donor font')
    def test_alias_preserves_container_and_every_existing_glyph(self):
        font = FntFile(str(DONOR))
        before = bytes(font.data)
        old_mapping = [(e.codepoint, e.glyph_index) for e in font.list_mapping()]
        start, end, _ = font.find_mapping_table()
        self.assertNotIn(0xAB, dict(old_mapping))
        font.add_mapping_alias(0xAB, 0xAC)
        self.assertEqual(len(before), len(font.data))
        self.assertEqual(before[font.dds_offset - 128:], font.data[font.dds_offset - 128:])
        self.assertEqual(before[0x60:start], font.data[0x60:start])
        mapping = [(e.codepoint, e.glyph_index) for e in font.list_mapping()]
        self.assertEqual(mapping, sorted(old_mapping + [(0xAB, dict(old_mapping)[0xAC])]))
        allowed = set(range(0x18, 0x1c)) | set(range(0x20, 0x24)) | set(range(start, end + 4))
        self.assertTrue(all(i in allowed for i, (a, b) in enumerate(zip(before, font.data)) if a != b))
        once = bytes(font.data)
        font.add_mapping_alias(0xAB, 0xAC)
        self.assertEqual(once, bytes(font.data))

    def test_targeting_alias_uses_existing_upward_triangle(self):
        font = FntFile(str(FONT))
        mapping = {e.codepoint: e.glyph_index for e in font.list_mapping()}
        self.assertIn(0xAB, mapping)
        self.assertEqual(mapping[0xAB], mapping[0xAC])
        triangle = font.get_glyph_metrics(mapping[0xAB])
        self.assertEqual((triangle.x, triangle.y, triangle.width), (389, 240, 38))


if __name__ == '__main__':
    unittest.main()
