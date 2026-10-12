#!/usr/bin/env python3
"""Relocation-normalized code comparison of two PE32 binaries.

Verifies that two builds contain the same machine code modulo layout:
absolute addresses (via each binary's .reloc table) and relative
call/jmp/jcc displacements are masked, .text is segmented into functions
on inter-function padding runs (0x90/0xCC), and segments are matched
across the binaries by normalized equivalence.

Usage: bindiff.py <ours.dll> <theirs.dll> [--verbose]

No dependencies. x86 (PE32/i386) only.
"""
import struct
import sys
from collections import defaultdict


class Pe:
    def __init__(self, path):
        self.path = path
        self.data = open(path, "rb").read()
        d = self.data
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        nsec = struct.unpack_from("<H", d, pe + 6)[0]
        opt = pe + 24
        self.image_base = struct.unpack_from("<I", d, opt + 28)[0]
        so = opt + struct.unpack_from("<H", d, pe + 20)[0]
        self.sections = {}
        for i in range(nsec):
            s = so + i * 40
            name = d[s : s + 8].rstrip(b"\0").decode()
            vsize, va, rsize, roff = struct.unpack_from("<4I", d, s + 8)
            self.sections[name] = (va, vsize, roff, rsize)
        self.relocs = self._parse_relocs()

    def _parse_relocs(self):
        """Return the set of RVAs of all 4-byte absolute fixups."""
        out = set()
        if ".reloc" not in self.sections:
            return out
        va, vsize, roff, rsize = self.sections[".reloc"]
        d, off, end = self.data, roff, roff + rsize
        while off + 8 <= end:
            page, size = struct.unpack_from("<II", d, off)
            if size < 8:
                break
            for i in range(off + 8, off + size, 2):
                ent = struct.unpack_from("<H", d, i)[0]
                if ent >> 12 == 3:  # IMAGE_REL_BASED_HIGHLOW
                    out.add(page + (ent & 0xFFF))
            off += size
        return out

    def text(self):
        va, vsize, roff, rsize = self.sections[".text"]
        return va, self.data[roff : roff + rsize]


PAD = (0x90, 0xCC)


def segment(text_va, text, relocs):
    """Split .text into (rva, bytes, reloc_offsets) segments on padding runs.

    Reloc'd dwords (absolute addresses, e.g. jump-table entries) are zeroed
    BEFORE splitting so their bytes can never look like 0x90/0xCC padding —
    otherwise segmentation would split at binary-specific places.
    """
    masked = bytearray(text)
    for r in relocs:
        off = r - text_va
        if 0 <= off < len(masked):
            for k in range(4):
                if off + k < len(masked):
                    masked[off + k] = 0
    segs = []
    text = bytes(masked)
    n = len(text)
    i = 0
    while i < n:
        # skip padding
        while i < n and text[i] in PAD:
            i += 1
        if i >= n:
            break
        start = i
        # advance to next run of >=2 padding bytes (single 90s appear inside code)
        while i < n:
            if text[i] in PAD:
                j = i
                while j < n and text[j] in PAD:
                    j += 1
                if j - i >= 2 or j >= n:
                    break
                i = j
            else:
                i += 1
        seg = text[start:i]
        rl = frozenset(
            r - (text_va + start)
            for r in relocs
            if text_va + start <= r < text_va + start + len(seg)
        )
        segs.append((text_va + start, seg, rl))
    return segs


def norm_hash(seg, rl):
    """Hash with reloc'd dwords and rel32 operands of E8/E9 masked."""
    b = bytearray(seg)
    for off in rl:
        for k in range(4):
            if off + k < len(b):
                b[off + k] = 0
    i = 0
    while i < len(b):
        if b[i] in (0xE8, 0xE9) and i + 5 <= len(b):
            b[i + 1 : i + 5] = b"\0\0\0\0"
            i += 5
        elif b[i] == 0x0F and i + 6 <= len(b) and 0x80 <= b[i + 1] <= 0x8F:
            b[i + 2 : i + 6] = b"\0\0\0\0"
            i += 6
        else:
            i += 1
    return bytes(b)


