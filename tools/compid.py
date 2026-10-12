#!/usr/bin/env python3
"""Read the `@comp.id` symbol out of COFF objects and MS .lib archives.

Every object MSVC emits carries an absolute symbol named `@comp.id` whose
value's low sixteen bits are the compiler's *build* number — 8168, 8447, 8804
and so on. For a shipped static library that is direct, unambiguous evidence
of which compiler built it, where a PE image only has its Rich header and an
object inside an image has nothing at all.

Usage:
  compid.py <file.lib|file.obj> [...]

  compid.py "$NOLF2_SOURCE"/LT2/lithshared/libs/Release/*.lib   # the shipped libraries
  compid.py src/lithshared/out/*.lib                          # ours
"""
import glob
import os
import struct
import sys
import tempfile

HERE = __file__.rsplit("/", 1)[0]
sys.path.insert(0, HERE)
from libextract import extract                       # noqa: E402


def comp_ids(data):
    """Every distinct @comp.id value in one COFF object."""
    if len(data) < 20:
        return set()
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from(
        "<HHIIIHH", data, 0)
    if machine != 0x14C or not nsyms:
        return set()
    strtab = data[symoff + nsyms * 18:]
    out = set()
    i = 0
    while i < nsyms:
        s = symoff + i * 18
        raw = data[s:s + 8]
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            end = strtab.find(b"\0", off)
            name = strtab[off:end].decode("latin-1")
        else:
            name = raw.rstrip(b"\0").decode("latin-1")
        if name == "@comp.id":
            out.add(struct.unpack_from("<I", data, s + 8)[0])
        i += 1 + data[s + 17]           # skip aux records
    return out


def report(path):
    ids = set()
    if path.lower().endswith(".lib"):
        with tempfile.TemporaryDirectory() as td:
            extract(path, td)
            for m in sorted(glob.glob(td + "/*")):
                ids |= comp_ids(open(m, "rb").read())
    else:
        ids = comp_ids(open(path, "rb").read())
    if not ids:
        print(f"{os.path.basename(path):<28} no @comp.id")
        return
    for v in sorted(ids):
        print(f"{os.path.basename(path):<28} 0x{v:06x}  build {v & 0xffff}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        report(p)
