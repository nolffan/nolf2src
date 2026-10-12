#!/usr/bin/env python3
"""Write a COFF object of full-length vtables for stand-in classes.

Why: much of the engine is reconstructed through stand-in ("view") classes
that declare only the one or two virtual slots their own code touches. Their
constructors are byte-identical -- the vptr store's relocation is masked --
but the table they install is the stand-in's, one or two slots long, where
the shipped table has dozens. The game DLLs call through the shipped layout
(the SDK headers), so the first call past the stand-in's last slot runs
whatever follows it in .rdata.

How: VC6 emits every vtable as a pick-any COMDAT (IMAGE_COMDAT_SELECT_ANY)
in each object that needs it, and LINK keeps the FIRST definition it reads.
This object defines the same `??_7Class@@6B@` symbols as pick-any COMDATs
holding the shipped table, slot for slot, as relocations against our real
member functions; linked ahead of the compiled objects, its copy is the one
kept. No code changes, so nothing byte-identical moves.

Input (src/engine/lithtech/link/vtables.txt):

    # comment
    vtable ??_7CPhysicsLTQ404@@6B@        0x004a1770
        ?GetFrictionCoefficient@CommonPhysicsLT@@UAEKPAVLTObject@@AAM@Z
        ...

One slot per line, in order. A slot may be `0x<hex>` for a literal dword
(nothing in this project should need it). Symbols are external references;
an unresolved one is a link error like any other.

Lines between `%ifdef NAME` and `%endif` count only when `--define NAME` is
given: build/engine.sh passes `--define NOLF2SRC_MODERN` in the modern build
(build/variant.sh), whose ILTClient has slots the retail one does not. Without
it they are skipped, so the release build's object is the same as ever.

Usage:
  mkvtabobj.py [--define NAME]... <spec.txt> <out.obj>
"""
import struct
import sys

EXTERNAL, STATIC = 2, 3
DIR32 = 6
# IMAGE_SCN_CNT_INITIALIZED_DATA | LNK_COMDAT | ALIGN_4BYTES | MEM_READ
RDATA_COMDAT = 0x00000040 | 0x00001000 | 0x00300000 | 0x40000000
SELECT_ANY = 2


def parse(path, defines=()):
    tabs = []
    skip = None          # outside %ifdef: None; inside: True to skip, False to keep
    for line in open(path, errors="replace"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        w = line.split()
        if w[0] == "%ifdef":
            if skip is not None or len(w) != 2:
                sys.exit("%s: bad or nested %%ifdef: %s" % (path, line))
            skip = w[1] not in defines
            continue
        if w[0] == "%endif":
            if skip is None:
                sys.exit("%s: %%endif without %%ifdef" % path)
            skip = None
            continue
        if skip:
            continue
        if w[0] == "vtable":
            tabs.append((w[1], []))
        else:
            tabs[-1][1].append(w[0])
    return tabs


def main():
    args = sys.argv[1:]
    defines = []
    while len(args) >= 2 and args[0] == "--define":
        defines.append(args[1])
        args = args[2:]
    if len(args) != 2:
        sys.exit(__doc__)
    sys.argv[1:] = args
    tabs = parse(sys.argv[1], defines)
    missing = [(n, s) for n, sl in tabs for s in sl if s == "MISSING"]
    if missing:
        sys.exit("%s: %d MISSING slot(s) (first in %s) -- every slot needs a "
                 "function" % (sys.argv[1], len(missing), missing[0][0]))

    strtab = bytearray(b"\0\0\0\0")

    def name_field(n):
        b = n.encode("latin-1")
        if len(b) <= 8:
            return b.ljust(8, b"\0")
        off = len(strtab)
        strtab.extend(b + b"\0")
        return b"\0\0\0\0" + struct.pack("<I", off)

    nsec = len(tabs)
    # symbol table: per section [section sym + aux, vtable sym], then externs
    syms = []
    ext_index = {}
    ext_list = []
    for _n, slots in tabs:
        for s in slots:
            if not s.startswith("0x") and s not in ext_index:
                ext_index[s] = None
                ext_list.append(s)
    nlocal = 3 * nsec
    for i, s in enumerate(ext_list):
        ext_index[s] = nlocal + i

    hdr_size = 20 + 40 * nsec
    data = bytearray()
    sechdrs = []
    for si, (name, slots) in enumerate(tabs, 1):
        raw = bytearray()
        rels = bytearray()
        for k, s in enumerate(slots):
            if s.startswith("0x"):
                raw += struct.pack("<I", int(s, 16))
            else:
                raw += b"\0\0\0\0"
                rels += struct.pack("<IIH", 4 * k, ext_index[s], DIR32)
        rawp = hdr_size + len(data)
        data += raw
        relp = hdr_size + len(data) if rels else 0
        data += rels
        sechdrs.append(b".rdata\0\0" + struct.pack(
            "<IIIIIIHHI", 0, 0, len(raw), rawp, relp, 0,
            len(rels) // 10, 0, RDATA_COMDAT))
        # section symbol + aux (length, nrelocs, nlines, checksum, assoc, sel)
        syms.append(b".rdata\0\0" + struct.pack("<IhHBB", 0, si, 0, STATIC, 1))
        syms.append(struct.pack("<IHHIHB", len(raw), len(rels) // 10, 0, 0, 0,
                                SELECT_ANY) + b"\0\0\0")
        syms.append(name_field(name) + struct.pack("<IhHBB", 0, si, 0,
                                                   EXTERNAL, 0))
    for s in ext_list:
        syms.append(name_field(s) + struct.pack("<IhHBB", 0, 0, 0x20,
                                                EXTERNAL, 0))
    struct.pack_into("<I", strtab, 0, len(strtab))
    symoff = hdr_size + len(data)
    nsyms = len(syms)
    hdr = struct.pack("<HHIIIHH", 0x14C, nsec, 0, symoff, nsyms, 0, 0)
    with open(sys.argv[2], "wb") as f:
        f.write(hdr + b"".join(sechdrs) + bytes(data) + b"".join(syms)
                + bytes(strtab))
    print("%s: %d vtables, %d slots, %d distinct targets" % (
        sys.argv[2], nsec, sum(len(s) for _n, s in tabs), len(ext_list)))


if __name__ == "__main__":
    main()