def lockstep_equal(a, ra, b, rb):
    """Compare two same-length segments, masking each side's own relocs and
    jointly-agreed rel32 operands."""
    if len(a) != len(b):
        return False
    n = len(a)
    skip = 0
    i = 0
    while i < n:
        in_ra = i in ra or (i - 1) in ra or (i - 2) in ra or (i - 3) in ra
        in_rb = i in rb or (i - 1) in rb or (i - 2) in rb or (i - 3) in rb
        if in_ra or in_rb:
            if in_ra != in_rb:
                return False  # reloc layout itself differs
            i += 1
            continue
        if a[i] != b[i]:
            return False
        if a[i] in (0xE8, 0xE9) and i + 5 <= n:
            i += 5
            continue
        if a[i] == 0x0F and i + 6 <= n and 0x80 <= a[i + 1] <= 0x8F and a[i + 1] == b[i + 1]:
            i += 6
            continue
        i += 1
    return True


def main():
    verbose = "--verbose" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ours, theirs = Pe(args[0]), Pe(args[1])

    segs_a = segment(*ours.text(), ours.relocs)
    segs_b = segment(*theirs.text(), theirs.relocs)
    print(f"{args[0]}: {len(segs_a)} code segments")
    print(f"{args[1]}: {len(segs_b)} code segments")

    # pass 1: match by normalized hash (multiset)
    pool = defaultdict(list)
    for rva, seg, rl in segs_b:
        pool[norm_hash(seg, rl)].append((rva, seg, rl))

    matched = []
    unmatched_a = []
    for rva, seg, rl in segs_a:
        h = norm_hash(seg, rl)
        if pool[h]:
            matched.append(((rva, seg, rl), pool[h].pop()))
        else:
            unmatched_a.append((rva, seg, rl))
    remaining_b = [s for lst in pool.values() for s in lst]

    # pass 2: lockstep compare leftovers of equal length
    by_len = defaultdict(list)
    for s in remaining_b:
        by_len[len(s[1])].append(s)
    still_a = []
    for rva, seg, rl in unmatched_a:
        hit = None
        for cand in by_len[len(seg)]:
            if lockstep_equal(seg, rl, cand[1], cand[2]):
                hit = cand
                break
        if hit:
            by_len[len(seg)].remove(hit)
            matched.append(((rva, seg, rl), hit))
        else:
            still_a.append((rva, seg, rl))
    still_b = [s for lst in by_len.values() for s in lst]

    code_a = sum(len(s[1]) for s in segs_a)
    code_m = sum(len(a[1]) for a, b in matched)
    print(f"\npass1+2 matched segments : {len(matched)}/{len(segs_a)}")
    print(f"pass1+2 matched code     : {code_m}/{code_a} bytes ({100*code_m/code_a:.2f}%)")

    # pass 3: segment-identity fails when adjacent functions merge into one
    # segment in different link orders. Score leftovers by normalized-chunk
    # coverage: does each 128-byte window of the segment appear ANYWHERE in
    # the other binary's normalized text?
    hay = bytearray()
    for rva, seg, rl in segs_b:
        hay += norm_hash(seg, rl) + b"\xf4"  # separator (hlt, rare in code)
    hay = bytes(hay)

    CHUNK, STEP = 128, 64
    covered = 0
    divergent = []
    for rva, seg, rl in still_a:
        nb = norm_hash(seg, rl)
        if len(nb) <= CHUNK:
            hit = nb in hay
            covered += len(nb) if hit else 0
            if not hit:
                divergent.append((rva, len(nb), 0.0))
            continue
        wins = range(0, len(nb) - CHUNK + 1, STEP)
        hits = sum(1 for o in wins if nb[o : o + CHUNK] in hay)
        frac = hits / len(wins)
        covered += int(len(nb) * frac)
        if frac < 0.95:
            divergent.append((rva, len(nb), frac))

    total_acc = code_m + covered
    print(f"pass3 chunk-covered      : {covered} of {sum(len(s[1]) for s in still_a)} unmatched bytes")
    print(f"TOTAL code accounted for : {total_acc}/{code_a} bytes ({100*total_acc/code_a:.2f}%)")

    if divergent:
        print(f"\n-- segments with <95% coverage (candidate real differences):")
        for rva, size, frac in sorted(divergent, key=lambda d: -d[1])[: 40 if not verbose else None]:
            print(f"  rva {hex(rva)}  {size:>6} bytes  coverage {100*frac:.1f}%")


if __name__ == "__main__":
    main()
