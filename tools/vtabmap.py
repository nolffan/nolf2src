#!/usr/bin/env python3
"""Map vtables in a stripped PE image back to SDK interfaces.

Finds runs of 3+ consecutive pointers into .text in the data sections —
vtables — and prints each slot. Slots whose target is already identified
(matched by exematch, or named by an argument-check literal) are labelled,
so an unidentified slot between two identified ones can be read straight
out of the SDK header's declaration order.

Usage:
  vtabmap.py <image> [--at 0xADDR] [--names out/reference/<img>-functions.csv]

--at prints only the run containing that address (as a slot target).
--names takes an enumfuncs --csv file and uses its name column as labels.
"""
import csv
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from enumfuncs import Image  # noqa: E402


def pointer_runs(img, min_len=3):
    runs = []
    for name, va, vs, rs, rp in img.secs:
        if name == ".text":
            continue
        blob = img.d[rp : rp + min(vs, rs)]
        cur = []
        for o in range(0, len(blob) - 3, 4):
            v = struct.unpack_from("<I", blob, o)[0]
            if img.tlo <= v < img.thi:
                cur.append((img.base + va + o, v))
            else:
                if len(cur) >= min_len:
                    runs.append(cur)
                cur = []
        if len(cur) >= min_len:
            runs.append(cur)
    return runs


def main():
    img = Image(sys.argv[1])
    want = None
    names = {}
    if "--at" in sys.argv:
        want = int(sys.argv[sys.argv.index("--at") + 1], 16)
    if "--names" in sys.argv:
        path = sys.argv[sys.argv.index("--names") + 1]
        for r in csv.DictReader(open(path)):
            if r["name"]:
                names[int(r["addr"], 16)] = r["name"]

    for run in pointer_runs(img):
        tgts = [v for _, v in run]
        if want is not None and want not in tgts:
            continue
        print("run at %08x, %d slots" % (run[0][0], len(run)))
        for i, (va, v) in enumerate(run):
            print("  slot %3d (+%#05x) @%08x -> %08x  %s"
                  % (i, i * 4, va, v, names.get(v, "")))


if __name__ == "__main__":
    main()
