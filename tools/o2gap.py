#!/usr/bin/env python3
"""Functions that match in server.dll (/O1) but NOT in lithtech.exe (/O2).

The shared engine translation units are compiled TWICE: /O1 into server.dll
and /O2 into lithtech.exe (build/engine.sh). A function that is byte-identical
in one and not the other is built from source we have ALREADY PROVEN CORRECT --
the semantics match at /O1 -- so what is missing is /O2-visible SHAPE, and
that is much cheaper to fix than reconstructing a function from raw bytes.

Why the asymmetry exists, and why it only points one way:

  * /O1 implies /Os, which declines to inline anything but the smallest
    functions; /O2 implies /Ot, which accepts them. A helper that the shipped
    /O2 image expands into its callers is simply called at /O1, so server.dll
    matches whether or not our source marks it `inline`.
  * /O1 tail-merges duplicated epilogues, so an early `return X` and a nested
    positive guard with a trailing `return X` produce the same /O1 bytes and
    DIFFERENT /O2 bytes.

So lithtech.exe is the stronger oracle for source SHAPE on every shared TU.
Fix against it, then re-verify server.dll -- never the other way round. See
guides/09-codegen-patterns.md ("the inliner is forward-only").

A row here is a claim about our source, not about the shipped image: both
addresses are real functions and one of our objects reproduces one of them.

ONE TRAP, and it is an expensive one. This
tool tests "is the symbol present on both sides", but PRESENT is tested against
OUR object -- which always has it, because we always compile the TU. It does
not ask whether the shipped LINKER kept the translation unit at all. Two TUs
are in server.dll and simply not in lithtech.exe: `servermgr.cpp` (whose
MyServerInterface vtable is absent -- the retail lithtech.exe contains zero
occurrences of the string "ServerInterface::", against nine in server.dll) and
`server.cpp` (whose CreateServer/DeleteServer are __declspec(dllexport), and
lithtech.exe has no export directory at all). Their 31 rows were pure phantom.

So a TU whose object barely matches the target image is reported as ABSENT and
excluded from the total. The threshold is deliberately crude -- one match can
be a coincidental tail-call thunk, which is exactly what servermgr.obj's single
"match" turned out to be.

Usage:
  o2gap.py                      every shared TU, ranked by gap
  o2gap.py smgr collection      just these, listing each function
  o2gap.py --top=20 smgr        list more than the default twelve
"""
import os
import re
import subprocess
import sys

SRV = "out/reference/server.dll"
LIT = "out/reference/lithtech.exe"


def matches(image, obj):
    """symbol -> (matched?, address or None, size). Both statuses, because a
    symbol absent from one side entirely is not a gap -- it is a TU that the
    other target does not compile, and counting it would invent work."""
    if not os.path.exists(obj):
        return {}
    out = subprocess.run([sys.executable, "tools/exematch.py", image, obj],
                         capture_output=True, text=True).stdout
    d = {}
    for line in out.splitlines():
        g = re.match(r"\s+MATCH\s+(\S+)\s+(\S+)\s+\((\d+)\)", line)
        if g:
            d[g.group(2)] = (True, g.group(1), int(g.group(3)))
            continue
        g = re.match(r"\s+----\s+(\S+)\s+\((\d+)", line)
        if g:
            d[g.group(1)] = (False, None, int(g.group(2)))
    return d


# Below this many confirmed matches against lithtech.exe, a TU is treated as
# not linked into it at all. One match can be a coincidental identical tail
# call; servermgr.obj's lone "match" was a 14-byte `jmp fs_FreeFileList` thunk
# that collided with a CLTClient method.
PRESENT_MIN = 2


def gap(tu):
    s = matches(SRV, f"src/engine/server/Release/{tu}.obj")
    t = matches(LIT, f"src/engine/lithtech/Release/{tu}.obj")
    if sum(1 for v in t.values() if v[0]) < PRESENT_MIN and s:
        return None          # the TU is not in lithtech.exe; every row phantom
    # Only symbols PRESENT ON BOTH SIDES: one that server.dll matches and
    # lithtech.exe never emitted is not shape, it is a different build.
    return sorted(((sym, v[2], v[1]) for sym, v in s.items()
                   if v[0] and sym in t and not t[sym][0]),
                  key=lambda r: -r[1])


def main():
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    top = next((int(o.split("=")[1]) for o in opts if o.startswith("--top=")), 12)

    if args:
        for tu in args:
            rows = gap(tu)
            if rows is None:
                print(f"\n# {tu}.cpp -- ABSENT from lithtech.exe. Every row "
                      f"would be phantom; nothing to fix here.")
                continue
            print(f"\n# {tu}.cpp -- {len(rows)} identical in server.dll, "
                  f"NOT in lithtech.exe")
            for sym, sz, addr in rows[:top]:
                print(f"  srv {addr}  {sz:>6}b  {sym}")
            if len(rows) > top:
                print(f"  ... and {len(rows) - top} more")
        return

    total = 0
    print(f"{'TU':<22}{'gap':>6}")
    print("-" * 28)
    for obj in sorted(os.listdir("src/engine/server/Release")):
        if not obj.endswith(".obj"):
            continue
        tu = obj[:-4]
        rows = gap(tu)
        if rows is None:
            print(f"{tu:<22}{'ABSENT':>6}")
            continue
        n = len(rows)
        if n:
            total += n
            print(f"{tu:<22}{n:>6}")
    print("-" * 28)
    print(f"{'TOTAL':<22}{total:>6}")
    print("\nEach row is source that already matches at /O1. See the module "
          "docstring\nfor why lithtech.exe is the oracle for shape.")


if __name__ == "__main__":
    main()
