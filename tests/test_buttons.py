"""The 4x button icons: the marked game font and the atlas the plugin loads for it.

Needs the extracted game font (game/), the LEGO Star Wars III button font (game/LSW3/) and its
enlargement (local/buttons/, tools/fonts/upscale_buttons.py); skipped otherwise.
"""
import io
import struct
import unittest

from PIL import Image

from ua import paths
from ua.pipeline import buttons_hd
from ua.pipeline import font_hd as fonts

FONT = paths.GAME / "GAME" / buttons_hd.RESOURCE
DONOR = paths.GAME / "LSW3" / buttons_hd.SOURCE
ART = paths.LOCAL / buttons_hd.ART


@unittest.skipUnless(FONT.exists() and DONOR.exists() and ART.exists(), "button sources not found")
class ButtonsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = FONT.read_bytes()
        cls.data, cls.hd, cls.cells = buttons_hd.build(cls.original, DONOR.read_bytes(), buttons_hd.art())
        cls.at = 8 + struct.unpack_from("<I", cls.original, 8)[0]

    def test_only_the_mark_changes_in_the_font(self):
        self.assertEqual(len(self.data), len(self.original))
        changed = [i for i, (a, b) in enumerate(zip(self.data, self.original)) if a != b]
        self.assertTrue(changed and all(self.at + 32 <= i < self.at + 44 for i in changed), changed)
        self.assertEqual(self.data[self.at + 32:self.at + 36], fonts.MARK)
        self.assertEqual(struct.unpack_from("<II", self.data, self.at + 36), (4, buttons_hd.SLOT))

    def test_hd_atlas_is_4x_with_a_full_mip_chain(self):
        self.assertEqual(self.hd[:4], b"DDS ")
        self.assertEqual(self.hd[84:88], b"DXT5")
        height, width = struct.unpack_from("<II", self.hd, 12)
        self.assertEqual((width, height), (1024, 512))
        self.assertEqual(struct.unpack_from("<I", self.hd, 28)[0], len(fonts.chain(width, height)))
        self.assertEqual(self.hd[32:36], bytes(4))

    def test_every_icon_comes_from_the_studio_art(self):
        self.assertEqual([c.index for c in self.cells], list(range(1, 16)))
        self.assertTrue(all(max(c.error, c.error_hd) <= buttons_hd.MAX_ERROR for c in self.cells))

    def test_hd_cells_match_the_game_icons_at_1x(self):
        small = Image.open(io.BytesIO(self.original[self.at:])).convert("RGBA")
        big = Image.open(io.BytesIO(self.hd)).convert("RGBA")
        for c in self.cells:
            box = (c.x, c.y, c.x + c.width, c.y + 36)
            cell = big.crop(tuple(v * 4 for v in box)).convert("RGBa").resize((c.width, 36), Image.Resampling.BOX)
            self.assertLess(buttons_hd.error(cell, small.crop(box)), buttons_hd.MAX_ERROR, c.index)


if __name__ == "__main__":
    unittest.main()
