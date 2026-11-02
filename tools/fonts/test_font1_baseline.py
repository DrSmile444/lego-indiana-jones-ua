"""Check the UI font baseline used when switching to controller icons."""
import unittest
import sys
from pathlib import Path

from ua.formats.fnt import FntFile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ua import paths  # noqa: E402
NAMES = ("FONT_PC.FNT", "PC_FONT.FNT", "PC_FONT_PC.FNT", "PC_FONT_NGC.FNT")
ORIGINAL = paths.GAME / "GAME/STUFF/TEXT/FONT_PC.FNT"


class Font1BaselineTests(unittest.TestCase):
    def test_all_shipped_ui_fonts_keep_indiana_jones_baseline(self):
        for folder in (paths.BUILD / "fonts/font1", paths.BUILD / "uap-unpacked/STUFF/TEXT"):
            for name in NAMES:
                with self.subTest(folder=folder, name=name):
                    font = FntFile(str(folder / name))
                    self.assertEqual(font.height, 48)
                    self.assertEqual(font.base, 37,
                                     "base=0 makes the separate button font sit above UI text")

    @unittest.skipUnless(ORIGINAL.exists(), "Requires extracted original UI font")
    def test_matches_original_ui_vertical_metrics(self):
        original = FntFile(str(ORIGINAL))
        patched = FntFile(str(paths.BUILD / "fonts/font1/PC_FONT_PC.FNT"))
        self.assertEqual((patched.height, patched.base), (original.height, original.base))

    def test_ui_aliases_and_release_are_identical(self):
        expected = (paths.BUILD / "fonts/font1/PC_FONT_PC.FNT").read_bytes()
        for folder in (paths.BUILD / "fonts/font1", paths.BUILD / "uap-unpacked/STUFF/TEXT"):
            for name in NAMES:
                with self.subTest(folder=folder, name=name):
                    self.assertEqual((folder / name).read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
