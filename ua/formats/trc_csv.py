"""
Parser/writer for STUFF/TEXT/TRC.CSV — a UTF-16LE CSV table with columns
LABEL, ENGLISH, FRENCH, ITALIAN, GERMAN, SPANISH, AMERICAN, DANISH.

This is a separate string table from ENGLISH.TXT (different LABEL ids, no
overlap confirmed), used for UI strings that ran out of space in the main
table (see ENGLISH.TXT comment "TRCs ran out of space - continued at 1450").

Encoding: UTF-16LE with BOM (confirmed via `file`).
"""
from __future__ import annotations

import csv
from pathlib import Path

HEADER = ["LABEL", "ENGLISH", "FRENCH", "ITALIAN", "GERMAN", "SPANISH", "AMERICAN", "DANISH"]


def read_rows(path: str | Path) -> list[list[str]]:
    with open(path, "r", encoding="utf-16", newline="") as f:
        reader = csv.reader(f)
        return list(reader)


def read_labels(path: str | Path) -> dict[str, str]:
    """label -> ENGLISH column text, skipping header/blank rows."""
    rows = read_rows(path)
    out = {}
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        label = row[0]
        english = row[1] if len(row) > 1 else ""
        out[label] = english
    return out


def write_translated(src_path: str | Path, translations: dict[str, str], out_path: str | Path,
                      target_column: str = "ENGLISH") -> dict:
    """
    Replace `target_column` for each row whose LABEL is a key in `translations`.
    Preserves every other column and every row untouched otherwise.
    """
    rows = read_rows(src_path)
    if not rows:
        raise ValueError(f"{src_path}: no rows parsed")
    header = rows[0]
    try:
        col_idx = header.index(target_column)
    except ValueError:
        raise ValueError(f"{src_path}: column {target_column!r} not found in header {header!r}")

    translated_count = 0
    kept = []
    seen_labels = set()
    out_rows = [header]
    for row in rows[1:]:
        if not row or not row[0]:
            out_rows.append(row)
            continue
        label = row[0]
        seen_labels.add(label)
        row = list(row) + [""] * (len(header) - len(row))
        if label in translations:
            row[col_idx] = translations[label]
            translated_count += 1
        else:
            kept.append(label)
        out_rows.append(row)

    unknown_labels = sorted(set(translations.keys()) - seen_labels)

    # Match the source file's own convention (confirmed by inspecting the
    # original): non-empty cells are quoted, empty trailing cells are bare
    # commas (not ""), unlike csv.QUOTE_ALL. Build lines manually so the
    # output stays byte-compatible with whatever lenient parser the game uses.
    def format_cell(v: str) -> str:
        if v == "":
            return ""
        escaped = v.replace('"', '""')
        return f'"{escaped}"'

    lines = [",".join(format_cell(c) for c in row) for row in out_rows]
    out_text = "\r\n".join(lines) + "\r\n"

    with open(out_path, "w", encoding="utf-16", newline="") as f:
        f.write(out_text)

    return {
        "translated": translated_count,
        "kept_english": kept,
        "unknown_labels": unknown_labels,
        "total_rows": len(seen_labels),
    }


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    rows = read_rows(p)
    print(f"{p}: {len(rows)} rows (incl. header), header={rows[0]}")
    labels = read_labels(p)
    print(f"{len(labels)} labeled rows")
