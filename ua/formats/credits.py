"""ENGLISH_CREDITS.TXT / PC_ENGLISH_CREDITS.TXT.

Format: `keyword "text"` lines (heading/title/name/company/credit) plus
`colour`/`duration` configuration lines, UTF-8 with BOM and CRLF. There are no
IDs, so translations are addressed by 1-based line number. Only `heading` and
`title` lines (section headings and job titles) are translated; `name` and
`company` lines (real people, studios) are never touched.
"""
from __future__ import annotations

import re

LINE_RE = re.compile(r'^(?P<indent>\s*)(?P<kw>heading|title)(?P<pad>\s+)"(?P<text>[^"]*)"(?P<trailing>.*)$')
BOM = b"\xef\xbb\xbf"


def _split(data: bytes) -> tuple[bool, str, list[str], bool]:
    has_bom = data.startswith(BOM)
    text = data[len(BOM):].decode("utf-8") if has_bom else data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return has_bom, newline, text.splitlines(), text.endswith(newline)


def translatable_lines(data: bytes) -> dict[int, tuple[str, str]]:
    """1-based line number -> (keyword, text) for every heading/title line."""
    _, _, lines, _ = _split(data)
    result = {}
    for number, line in enumerate(lines, 1):
        match = LINE_RE.match(line)
        if match:
            result[number] = (match.group("kw"), match.group("text"))
    return result


def apply(data: bytes, values: dict[int, str]) -> bytes:
    """Replace the quoted text of the given heading/title lines."""
    has_bom, newline, lines, trailing_newline = _split(data)
    unknown = set(values)
    for number, line in enumerate(lines, 1):
        if number not in values:
            continue
        match = LINE_RE.match(line)
        if not match:
            raise ValueError(f"Line {number} is not a heading/title line")
        if '"' in values[number]:
            raise ValueError(f"Line {number}: quotes are not allowed in credits text")
        lines[number - 1] = (f'{match.group("indent")}{match.group("kw")}{match.group("pad")}'
                             f'"{values[number]}"{match.group("trailing")}')
        unknown.discard(number)
    if unknown:
        raise ValueError(f"Unknown credits lines: {sorted(unknown)[:10]}")
    out = newline.join(lines) + (newline if trailing_newline else "")
    return (BOM if has_bom else b"") + out.encode("utf-8")


def translate_by_title(data: bytes, titles: dict[str, str]) -> bytes:
    """Translate an original English credits file by exact heading/title text."""
    numbers = {n: titles[text] for n, (_, text) in translatable_lines(data).items() if text in titles}
    return apply(data, numbers)
