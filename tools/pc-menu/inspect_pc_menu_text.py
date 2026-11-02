"""Read-only audit of the separate PC menu string tables in LEGOIndy.exe.

Usage: python tools/inspect_pc_menu_text.py <exe> [--pid <running-game-pid>]
       [--output <report.json>]
Only --pid requires Windows and access to the running process. No game files
or process memory are written. Capstone, if available, adds disassembly.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct


STEAM_SHA256 = "c12f7348ec63aed61f56eb15d825f15b8340500668fa8c8dcf06c2f332e5e5fd"


def inspect(exe, pid=None):
    data = exe.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[:2] != b"MZ" or data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Expected a PE executable")
    count, = struct.unpack_from("<H", data, pe + 6)
    opt_size, = struct.unpack_from("<H", data, pe + 20)
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        raise ValueError("Expected a PE32 executable")
    base, = struct.unpack_from("<I", data, opt + 28)
    sections = []
    for i in range(count):
        start = opt + opt_size + i * 40
        _, rva, size, raw = struct.unpack_from("<IIII", data, start + 8)
        sections.append((rva, size, raw))

    def va_to_raw(va):
        for rva, size, raw in sections:
            if rva <= va - base < rva + size:
                return raw + va - base - rva
        raise ValueError(f"Unmapped address {va:#x}")

    def raw_to_va(offset):
        for rva, size, raw in sections:
            if raw <= offset < raw + size:
                return base + rva + offset - raw
        raise ValueError(f"Unmapped offset {offset:#x}")

    anchor = data.index(b"Quit to Windows\0")
    pointer = struct.pack("<I", raw_to_va(anchor))
    tables = []
    position = 0
    while (position := data.find(pointer, position)) != -1:
        start = position - 12  # ID 1's pointer follows ID 0's 8-byte record.
        position += 1
        try:
            rows = []
            for index in range(38):
                key, va = struct.unpack_from("<II", data, start + index * 8)
                raw = va_to_raw(va)
                end = data.index(b"\0", raw)
                rows.append({"id": key, "va": hex(va), "file_offset": hex(raw),
                             "text": data[raw:end].decode("utf-8")})
            if {row["id"] for row in rows} != set(range(38)):
                continue
            if struct.unpack_from("<II", data, start + 38 * 8) != (38, 0):
                continue
            tables.append({"file_offset": hex(start), "va": hex(raw_to_va(start)),
                           "rows": rows})
        except (ValueError, UnicodeDecodeError, struct.error):
            continue
    report = {"exe_sha256": hashlib.sha256(data).hexdigest(),
              "image_base": hex(base), "english_pc_tables": tables}
    if pid is None:
        return report
    if report["exe_sha256"] != STEAM_SHA256:
        raise ValueError("Runtime addresses are verified only for the recorded Steam build")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.POINTER(ctypes.c_size_t)]
    kernel.ReadProcessMemory.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        buf = ctypes.create_string_buffer(size)
        received = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buf, size, ctypes.byref(received)):
            raise ctypes.WinError(ctypes.get_last_error())
        if received.value != size:
            raise ValueError("Incomplete process memory read")
        return buf.raw

    try:
        for table in tables:
            raw = int(table["file_offset"], 16)
            if read(int(table["va"], 16), 312) != data[raw:raw + 312]:
                raise ValueError("Runtime table differs from the inspected executable")
        active = read(0x9D0C30, 152)
        lookup = {int(row["va"], 16): row for t in tables for row in t["rows"]}
        report["runtime"] = {"pid": pid, "active_table_va": "0x9d0c30", "rows": []}
        for key, (va,) in enumerate(struct.iter_unpack("<I", active)):
            row = lookup.get(va)
            text = None
            if row:
                expected = row["text"].encode("utf-8") + b"\0"
                if read(va, len(expected)) == expected:
                    text = row["text"]
            report["runtime"]["rows"].append({"id": key, "va": hex(va), "text": text})
        report["runtime"]["code"] = []
        for address, size in [(0x521230, 127), (0x4B1EF0, 22),
                              (0x620A10, 22), (0x6960B0, 22)]:
            code = read(address, size)
            entry = {"va": hex(address), "bytes": code.hex()}
            try:
                import capstone
                decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
                entry["disassembly"] = [f"{i.address:#x}: {i.mnemonic} {i.op_str}"
                                        for i in decoder.disasm(code, address)]
            except ImportError:
                pass
            report["runtime"]["code"].append(entry)
    finally:
        kernel.CloseHandle(handle)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(inspect(args.exe, args.pid), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result)
