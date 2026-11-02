"""
Parser/writer for TT Games' STUFF/TEXT/<LANG>.TXT localization format.

Format (observed in LEGO Indiana Jones: The Original Adventures, ENGLISH.TXT):
    ;                              <- comment line
    ; Section header               <- comment line
    ;
    49 "Screen V-Sync"             <- id, quoted string
    1270 pc "Control Setup"        <- id, optional platform marker, quoted string
    88 "Posted" ;was "Available to Buy"   <- id, string, trailing comment (kept verbatim)

The quoted text is matched greedily: on a translated line a trailing comment
that itself contains quotes is replaced together with the text. All releases
have this shape, and byte-identical rebuilds depend on it.

This module treats every line as opaque text by default and only replaces the
quoted string content for lines matching an id, so comments, blank lines,
platform markers, and trailing inline comments are preserved exactly as-is.

Encoding: ENGLISH.TXT is UTF-8 with BOM, CRLF line endings (confirmed via
`file` on the extracted original). Always read/write with encoding="utf-8-sig"
and newline="" to keep CRLF intact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ENTRY_RE = re.compile(
    r'^(?P<indent>\s*)(?P<id>\d+)(?P<pcmarker>\s+pc)?(?P<pad>\s+)"(?P<text>.*)"(?P<trailing>.*)$'
)


@dataclass
class Entry:
    line_no: int
    id: int
    text: str
    raw: str
    matched: bool  # False for comments/blank lines/anything not matching ENTRY_RE


def _read_raw(path: str | Path) -> str:
    # newline="" disables Python's universal-newline translation so we can
    # detect/preserve the source file's actual CRLF vs LF line endings.
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return f.read()


def parse_file(path: str | Path) -> list[Entry]:
    text = _read_raw(path)
    lines = text.splitlines(keepends=False)
    entries = []
    for i, line in enumerate(lines):
        m = ENTRY_RE.match(line)
        if m:
            entries.append(Entry(line_no=i, id=int(m.group("id")), text=m.group("text"), raw=line, matched=True))
        else:
            entries.append(Entry(line_no=i, id=-1, text="", raw=line, matched=False))
    return entries


def ids(path: str | Path) -> set[int]:
    return {e.id for e in parse_file(path) if e.matched}


def write_translated(src_path: str | Path, translations: dict[int, str], out_path: str | Path,
                      allow_missing: bool = True) -> dict:
    """
    Replace the quoted text of every entry line whose id is in `translations`.
    Lines whose id has no translation are left untouched (kept in English) unless
    allow_missing=False, in which case a KeyError-style report is returned instead
    of writing partial output.

    Returns a report dict: {"translated": int, "kept_english": [ids], "unknown_ids": [ids in translations not found in src]}.
    """
    src_bytes = Path(src_path).read_bytes()
    has_bom = src_bytes.startswith(b"\xef\xbb\xbf")
    original_text = _read_raw(src_path)
    newline = "\r\n" if "\r\n" in original_text else "\n"

    entries = parse_file(src_path)
    src_ids = {e.id for e in entries if e.matched}
    unknown_ids = sorted(set(translations.keys()) - src_ids)
    kept_english = []

    out_lines = []
    for e in entries:
        if not e.matched:
            out_lines.append(e.raw)
            continue
        if e.id in translations:
            new_text = translations[e.id]
            m = ENTRY_RE.match(e.raw)
            new_line = f'{m.group("indent")}{m.group("id")}{m.group("pcmarker") or ""}{m.group("pad")}"{new_text}"{m.group("trailing")}'
            out_lines.append(new_line)
        else:
            kept_english.append(e.id)
            out_lines.append(e.raw)

    if not allow_missing and kept_english:
        raise ValueError(f"{len(kept_english)} ids have no translation and allow_missing=False: {kept_english[:20]}...")

    out_text = newline.join(out_lines)
    if out_lines and original_text.endswith(newline):
        out_text += newline

    out_bytes = out_text.encode("utf-8")
    if has_bom:
        out_bytes = b"\xef\xbb\xbf" + out_bytes
    Path(out_path).write_bytes(out_bytes)

    return {
        "translated": len(translations) - len(unknown_ids),
        "kept_english": kept_english,
        "unknown_ids": unknown_ids,
        "total_entries": len(src_ids),
    }


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    es = parse_file(p)
    matched = [e for e in es if e.matched]
    print(f"{p}: {len(es)} lines, {len(matched)} translatable entries, id range {min(e.id for e in matched)}-{max(e.id for e in matched)}")
