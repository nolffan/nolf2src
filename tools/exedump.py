#!/usr/bin/env python3
"""Annotated disassembly of a PE32 .text range.

Disassembles with objdump (i386, AT&T) and annotates:
  - calls/jumps through the IAT with the imported function name
  - immediates/memory operands that point at ASCII strings in the image
  - operands that land in .rdata/.data/.rsrc with a section+offset tag

Usage: exedump.py <exe> [start_va [end_va]]     (defaults: whole .text)
"""
import os
import re
import struct
import subprocess
import sys
import tempfile


class Pe:
    """A PE image. The retail ones (the ground truth every oracle compares
    against) are in out/reference/, extracted from the retail game by `tools/retailextract.py reference`."""

    def __init__(self, path):
        self.path = path
        self.d = open(path, "rb").read()
        d = self.d
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        self.nsec = struct.unpack_from("<H", d, pe + 6)[0]
        optsz = struct.unpack_from("<H", d, pe + 20)[0]
        self.base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
        self.entry = self.base + struct.unpack_from("<I", d, pe + 24 + 16)[0]
        so = pe + 24 + optsz
        self.secs = {}
        # Raw size kept separately: self.secs stays a 3-tuple because every
        # caller unpacks it as one.
        self.rawsz = {}
        for i in range(self.nsec):
            s = so + i * 40
            name = d[s : s + 8].rstrip(b"\0").decode()
            vs, va, rs, rp = struct.unpack_from("<IIII", d, s + 8)
            self.secs[name] = (self.base + va, vs, rp)
            self.rawsz[name] = rs
        self.pe = pe

    def va2off(self, va):
        """File offset for a virtual address, or None if it has none.

        A section's virtual size can far exceed what is stored on disk -- the
        tail is BSS, zero-filled by the loader and absent from the file.
        d3d.ren's .data is 0x1a520 virtual against 0x2000 raw, so 90% of it
        is BSS. Mapping those addresses by virtual offset alone lands inside
        the NEXT section's bytes and invents a string for them: a BSS
        reference at 0x1008be60 was being annotated
        "Model::SetupTransforms failed for %s." out of .data1, and three
        colour ramp tables came out as console format strings. Silently
        wrong, and exactly the sort of thing a reconstruction pass trusts.
        """
        for name, (sva, vs, rp) in self.secs.items():
            if sva <= va < sva + vs:
                if va - sva >= self.rawsz.get(name, vs):
                    return None          # BSS: not in the file
                return rp + (va - sva)
        return None

    def sec_of(self, va):
        for name, (sva, vs, rp) in self.secs.items():
            if sva <= va < sva + vs:
                return name, va - sva
        return None, 0

    def cstr(self, va, maxlen=60):
        off = self.va2off(va)
        if off is None:
            return None
        e = self.d.find(b"\0", off, off + 256)
        if e < 0:
            return None
        s = self.d[off:e]
        if len(s) >= 3 and all(32 <= c < 127 or c in (9, 10, 13) for c in s):
            t = s.decode("latin-1")
            return t if len(t) <= maxlen else t[:maxlen] + "…"
        return None

    def imports(self):
        d = self.d
        irva = struct.unpack_from("<I", d, self.pe + 24 + 104)[0]
        out = {}
        if not irva:
            return out
        io = self.va2off(self.base + irva)
        j = 0
        while True:
            ilt, _ts, _fc, nm, iat = struct.unpack_from("<IIIII", d, io + j * 20)
            if not nm:
                break
            dll = self.cstr(self.base + nm)
            t = self.va2off(self.base + (ilt or iat))
            k = 0
            while True:
                v = struct.unpack_from("<I", d, t + k * 4)[0]
                if not v:
                    break
                if v & 0x80000000:
                    name = f"{dll}#{v & 0xffff}"
                else:
                    name = self.cstr(self.base + (v & 0x7FFFFFFF) + 2)
                out[self.base + iat + k * 4] = f"{dll}!{name}"
                k += 1
            j += 1
        return out


def main():
    pe = Pe(sys.argv[1])
    tva, tvs, trp = pe.secs[".text"]
    start = int(sys.argv[2], 16) if len(sys.argv) > 2 else tva
    end = int(sys.argv[3], 16) if len(sys.argv) > 3 else tva + tvs
    imp = pe.imports()
    blob = pe.d[trp + (start - tva) : trp + (end - tva)]
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(blob)
        tmp = f.name
    out = subprocess.run(
        ["objdump", "-D", "-b", "binary", "-m", "i386",
         f"--adjust-vma=0x{start:x}", tmp],
        capture_output=True, text=True).stdout
    memref = re.compile(r"0x([0-9a-f]{6,8})")
    for line in out.splitlines():
        if not re.match(r"^\s*[0-9a-f]+:", line):
            continue
        note = []
        for m in memref.finditer(line):
            va = int(m.group(1), 16)
            if va in imp:
                note.append(imp[va])
            else:
                s = pe.cstr(va)
                if s is not None:
                    note.append(f'"{s}"')
                else:
                    sec, off = pe.sec_of(va)
                    if sec and sec != ".text":
                        note.append(f"{sec}+0x{off:x}")
        # bare call/jmp targets already carry the va in the mnemonic
        print(line + ("   ; " + " ".join(note) if note else ""))


if __name__ == "__main__":
    main()
