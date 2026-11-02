import struct
import unittest

from rename_saved_custom_characters import (
    renamed, with_names, checksum, SAVE_SIZE, CHECKSUM_OFFSET, NAME_OFFSETS, NAME_SIZE,
)


class SavedNamesTests(unittest.TestCase):
    def test_explicit_two_names_preserve_progress(self):
        source = renamed(self.fixture())
        result = with_names(source, ('Форелька', 'Льоля'))
        allowed = set(range(CHECKSUM_OFFSET, CHECKSUM_OFFSET + 4))
        for offset, expected in zip(NAME_OFFSETS, ('Форелька', 'Льоля')):
            self.assertEqual(result[offset:offset+32].split(b'\0')[0].decode(), expected)
            allowed.update(range(offset, offset+32))
        self.assertTrue(all(i in allowed for i, (a,b) in enumerate(zip(source,result)) if a != b))
        self.assertEqual(checksum(result), struct.unpack_from('<I',result,CHECKSUM_OFFSET)[0])

    def fixture(self):
        data = bytearray(SAVE_SIZE)
        data[:4] = b'HMGR'
        for index, offset in enumerate(NAME_OFFSETS, 1):
            name = f'Stranger {index}'.encode() + b'\0'
            data[offset:offset+len(name)] = name
            data[offset+NAME_SIZE:offset+NAME_SIZE+4] = b'\x01\x00\x01\x00'
        struct.pack_into('<I', data, CHECKSUM_OFFSET, checksum(data))
        return data

    def test_only_names_and_checksum_change(self):
        source = self.fixture()
        result = renamed(source)
        allowed = set(range(CHECKSUM_OFFSET, CHECKSUM_OFFSET+4))
        for index, offset in enumerate(NAME_OFFSETS, 1):
            self.assertEqual(result[offset:offset+NAME_SIZE].split(b'\0')[0].decode(), f'Форелька {index}')
            allowed.update(range(offset, offset+NAME_SIZE))
        self.assertEqual(len(source), len(result))
        self.assertTrue(all(i in allowed for i, (a, b) in enumerate(zip(source, result)) if a != b))
        self.assertEqual(struct.unpack_from('<I', result, CHECKSUM_OFFSET)[0], checksum(result))

    def test_rejects_invalid_original_checksum(self):
        source = self.fixture()
        source[9000] = 1
        with self.assertRaisesRegex(ValueError, 'checksum'):
            renamed(source)

    def test_preserves_user_custom_name_by_refusing_update(self):
        source = self.fixture()
        source[NAME_OFFSETS[0]] = ord('X')
        struct.pack_into('<I', source, CHECKSUM_OFFSET, checksum(source))
        with self.assertRaisesRegex(ValueError, 'preserve custom name'):
            renamed(source)


if __name__ == '__main__':
    unittest.main()
