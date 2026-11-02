"""Translation checks that need nothing but git: structure, tokens, glyphs, glossary."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import paths
from ..util import read_json
from . import index as string_index
from .text import PC_MENU_COUNT, load_translations

# Characters the engine handles itself or that never reach a glyph lookup.
CONTROL = set("\n\r\t")
# Kept from the original string: `~0ý~~` is an Xbox-only button control sequence
# that the PC build never renders.
KNOWN_EXCEPTIONS = {"ENGLISH.TXT 1455": set("~")}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def _check_text(report: Report, where: str, text: str, expected_tokens: list[str], charset: set[str]) -> None:
    if not isinstance(text, str) or not text.strip():
        report.error(f"{where}: empty translation")
        return
    if '"' in text:
        report.error(f"{where}: double quotes break the quoted game format")
    found = string_index.tokens(text)
    if sorted(found) != sorted(expected_tokens):
        report.error(f"{where}: tokens {found} differ from expected {expected_tokens}")
    plain = string_index.TOKEN_RE.sub("", text)
    allowed = KNOWN_EXCEPTIONS.get(where, set())
    missing = sorted({c for c in plain if c not in charset and c not in CONTROL and c not in allowed})
    if missing:
        report.error(f"{where}: characters missing from Font 1: {' '.join(repr(c) for c in missing)}")


def run() -> Report:
    report = Report()
    try:
        tr = load_translations()
        idx = string_index.load()
    except (OSError, ValueError) as error:
        report.error(f"cannot load translations or index: {error}")
        return report
    charset = set(idx["fonts"]["font1"])

    english_index = idx["english_txt"]
    for key in sorted(set(english_index) - {str(k) for k in tr["english"]}, key=int):
        report.error(f"ENGLISH.TXT {key}: missing translation")
    for key in sorted({str(k) for k in tr["english"]} - set(english_index), key=int):
        report.error(f"ENGLISH.TXT {key}: ID not in index")
    for key, text in tr["english"].items():
        if str(key) in english_index:
            _check_text(report, f"ENGLISH.TXT {key}", text, english_index[str(key)]["tokens"], charset)

    trc_index = idx["trc_csv"]
    for label, entry in trc_index.items():
        if entry["translate"] and label not in tr["trc"]:
            report.error(f"TRC.CSV {label}: missing translation")
    for label, text in tr["trc"].items():
        if label not in trc_index:
            report.error(f"TRC.CSV {label}: label not in index")
            continue
        _check_text(report, f"TRC.CSV {label}", text, trc_index[label]["tokens"], charset)

    for name, lines in idx["credits"].items():
        values = tr["credits"].get(name, {})
        for number, entry in lines.items():
            if entry["translate"] and int(number) not in values:
                report.error(f"{name} line {number}: missing translation")
        for number, text in values.items():
            if str(number) not in lines:
                report.error(f"{name} line {number}: not a heading/title line")
                continue
            _check_text(report, f"{name} line {number}", text, [], charset)

    for i in range(PC_MENU_COUNT):
        text = tr["pc_menu"].get(str(i))
        if text is None:
            report.error(f"PC menu {i}: missing translation")
        elif "\n" in text or "\0" in text:
            report.error(f"PC menu {i}: must be a single line without NUL")
        else:
            _check_text(report, f"PC menu {i}", text, [], charset)
    if len(tr["pc_menu"]) != PC_MENU_COUNT:
        report.error(f"PC menu: expected exactly {PC_MENU_COUNT} entries")

    _check_glossary(report, tr["english"])
    return report


def _check_glossary(report: Report, english: dict[int, str]) -> None:
    glossary = read_json(paths.TRANSLATIONS / "glossary.json")
    for category, terms in glossary.items():
        if category.startswith("_"):
            continue
        for term, entry in terms.items():
            if entry.get("confidence") != "team-approved":
                continue
            for string_id in entry.get("ids", []):
                text = english.get(int(string_id))
                if text is None:
                    report.warn(f"glossary {term}: ID {string_id} has no translation")
                elif entry["uk"].casefold() not in text.casefold():
                    report.warn(f"glossary {term}: ENGLISH.TXT {string_id} = {text!r}, expected form {entry['uk']!r}")


def glossary_ids_from_notes(glossary: dict) -> int:
    """One-time helper: copy 'ID 123' references from notes into an `ids` list."""
    added = 0
    for category, terms in glossary.items():
        if category.startswith("_"):
            continue
        for entry in terms.values():
            ids = sorted({int(n) for match in re.findall(r"\bIDs? ([\d/ ,]+)", entry.get("note", ""))
                          for n in re.findall(r"\d+", match)})
            if ids and "ids" not in entry:
                entry["ids"] = ids
                added += 1
    return added
