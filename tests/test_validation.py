"""`ua validate` passes on the repository and catches typical mistakes."""
import copy
import unittest
from unittest import mock

from ua.pipeline import text, validate


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.original = text.load_translations()

    def run_with(self, translations):
        with mock.patch.object(validate, "load_translations", return_value=translations):
            return validate.run()

    def test_repository_translations_pass(self):
        report = validate.run()
        self.assertEqual(report.errors, [])

    def test_missing_translation(self):
        broken = copy.deepcopy(self.original)
        del broken["english"][20]
        self.assertTrue(any("ENGLISH.TXT 20: missing" in e for e in self.run_with(broken).errors))

    def test_broken_token(self):
        broken = copy.deepcopy(self.original)
        key = next(k for k, v in broken["english"].items() if "[" in v)
        broken["english"][key] = broken["english"][key].split("[")[0] + "кнопку"
        self.assertTrue(any(f"ENGLISH.TXT {key}: tokens" in e for e in self.run_with(broken).errors))

    def test_unsupported_character(self):
        broken = copy.deepcopy(self.original)
        broken["english"][20] = "Довге — тире"
        self.assertTrue(any("ENGLISH.TXT 20: characters missing" in e for e in self.run_with(broken).errors))

    def test_double_quote(self):
        broken = copy.deepcopy(self.original)
        broken["pc_menu"]["0"] = 'Вийти "зараз"'
        self.assertTrue(any("PC menu 0" in e for e in self.run_with(broken).errors))


if __name__ == "__main__":
    unittest.main()
