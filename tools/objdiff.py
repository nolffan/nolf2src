#!/usr/bin/env python3
"""Symbol-level comparison of COFF objects / MS .lib archives.

For each function symbol in code sections, compares the machine code with
relocation targets masked (4 bytes per relocation). Functions are matched
across the two inputs by mangled symbol name, so this is immune to link
order and layout — a strict per-function correctness oracle.

Usage: objdiff.py <ours.lib|.obj> <theirs.lib|.obj> [--verbose]
"""
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from libextract import extract  # noqa: E402
import tempfile, os, glob  # noqa: E402


def parse_obj(data):
    """Return {symbol_name: masked_code_bytes} for function symbols."""
    if len(data) < 20:
        return {}
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from("<HHIIIHH", data, 0)
    if machine not in (0x14C,):
        return {}
    strtab_off = symoff + nsyms * 18
    strtab = data[strtab_off:]

    def symname(raw):
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            end = strtab.find(b"\0", off)
            return strtab[off:end].decode("latin-1")
        return raw.rstrip(b"\0").decode("latin-1")

    secs = []
    for i in range(nsec):
        s = 20 + optsz + i * 40
        name = data[s : s + 8]
        vsize, _va, rawsz, rawp, relp, _lnp, nrel, _nln = struct.unpack_from("<IIIIIIHH", data, s + 8)
        flags = struct.unpack_from("<I", data, s + 36)[0]
        secs.append((name, rawsz, rawp, relp, nrel, flags))

    # collect symbols: (name, value, secnum, is_func)
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
    for si, (sname, rawsz, rawp, relp, nrel, flags) in enumerate(secs, 1):
        if not flags & 0x20 or rawsz == 0 or rawp == 0:  # IMAGE_SCN_CNT_CODE
            continue
        code = bytearray(data[rawp : rawp + rawsz])
        for r in range(nrel):
            va = struct.unpack_from("<I", data, relp + r * 10)[0]
            for k in range(4):
                if va + k < len(code):
                    code[va + k] = 0
        # function symbols in this section, sorted by offset
        fsyms = sorted(
            (v, n) for n, v, sn, typ, st in syms
            if sn == si and st in (2, 3) and typ == 0x20
        )
        if not fsyms:
            continue
        for j, (v, n) in enumerate(fsyms):
            end = fsyms[j + 1][0] if j + 1 < len(fsyms) else rawsz
            out[n] = bytes(code[v:end]).rstrip(b"\x90").rstrip(b"\xcc")
    return out


def load(path):
    """Load a .obj or every member of a .lib; return {symbol: code}."""
    out = {}
    if path.lower().endswith(".lib"):
        with tempfile.TemporaryDirectory() as td:
            extract(path, td)
            for m in sorted(glob.glob(td + "/*")):
                out.update(parse_obj(open(m, "rb").read()))
    else:
        out.update(parse_obj(open(path, "rb").read()))
    return out


def main():
    verbose = "--verbose" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ours, theirs = load(args[0]), load(args[1])

    both = sorted(set(ours) & set(theirs))
    only_a = sorted(set(ours) - set(theirs))
    only_b = sorted(set(theirs) - set(ours))
    same = [n for n in both if ours[n] == theirs[n]]
    diff = [n for n in both if ours[n] != theirs[n]]

    print(f"functions: ours {len(ours)}, theirs {len(theirs)}, common {len(both)}")
    print(f"  identical : {len(same)}/{len(both)} ({100*len(same)/max(len(both),1):.1f}%)")
    print(f"  differing : {len(diff)}")
    if only_a:
        print(f"  only ours : {len(only_a)}")
    if only_b:
        print(f"  only theirs: {len(only_b)}")

    def show(label, names):
        if not names:
            return
        print(f"\n-- {label}:")
        for n in names[: None if verbose else 25]:
            extra = ""
            if n in ours and n in theirs:
                extra = f"  ({len(ours[n])} vs {len(theirs[n])} bytes)"
            print(f"  {n}{extra}")

    show("differing", diff)
    show("only in ours", only_a)
    show("only in theirs", only_b)


if __name__ == "__main__":
    main()
