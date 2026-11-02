"""Prepare a copy of the verified PC SaveGame0 with two renamed defaults.

Only 32-byte name fields and the checksum change. Original save is never
written by this tool. The additive checksum parameters were cross-checked
with LEGO Games save file checksum updater and the untouched user's save.
"""
import argparse
from pathlib import Path
import struct

SAVE_SIZE = 40880
CHECKSUM_OFFSET = 40872
NAME_OFFSETS = (0x9D8C, 0x9DC4)
NAME_SIZE = 32


def checksum(data):
    return (6031769 + sum(value for value, in struct.iter_unpack('<I', data[8232:CHECKSUM_OFFSET]))) & 0xFFFFFFFF


def with_names(data, names):
    if len(data) != SAVE_SIZE or data[:4] != b'HMGR':
        raise ValueError('Unsupported save layout')
    if struct.unpack_from('<I', data, CHECKSUM_OFFSET)[0] != checksum(data):
        raise ValueError('Original save checksum mismatch')
    result = bytearray(data)
    if len(names) != 2:
        raise ValueError('Exactly two names required')
    for text, offset in zip(names, NAME_OFFSETS):
        if not text or '\0' in text:
            raise ValueError('Invalid name')
        name = text.encode('utf-8') + b'\0'
        if len(name) > NAME_SIZE:
            raise ValueError('Name exceeds fixed save field')
        result[offset:offset + NAME_SIZE] = name.ljust(NAME_SIZE, b'\0')
    struct.pack_into('<I', result, CHECKSUM_OFFSET, checksum(result))
    return bytes(result)


def renamed(data):
    # Legacy migration only accepts untouched English defaults.
    with_names(data, ('Форелька 1', 'Форелька 2'))
    for number, offset in enumerate(NAME_OFFSETS, 1):
        current = data[offset:offset + NAME_SIZE].split(b'\0', 1)[0]
        if current != f'Stranger {number}'.encode('ascii'):
            raise ValueError(f'Slot {number} is not the expected default; preserve custom name')
    return with_names(data, ('Форелька 1', 'Форелька 2'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    updated = renamed(args.source.read_bytes())
    with args.output.open('xb') as stream:
        stream.write(updated)
    print('Prepared two names and a valid checksum; source save unchanged.')
