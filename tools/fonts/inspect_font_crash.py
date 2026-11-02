"""Read a local x86 Windows minidump without installing a debugger.

Print only exception, registers, relevant stack addresses and disassembly.
Requires capstone for disassembly; does not change the dump or game.
"""
import argparse
import struct
from pathlib import Path


class Dump:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        if self.data[:4] != b"MDMP":
            raise ValueError("Not a Windows minidump")
        count, directory = self.unpack("II", 8)
        self.streams = {}
        for i in range(count):
            kind, size, rva = self.unpack("III", directory + i * 12)
            self.streams[kind] = (rva, size)
        self.modules = []
        rva, _ = self.streams[4]
        for i in range(self.unpack("I", rva)[0]):
            p = rva + 4 + i * 108
            base, size, _, _, name = self.unpack("QIIII", p)
            length = self.unpack("I", name)[0]
            text = self.data[name + 4:name + 4 + length].decode("utf-16-le")
            self.modules.append((base, size, text))
        self.memory = []
        if 9 in self.streams:
            rva, _ = self.streams[9]
            count, file_offset = self.unpack("QQ", rva)
            for i in range(count):
                address, size = self.unpack("QQ", rva + 16 + i * 16)
                self.memory.append((address, size, file_offset))
                file_offset += size
        if 5 in self.streams:
            rva, _ = self.streams[5]
            for i in range(self.unpack("I", rva)[0]):
                address, size, offset = self.unpack("QII", rva + 4 + i * 16)
                self.memory.append((address, size, offset))

    def unpack(self, fmt, offset):
        return struct.unpack_from("<" + fmt, self.data, offset)

    def read(self, address, size):
        for start, length, offset in self.memory:
            if start <= address and address + size <= start + length:
                return self.data[offset + address - start:offset + address - start + size]
        return b""

    def label(self, address):
        for base, size, name in self.modules:
            if base <= address < base + size:
                return f"{Path(name).name}+0x{address-base:x}"
        return ""

    def exception(self):
        rva, _ = self.streams[6]
        thread = self.unpack("I", rva)[0]
        code = self.unpack("I", rva + 8)[0]
        address = self.unpack("Q", rva + 24)[0]
        count = self.unpack("I", rva + 32)[0]
        params = self.unpack("Q" * count, rva + 40)
        size, context = self.unpack("II", rva + 160)
        regs = dict(zip(("edi", "esi", "ebx", "edx", "ecx", "eax", "ebp", "eip"), self.unpack("8I", context + 156)))
        regs["esp"] = self.unpack("I", context + 196)[0]
        print(f"thread={thread} exception=0x{code:08x} address=0x{address:08x} {self.label(address)}")
        print("parameters:", [hex(p) for p in params])
        print("registers:", {k: hex(v) for k, v in regs.items()})
        for offset in range(0, 160, 4):
            raw = self.read(regs["esp"] + offset, 4)
            if raw:
                value = struct.unpack("<I", raw)[0]
                label = self.label(value)
                if label:
                    print(f"esp+0x{offset:02x}: 0x{value:08x} {label}")
        self.disassemble(address - 24, 80)
        return regs

    def disassemble(self, address, size):
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        for instruction in Cs(CS_ARCH_X86, CS_MODE_32).disasm(self.read(address, size), address):
            print(f"0x{instruction.address:08x}: {instruction.mnemonic} {instruction.op_str}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump")
    parser.add_argument("--address", type=lambda x: int(x, 0))
    parser.add_argument("--size", type=int, default=160)
    args = parser.parse_args()
    dump = Dump(args.dump)
    if args.address is None:
        dump.exception()
    else:
        dump.disassemble(args.address, args.size)


if __name__ == "__main__":
    main()
