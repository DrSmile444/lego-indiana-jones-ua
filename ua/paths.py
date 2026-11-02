"""Repository zones. Every tool resolves inputs through these names.

Environment variables override the defaults so a game copy or donor folder can
live outside the repository:
    UA_GAME_DIR    extracted DAT archives          (default: game/)
    UA_LOCAL_DIR   donors, fonts, baselines, notes (default: local/)
    UA_STEAM_GAME  installed Steam copy            (no default; pass --game)
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _env_dir(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).resolve() if value else default


GAME = _env_dir("UA_GAME_DIR", REPO / "game")
LOCAL = _env_dir("UA_LOCAL_DIR", REPO / "local")
BUILD = REPO / "build"
DIST = REPO / "dist"

DONORS = LOCAL / "donors"
FONTS = LOCAL / "fonts"
BASELINES = LOCAL / "baseline"
TOOLS_BIN = LOCAL / "tools"

TRANSLATIONS = REPO / "translations"
INDEX = REPO / "index"
ASSETS = REPO / "assets"
MANIFESTS = REPO / "manifests"
NATIVE = REPO / "native"

# Resource paths inside the game data and inside UKRAINIAN.uap.
TEXT_DIR = "STUFF/TEXT"
ENGLISH_TXT = f"{TEXT_DIR}/ENGLISH.TXT"
# With an en-US system locale (e.g. Proton on Steam Deck) the game reads AMERICAN.TXT
# on top of ENGLISH.TXT, the AMERICAN column of TRC.CSV and AMERICAN_CREDITS.TXT.
AMERICAN_TXT = f"{TEXT_DIR}/AMERICAN.TXT"
TRC_CSV = f"{TEXT_DIR}/TRC.CSV"
CREDITS = (f"{TEXT_DIR}/ENGLISH_CREDITS.TXT", f"{TEXT_DIR}/PC_ENGLISH_CREDITS.TXT",
           f"{TEXT_DIR}/AMERICAN_CREDITS.TXT")
TRC_COLUMNS = ("ENGLISH", "AMERICAN")
# Text resources added after the 0.1.10 baseline; until the baseline contains them,
# their template is taken once from the extracted game (game/).
ADDED_TEXT = (AMERICAN_TXT, f"{TEXT_DIR}/AMERICAN_CREDITS.TXT")
PC_MENU = "UKRAINIAN/PC_MENU.UTF8"
FONT1_FILES = ("FONT_PC.FNT", "PC_FONT.FNT", "PC_FONT_NGC.FNT", "PC_FONT_PC.FNT")
FONT2_FILES = ("FONT2.FNT", "FONT2_NGC.FNT", "FONT2_PC.FNT")


def game_file(relative: str) -> Path:
    """Locate a resource inside the extracted game (any DAT subfolder)."""
    direct = GAME / relative
    if direct.exists():
        return direct
    matches = sorted(GAME.glob("*/" + relative))
    if len(matches) != 1:
        raise FileNotFoundError(f"{relative}: expected one match under {GAME}, found {len(matches)}."
                                " Run: python -m ua extract --game <Steam folder>")
    return matches[0]
