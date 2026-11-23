"""Shared terminology checks for the Ukrainian localizations of TT Games LEGO games.

Each game repository keeps a copy of this file and glossary.json in vendor/lego-ua-glossary/
and calls check() from `python -m ua validate`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

GLOSSARY = Path(__file__).with_name("glossary.json")


def _norm(text: str) -> str:
    return " ".join(text.replace("'", "’").split())


def load(path: Path = GLOSSARY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(pairs: Iterable[tuple[str, str, str]], game: str, glossary: dict | None = None) -> list[str]:
    """Return one message per rule violation.

    pairs: (where, english, ukrainian) for every translated string of the game.
    game: "saga", "indy" or "lsw3"; rules with a "games" list apply only to those games.
    """
    glossary = glossary or load()
    ui = [r for r in glossary["ui"] if game in r.get("games", [game])]
    forbid = [r for r in glossary["forbid"] if game in r.get("games", [game])]
    ui_rx = [(r, re.compile(r["en"], re.I), re.compile(r["uk"], re.I)) for r in ui]
    forbid_rx = [(r, re.compile(r["uk"], 0 if r.get("case") else re.I)) for r in forbid]
    problems = []
    for where, english, ukrainian in pairs:
        if not ukrainian:
            continue
        en, uk = _norm(english), _norm(ukrainian)
        for rule, en_rx, uk_rx in ui_rx:
            if en_rx.search(en) and not uk_rx.search(uk):
                problems.append(f"{where}: {english!r} -> {ukrainian!r}; glossary expects {rule['use']!r} ({rule['decision']})")
        for rule, uk_rx in forbid_rx:
            match = uk_rx.search(uk)
            if match:
                problems.append(f"{where}: {match.group(0)!r} in {ukrainian[:80]!r}; glossary: {rule['use']} ({rule['decision']})")
    return problems
