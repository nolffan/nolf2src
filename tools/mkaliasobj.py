#!/usr/bin/env python3
"""Write a COFF object of weak externals: `alias -> target` pairs.

VC6's LINK.EXE has no /ALTERNATENAME. A COFF weak external does the same job
and every linker of that generation honours it: an undefined symbol with
storage class IMAGE_SYM_CLASS_WEAK_EXTERNAL and one aux record naming a
default symbol. If nothing else defines the alias, references to it resolve
to the default. Nothing else is emitted -- no sections, no code -- so the
object cannot change a byte of any function.

Input is a response file of `/ALTERNATENAME:alias=target` lines (the
src/engine/*/link/aliases.rsp files) or plain `alias=target` lines.

Usage:
  mkaliasobj.py <aliases.txt> <out.obj> [--characteristics=N]
      N: 1 NOLIBRARY, 2 LIBRARY, 3 ALIAS (default 3)
"""
import struct
import sys

WEAK = 105        # IMAGE_SYM_CLASS_WEAK_EXTERNAL
EXTERNAL = 2      # IMAGE_SYM_CLASS_EXTERNAL


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) for a in sys.argv[1:]
                if a.startswith("--") and "=" in a)
    if len(args) != 2:
        sys.exit(__doc__)
    ch = int(opts.get("--characteristics", "3"))
    pairs, seen = [], set()
    for line in open(args[0]):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("/ALTERNATENAME:"):
            line = line.split(":", 1)[1]
        a, t = line.split("=", 1)
        if a in seen or a == t:
            continue
        seen.add(a)
        pairs.append((a, t))

    strtab = bytearray(b"\0\0\0\0")

    def name_field(n):
        b = n.encode("latin-1")
        if len(b) <= 8:
            return b.ljust(8, b"\0")
        off = len(strtab)
        strtab.extend(b + b"\0")
        return b"\0\0\0\0" + struct.pack("<I", off)

    syms = []
    targets = {}                  # target name -> symbol-table index
    idx = 0
    for _a, t in pairs:
        if t not in targets:
            targets[t] = idx
            syms.append(name_field(t) + struct.pack("<IhHBB", 0, 0, 0,
                                                    EXTERNAL, 0))
            idx += 1
    for a, t in pairs:
        syms.append(name_field(a) + struct.pack("<IhHBB", 0, 0, 0, WEAK, 1))
        syms.append(struct.pack("<II", targets[t], ch) + b"\0" * 10)
        idx += 2
    struct.pack_into("<I", strtab, 0, len(strtab))

    hdr = struct.pack("<HHIIIHH", 0x14C, 0, 0, 20, idx, 0, 0)
    with open(args[1], "wb") as f:
        f.write(hdr + b"".join(syms) + bytes(strtab))
    print(f"{args[1]}: {len(pairs)} weak aliases onto {len(targets)} targets")


if __name__ == "__main__":
    main()
