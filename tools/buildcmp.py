#!/usr/bin/env python3
"""Compare two sets of build outputs, ignoring only what changes every build.

A change to how the game is built (build/build.mk, the scripts) must not
change what it builds. This compares two directories of build outputs --
two snapshots of the same files -- byte for byte, after blanking the fields
that VC6's tools fill with the time of the run:

  .obj        the COFF header's TimeDateStamp
  .lib        each archive member's date, and the TimeDateStamp of every
              object or short import record inside it
  PE images   the COFF header's TimeDateStamp and the optional header's
              CheckSum; the export and resource directories' TimeDateStamp;
              each debug directory entry's TimeDateStamp and, in a CodeView
              NB10 record, the .pdb's signature (also a time)
  .map        the "Timestamp is ..." line

and skipping what has no stable form at all: .pdb, .idb and .pch files (the
objects and images built with them are still compared). Everything else --
.res, link reports, MANIFEST.txt -- must match exactly.

  tools/buildcmp.py <dir-a> <dir-b>

Prints each file that differs (or is in only one of the two) and exits 1 if
there is any; else prints the count of files compared and exits 0.
"""
import os
import re
import struct
import sys

SKIP_EXT = (".pdb", ".idb", ".pch")


def blank(buf, off, n):
    if 0 <= off and off + n <= len(buf):
        buf[off:off + n] = b"\0" * n


def norm_coff_obj(buf, base=0):
    # IMAGE_FILE_HEADER: Machine(2) NumberOfSections(2) TimeDateStamp(4)
    blank(buf, base + 4, 4)


def norm_import_record(buf, base):
    # IMPORT_OBJECT_HEADER: Sig1(2)=0 Sig2(2)=0xffff Version(2) Machine(2)
    # TimeDateStamp(4)
    blank(buf, base + 8, 4)


def norm_lib(buf):
    if not buf.startswith(b"!<arch>\n"):
        return
    off = 8
    while off + 60 <= len(buf):
        hdr = buf[off:off + 60]
        try:
            size = int(hdr[48:58].decode("ascii").strip())
        except ValueError:
            return
        blank(buf, off + 16, 12)            # member date
        body = off + 60
        name = hdr[:16]
        if name not in (b"/               ", b"//              "):
            sig = struct.unpack_from("<HH", buf, body) if body + 4 <= len(buf) else (1, 1)
            if sig == (0, 0xFFFF):
                norm_import_record(buf, body)
            elif sig[0] == 0x14C:
                norm_coff_obj(buf, body)
        off = body + size + (size & 1)


def rva_to_off(sections, rva):
    for va, vsize, raw, rawsize in sections:
        if va <= rva < va + max(vsize, rawsize):
            return raw + (rva - va)
    return None


def norm_resource_dir(buf, base, off, depth=0):
    if depth > 4 or off + 16 > len(buf):
        return
    blank(buf, off + 4, 4)
    named, ids = struct.unpack_from("<HH", buf, off + 12)
    for i in range(named + ids):
        e = off + 16 + 8 * i
        if e + 8 > len(buf):
            return
        _, target = struct.unpack_from("<II", buf, e)
        if target & 0x80000000:
            norm_resource_dir(buf, base, base + (target & 0x7FFFFFFF), depth + 1)


def norm_pe(buf):
    if buf[:2] != b"MZ" or len(buf) < 0x40:
        return
    pe = struct.unpack_from("<I", buf, 0x3C)[0]
    if buf[pe:pe + 4] != b"PE\0\0":
        return
    coff = pe + 4
    nsec, = struct.unpack_from("<H", buf, coff + 2)
    blank(buf, coff + 4, 4)                 # TimeDateStamp
    optsize, = struct.unpack_from("<H", buf, coff + 16)
    opt = coff + 20
    blank(buf, opt + 64, 4)                 # CheckSum
    ndirs, = struct.unpack_from("<I", buf, opt + 92)
    dirs = [struct.unpack_from("<II", buf, opt + 96 + 8 * i) for i in range(min(ndirs, 16))]
    sections = []
    sec = opt + optsize
    for i in range(nsec):
        s = sec + 40 * i
        vsize, va, rawsize, raw = struct.unpack_from("<IIII", buf, s + 8)
        sections.append((va, vsize, raw, rawsize))
    if len(dirs) > 0 and dirs[0][0]:        # exports
        o = rva_to_off(sections, dirs[0][0])
        if o is not None:
            blank(buf, o + 4, 4)
    if len(dirs) > 2 and dirs[2][0]:        # resources
        o = rva_to_off(sections, dirs[2][0])
        if o is not None:
            norm_resource_dir(buf, o, o)
    if len(dirs) > 6 and dirs[6][0]:        # debug directory
        o = rva_to_off(sections, dirs[6][0])
        if o is not None:
            for i in range(dirs[6][1] // 28):
                e = o + 28 * i
                blank(buf, e + 4, 4)
                size, _, ptr = struct.unpack_from("<III", buf, e + 16)
                if buf[ptr:ptr + 4] == b"NB10":
                    blank(buf, ptr + 8, 4)  # the .pdb signature: a time


MAP_TIMESTAMP = re.compile(rb"^ *Timestamp is .*$", re.M)


def normalised(path):
    with open(path, "rb") as f:
        buf = bytearray(f.read())
    ext = os.path.splitext(path)[1].lower()
    if ext == ".obj":
        norm_coff_obj(buf)
    elif ext == ".lib":
        norm_lib(buf)
    elif ext in (".exe", ".dll", ".ren", ".lto"):
        norm_pe(buf)
    elif ext == ".map":
        return MAP_TIMESTAMP.sub(b"", bytes(buf))
    return bytes(buf)


def files(root):
    out = set()
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.lower().endswith(SKIP_EXT):
                out.add(os.path.relpath(os.path.join(d, f), root))
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    a, b = sys.argv[1:]
    fa, fb = files(a), files(b)
    bad = 0
    for rel in sorted(fa | fb):
        if rel not in fb:
            print(f"only in {a}: {rel}"); bad += 1; continue
        if rel not in fa:
            print(f"only in {b}: {rel}"); bad += 1; continue
        x, y = normalised(os.path.join(a, rel)), normalised(os.path.join(b, rel))
        if x != y:
            first = next((i for i in range(min(len(x), len(y))) if x[i] != y[i]), min(len(x), len(y)))
            print(f"DIFFERS: {rel} (sizes {len(x)} / {len(y)}, first difference at 0x{first:x})")
            bad += 1
    if bad:
        print(f"{bad} of {len(fa | fb)} files differ")
        return 1
    print(f"identical: {len(fa | fb)} files (timestamps aside)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
