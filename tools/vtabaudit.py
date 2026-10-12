#!/usr/bin/env python3
"""Enumerate a PE image's vtables from EVIDENCE, one table per row.

WHY THIS EXISTS AND WHY vtabmap.py IS NOT ENOUGH. vtabmap finds RUNS of
consecutive pointers into .text, and a run is not a vtable: adjacent tables
in .rdata are contiguous, so one run spans several. Reading a run as a table
is how lithtech.exe's ILTCursor front end came to be recorded as CLTClient
slots 110-117, and how CLTClient's own length was got wrong twice. Three
corrections to this project's vtable map all trace to that.

So this splits runs on independent evidence and reports what it can prove:

  BASE      -- a vtable base is a 4-byte IMMEDIATE stored by a constructor.
               `mov $0x4a14e0,(%eax)` and its addressing-mode variants are
               searched for over the whole of .text, and every run is cut at
               every referenced address inside it. A run with no reference
               at all is reported as UNREFERENCED, which is a finding in
               itself. It is how the CRT's static-initialiser array is told
               from a vtable without special-casing it: lithtech.exe's is 53
               consecutive thunk pointers in .data and looks exactly like a
               53-slot table, but nothing ever stores its base, because the
               CRT startup walks it rather than installing it in an object.
               Offering it as work would have been 53 functions that do not
               exist.

  LENGTH    -- from the base to the next referenced base in the same run, or
               to the end of the run. Never guessed.

  ABSTRACT  -- a table with the _purecall thunk in ANY slot belongs to an
               abstract class and holds no implementation. Two of the four
               tables this project was using as naming anchors are abstract;
               anchoring off one names nothing. _purecall is found as the
               target that the most tables share in slot position, or given
               with --purecall=0x...

  ARGS      -- each slot's target is decoded far enough to read its `ret $N`,
               giving the callee's popped-argument count. A header's declared
               argument counts, read down the slots, are a fingerprint that
               confirms a mapping independently of any name: iltcursor.h's
               1,1,1,2,1,1,1,0 matched the shipped image slot for slot, and
               that is what settled the ILTCursor base. `ret` with no operand
               is reported as `c` (cdecl or a tail jump, so no clean-up).

Usage:
  vtabaudit.py <image> [--purecall=0xADDR] [--min=3] [--csv=out.csv]
                       [--at=0xADDR]        # only the table containing this
"""
import collections
import csv
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from enumfuncs import Image  # noqa: E402


def pointer_runs(img, min_len):
    """Every run of >= min_len consecutive dwords pointing into .text.

    The section name travels with the run, because not every such run is a
    vtable: `.CRT$XC` is an array of 53 static-initialiser thunks in
    lithtech.exe and looked like a 53-slot table with nothing done, which
    is a worklist of 53 functions that do not exist.
    """
    runs = []
    for name, va, vs, rs, rp in img.secs:
        if name == ".text":
            continue
        blob = img.d[rp:rp + min(vs, rs)]
        cur = []
        for o in range(0, len(blob) - 3, 4):
            v = struct.unpack_from("<I", blob, o)[0]
            if img.tlo <= v < img.thi:
                cur.append((img.base + va + o, v))
            else:
                if len(cur) >= min_len:
                    runs.append((name, cur))
                cur = []
        if len(cur) >= min_len:
            runs.append((name, cur))
    return runs


def referenced_addrs(img, lo, hi):
    """Addresses in [lo,hi) that appear as a 4-byte immediate in .text.

    A constructor stores its vptr as an immediate, whatever the addressing
    mode -- `c7 06`, `c7 00`, `c7 40 xx`, `c7 45 xx`, `c7 83 xx xx xx xx`.
    Rather than enumerate the forms, this scans every 4-byte window and
    keeps the ones that land on a table candidate; a false positive has to
    be four bytes that happen to equal a table address, which the caller
    filters by requiring the hit to sit inside a pointer run anyway.
    """
    seen = collections.Counter()
    t = img.text
    for o in range(len(t) - 3):
        v = struct.unpack_from("<I", t, o)[0]
        if lo <= v < hi:
            seen[v] += 1
    return seen


