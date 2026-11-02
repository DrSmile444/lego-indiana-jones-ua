"""Read-only check that all 38 PC strings in a running game match the DLL translation."""
import argparse
import ctypes as c
import json
from pathlib import Path
import struct

from inspect_pc_menu_text import inspect, STEAM_SHA256


def verify(exe, pid):
    audit = inspect(exe)
    if audit["exe_sha256"] != STEAM_SHA256:
        raise ValueError("Unsupported executable")
    repo = Path(__file__).resolve().parents[1]
    translations = json.loads((repo / "translations/pc_menu_ua.json").read_text(encoding="utf-8"))
    kernel = c.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [c.c_uint32, c.c_int, c.c_uint32]
    kernel.OpenProcess.restype = c.c_void_p
    kernel.ReadProcessMemory.argtypes = [c.c_void_p, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
    kernel.ReadProcessMemory.restype = c.c_int
    kernel.QueryFullProcessImageNameW.argtypes = [c.c_void_p, c.c_uint32, c.c_wchar_p, c.POINTER(c.c_uint32)]
    kernel.CloseHandle.argtypes = [c.c_void_p]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        raise c.WinError(c.get_last_error())

    def read(address, size):
        buf = c.create_string_buffer(size)
        received = c.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buf, size, c.byref(received)):
            raise c.WinError(c.get_last_error())
        if received.value != size:
            raise ValueError("Incomplete process read")
        return buf.raw

    try:
        path = c.create_unicode_buffer(32768)
        capacity = c.c_uint32(len(path))
        if not kernel.QueryFullProcessImageNameW(handle, 0, path, c.byref(capacity)):
            raise c.WinError(c.get_last_error())
        if Path(path.value).resolve() != exe.resolve():
            raise ValueError("PID belongs to a different executable")
        base = int(audit["image_base"], 16)
        if read(base, 2) != b"MZ":
            raise ValueError("Unexpected loaded image base")
        if struct.unpack("<I", read(base + 0x5D0CC8, 4))[0] != 1:
            raise ValueError("PC menu strings have not been initialized; open the main menu")
        groups = []
        for table in audit["english_pc_tables"]:
            entries = list(struct.iter_unpack("<II", read(int(table["va"], 16), 312)))
            if entries[-1] != (38, 0) or {k for k, _ in entries[:-1]} != set(range(38)):
                raise ValueError("Unexpected PC table IDs or terminator")
            groups.append(entries[:-1])
        groups.append(list(enumerate(struct.unpack("<38I", read(base + 0x5D0C30, 152)))))
        for entries in groups:
            for key, pointer in entries:
                expected = translations[str(key)].encode("utf-8") + b"\0"
                if read(pointer, len(expected)) != expected:
                    raise ValueError(f"PC ID {key} does not match its Ukrainian translation")
        return {"exe_sha256": audit["exe_sha256"], "source_pointers_verified": 76,
                "active_pointers_verified": 38, "utf8_strings_match": True,
                "rows": [{"id": i, "text": translations[str(i)]} for i in range(38)]}
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(verify(args.exe, args.pid), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
