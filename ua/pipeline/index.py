"""String index: IDs, platform markers, tokens and font character sets.

Generated once from the baseline release (`python -m ua index`) and committed.
It holds no game text, so CI can validate translations without game files.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from .. import paths
from ..formats import credits, fnt, trc_csv, txt
from ..util import write_json

TOKEN_RE = re.compile(r"\[[^\]]+\]|%(?:\d+\$)?[diusf]")


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def _temp(data: bytes) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False)
    handle.write(data)
    handle.close()
    return Path(handle.name)


def _font_chars(data: bytes) -> str:
    path = _temp(data)
    try:
        entries = fnt.FntFile(str(path)).list_mapping()
    finally:
        path.unlink()
    return "".join(sorted({chr(e.codepoint) for e in entries}))


def build(resources: list[tuple[str, bytes]], translations: dict) -> dict:
    res = dict(resources)
    english = {}
    path = _temp(res[paths.ENGLISH_TXT])
    try:
        for entry in txt.parse_file(path):
            if entry.matched:
                pc = bool(txt.ENTRY_RE.match(entry.raw).group("pcmarker"))
                english[str(entry.id)] = {"pc": pc, "tokens": tokens(entry.text)}
    finally:
        path.unlink()

    path = _temp(res[paths.TRC_CSV])
    try:
        rows = trc_csv.read_labels(path)
    finally:
        path.unlink()
    trc = {label: {"translate": label in translations["trc"],
                   "tokens": tokens(translations["trc"].get(label, ""))} for label in rows}

    credit_index = {}
    for name in paths.CREDITS:
        short = name.rsplit("/", 1)[1]
        values = translations["credits"].get(short, {})
        credit_index[short] = {str(n): {"kw": kw, "translate": n in values}
                               for n, (kw, _) in credits.translatable_lines(res[name]).items()}

    return {
        "english_txt": english,
        "trc_csv": trc,
        "credits": credit_index,
        "pc_menu": {"count": 38},
        "fonts": {"font1": _font_chars(res[f"{paths.TEXT_DIR}/PC_FONT_PC.FNT"]),
                  "font2": _font_chars(res[f"{paths.TEXT_DIR}/FONT2_PC.FNT"])},
    }


def write(index: dict) -> list[Path]:
    written = []
    for key, value in index.items():
        target = paths.INDEX / f"{key}.json"
        write_json(target, value)
        written.append(target)
    return written


def load() -> dict:
    from ..util import read_json
    return {p.stem: read_json(p) for p in sorted(paths.INDEX.glob("*.json"))}
