import unittest
from pathlib import Path

from ua.pipeline import shared_glossary

GAME = "indy"


class SharedGlossaryTest(unittest.TestCase):
    def test_vendored_rules_catch_old_forms(self):
        self.assertTrue(shared_glossary.check([("x", "Drop Out", "Вийти з гри")], GAME))
        self.assertEqual(shared_glossary.check([("x", "Drop Out", "Залишити гру")], GAME), [])

    def test_translations_have_no_forbidden_forms(self):
        from ua.pipeline.text import load_translations
        tr = load_translations()
        pairs = [(str(k), "", v) for k, v in tr["english"].items()]
        pairs += [(k, "", v) for part in ("trc", "pc_menu") for k, v in tr[part].items()]
        self.assertEqual(shared_glossary.check(pairs, GAME), [])

    def test_vendored_copy_matches_the_source_repository(self):
        source = Path(__file__).resolve().parents[2] / "lego-ua-glossary"
        if not source.exists():
            self.skipTest("lego-ua-glossary is not checked out next to this repository")
        for name in ("glossary.json", "lego_ua_glossary.py"):
            self.assertEqual((shared_glossary.VENDOR / name).read_bytes(), (source / name).read_bytes(), name)


if __name__ == "__main__":
    unittest.main()