def ret_pops(img, va):
    """The callee's popped-argument count: N from `ret $N`, or None.

    Walks forward from the entry to the first 0xC3/0xC2, which is enough for
    the small forwarders that fill these tables, and gives up after 256
    bytes rather than mis-report. 0xE9 (a tail jump) is reported as a jump:
    such a slot cleans nothing itself.
    """
    off = img.rva2off(va - img.base)
    if off is None:
        return None
    end = min(off + 256, len(img.d))
    i = off
    while i < end:
        b = img.d[i]
        if b == 0xC3:
            return 0
        if b == 0xC2:
            n = struct.unpack_from("<H", img.d, i + 1)[0]
            # A `ret $N` popping more than 64 bytes is not a real argument
            # list, it is a 0xC2 reached inside data or a mis-stepped
            # instruction. Report unknown rather than a nonsense arity --
            # one slot came back as "args 12450".
            return n if n <= 64 and n % 4 == 0 else None
        if b == 0xE9:
            return "j"
        i += 1
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) if "=" in a else (a, True)
                for a in sys.argv[1:] if a.startswith("--"))
    if not args:
        sys.exit(__doc__)
    img = Image(args[0])
    min_len = int(opts.get("--min", 3))

    runs = pointer_runs(img, min_len)
    if not runs:
        sys.exit("no pointer runs found")
    lo = min(r[1][0][0] for r in runs)
    hi = max(r[1][-1][0] for r in runs) + 4
    refs = referenced_addrs(img, lo, hi)

    # _purecall: the target appearing in the MOST SLOTS across all tables.
    # An abstract class's vftable is purecall in every slot it does not
    # implement, so that target dominates by a wide margin. (Counting only
    # slot 0 does NOT work -- it picked an ordinary function on the first
    # run, because concrete tables' slot 0 is a destructor and abstract
    # ones are outnumbered.) Verified structurally: the winner should be
    # `push $0x19; call <CRT>; pop %ecx; ret`, 0x19 being _RT_PUREVIRT.
    if "--purecall" in opts:
        pure = int(opts["--purecall"], 16)
    else:
        allslots = collections.Counter(t for _, r in runs for _, t in r)
        pure = allslots.most_common(1)[0][0] if allslots else 0

    tables = []
    for sec, run in runs:
        addrs = [a for a, _ in run]
        cuts = [i for i, a in enumerate(addrs) if a in refs]
        if not cuts:
            tables.append((run[0][0], run, False, sec))
            continue
        if cuts[0] != 0:
            tables.append((run[0][0], run[:cuts[0]], False, sec))
        for j, c in enumerate(cuts):
            end = cuts[j + 1] if j + 1 < len(cuts) else len(run)
            tables.append((addrs[c], run[c:end], True, sec))

    want = int(opts["--at"], 16) if "--at" in opts else None
    rows = []
    print(f"_purecall taken as {pure:#010x} "
          f"(override with --purecall=0x...)\n")
    for base, slots, referenced, sec in tables:
        if want is not None and not (base <= want < base + 4 * len(slots)):
            continue
        npure = sum(1 for _, t in slots if t == pure)
        kind = ("ABSTRACT" if npure else "concrete")
        tag = "" if referenced else "  UNREFERENCED"
        print(f"{base:#010x}  {sec:<9} {len(slots):>3} slots  {kind}"
              f"{'  (%d pure)' % npure if npure else ''}"
              f"  stored {refs.get(base, 0)}x{tag}")
        for i, (_, tgt) in enumerate(slots):
            n = ret_pops(img, tgt)
            a = "?" if n is None else ("jmp" if n == "j" else str(n // 4))
            print(f"    [{i:>3}] {tgt:#010x}  args {a:>3}"
                  f"{'   _purecall' if tgt == pure else ''}")
            rows.append([f"0x{base:08x}", sec, i, f"0x{tgt:08x}", a, kind])
        print()

    if opts.get("--csv"):
        with open(opts["--csv"], "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["table", "section", "slot", "target", "args", "kind"])
            w.writerows(rows)
        print(f"wrote {opts['--csv']}")


if __name__ == "__main__":
    main()
