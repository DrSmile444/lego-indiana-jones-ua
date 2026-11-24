"""Font 1 and Font 2 drawn again at k times the resolution (ua/pipeline/font_hd.py)."""
import struct
import unittest

from ua import paths
from ua.util import UaError
from ua.formats.fnt import FntFile
from ua.pipeline import font_hd

FONT1 = paths.BUILD / "fonts/font1/PC_FONT_PC.FNT"
FONT2 = paths.BUILD / "fonts/font2/FONT2_PC.FNT"
K = 2  # a small scale keeps the tests fast; every rule is the same at x4


def _available() -> bool:
    try:
        font_hd.typeface_path(font_hd.style()["files"])
        font_hd.typeface_path(font_hd.font2_style()["files"])
    except UaError:
        return False
    return FONT1.exists() and FONT2.exists()


def _bottom(font: FntFile, atlas, char: str, k: int) -> int:
    """Lowest inked row of the glyph's cell, in k-scale pixels."""
    index = {e.codepoint: e.glyph_index for e in font.list_mapping()}[ord(char)]
    g = font.get_glyph_metrics(index)
    cell = atlas.crop((int(g.x * k), int(g.y * k), int((g.x + g.width) * k), int((g.y + font.height) * k)))
    return font_hd.ink(cell.getchannel("A").point(lambda v: 255 if v > 128 else 0))[3]


@unittest.skipUnless(_available(), "needs build/fonts (python -m ua build --level full) and the typefaces")
class FontHdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s1, s2 = font_hd.style, font_hd.font2_style
        font_hd.style = lambda: {**s1(), "scale": K}
        font_hd.font2_style = lambda: {**s2(), "scale": K}
        try:
            cls.one = font_hd.render(FONT1.read_bytes())
            cls.two = font_hd.render2(FONT2.read_bytes())
            cls.packed = font_hd.compose2(FONT2.read_bytes())
        finally:
            font_hd.style, font_hd.font2_style = s1, s2

    def assertOneBaseline(self, font, atlas, letters, slack=0):
        bottoms = {c: _bottom(font, atlas, c, K) for c in letters}
        low = min(bottoms.values())
        off = {c: b for c, b in bottoms.items() if b - low > slack}
        self.assertFalse(off, f"letters below the shared baseline {low}: {off}")

    def test_font1_letters_share_one_baseline(self):
        font, _, big, _ = self.one
        self.assertOneBaseline(font, big, "абвгґеєжзиіїйклмнптшьАБВГҐЕЄЖЗИІЇЙКЛМНПТШЬЮЯHIEFLTZxzwvnmhkl", slack=K)

    def test_font1_descenders_go_below_the_baseline(self):
        font, _, big, _ = self.one
        base = _bottom(font, big, "н", K)
        for c in "дщцДЩЦру":
            self.assertGreater(_bottom(font, big, c, K), base + 2 * K, c)

    def test_font2_capitals_share_one_baseline(self):
        font, _, big, _ = self.two
        self.assertOneBaseline(font, big, "АБВГҐЕЄЖЗИІЇЙКЛМНПТШЬЯHIEFLT", slack=2 * K)

    def test_font2_ukrainian_capitals_match_latin_height(self):
        font, _, big, _ = self.two
        index = {e.codepoint: e.glyph_index for e in font.list_mapping()}

        def height(c):
            g = font.get_glyph_metrics(index[ord(c)])
            cell = big.crop((int(g.x * K), int(g.y * K), int((g.x + g.width) * K), int((g.y + font.height) * K)))
            box = font_hd.ink(cell.getchannel("A").point(lambda v: 255 if v > 128 else 0))
            return box[3] - box[1]

        latin = sum(height(c) for c in "HEFT") / 4
        for c in "НЕПТ":
            self.assertAlmostEqual(height(c), latin, delta=3 * K, msg=c)

    def test_capitals_with_marks_keep_the_plain_body(self):
        # fill rows of the drawn glyph: the run that ends on the baseline is the body, the runs above it the mark
        font1 = font_hd.Renderer(K, {**font_hd.style(), "scale": K}, int(self.one[0].height))
        font2 = font_hd.Adventure({**font_hd.font2_style(), "scale": K}, K, int(self.two[0].height))

        def runs(fill):
            rows = "".join("#" if fill.crop((0, y, fill.width, y + 1)).getextrema()[1] > 128 else "."
                           for y in range(fill.height))
            return [len(run) for run in rows.split(".") if run]

        for name, fill in (("Font 1", lambda c: font1.masks(c)[0]), ("Font 2", font2.fill)):
            for accented, plain in (("Й", "И"), ("Ї", "І")):
                self.assertEqual(runs(fill(accented))[-1], runs(fill(plain))[-1], f"{name} {accented}")
                self.assertGreaterEqual(len(runs(fill(accented))), 2, f"{name} {accented}: mark joined the body")

    def test_font2_descenders_stay_inside_the_cell(self):
        # the outline _paint2 adds around the fill keeps one clear row at the bottom of the cell
        font2 = font_hd.Adventure({**font_hd.font2_style(), "scale": K}, K, int(self.two[0].height))
        outline = round(font_hd.font2_style()["outline"] * K)
        for c in "ДЦЩ":
            fill = font2.fill(c)
            self.assertLessEqual(font_hd.visible(fill)[3], fill.height - outline - K, c)

    def test_font2_file_keeps_size_and_carries_mark(self):
        data, hd, _ = self.packed
        self.assertEqual(len(data), len(FONT2.read_bytes()))
        at = font_hd._font(data).dds_offset
        self.assertEqual(data[at + 32:at + 36], font_hd.MARK)
        self.assertEqual(struct.unpack_from("<II", data, at + 36), (K, 1))
        self.assertEqual(hd[:4], b"DDS ")
        self.assertEqual(struct.unpack_from("<II", hd, 12), (1024 * K, 1024 * K))


if __name__ == "__main__":
    unittest.main()
