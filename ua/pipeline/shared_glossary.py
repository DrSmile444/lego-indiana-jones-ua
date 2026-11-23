"""Shared terminology rules of the LEGO localizations, vendored from the lego-ua-glossary repository."""
from __future__ import annotations

import importlib.util

from .. import paths

VENDOR = paths.REPO / "vendor" / "lego-ua-glossary"


def check(pairs, game: str) -> list[str]:
    """pairs: (where, english, ukrainian); english may be empty when the game is not extracted."""
    spec = importlib.util.spec_from_file_location("lego_ua_glossary", VENDOR / "lego_ua_glossary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check(pairs, game)
