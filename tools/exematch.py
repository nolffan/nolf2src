#!/usr/bin/env python3
"""Match functions from COFF objects against a PE32 image's .text.

For every function symbol in the given .obj/.lib files, masks the bytes
covered by the object's relocations and scans the executable's .text for
a byte-match of the remaining (position-independent) bytes. Because the
mask positions come from our object, a match means the shipped code is
byte-identical up to addresses — the exe-level equivalent of objdiff.

Usage: exematch.py <exe> <obj|lib>... [--verbose]
"""
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from objdiff import parse_obj  # noqa: E402
from exedump import Pe  # noqa: E402
import tempfile, glob, os  # noqa: E402
from libextract import extract  # noqa: E402


def parse_obj_masked(data):
    """Like objdiff.parse_obj but returns (code, maskset) per function."""
    if len(data) < 20:
        return {}
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from("<HHIIIHH", data, 0)
    if machine != 0x14C:
        return {}
    strtab = data[symoff + nsyms * 18:]

    def symname(raw):
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            return strtab[off:strtab.find(b"\0", off)].decode("latin-1")
        return raw.rstrip(b"\0").decode("latin-1")

    secs = []
    for i in range(nsec):
        s = 20 + optsz + i * 40
        vsize, _va, rawsz, rawp, relp, _lnp, nrel, _nln = struct.unpack_from(
            "<IIIIIIHH", data, s + 8)
        flags = struct.unpack_from("<I", data, s + 36)[0]
        secs.append((rawsz, rawp, relp, nrel, flags))

    syms = []
    i = 0
    while i < nsyms:
        e = symoff + i * 18
        raw = data[e : e + 18]
        name = symname(raw[:8])
        value, secnum, typ, storage, naux = struct.unpack_from("<IhHBB", raw, 8)
        syms.append((name, value, secnum, typ, storage))
        i += 1 + naux

    out = {}
    for si, (rawsz, rawp, relp, nrel, flags) in enumerate(secs, 1):
        if not flags & 0x20 or rawsz == 0 or rawp == 0:
            continue
        code = data[rawp : rawp + rawsz]
        masks = set()
        for r in range(nrel):
            va = struct.unpack_from("<I", data, relp + r * 10)[0]
            masks.update(range(va, min(va + 4, rawsz)))
        fsyms = sorted(
            (v, n) for n, v, sn, typ, st in syms
            if sn == si and st in (2, 3) and typ == 0x20)
        for j, (v, n) in enumerate(fsyms):
            end = fsyms[j + 1][0] if j + 1 < len(fsyms) else rawsz
            fcode = code[v:end]
            while fcode and fcode[-1] in (0x90, 0xCC):
                fcode = fcode[:-1]
            fmask = {m - v for m in masks if v <= m < v + len(fcode)}
            out[n] = (fcode, fmask)
    return out


def find(text, tbase, code, mask):
    """Scan text for code with masked positions ignored; yield offsets."""
    if not code:
        return
    # anchor: longest unmasked run
    runs = []
    start = None
    for i in range(len(code) + 1):
        if i < len(code) and i not in mask:
            if start is None:
                start = i
        else:
            if start is not None:
                runs.append((i - start, start))
                start = None
    if not runs:
        return
    alen, aoff = max(runs)
    anchor = code[aoff : aoff + alen]
    pos = -1
    while True:
        pos = text.find(anchor, pos + 1)
        if pos < 0:
            return
        fstart = pos - aoff
        if fstart < 0 or fstart + len(code) > len(text):
            continue
        if all(text[fstart + i] == code[i] for i in range(len(code)) if i not in mask):
            yield tbase + fstart


def main():
    verbose = "--verbose" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pe = Pe(args[0])
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp : trp + tvs]

    funcs = {}
    for path in args[1:]:
        if path.lower().endswith(".lib"):
            with tempfile.TemporaryDirectory() as td:
                extract(path, td)
                for m in sorted(glob.glob(td + "/*")):
                    funcs.update(parse_obj_masked(open(m, "rb").read()))
        else:
            funcs.update(parse_obj_masked(open(path, "rb").read()))

    matched = missing = tiny = 0
    for n, (code, mask) in sorted(funcs.items()):
        if len(code) - len(mask) < 8:
            tiny += 1
            if verbose:
                print(f"  ?tiny    {n} ({len(code)} bytes)")
            continue
        hits = list(find(text, tva, code, mask))
        if hits:
            matched += 1
            print(f"  MATCH 0x{hits[0]:x}{'+' if len(hits) > 1 else ' '}  {n} ({len(code)})")
        else:
            missing += 1
            print(f"  ----     {n} ({len(code)} bytes)")
    print(f"matched {matched}, unmatched {missing}, too-small-to-match {tiny}")


if __name__ == "__main__":
    main()
