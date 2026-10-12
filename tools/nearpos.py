#!/usr/bin/env python3
"""Locate an UNMATCHED function in the image and print the bytes that differ.

exematch answers yes or no. When the answer is no it says nothing about why,
and the usual why is not a codegen subtlety at all -- it is one wrong number
in a class layout, repeated at every field below it. This finds that number.

For each of our COMDATs that exematch cannot place, it slides the body over
the whole of .text and keeps the positions where at most `tol` unmasked bytes
disagree. A function whose source is RIGHT and whose layout is off by four
lands at its true address with one or two differing bytes, and those bytes
are the displacements: `+21:a8->a4` reads "we emitted 0xa8 where the shipped
build has 0xa4", which is a field four bytes too high.

Three layout bugs found this way, each in seconds and each worth several
functions at once:

  * CClientMgrView was missing a pointer at +0x508, so every field below it
    was four low -- `+6:d4->d8`. Restoring it took that TU from 13 matched
    to 19.
  * CObj4a2078View opened with `uint8 m_pad_000[0x34]` on a class that has
    virtuals, so the vptr pushed the pad's contents four bytes high --
    `+11:38->34`. The pad has to be `[0x34 - 0x04]`.
  * two GetLoader bodies came out size-exact with the arms swapped, which is
    the shared-exit lever and not a layout fault at all.

Read the output with that in mind: a single repeated delta in one direction is
a layout fault, scattered register bytes are codegen, and a hit with SIX
differences at a plausible-looking address is usually coincidence -- at tol 8
a 20-byte body can land almost anywhere. Trust a hit when the differences
have a pattern, not when there are merely few of them.

Usage:
  nearpos.py <image> <obj> [tol]        # tol defaults to 3
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    img, obj = sys.argv[1], sys.argv[2]
    tol = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    pe = Pe(img)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]
    fns = parse_obj_masked(open(obj, "rb").read())

    unplaced = sorted(n for n in fns if not list(find(text, tva, *fns[n])))
    print(f"{len(fns)} symbol(s), {len(unplaced)} unplaced, tolerance {tol}")
    for n in unplaced:
        code, mask = fns[n]
        size = len(code)
        # Below exematch's floor there is not enough signal to site anything.
        if size - len(mask) < 8:
            print(f"  {n[:60]:60} {size:>4}b  under the 8-byte floor")
            continue
        best = []
        for off in range(len(text) - size):
            d = 0
            for i in range(size):
                if i in mask:
                    continue
                if text[off + i] != code[i]:
                    d += 1
                    if d > tol:
                        break
            else:
                best.append((d, tva + off))
        best.sort()
        if not best:
            print(f"  {n[:60]:60} {size:>4}b  no position within {tol}")
            continue
        d, a = best[0]
        diffs = " ".join(
            f"+{i}:{code[i]:02x}->{text[a - tva + i]:02x}"
            for i in range(size)
            if i not in mask and code[i] != text[a - tva + i])
        more = f"  (+{len(best) - 1} more)" if len(best) > 1 else ""
        print(f"  {n[:60]:60} {size:>4}b @{a:#010x} {diffs}{more}")


if __name__ == "__main__":
    main()
