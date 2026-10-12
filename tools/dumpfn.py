#!/usr/bin/env python3
"""Disassemble one function from a COFF object, cleanly.

Extracts the function's own COMDAT section bytes and disassembles them in
isolation (objdump -b binary), annotating relocation targets inline — no
linear-sweep confusion from neighbouring sections or embedded labels.

Usage: dumpfn.py <obj> <symbol-substring> [--all]
"""
import struct
import subprocess
import sys
import tempfile


def dump(path, want, list_only=False):
    data = open(path, "rb")
    d = data.read()
    machine, nsec, _ts, symoff, nsyms, optsz, _ch = struct.unpack_from("<HHIIIHH", d, 0)
    strtab = d[symoff + nsyms * 18:]

    def symname(raw):
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            return strtab[off:strtab.find(b"\0", off)].decode("latin-1")
        return raw.rstrip(b"\0").decode("latin-1")

    secs = []
    for i in range(nsec):
        s = 20 + optsz + i * 40
        _vs, _va, rawsz, rawp, relp, _lp, nrel, _nl = struct.unpack_from("<IIIIIIHH", d, s + 8)
        secs.append((rawsz, rawp, relp, nrel))

    syms = []
    i = 0
    while i < nsyms:
        e = symoff + i * 18
        raw = d[e:e + 18]
        name = symname(raw[:8])
        value, secnum, typ, storage, naux = struct.unpack_from("<IhHBB", raw, 8)
        syms.append((name, value, secnum, typ, storage))
        i += 1 + naux

    matches = [s for s in syms if want in s[0] and s[3] == 0x20 and s[2] > 0]
    if list_only:
        for name, value, secnum, typ, st in matches:
            print(name)
        return
    if not matches:
        print(f"no function symbol matching {want!r}")
        return

    for name, value, secnum, *_ in matches[:3]:
        rawsz, rawp, relp, nrel = secs[secnum - 1]
        # Slice to THIS function and strip trailing alignment padding, exactly
        # as exematch.py does. Taking the whole COMDAT section instead made
        # every comparison on lithtech.exe misread: fndiff would report e.g.
        # 973 shipped bytes against 980 of ours, SKIP its own byte-identity
        # check because the lengths differed, and print a mnemonic diff for a
        # function that was in fact instruction-for-instruction equal. Six of
        # twenty surveyed near-misses turned out to differ in no instruction at
        # all once this was corrected.
        fsyms = sorted(v for n, v, sn, typ, st in syms
                       if sn == secnum and st in (2, 3) and typ == 0x20)
        nxt = next((v for v in fsyms if v > value), rawsz)
        code = d[rawp + value:rawp + nxt]
        while code and code[-1] in (0x90, 0xCC):
            code = code[:-1]
        reloc_base = value
        relocs = {}
        for r in range(nrel):
            va, symidx, rtyp = struct.unpack_from("<IIH", d, relp + r * 10)
            # resolve symbol name by table index (accounting for aux entries)
            j = 0
            k = 0
            while k < nsyms:
                e = symoff + k * 18
                if k == symidx:
                    relocs[va - reloc_base] = symname(d[e:e + 8])
                    break
                naux = d[e + 17]
                k += 1 + naux
        print(f"===== {name} (section {secnum}, {len(code)} bytes, "
              f"{nrel} relocs)")
        with tempfile.NamedTemporaryFile(suffix=".bin") as f:
            f.write(code)
            f.flush()
            out = subprocess.run(
                ["objdump", "-D", "-b", "binary", "-m", "i386", f.name],
                capture_output=True, text=True).stdout
        for line in out.splitlines():
            if "\t" not in line:
                continue
            try:
                addr = int(line.split(":")[0], 16)
            except ValueError:
                continue
            ann = [nm for va, nm in relocs.items() if addr < va < addr + 12]
            print(line + ("   ; " + ", ".join(ann) if ann else ""))
        print("-- relocs:")
        for va, nm in sorted(relocs.items()):
            print(f"   {va:#x}: {nm}")


if __name__ == "__main__":
    dump(sys.argv[1], sys.argv[2], "--all" in sys.argv)
