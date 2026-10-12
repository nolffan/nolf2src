#!/usr/bin/env python3
"""Write a COFF object that defines d3d.ren's "view regions": one shipped
object reached under several names at several offsets.

C++ cannot give one object two names at two offsets, and the d3d TUs do
exactly that: big26728.cpp copies the whole 0x4f8-byte view block
`XForm26728 g_1008b880` while thirty other TUs name its fields one by one
(g_nViewLeft at +0x1c, g_Mat1008b91c at +0x9c, g_v1008bd34 at +0x4b4 ...);
fifteen TUs index a [2][2] float table g_a1008e664 whose elements four others
name as g_1008e668/66c/670. Separate C++ definitions cannot stand for that --
and icl lays a TU's .bss out in REVERSE definition order, so separately
defined neighbours are not even adjacent in the shipped direction.

A COFF section can: one section per region, sized as the shipped object,
with an external symbol at each spelling's offset. The committed
src/engine/d3d/link/d3dviews.txt lists the regions; this turns that
into link/d3dviews.obj at d3d-link time (like aliases.rsp -> aliases.obj).

Input (d3dviews.txt):
    region <addr> <size> bss|data <section-alignment>
    sym <offset> <mangled name>          (an external definition)
    bytes <offset> <hex>                 (initial bytes, data regions only)
    reloc <offset> <symbol>              (a DIR32 to an external symbol)
Lines starting with # are comments.

Usage: mkviewobj.py <d3dviews.txt> <out.obj>
"""
import struct
import sys

EXTERNAL, STATIC = 2, 3
BSS = 0x00000080 | 0x40000000 | 0x80000000          # uninit | read | write
DATA = 0x00000040 | 0x40000000 | 0x80000000         # init   | read | write
ALIGN = {1: 0x00100000, 2: 0x00200000, 4: 0x00300000, 8: 0x00400000,
         16: 0x00500000, 32: 0x00600000}


def parse(path):
    regions = []
    for line in open(path):
        f = line.split()
        if not f or f[0].startswith("#"):
            continue
        if f[0] == "region":
            regions.append(dict(addr=int(f[1], 16), size=int(f[2], 16), kind=f[3],
                                align=int(f[4]), syms=[], data=None, relocs=[]))
            continue
        r = regions[-1]
        if f[0] == "sym":
            r["syms"].append((int(f[1], 16), f[2]))
        elif f[0] == "bytes":
            if r["data"] is None:
                r["data"] = bytearray(r["size"])
            o, b = int(f[1], 16), bytes.fromhex(f[2])
            r["data"][o:o + len(b)] = b
        elif f[0] == "reloc":
            r["relocs"].append((int(f[1], 16), f[2]))
        else:
            sys.exit(f"{path}: unknown line {line!r}")
    return regions


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    regions = parse(sys.argv[1])
    strtab = bytearray(b"\0\0\0\0")

    def name_field(n):
        b = n.encode("latin-1")
        if len(b) <= 8:
            return b.ljust(8, b"\0")
        off = len(strtab)
        strtab.extend(b + b"\0")
        return b"\0\0\0\0" + struct.pack("<I", off)

    nsec = len(regions)
    # symbol table: one section symbol (+aux) per region, then the external
    # definitions, then the undefined relocation targets
    syms, index = [], {}
    for i, r in enumerate(regions):
        name = ".bss" if r["kind"] == "bss" else ".data"
        syms.append(name_field(name) + struct.pack("<IhHBB", 0, i + 1, 0, STATIC, 1))
        syms.append(struct.pack("<IHHIHB", r["size"], len(r["relocs"]), 0, 0, 0, 0)
                    + b"\0" * 3)
    n = len(syms)
    seen = set()
    for i, r in enumerate(regions):
        for off, s in r["syms"]:
            if s in seen:
                sys.exit(f"{s} defined twice")
            seen.add(s)
            syms.append(name_field(s) + struct.pack("<IhHBB", off, i + 1, 0, EXTERNAL, 0))
            index[s] = n
            n += 1
    for r in regions:
        for _o, s in r["relocs"]:
            if s not in index:
                syms.append(name_field(s) + struct.pack("<IhHBB", 0, 0, 0, EXTERNAL, 0))
                index[s] = n
                n += 1
    struct.pack_into("<I", strtab, 0, len(strtab))

    # layout: header, section headers, raw data + relocations, symbols, strings
    pos = 20 + 40 * nsec
    shdrs, blobs = [], []
    for r in regions:
        ch = (BSS if r["kind"] == "bss" else DATA) | ALIGN[r["align"]]
        rawp = relp = 0
        blob = b""
        if r["kind"] == "data":
            rawp = pos
            blob = bytes(r["data"] if r["data"] is not None else bytearray(r["size"]))
            pos += len(blob)
            if r["relocs"]:
                relp = pos
                rel = b"".join(struct.pack("<IIH", o, index[s], 6) for o, s in r["relocs"])
                blob += rel
                pos += len(rel)
        name = b".bss\0\0\0\0" if r["kind"] == "bss" else b".data\0\0\0"
        shdrs.append(name + struct.pack("<IIIIIIHHI", 0, 0, r["size"], rawp, relp, 0,
                                        len(r["relocs"]), 0, ch))
        blobs.append(blob)
    hdr = struct.pack("<HHIIIHH", 0x14C, nsec, 0, pos, len(syms), 0, 0)
    with open(sys.argv[2], "wb") as f:
        f.write(hdr + b"".join(shdrs) + b"".join(blobs) + b"".join(syms) + bytes(strtab))
    print(f"{sys.argv[2]}: {nsec} view region(s), {len(seen)} names")


if __name__ == "__main__":
    main()
