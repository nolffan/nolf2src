#!/usr/bin/env python3
"""Bytes under STRUCTURAL reconstruction, and how well each one is proved.

The byte oracle scores a large function at zero until it is exact, and large
functions are where the remaining bytes are: 169 functions over 1000 bytes
hold 47% of everything left in this project. Reconstructing one to be
structurally right -- same control flow, same calls to the same callees in
the same order -- is real, durable work that `progress.py` reports as
nothing, which makes it invisible exactly where it matters most.

This counts it. A reconstruction enters the count by CONVENTION: a file named
`big<addr>.cpp` under src/engine/<target>/, holding the function that shipped
at 0x<addr>. The extent comes from the enumeration, the object from the build,
and the evidence from tools/callseq.py -- so nothing here is asserted by hand.

The number this prints is NOT interchangeable with progress.py's. A decoded
function is understood, not reproduced; it is credited here and nowhere else,
and the two must never be added together. `callseq` is also blind to
call-free code, so a high agreement figure on a function with a large
call-free region means less than the same figure on a call-dense one -- which
is why bytes-per-call is printed beside it.

Usage:
  decoded.py [--csv=out/progress/decoded.csv]
"""
import csv
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

IMAGES = {"d3d": "out/reference/d3d.ren",
          "server": "out/reference/server.dll",
          "lithtech": "out/reference/lithtech.exe"}
PROGRESS_NAME = {"d3d": "d3d.ren", "server": "server.dll",
                 "lithtech": "lithtech.exe"}
# the function tables build/reference.sh writes
ENUM = {"d3d": "out/reference/d3d-functions.csv",
        "server": "out/reference/server-functions.csv",
        "lithtech": "out/reference/lithtech-functions.csv"}


