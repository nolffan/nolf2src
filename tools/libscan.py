#!/usr/bin/env python3
"""Where each library's code sits in a retail image.

Searches the image's .text for every function of the given static
libraries (masked by the library object's own relocations, as exematch.py
does) and prints, per library, the functions found at exactly one address,
grouped into runs. A library is linked as one block of its members, so its
unique hits cluster: the start of the C runtime's run is where an image's
own code ends (tools/progress.py's `app` ranges in progress/targets.py), and
a run of a third-party library inside that range is its `middleware`.

Usage:
  libscan.py <image> <lib>... [--min=24] [--gap=0x2000] [--list]

  --min   ignore functions with fewer unmasked bytes (default 24: shorter
          ones recur by coincidence)
  --gap   two hits further apart than this start a new run
  --list  print every unique hit, not just the runs

  libscan.py out/reference/Lithtech.exe toolchains/msvc-6.00-8966/LIB/libcmt.lib \\
      toolchains/dxsdk-8.1/lib/d3dx8.lib
"""
import glob
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402
from libextract import extract  # noqa: E402


def lib_funcs(path):
    """{(member, symbol): (code, mask)} of a .lib or .obj."""
    out = {}
    if path.lower().endswith(".lib"):
        with tempfile.TemporaryDirectory() as td:
            extract(path, td)
            for m in sorted(glob.glob(td + "/*")):
                for k, v in parse_obj_masked(open(m, "rb").read()).items():
                    out[(os.path.basename(m), k)] = v
    else:
        for k, v in parse_obj_masked(open(path, "rb").read()).items():
            out[(os.path.basename(path), k)] = v
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    if len(args) < 2:
        sys.exit(__doc__)
    least = int(opts.get("min", "24"))
    gap = int(opts.get("gap", "0x2000"), 0)
    pe = Pe(args[0])
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]
    for lib in args[1:]:
        hits = []
        for (mem, sym), (code, mask) in sorted(lib_funcs(lib).items()):
            if len(code) - len(mask) < least:
                continue
            h = list(find(text, tva, code, mask))
            if len(h) == 1:
                hits.append((h[0], len(code), mem, sym))
        hits.sort()
        print(f"{os.path.basename(lib)}: {len(hits)} function(s) found at "
              f"exactly one address")
        runs = []
        for h in hits:
            if runs and h[0] - (runs[-1][-1][0] + runs[-1][-1][1]) <= gap:
                runs[-1].append(h)
            else:
                runs.append([h])
        for r in runs:
            lo, hi = r[0], r[-1]
            print(f"  0x{lo[0]:08x} .. 0x{hi[0] + hi[1]:08x}  {len(r):>4} hit(s)"
                  f"  first {lo[2]}:{lo[3]}  last {hi[2]}:{hi[3]}")
            if "list" in opts:
                for a, n, mem, sym in r:
                    print(f"      0x{a:08x} {n:>6}  {mem}:{sym}")


if __name__ == "__main__":
    main()
