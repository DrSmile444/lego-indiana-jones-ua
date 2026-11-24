"""Shows every character of the built Font 1 and Font 2 in the running game, five main-menu lines at a time.

Needs a test-mode install (`python -m ua install --game DIR --test-mode`) and UA_STEAM_GAME.
For each run the tool writes a copy of build/UKRAINIAN.uap with four ENGLISH.TXT menu
strings and one PC menu string replaced by charset lines into the game's scripts/ folder;
for Font 2 the package also serves Font 2 in place of every Font 1 file. It starts the
game in a background window (tools/runtime/live.py), presses ENTER through the intro until
the title logo shows, opens the main menu and takes the frame: build/screens/charset-<n>.png.
The installed package is restored at the end.

    python tools/fonts/show_charset.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ua import paths  # noqa: E402
from ua.formats import uap  # noqa: E402
from ua.pipeline import font_hd  # noqa: E402

TEXT_IDS = (701, 702, 53, 712)  # ENGLISH.TXT strings on the main menu; PC menu string 1 is the fifth line
PER_LINE = 24
FONT1 = [f"{paths.TEXT_DIR}/{n}" for n in paths.FONT1_FILES]
FONT2 = f"{paths.TEXT_DIR}/FONT2_PC.FNT"


def logo(image: Image.Image) -> float:
    """Share of the red title logo pixels in its box."""
    w, h = image.size
    box = image.crop((int(w * .08), int(h * .08), int(w * .29), int(h * .46))).resize((60, 70)).getdata()
    return sum(1 for r, g, b in box if r > 190 and g < 60 and b < 60) / len(box)


def charset(data: bytes) -> str:
    font = font_hd._font(data)
    chars = {chr(e.codepoint) for e in font.list_mapping()}
    return "".join(sorted(c for c in chars if c.isprintable() and c not in ' "'))


def package(items: list[tuple[str, bytes]], lines: list[str], font2: bool) -> bytes:
    built = dict(items)
    text = built[paths.ENGLISH_TXT].decode("utf-8")
    for tid, line in zip(TEXT_IDS, lines):
        text = re.sub(rf'\n{tid} "[^"\r\n]*"', lambda m: f'\n{tid} "{line}"', text)
    menu = built[paths.PC_MENU].split(b"\0")
    if len(lines) > len(TEXT_IDS):
        menu[1] = lines[len(TEXT_IDS)].encode("utf-8")
    out = []
    for name, data in items:
        if name == paths.ENGLISH_TXT:
            data = text.encode("utf-8")
        elif name == paths.PC_MENU:
            data = b"\0".join(menu)
        elif font2 and name in FONT1:
            data = built[FONT2]
        out.append((name, data))
    return uap.pack(out)


def main_menu(live, tries: int = 40) -> bool:
    """Press ENTER through the intro until the title logo shows, then open the main menu."""
    for _ in range(tries):
        time.sleep(3)
        if logo(Image.open(live.shot("charset-probe")).convert("RGB")) > .35:
            time.sleep(4)
            live.keys(["ENTER"])
            time.sleep(5)
            return True
        live.keys(["ENTER"])
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--uap", default=str(paths.BUILD / "UKRAINIAN.uap"))
    args = parser.parse_args()
    if not os.environ.get("UA_STEAM_GAME"):
        sys.exit("Set UA_STEAM_GAME to the Steam game folder (test-mode install).")
    from tools.runtime import live

    items = uap.read(Path(args.uap).read_bytes())
    built = dict(items)
    runs = []
    for font2, name in ((False, FONT1[-1]), (True, FONT2)):
        chars = charset(built[name])
        lines = [chars[i:i + PER_LINE] for i in range(0, len(chars), PER_LINE)]
        runs += [(font2, lines[i:i + len(TEXT_IDS) + 1]) for i in range(0, len(lines), len(TEXT_IDS) + 1)]
    installed = live.GAME_DIR / "scripts" / "UKRAINIAN.uap"
    backup = installed.read_bytes()
    try:
        for run, (font2, lines) in enumerate(runs):
            live.stop()
            installed.write_bytes(package(items, lines, font2))
            live.start()
            ok = main_menu(live)
            shot = live.shot(f"charset-{run}")
            print(f"run {run} font {2 if font2 else 1}: {'menu' if ok else 'NO MENU'} {shot}", lines, flush=True)
    finally:
        live.stop()
        installed.write_bytes(backup)
        (live.OUT / "charset-probe.png").unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