def main():
    opts = dict(a.split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    overrides = {}
    if os.path.exists("progress/decoded-extents.csv"):
        for r in csv.DictReader(open("progress/decoded-extents.csv")):
            # A LIST, not a single value: one big*.cpp may reconstruct more
            # than one function. big66f08.cpp holds two -- 0x10066f00 and
            # 0x10067aa0 -- and crediting it as one range measured the wrong
            # function's calls against the other's bytes.
            overrides.setdefault((r["target"], r["tail"]), []).append(
                (int(r["addr"], 16), int(r["size"])))
    # Functions already byte-identical belong to progress.py and are not
    # counted here: this figure is read beside progress.py's exact bytes, so
    # a reconstruction that has since become exact would be counted twice
    # (big21f90.cpp was, at 3,832 bytes). progress.py is the
    # authority rather than exematch (decodedlt.py's test) because it knows
    # icl's padding. A function is out only when identical rows cover its
    # WHOLE extent: a 14-byte stack-realign stub scored identical at the
    # start of a large function (0x10043e10, 0x1004b720) is not the function.
    ident = {}
    if os.path.exists("out/progress/functions.csv"):
        for r in csv.reader(open("out/progress/functions.csv")):
            if len(r) >= 4 and r[-1].strip() == "identical" and r[1].startswith("sub_"):
                try:
                    ident.setdefault(r[0], []).append((int(r[1][4:], 16), int(r[2])))
                except ValueError:
                    pass

    def exact(target, addr, size):
        rs = ident.get(PROGRESS_NAME[target], ())
        return sum(n for a, n in rs if addr <= a < addr + size) >= size

    rows, exact_skipped = [], []
    for target, image in IMAGES.items():
        d = f"src/engine/{target}"
        # Extents, with rows the suspect file calls bogus MERGED AWAY. A
        # bogus row splits a real function in two: 0x10017cee is the
        # EPILOGUE of 0x10017c14, so the enumeration lists 218 bytes and
        # then 6,486, and crediting the first alone understates the
        # function by 97%. The suspect CSV is this repo's record of which
        # rows are not function starts, so it is the right authority.
        bogus = set()
        sus = f"progress/{target}-enum-suspect.csv"
        if os.path.exists(sus):
            for r in csv.DictReader(open(sus)):
                if r.get("severity") == "bogus":
                    bogus.add(int(r["addr"], 16))
        raw = {}
        if os.path.exists(ENUM[target]):
            for r in csv.DictReader(open(ENUM[target])):
                raw[int(r["addr"], 16)] = int(r["size"])
        sizes = {}
        for a in sorted(raw):
            if a in bogus:
                continue
            n, nxt = raw[a], a + raw[a]
            while nxt in bogus and nxt in raw:
                n += raw[nxt]
                nxt += raw[nxt]
            sizes[a] = n
        for src in sorted(glob.glob(os.path.join(d, "big*.cpp"))):
            m = re.match(r"big([0-9a-f]+)\.cpp$", os.path.basename(src))
            if not m:
                continue
            # The filename carries the low hex digits, not the whole VA
            # (big48180.cpp is 0x10048180), and the image base differs per
            # target -- 0x10000000 for a DLL, 0x400000 for the exe. So
            # resolve against the enumeration rather than assuming a base:
            # exactly one enumerated start ends with these digits.
            tail = m.group(1)
            # An extent the enumeration does not carry at all. When someone
            # proves a function starts somewhere the enumeration has no row
            # for -- 0x10024090's row begins at 0x10024024, which is a
            # different function's register entry -- there is nothing to
            # resolve against. progress/decoded-extents.csv records those
            # corrections explicitly, so the number stays traceable to
            # evidence rather than being hand-entered here.
            if (target, tail) in overrides:
                parts = overrides[(target, tail)]
            else:
                cands = [a for a in sizes if f"{a:08x}".endswith(tail)]
                if len(cands) != 1:
                    print(f"  {src}: {len(cands)} enumerated starts end in "
                          f"{tail} -- skipped", file=sys.stderr)
                    continue
                parts = [(cands[0], sizes.get(cands[0]))]
            if any(not sz for _, sz in parts):
                print(f"  {src}: an extent is not in the enumeration -- "
                      f"skipped", file=sys.stderr)
                continue
            obj = os.path.join(d, "Release",
                               os.path.basename(src)[:-4] + ".obj")
            if not os.path.exists(obj):
                print(f"  {src}: no object, build it first", file=sys.stderr)
                continue
            # `sub_<addr>` is the naming convention, but a function whose
            # real name was recovered from a string carries that instead --
            # r_TransferTexture, say. Fall back to the object's largest
            # symbol, which for a one-function big*.cpp is the function.
            for addr, size in parts:
                if exact(target, addr, size):
                    exact_skipped.append((target, addr, size))
                    continue

                def run(sym):
                    return subprocess.run(
                        [sys.executable, "tools/callseq.py", image, hex(addr),
                         hex(addr + size), obj, sym],
                        capture_output=True, text=True).stdout
                out = run("sub_%x" % addr)
                if "not found in" in out or not out.strip():
                    try:
                        # The largest symbol BY BODY LENGTH. Picking by name
                        # length instead measured one function of a two-
                        # function file against the other's bytes and called
                        # the result a regression.
                        from exematch import parse_obj_masked
                        fns = parse_obj_masked(open(obj, "rb").read())
                        big = max(fns, key=lambda n: len(fns[n][0]))
                        out = run(re.sub(r"^\?", "", big).split("@")[0])
                    except Exception:
                        pass
                ship = ours = agree = 0
                for line in out.splitlines():
                    g = re.search(r"shipped calls\s+(\d+)\s+ours\s+(\d+)", line)
                    if g:
                        ship, ours = int(g.group(1)), int(g.group(2))
                    g = re.search(r"in agreement\s+(\d+)", line)
                    if g:
                        agree = int(g.group(1))
                rows.append((target, addr, size, ship, ours, agree))

    # Reconstructions that LEFT their big<addr>.cpp -- moved into another
    # file because a /Qip register call needs caller and callee in one
    # translation unit -- keep their credit through an explicit record,
    # progress/decoded-moved.csv (target, addr, size, file, symbol, why):
    # the filename convention cannot find them any more.
    moved = "progress/decoded-moved.csv"
    if os.path.exists(moved):
        for r in csv.DictReader(open(moved)):
            target, addr, size = r["target"], int(r["addr"], 16), int(r["size"])
            if exact(target, addr, size):
                exact_skipped.append((target, addr, size))
                continue
            obj = os.path.join(f"src/engine/{target}", "Release",
                               r["file"][:-4] + ".obj")
            if not os.path.exists(obj):
                print(f"  {r['file']}: no object, build it first", file=sys.stderr)
                continue
            out = subprocess.run(
                [sys.executable, "tools/callseq.py", IMAGES[target], hex(addr),
                 hex(addr + size), obj, r["symbol"]],
                capture_output=True, text=True).stdout
            ship = ours = agree = 0
            for line in out.splitlines():
                g = re.search(r"shipped calls\s+(\d+)\s+ours\s+(\d+)", line)
                if g:
                    ship, ours = int(g.group(1)), int(g.group(2))
                g = re.search(r"in agreement\s+(\d+)", line)
                if g:
                    agree = int(g.group(1))
            rows.append((target, addr, size, ship, ours, agree))

    if not rows:
        sys.exit("no big<addr>.cpp reconstructions found")
    print(f"{'target':<10}{'addr':>12}{'bytes':>9}{'calls':>7}{'agree':>7}"
          f"{'':>3}{'B/call':>7}")
    print("-" * 56)
    tb = tc = ta = 0
    for target, addr, size, ship, ours, agree in rows:
        pct = f"{100*agree//max(ship,1)}%"
        print(f"{target:<10}0x{addr:08x}{size:>9,}{ship:>7}{agree:>7}"
              f"{pct:>5}{size/max(ship,1):>7.0f}")
        tb += size; tc += ship; ta += agree
    print("-" * 56)
    print(f"{'TOTAL':<10}{'':>10}{tb:>9,}{tc:>7}{ta:>7}"
          f"{100*ta//max(tc,1):>4}%")
    print(f"\n{tb:,} bytes decoded across {len(rows)} functions, "
          f"{ta} of {tc} calls in agreement.")
    print("NOT interchangeable with progress.py's byte count: these are "
          "understood, not reproduced.")
    for t, a, n in exact_skipped:
        print(f"  not counted, already byte-identical: {t} 0x{a:08x} ({n:,} bytes)")


    if "--csv" in opts:
        with open(opts["--csv"], "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["target", "addr", "bytes", "shipped_calls",
                        "our_calls", "calls_agree"])
            for t, a, s, sh, o, ag in rows:
                w.writerow([t, f"0x{a:08x}", s, sh, o, ag])
        print(f"wrote {opts['--csv']}")


if __name__ == "__main__":
    main()
