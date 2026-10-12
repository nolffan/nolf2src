#!/usr/bin/env python3
"""Rank unreconstructed functions by how much reconstructed code calls them.

The error-tag oracle (tagmap.py) is exhausted on server.dll and the
"referenced from one of our headers" seam is nearly so. What is left has
nothing naming it -- but plenty of it is *called* from functions we have
already matched byte-for-byte, and a call site we understand constrains the
callee hard: the pushes give the argument count and order, the cleanup gives
the convention, and the caller's own reconstruction usually names the types.

So: take every shipped address exematch places from our objects, disassemble
its bytes, collect the direct `call rel32` targets that are still todo, and
rank them by how many distinct matched callers reach them. A function called
from four reconstructed places is far cheaper than one called from none.

Usage:
  callseam.py <image> <objdir> <functions.csv> [--min=2] [--csv=out.csv]
"""
import csv
import glob
import os
import struct
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    if len(args) != 3:
        sys.exit(__doc__)
    image, objdir, fcsv = args
    minc = int(opts.get("--min", 2))

    pe = Pe(image)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]

    size = {}
    for r in csv.DictReader(open(fcsv)):
        a = int(r["addr"], 16)
        size[a] = int(r["size"])
    # every shipped address our objects account for, and which TU did it.
    # This is computed live rather than read from progress/functions.csv,
    # because that file is only as fresh as the last progress.py run -- an
    # address reconstructed since then still reads "todo" there, and the first
    # user of this tool lost a function to exactly that.
    owner = {}
    for obj in sorted(glob.glob(os.path.join(objdir, "*.obj"))):
        tu = os.path.basename(obj)[:-4]
        try:
            fns = parse_obj_masked(open(obj, "rb").read())
        except Exception:
            continue
        for n, (code, mask) in fns.items():
            if len(code) - len(mask) < 8:
                continue
            for a in find(text, tva, code, mask):
                owner.setdefault(a, (tu, n))

    # "still to do" now means "no object of ours accounts for it", which is
    # the same question exematch answers and cannot go stale.
    #
    # CAVEAT, and it costs real time if you do not know it: `find` skips any
    # function with fewer than eight unmasked bytes, because there is nothing
    # left to anchor on. So a small function -- an eleven-byte destructor that
    # is a vptr store and a tail jump, say -- never appears in `owner` even
    # when it is written and byte-perfect, and therefore always lists as todo
    # here. Two of five such destructors in one batch were already correct.
    # Below about twenty bytes, check the address with fndiff before
    # reconstructing anything.
    todo = {a for a in size if a not in owner}

    callers = collections.defaultdict(set)
    for a, (tu, sym) in owner.items():
        n = size.get(a)
        if not n:
            continue
        body = text[a - tva:a - tva + n]
        for i in range(len(body) - 4):
            if body[i] != 0xE8:
                continue
            rel = struct.unpack_from("<i", body, i + 1)[0]
            tgt = a + i + 5 + rel
            if tgt in todo:
                callers[tgt].add((tu, sym))

    rows = sorted(callers.items(), key=lambda kv: (-len(kv[1]), size.get(kv[0], 0)))
    rows = [(t, c) for t, c in rows if len(c) >= minc]
    print(f"{len(callers)} todo functions are called from reconstructed code; "
          f"{len(rows)} have {minc}+ distinct callers\n")
    tus = collections.Counter()
    for t, c in rows:
        tus[sorted({tu for tu, _ in c})[0]] += 1
    for tu, n in tus.most_common():
        print(f"  nearest-TU {tu:<18} {n:>3}")
    out = opts.get("--csv")
    if out:
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["addr", "size", "ncallers", "callers"])
            for t, c in rows:
                w.writerow([f"0x{t:08x}", size.get(t, 0), len(c),
                            "; ".join(f"{tu}:{sym}" for tu, sym in sorted(c))])
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
