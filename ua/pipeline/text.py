"""Text level: apply translations/*.json to the text resources of a template.

The template is a list of UAP resources (normally the baseline release). Fonts
and textures pass through untouched; only text resources are regenerated.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .. import paths
from ..formats import credits, trc_csv, txt
from ..util import UaError, read_json

PC_MENU_COUNT = 38


def load_translations() -> dict:
    root = paths.TRANSLATIONS
    return {
        "english": {int(k): v for k, v in read_json(root / "english_txt_ua.json").items()},
        "trc": read_json(root / "trc_csv_ua.json"),
        "credits": {name: {int(k): v for k, v in values.items()}
                    for name, values in read_json(root / "credits_ua.json").items()},
        "pc_menu": read_json(root / "pc_menu_ua.json"),
    }


def _via_file(data: bytes, transform) -> tuple[bytes, dict]:
    with tempfile.TemporaryDirectory() as work:
        source, target = Path(work) / "in", Path(work) / "out"
        source.write_bytes(data)
        report = transform(source, target)
        return target.read_bytes(), report


def english_txt(data: bytes, values: dict[int, str], overlay: bool = False) -> bytes:
    """ENGLISH.TXT gets every ID; AMERICAN.TXT is an overlay and gets only its own IDs."""
    if overlay:
        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / "in"
            source.write_bytes(data)
            own = txt.ids(source)
        missing = sorted(own - set(values))
        if missing:
            raise UaError(f"AMERICAN.TXT: IDs without translation: {missing}")
        values = {k: v for k, v in values.items() if k in own}
    out, report = _via_file(data, lambda s, t: txt.write_translated(s, values, t, allow_missing=False))
    if report["unknown_ids"]:
        raise UaError(f"ENGLISH.TXT: IDs not present in the template: {report['unknown_ids'][:10]}")
    return out


def trc(data: bytes, values: dict[str, str]) -> bytes:
    """Write the translation into every English-language column (UK and US locale)."""
    for column in paths.TRC_COLUMNS:
        data, report = _via_file(data, lambda s, t, c=column: trc_csv.write_translated(s, values, t, target_column=c))
        if report["unknown_labels"]:
            raise UaError(f"TRC.CSV: labels not present in the template: {report['unknown_labels'][:10]}")
    return data


def pc_menu(values: dict[str, str]) -> bytes:
    missing = [i for i in range(PC_MENU_COUNT) if str(i) not in values]
    if missing or len(values) != PC_MENU_COUNT:
        raise UaError(f"pc_menu_ua.json must contain IDs 0..{PC_MENU_COUNT - 1}; missing {missing}")
    return b"".join(values[str(i)].encode("utf-8") + b"\0" for i in range(PC_MENU_COUNT))


def apply(resources: list[tuple[str, bytes]], translations: dict | None = None) -> list[tuple[str, bytes]]:
    """Return a new resource list with every text resource regenerated."""
    tr = translations or load_translations()
    credit_names = {f"{paths.TEXT_DIR}/{name}": values for name, values in tr["credits"].items()}
    result, handled = [], set()
    for name, data in resources:
        if name == paths.ENGLISH_TXT:
            data = english_txt(data, tr["english"])
        elif name == paths.AMERICAN_TXT:
            data = english_txt(data, tr["english"], overlay=True)
        elif name == paths.TRC_CSV:
            data = trc(data, tr["trc"])
        elif name in credit_names:
            data = credits.apply(data, credit_names[name])
        elif name == paths.PC_MENU:
            data = pc_menu(tr["pc_menu"])
        else:
            result.append((name, data))
            continue
        handled.add(name)
        result.append((name, data))
    expected = {paths.ENGLISH_TXT, paths.AMERICAN_TXT, paths.TRC_CSV, paths.PC_MENU, *credit_names}
    if handled != expected:
        raise UaError(f"Template is missing text resources: {sorted(expected - handled)}")
    return result
