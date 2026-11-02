"""Format round trips on synthetic data — no game files involved."""
import tempfile
import unittest
from pathlib import Path

from ua.formats import credits, trc_csv, txt, uap


class UapTest(unittest.TestCase):
    def test_round_trip_and_dedup(self):
        items = [("STUFF/TEXT/A.TXT", b"one"), ("STUFF/TEXT/B.TXT", b"two"), ("COPY/A.TXT", b"one")]
        data = uap.pack(items)
        self.assertEqual(uap.read(data), items)
        self.assertEqual(data.count(b"one"), 1)

    def test_rejects_tampered_payload(self):
        data = bytearray(uap.pack([("A.TXT", b"payload")]))
        data[-1] ^= 1
        with self.assertRaises(ValueError):
            uap.read(bytes(data))

    def test_rejects_unsafe_path(self):
        with self.assertRaises(ValueError):
            uap.read(uap.pack([("../EVIL.TXT", b"x")]))


class TxtTest(unittest.TestCase):
    def test_translation_keeps_structure(self):
        # The quoted text is matched greedily, so a trailing `;was "..."` comment
        # on a translated line is replaced together with the text. Every release
        # since 0.1.0 has this shape; keeping it is what makes rebuilds byte-identical.
        source = '﻿; Section\r\n10 "Hello"\r\n11 pc "Press [A]" ;was "old"\r\n'
        with tempfile.TemporaryDirectory() as work:
            src, out = Path(work) / "in.txt", Path(work) / "out.txt"
            src.write_bytes(source.encode("utf-8"))
            report = txt.write_translated(src, {10: "Привіт", 11: "Натисніть [A]"}, out, allow_missing=False)
            self.assertEqual(report["unknown_ids"], [])
            self.assertEqual(out.read_bytes().decode("utf-8"),
                             '﻿; Section\r\n10 "Привіт"\r\n11 pc "Натисніть [A]"\r\n')

    def test_missing_translation_is_an_error(self):
        with tempfile.TemporaryDirectory() as work:
            src = Path(work) / "in.txt"
            src.write_text('10 "a"\n11 "b"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                txt.write_translated(src, {10: "x"}, Path(work) / "out.txt", allow_missing=False)


class TrcCsvTest(unittest.TestCase):
    def test_only_target_column_changes(self):
        header = ",".join(f'"{c}"' for c in trc_csv.HEADER)
        source = header + '\r\n"GREETING","Hello","Bonjour",,,,"Hello",\r\n'
        with tempfile.TemporaryDirectory() as work:
            src, out = Path(work) / "in.csv", Path(work) / "out.csv"
            src.write_text(source, encoding="utf-16", newline="")
            trc_csv.write_translated(src, {"GREETING": "Привіт"}, out)
            rows = trc_csv.read_rows(out)
            self.assertEqual(rows[1][:3], ["GREETING", "Привіт", "Bonjour"])


class CreditsTest(unittest.TestCase):
    SOURCE = '﻿heading colour 1 0 0\r\nheading "DEVELOPED BY"\r\nname "Jane Doe"\r\ntitle\t"PRODUCER"\r\n'

    def test_line_addressed_translation(self):
        data = self.SOURCE.encode("utf-8")
        self.assertEqual(credits.translatable_lines(data), {2: ("heading", "DEVELOPED BY"), 4: ("title", "PRODUCER")})
        out = credits.apply(data, {2: "РОЗРОБЛЕНО", 4: "ПРОДЮСЕР"}).decode("utf-8")
        self.assertIn('heading "РОЗРОБЛЕНО"', out)
        self.assertIn('title\t"ПРОДЮСЕР"', out)
        self.assertIn('name "Jane Doe"', out)

    def test_names_are_never_addressable(self):
        with self.assertRaises(ValueError):
            credits.apply(self.SOURCE.encode("utf-8"), {3: "Хтось"})


if __name__ == "__main__":
    unittest.main()
