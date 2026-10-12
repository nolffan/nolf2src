#!/usr/bin/env python3
"""Write a short-format COFF import library for a few functions of one DLL.

VC6's own import libraries predate DirectX 7: its ddraw.lib has no
DirectDrawCreateEx, which the shipped d3d.ren imports from DDRAW.dll (its
import table lists DirectDrawCreateEx, DirectDrawEnumerateA and
DirectDrawCreate). This writes the missing import the way any SDK import
library carries it: one short import member per function (the format VC6's
LINK reads in its own ddraw.lib), plus the two archive linker members. The
DLL's import descriptor and null thunk still come from the stock library
linked alongside it, so this library adds imports and nothing else -- no
code, no data.

Each function is given as its decorated C name; the imported name is the
undecorated one (IMPORT_NAME_UNDECORATE), exactly as the SDK libraries do it:
`_DirectDrawCreateEx@16` imports `DirectDrawCreateEx`.

With --keep-decoration the imported name is the decorated symbol itself
(IMPORT_NAME): `_AIL_startup@0` imports `_AIL_startup@0`. Miles' mss32.dll
exports its stdcall functions under the full decorated names, and the shipped
lithtech.exe imports them that way; an undecorated import name resolves to
nothing and Wine binds a stub that aborts on the first call.

Usage:
  mkimplib.py [--keep-decoration] <out.lib> <DLL name> <_decorated@N>...
"""
import struct
import sys

MACHINE_I386 = 0x14C
IMPORT_CODE = 0
IMPORT_NAME = 1
IMPORT_NAME_UNDECORATE = 3
NAME_TYPE = IMPORT_NAME_UNDECORATE


def header(name, size):
    h = b"%-16s%-12s%-6s%-6s%-8s%-10d`\n" % (name.encode(), b"0", b"", b"",
                                            b"0", size)
    assert len(h) == 60
    return h


def short_import(sym, dll):
    data = sym.encode() + b"\0" + dll.encode() + b"\0"
    kind = IMPORT_CODE | (NAME_TYPE << 2)
    return struct.pack("<HHHHIIHH", 0, 0xFFFF, 0, MACHINE_I386, 0, len(data),
                       0, kind) + data


def main():
    global NAME_TYPE
    if "--keep-decoration" in sys.argv:
        sys.argv.remove("--keep-decoration")
        NAME_TYPE = IMPORT_NAME
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    out, dll, syms = sys.argv[1], sys.argv[2], sys.argv[3:]
    members = [(dll + "/", short_import(s, dll), [s, "__imp_" + s])
               for s in syms]
    names = [(n, i) for i, (_, _, ns) in enumerate(members) for n in ns]

    def linker_sizes():
        first = 4 + 4 * len(names) + sum(len(n) + 1 for n, _ in names)
        second = (4 + 4 * len(members) + 4 + 2 * len(names)
                  + sum(len(n) + 1 for n, _ in names))
        return first, second

    first_sz, second_sz = linker_sizes()
    pos = 8 + 60 + first_sz + (first_sz & 1) + 60 + second_sz + (second_sz & 1)
    offsets = []
    for _, body, _ in members:
        offsets.append(pos)
        pos += 60 + len(body) + (len(body) & 1)

    first = struct.pack(">I", len(names)) + b"".join(
        struct.pack(">I", offsets[i]) for _, i in names) + b"".join(
        n.encode() + b"\0" for n, _ in names)
    srt = sorted(names)
    second = (struct.pack("<I", len(members))
              + b"".join(struct.pack("<I", o) for o in offsets)
              + struct.pack("<I", len(srt))
              + b"".join(struct.pack("<H", i + 1) for _, i in srt)
              + b"".join(n.encode() + b"\0" for n, _ in srt))
    assert (len(first), len(second)) == (first_sz, second_sz)

    blob = b"!<arch>\n"
    for name, body in [("/", first), ("/", second)] + \
            [(m, b) for m, b, _ in members]:
        blob += header(name, len(body)) + body + (b"\n" if len(body) & 1 else b"")
    open(out, "wb").write(blob)
    print(f"{out}: {len(syms)} import(s) from {dll}")


if __name__ == "__main__":
    main()
