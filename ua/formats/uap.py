"""UAP1 resource package read by UKRAINIAN.asi.

Layout (little endian):
    8-byte magic  b"UAP1\\r\\n\\x1a\\0"
    u32 count
    count * (256-byte NUL-padded ASCII path, u32 offset, u32 size, SHA-256)
    payloads

Identical payloads are stored once and shared by several entries. Entry order
is significant for byte-for-byte reproduction and is always preserved.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path, PurePosixPath

MAGIC = b"UAP1\r\n\x1a\0"
ENTRY = struct.Struct("<256sII32s")
MAX_ENTRIES = 64


def read(data: bytes) -> list[tuple[str, bytes]]:
    """Parse and fully verify a package; return (path, payload) in index order."""
    if len(data) < 12 or data[:8] != MAGIC:
        raise ValueError("Invalid UAP1 header")
    count, = struct.unpack_from("<I", data, 8)
    end = 12 + count * ENTRY.size
    if not 0 < count <= MAX_ENTRIES or end > len(data):
        raise ValueError("Invalid entry count")
    result: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for raw, offset, size, digest in ENTRY.iter_unpack(data[12:end]):
        if b"\0" not in raw:
            raise ValueError("Unterminated entry name")
        name = raw.split(b"\0", 1)[0].decode("ascii")
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or "\\" in name or ":" in name
                or any(part in ("", ".", "..") for part in name.split("/")) or name.upper() in seen):
            raise ValueError(f"Unsafe or duplicate path: {name}")
        if offset < end or not size or offset + size > len(data):
            raise ValueError(f"Invalid payload bounds: {name}")
        payload = data[offset:offset + size]
        if hashlib.sha256(payload).digest() != digest:
            raise ValueError(f"Payload hash mismatch: {name}")
        seen.add(name.upper())
        result.append((name, payload))
    return result


def pack(items: list[tuple[str, bytes]]) -> bytes:
    """Build a package; shared payloads are deduplicated in first-seen order."""
    if not 0 < len(items) <= MAX_ENTRIES:
        raise ValueError("Invalid entry count")
    offset = 12 + len(items) * ENTRY.size
    index, payloads, seen = [], [], {}
    for name, data in items:
        encoded = name.encode("ascii")
        if len(encoded) >= 256:
            raise ValueError(f"Path too long: {name}")
        if data not in seen:
            seen[data] = offset
            payloads.append(data)
            offset += len(data)
        index.append(ENTRY.pack(encoded, seen[data], len(data), hashlib.sha256(data).digest()))
    return MAGIC + struct.pack("<I", len(items)) + b"".join(index + payloads)


def unpack_to(data: bytes, destination: Path) -> int:
    """Verify the whole package first, then extract into a new directory."""
    items = read(data)
    destination.mkdir(parents=True, exist_ok=False)
    for name, payload in items:
        target = destination.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return len(items)
