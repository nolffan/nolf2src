#!/usr/bin/env python3
"""Name the function an address falls in, from a linker .map file.

For the debug build's crash log (out/nolf2-legacy-debug/nolf2src.log): a frame the
.pdb files cannot name -- the static CRT, or a d3d.ren function compiled with
/Qip, for which Intel C/C++ 4.0 writes no debug information -- is logged with
its address at the image's preferred base, "(0x10036d1c in its .map)". This
looks that address up in the map the debug build puts beside the binary.

  tools/mapaddr.py out/nolf2-legacy-debug/d3d.map 0x10036d1c [0x... ...]
"""
import re
import sys


def load(path):
    """[(address, symbol, object)] from a VC6 LINK /map, sorted."""
    syms = []
    pat = re.compile(r"\s*[0-9a-fA-F]{4}:[0-9a-fA-F]{8}\s+(\S+)\s+([0-9a-fA-F]{8})\s+(?:f\s+)?(?:i\s+)?(\S+)?")
    for line in open(path, errors="replace"):
        m = pat.match(line)
        if m:
            syms.append((int(m.group(2), 16), m.group(1), m.group(3) or ""))
    syms.sort()
    return syms


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    syms = load(sys.argv[1])
    for a in sys.argv[2:]:
        addr = int(a, 16)
        best = None
        for s in syms:
            if s[0] > addr:
                break
            best = s
        if best is None:
            print(f"0x{addr:08x}  (before the first symbol)")
        else:
            print(f"0x{addr:08x}  {best[1]}+0x{addr - best[0]:x}  ({best[2]})")


if __name__ == "__main__":
    main()
