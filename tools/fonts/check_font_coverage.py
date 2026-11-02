"""
Scans release/STUFF/TEXT/*.TXT and TRC.CSV for characters not present in the
patched Font 1 mapping table. Run after build_release.py.
"""
import sys
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
from ua.formats.fnt import FntFile  # noqa: E402

FONT = paths.BUILD / "fonts/font1/PC_FONT_PC.FNT"
OUT_TEXT = paths.BUILD / "uap-unpacked/STUFF/TEXT"


def main():
    f = FntFile(str(FONT))
    entries = f.list_mapping()
    supported = {e.codepoint for e in entries}
    print(f"Font supports {len(supported)} codepoints")

    # Known, deliberate exceptions: `~0ý~~`-style markup in ID 1455 is an
    # Xbox-Guide-button placeholder the game substitutes at render time, not
    # literal text — and that whole string is Xbox-only (unreachable on the
    # PC Steam build we target). Documented in README rather than "fixed".
    KNOWN_EXCEPTIONS = {"~"}

    problems = {}
    for path in sorted(OUT_TEXT.glob("*")):
        if path.suffix.upper() not in (".TXT", ".CSV"):
            continue
        if path.suffix.upper() == ".TXT":
            # Use the structural parser so the format's own delimiter quotes
            # aren't flagged as if they were rendered game text.
            import txt_format  # noqa: E402
            entries = txt_format.parse_file(path)
            text = "".join(e.text for e in entries if e.matched)
        else:
            # CSV delimiter quotes and other-language columns are not rendered
            # by the localized English PC slot.
            import trc_csv
            text = "".join(value for label, value in trc_csv.read_labels(path).items()
                           if label.startswith(("GEN_", "PC_")))
        missing = set()
        for ch in text:
            cp = ord(ch)
            if cp < 0x20 or ch in "\r\n\t" or ch in KNOWN_EXCEPTIONS:
                continue
            if cp not in supported:
                missing.add(ch)
        if missing:
            problems[path.name] = sorted(missing)

    pc_path = REPO / "translations/pc_menu_ua.json"
    pc_strings = json.loads(pc_path.read_text(encoding="utf-8"))
    if set(pc_strings) != {str(i) for i in range(38)}:
        raise ValueError("PC menu translation must contain exactly IDs 0..37")
    pc_missing = {ch for value in pc_strings.values() for ch in value
                  if ord(ch) >= 0x20 and ord(ch) not in supported}
    if pc_missing:
        problems[pc_path.name] = sorted(pc_missing)
    if not problems:
        print("OK: no unsupported characters found in release text or the 38 PC menu strings.")
    else:
        print("Characters NOT covered by the patched font, found in:")
        for name, chars in problems.items():
            print(f"  {name}: {''.join(chars)!r}")
    return problems


if __name__ == "__main__":
    main()
