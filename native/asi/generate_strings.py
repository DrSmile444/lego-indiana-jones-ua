"""Generate UTF-8 C literals and validated Steam addresses from tracked inputs."""
import json
from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[2]
audit = json.loads((Path(__file__).with_name("pc_menu_table.json")).read_text(encoding="utf-8"))
translations = json.loads((repo / "translations/pc_menu_ua.json").read_text(encoding="utf-8"))
if set(translations) != {str(i) for i in range(38)}:
    raise ValueError("Expected exactly PC IDs 0..37")
rows = sorted(audit["rows"], key=lambda row: row["id"])
if [row["id"] for row in rows] != list(range(38)):
    raise ValueError("Invalid audited PC table")
for value in translations.values():
    if not isinstance(value, str) or not value or "\0" in value or "\n" in value or "\r" in value:
        raise ValueError("Expected nonempty, single-line strings without NUL")


def literal(value):
    return '"' + ''.join(f"\\{byte:03o}" for byte in value.encode("utf-8")) + '"'


lines = ["// Generated; edit translations/pc_menu_ua.json instead.",
         "static const unsigned char expected_sha256[32] = {" +
         ','.join(f"0x{b:02x}" for b in bytes.fromhex(audit["exe_sha256"])) + "};",
         "static const unsigned long original_rva[38] = {" +
         ','.join(hex(int(row["va"], 16) - int(audit["image_base"], 16)) for row in rows) + "};",
         "static const char *const original_text[38] = {" +
         ',\n'.join(literal(row["text"]) for row in rows) + "};",
         "static const char *const ukrainian_text[38] = {" +
         ',\n'.join(literal(translations[str(i)]) for i in range(38)) + "};"]
Path(sys.argv[1]).write_text('\n'.join(lines) + '\n', encoding="ascii")
