"""Read-only comparison of all main text IDs and PC text in an isolated game."""
import argparse
import csv
import ctypes as c
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ua import paths  # noqa: E402
from verify_pc_menu_dll import verify


def audit(pid, expect_original=False):
    kernel = c.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [c.c_uint32, c.c_int, c.c_uint32]
    kernel.OpenProcess.restype = c.c_void_p
    kernel.ReadProcessMemory.argtypes = [c.c_void_p, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
    kernel.ReadProcessMemory.restype = c.c_int
    kernel.CloseHandle.argtypes = [c.c_void_p]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        raise c.WinError(c.get_last_error())

    def read(address, size):
        buffer = c.create_string_buffer(size)
        got = c.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size, c.byref(got)) or got.value != size:
            raise c.WinError(c.get_last_error())
        return buffer.raw

    try:
        if expect_original:
            functions = {0x6B44F0: "81ec04010000", 0x6B46D0: "578b7c2408",
                         0x6B4750: "51a1d837b000", 0x6B7440: "a1d037b000",
                         0x6B0250: "8b4424043d00100000", 0x6B55A0: "518b442408"}
            original_hooks = all(read(address, len(bytes.fromhex(code))) == bytes.fromhex(code)
                                 for address, code in functions.items())
            audited = json.loads((paths.NATIVE / "asi/pc_menu_table.json").read_text(encoding="utf-8"))
            expected = {row['id']: int(row['va'], 16) for row in audited['rows']}
            checked = 0
            for address in (0x921D10, 0x921E48):
                for key, pointer in struct.iter_unpack("<II", read(address, 38 * 8)):
                    if pointer != expected[key]:
                        raise ValueError("PC table changed despite rejected package")
                    checked += 1
            if not original_hooks:
                raise ValueError("Resource code changed despite rejected package")
            return dict(rejected_pack_keeps_original_code=True, original_pc_pointers_verified=checked)
        table, = struct.unpack("<I", read(0xA90268, 4))
        print("Main table", hex(table))
        pointers = struct.unpack("<1805I", read(table, 1805 * 4))
        source = json.loads((ROOT / "translations/english_txt_ua.json").read_text(encoding="utf-8"))
        passed, mismatches = 0, []
        for key, value in source.items():
            index = int(key)
            expected = value.encode("utf-8") + b"\0"
            pointer = pointers[index]
            if pointer and read(pointer, len(expected)) == expected:
                passed += 1
            else:
                mismatches.append(dict(id=index, pointer=hex(pointer), expected=value,
                                       actual=read(pointer, min(len(expected), 120)).split(b"\0")[0].decode("utf-8", "replace") if pointer else None))
        def string(address):
            data = bytearray()
            for n in range(8192):
                byte = read(address + n, 1)
                if byte == b"\0":
                    return data.decode("utf-8")
                data.extend(byte)
            raise ValueError("Unterminated text")

        trc = {}
        for slot in range(3):
            address, count, _ = struct.unpack("<III", read(0xB03848 + slot * 12, 12))
            if not count:
                continue
            if count > 10000:
                raise ValueError("Invalid CSV label count")
            for label, value in struct.iter_unpack("<II", read(address, count * 8)):
                if label and value:
                    trc[string(label)] = string(value)
        csv_bytes = (paths.BUILD / "uap-unpacked/STUFF/TEXT/TRC.CSV").read_bytes()
        csv_text = csv_bytes.decode("utf-16" if csv_bytes[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig")
        rows = list(csv.DictReader(csv_text.splitlines()))
        csv_expected = {row['LABEL']: row['ENGLISH'] for row in rows if row['ENGLISH']}
        csv_mismatches = [dict(label=key, expected=value, actual=trc.get(key))
                          for key, value in csv_expected.items() if trc.get(key) != value]
        return dict(main_strings_verified=passed, main_strings_total=len(source), mismatches=mismatches,
                    csv_strings_total=len(csv_expected), csv_strings_verified=len(csv_expected)-len(csv_mismatches),
                    csv_mismatches=csv_mismatches)
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-original", action="store_true")
    parser.add_argument("--exe", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.pid, args.expect_original)
    if not args.expect_original:
        try:
            report["pc_menu"] = verify(args.exe, args.pid)
        except ValueError as error:
            report["pc_menu_error"] = str(error)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != 'pc_menu'}, ensure_ascii=False))
    if not args.expect_original and (report['mismatches'] or report['csv_mismatches'] or 'pc_menu_error' in report):
        raise SystemExit(1)
