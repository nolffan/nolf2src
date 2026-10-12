#!/usr/bin/env python3
"""Check the constants that byte-matching cannot see.

exematch masks every byte a relocation covers, which is what lets an
unrelocated object be compared against a linked image at all. The cost is
that anything reached *through* a relocation is invisible to it: a float
literal lives in .rdata and is loaded by address, so `+= 0.001f` and
`+= 1.0f` produce identical maskable bytes and the oracle calls both a
match. One such error sat in CNetMgr::AddRecvBytes for months and was
found only by accident.

This closes that hole. For every function of ours that exematch places in
the image, it walks the object's relocations, and where one points at a
read-only constant in our object it reads the matching address out of the
shipped image and compares the constant itself.

Usage:
  fpconst.py <image> <obj|dir>...            e.g.
  fpconst.py out/reference/server.dll src/engine/server/Release
"""
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402

# x87 loads whose operand width we can state from the opcode alone. The
# modrm byte's reg field selects the operation; only the width matters here.
W4 = {0xD8, 0xD9}          # fadds/fsubs/fmuls/fdivs/fcomps/flds  -> dword
W8 = {0xDC, 0xDD}          # faddl/.../fldl/fcompl                -> qword


def sections(data):
    """[(name, vsize, rawsize, rawptr)] plus the symbol table, from a COFF."""
    nsec, symoff, nsyms, optsz = struct.unpack_from("<HxxxxIIH", data, 2)
    secs = []
    for i in range(nsec):
        s = 20 + optsz + i * 40
        name = data[s:s + 8].rstrip(b"\0").decode("latin-1")
        vsize, _va, rawsz, rawp = struct.unpack_from("<IIII", data, s + 8)
        relp, _lnp, nrel = struct.unpack_from("<IIH", data, s + 24)
        flags = struct.unpack_from("<I", data, s + 36)[0]
        secs.append((name, rawsz, rawp, relp, nrel, flags))
    return secs, symoff, nsyms


def const_at(data, secs, symoff, nsyms, symidx, addend, width):
    """The `width` bytes our object holds for relocation target symidx."""
    e = symoff + symidx * 18
    if e + 18 > len(data):
        return None
    value, secnum = struct.unpack_from("<Ih", data, e + 8)
    if secnum <= 0 or secnum > len(secs):
        return None
    name, rawsz, rawp, _rp, _nr, flags = secs[secnum - 1]
    if not flags & 0x40:            # IMAGE_SCN_CNT_INITIALIZED_DATA
        return None
    if flags & 0x80000000:          # writable: not a literal pool
        return None
    off = rawp + value + addend
    if off < rawp or off + width > rawp + rawsz:
        return None
    return data[off:off + width]


def func_syms(data, secs, symoff, nsyms):
    """[(name, section_index, offset_in_section)] for defined code symbols.

    Needed because a relocation's address is relative to its own section, and
    a function is only the whole of its section under /Gy. Attributing every
    section's relocations to every function -- which the first version of this
    did -- cross-attributes constants between unrelated functions and invents
    mismatches. So each symbol is tied to the section it is defined in.
    """
    strtab = data[symoff + nsyms * 18:]
    out, i = [], 0
    while i < nsyms:
        e = symoff + i * 18
        raw = data[e:e + 8]
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            name = strtab[off:strtab.find(b"\0", off)].decode("latin-1")
        else:
            name = raw.rstrip(b"\0").decode("latin-1")
        value, secnum, _typ, storage, naux = struct.unpack_from("<IhHBB", data, e + 8)
        if 0 < secnum <= len(secs) and storage in (2, 6):
            if secs[secnum - 1][5] & 0x20:      # code section
                out.append((name, secnum, value))
        i += 1 + naux
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    pe = Pe(sys.argv[1])
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]

    def img_read(va, n):
        for _nm, (sva, svs, srp) in pe.secs.items():
            if sva <= va < sva + svs:
                o = srp + (va - sva)
                return pe.d[o:o + n]
        return None

    objs = []
    for a in sys.argv[2:]:
        objs += sorted(glob.glob(os.path.join(a, "*.obj"))) if os.path.isdir(a) else [a]

    checked = bad = 0
    for path in objs:
        data = open(path, "rb").read()
        try:
            fns = parse_obj_masked(data)
            secs, symoff, nsyms = sections(data)
        except Exception:
            continue
        home = {n: (si, val) for n, si, val in func_syms(data, secs, symoff, nsyms)}
        relbysec = {}
        for si, (name, rawsz, rawp, relp, nrel, flags) in enumerate(secs, 1):
            if not flags & 0x20 or not relp:
                continue
            relbysec[si] = [struct.unpack_from("<IIH", data, relp + i * 10)
                            for i in range(nrel)]

        for sym, (code, mask) in fns.items():
            if len(code) - len(mask) < 8 or sym not in home:
                continue
            si, symval = home[sym]
            hits = list(find(text, tva, code, mask))
            if len(hits) != 1:
                continue                     # ambiguous or absent: not ours to judge
            base = hits[0]
            for vaddr, symidx, _typ in relbysec.get(si, []):
                fn_off = vaddr - symval
                if not (0 <= fn_off < len(code)) or fn_off not in mask:
                    continue
                op = code[fn_off - 2] if fn_off >= 2 else 0
                width = 4 if op in W4 else 8 if op in W8 else 0
                if not width:
                    continue
                ours = const_at(data, secs, symoff, nsyms, symidx, 0, width)
                if ours is None:
                    continue
                va = struct.unpack_from("<I", text, base - tva + fn_off)[0]
                theirs = img_read(va, width)
                if not theirs or len(theirs) != width:
                    continue
                checked += 1
                if ours != theirs:
                    bad += 1
                    f = "<f" if width == 4 else "<d"
                    print(f"MISMATCH {os.path.basename(path)} {sym}")
                    print(f"    +0x{fn_off:x} operand at 0x{va:08x}: "
                          f"ours {struct.unpack(f, ours)[0]!r} "
                          f"ship {struct.unpack(f, theirs)[0]!r}")
    print(f"\n{checked} floating-point operand(s) behind masked relocations "
          f"checked, {bad} mismatched")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
