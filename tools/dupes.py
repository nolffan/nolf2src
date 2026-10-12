#!/usr/bin/env python3
"""Find shipped addresses that MORE THAN ONE of our symbols reconstructs.

The failure this exists for: the same shipped function gets written twice,
under two names, from two directions. It happened on 0x10024e2e and
0x10024e51 -- a vftable sweep reached CObjWorldModel from the object side
while worldmodels.cpp and the object header had already come at the same code
from the other -- and nothing complained. The scoreboard does not: exematch
credits each ADDRESS once, so a duplicate costs nothing and shows up as
nothing.

uncovered.py structurally cannot catch it either. It drops every row whose
address is mentioned anywhere in src/engine/<target>/, which is exactly the
case for a function that is already written up. So the second reconstruction
looks like new work precisely because the first one exists.

What this does instead: place every COMDAT, group by address, and report any
address reached by two or more DIFFERENT bodies-or-names.

Two exclusions, both necessary or the output is all noise:

  * identical bodies under two names are usually one function legitimately
    modelled twice -- a base's method and a view class's copy of it, or one
    template standing in for a family. Those are reported separately, as
    "same body", because they are worth knowing but are not bugs.
  * template stand-ins (`?$` in the mangled name) match at every
    instantiation's address by construction.

A "different body" hit at one address is impossible -- two different byte
strings cannot both be there -- so the interesting report is the same-body
one, filtered down to pairs whose names are not related. Read it as a
worklist of suspects, not as a list of defects.

Usage:
  dupes.py <image> <objdir> [--all]
"""
import collections
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402


def leaf(sym):
    """The bare method/function name inside a mangled symbol, lowercased."""
    s = sym.lstrip("?")
    for i, c in enumerate(s):
        if c == "@":
            return s[:i].lower()
    return s.lower()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) != 2:
        sys.exit(__doc__)
    image, objdir = args

    pe = Pe(image)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]

    at = collections.defaultdict(list)     # addr -> [(sym, tu, bodykey)]
    for obj in sorted(glob.glob(os.path.join(objdir, "*.obj"))):
        tu = os.path.basename(obj)
        try:
            fns = parse_obj_masked(open(obj, "rb").read())
        except Exception:
            continue
        for name, (code, mask) in fns.items():
            if len(code) - len(mask) < 8 or "?$" in name:
                continue
            hits = list(find(text, tva, code, mask))
            if len(hits) != 1:
                continue                    # ambiguous: says nothing
            at[hits[0]].append((name, tu, (bytes(code), tuple(sorted(mask)))))

    rows = []
    for addr, syms in sorted(at.items()):
        names = {s for s, _tu, _b in syms}
        if len(names) < 2:
            continue
        bodies = {b for _s, _tu, b in syms}
        # Names that share a leaf are the deliberate-copy case (a view class
        # repeating a base's method under the same method name).
        related = len({leaf(s) for s in names}) == 1
        if related and "--all" not in opts:
            continue
        rows.append((addr, sorted(syms, key=lambda t: t[0]), len(bodies) > 1))

    print(f"{len(at)} address(es) uniquely placed; "
          f"{len(rows)} reached by more than one unrelated symbol\n")
    for addr, syms, differ in rows:
        tag = "DIFFERENT BODIES" if differ else "same body"
        print(f"  {addr:#010x}  {tag}")
        for name, tu, _b in syms:
            print(f"      {tu:<24} {name}")
    if not rows:
        print("no unrelated duplicates found")
    sys.exit(1 if rows else 0)


if __name__ == "__main__":
    main()
