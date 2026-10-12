#!/usr/bin/env python3
"""Compare the instruction census of a shipped function against ours.

guides/11 asks for "an instruction census with no residue" whenever the call
sequence is weak, and for functions with NO calls it is the only quantitative
instrument there is -- callseq reports 0 of 0 and says so. A census taken by
hand, from the shipped side only, shows that a reading is self-consistent but
never that OUR SOURCE reproduces it.

This compares both sides:

  python3 tools/census.py out/reference/d3d.ren 0x10003c40 0x1000519a \\
          src/engine/d3d/Release/big3c40.obj sub_10003c40

`residue` is the total absolute difference across all mnemonics -- 0 means the
two functions execute the same multiset of instruction kinds. It is a weaker
statement than byte-identity and a much stronger one than "it compiles", and
unlike the call check it works on call-free code.

READ THE ROWS, NOT THE TOTAL. The rows say what KIND of difference it is, and
the kinds are very unequal:

  * A run of rows all differing by the SAME count is one cause, not many.
    0x10003c40 at plain /O2 showed fistpl 30 -> 0 with shld/neg/or/shr/fstpl
    all appearing at exactly 30: one float-to-int idiom, thirty sites.
  * That one is worth knowing about. icl 4.0 has NO /QIfist -- it parses as
    /QIf and is silently ignored, which is why an earlier test of that flag
    "changed nothing". The real option is /Qrcd, "fast float-to-int
    conversions", and it cuts that function's residue from 875 to 304. It
    still emits a 64-bit `fistpll` where the shipped code has a 32-bit
    `fistpl` plus a float store/reload, and no cast spelling or precision flag
    tried so far changes that. Treat a leftover fistpl/fistpll row as this
    known gap, not as a defect in the reconstruction.
  * `mov`, `lea` and `push`/`pop` differences are usually register allocation
    and frame layout, not structure.
"""
import collections
import re
import subprocess
import sys


def hist(argv, sym=None):
    out = subprocess.run(argv, capture_output=True, text=True).stdout
    h = collections.Counter()
    on = sym is None
    for line in out.splitlines():
        if sym is not None:
            m = re.match(r"^[0-9a-f]+ <(.*)>:", line)
            if m:
                on = sym in m.group(1)
                continue
        m = re.match(r"\s*[0-9a-f]+:\t[0-9a-f ]+\t(\S+)", line)
        if m and on:
            h[m.group(1)] += 1
    return h


def main():
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    image, start, end, obj, sym = sys.argv[1:]
    a = hist(["objdump", "-d", f"--start-address={start}",
              f"--stop-address={end}", image])
    b = hist(["objdump", "-d", obj], sym)
    if not b:
        sys.exit(f"no symbol matching {sym!r} in {obj}")

    keys = set(a) | set(b)
    diff = sorted(((k, a.get(k, 0), b.get(k, 0)) for k in keys
                   if a.get(k, 0) != b.get(k, 0)),
                  key=lambda r: -abs(r[1] - r[2]))
    residue = sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys)

    print(f"shipped {sum(a.values()):,} instructions, "
          f"ours {sum(b.values()):,}")
    print(f"{len(keys) - len(diff)} mnemonics match exactly, "
          f"{len(diff)} differ, residue {residue}\n")
    for k, x, y in diff:
        print(f"  {k:<10} shipped {x:>5}  ours {y:>5}   {y - x:+d}")

    # A group of rows differing by the same amount is ONE cause. Saying so
    # stops the reader treating six rows of 30 as six problems.
    by = collections.Counter(abs(x - y) for _, x, y in diff)
    for n, c in by.most_common(3):
        if c >= 3 and n:
            print(f"\n  note: {c} rows differ by exactly {n} -- that is one "
                  f"cause at {n} sites, not {c} separate problems")
    if not diff:
        print("\nCENSUS AGREES -- same multiset of instruction kinds")
    return 0 if not diff else 1


sys.exit(main())
