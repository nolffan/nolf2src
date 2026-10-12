#!/usr/bin/env python3
"""Count structurally-decoded bytes in an MSVC target (lithtech.exe).

tools/decoded.py does this for d3d.ren, where every reconstruction lives in a
file named `big<addr>.cpp` so the shipped address is implicit. lithtech.exe's
sources are real translation units full of properly-named functions, so the
address has to be supplied: this reads an explicit mapping produced by
harvesting address citations out of the sources and validating each one
against the enumeration and the built objects.

WHY THE BAR IS HIGHER HERE THAN FOR d3d. d3d's `big<addr>.cpp` files are each
a deliberate reconstruction with a written evidence trail, so decoded.py
credits all of them and reports agreement alongside. lithtech's unmatched
functions are simply source that exists -- some of it excellent, some of it
old, some of it possibly wrong -- and crediting all of it as "decoded" would
claim work that has not been demonstrated. So a function counts here ONLY if
its call sequence agrees with the shipped function's in full:

    DECODED   shipped_calls > 0 and every call agrees, by target or position.
              Same callees, same order: structurally correct.
    PARTIAL   some calls agree. Reported, not counted. This is where a
              function whose middle has diverged shows up.
    BLIND     the shipped function makes no calls, so callseq is VACUOUS and
              proves nothing. Reported, never counted -- on d3d such functions
              were carried by a census, a frame decomposition and a literal
              pool, and nothing here has done that work.

The figure this prints is NOT interchangeable with progress.py's byte count
and the two must never be added: a decoded function is understood, not
reproduced. A function that is byte-identical belongs to progress.py and must
not appear in the mapping at all -- the tool rejects it if it does.

Usage:
  decodedlt.py progress/lithtech-decoded-map.csv [--csv=out/progress/lithtech-decoded.csv]
              [--verbose]
"""
import csv
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = "out/reference/lithtech.exe"
OBJDIR = "src/engine/lithtech/Release"


def measure(addr, size, obj, sym):
    """Ordered call-sequence comparison for one function."""
    out = subprocess.run(
        [sys.executable, f"{ROOT}/tools/callseq.py", f"{ROOT}/{IMAGE}",
         hex(addr), hex(addr + size), f"{ROOT}/{OBJDIR}/{obj}", sym],
        capture_output=True, text=True).stdout
    m = re.search(r"shipped calls\s+(\d+)\s+ours\s+(\d+)", out)
    g = re.search(r"in agreement\s+(\d+)", out)
    if not m or not g:
        return None
    return int(m.group(1)), int(m.group(2)), int(g.group(1))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a.split("=", 1) if "=" in a else (a, True)
                for a in sys.argv[1:] if a.startswith("--"))
    if len(args) != 1:
        sys.exit(__doc__)

    # Addresses that are already byte-identical belong to progress.py. If one
    # appears in the mapping it is a harvesting error, not a decoded function,
    # and silently counting it would double-count a function in two metrics.
    matched = set()
    em = subprocess.run(
        [sys.executable, f"{ROOT}/tools/exematch.py", f"{ROOT}/{IMAGE}"] +
        [os.path.join(ROOT, OBJDIR, f)
         for f in sorted(os.listdir(os.path.join(ROOT, OBJDIR)))
         if f.endswith(".obj")],
        capture_output=True, text=True).stdout
    for mm in re.finditer(r"MATCH (0x[0-9a-f]+)", em):
        matched.add(int(mm.group(1), 16))

    rows, bad = [], []
    for r in csv.DictReader(open(args[0])):
        addr = int(r["addr"], 16)
        size = int(r["ship_size"])
        if addr in matched:
            bad.append((r["symbol"], "already byte-identical"))
            continue
        got = measure(addr, size, r["object"], r["symbol"])
        if got is None:
            bad.append((r["symbol"], "callseq gave no figure"))
            continue
        ship, ours, agree = got
        tier = ("blind" if ship == 0 else
                "decoded" if agree == ship else "partial")
        rows.append((tier, addr, size, ship, ours, agree,
                     r["object"], r["symbol"], r.get("evidence", "")))

    rows.sort(key=lambda x: (x[0], -x[2]))
    if "--verbose" in opts:
        print(f"{'tier':<9}{'addr':<12}{'bytes':>7}{'ship':>6}{'agree':>6}"
              f"  symbol")
        for t, a, sz, sh, ou, ag, ob, sy, ev in rows:
            print(f"{t:<9}0x{a:08x}{sz:>7}{sh:>6}{ag:>6}  {sy[:48]}")

    tot = {}
    for t, a, sz, sh, ou, ag, ob, sy, ev in rows:
        d = tot.setdefault(t, [0, 0, 0, 0])
        d[0] += 1; d[1] += sz; d[2] += sh; d[3] += ag
    print()
    for t in ("decoded", "partial", "blind"):
        if t in tot:
            n, b, sh, ag = tot[t]
            extra = f", {ag} of {sh} calls" if sh else ""
            print(f"  {t:<9} {n:>5} functions  {b:>8,} bytes{extra}")
    d = tot.get("decoded", [0, 0, 0, 0])
    print(f"\n{d[1]:,} bytes decoded across {d[0]} functions "
          f"({d[3]} of {d[2]} calls in agreement).")
    print("NOT interchangeable with progress.py's byte count: these are "
          "understood, not reproduced.")
    if bad:
        print(f"\n{len(bad)} mapping rows rejected:")
        seen = {}
        for s, why in bad:
            seen[why] = seen.get(why, 0) + 1
        for why, n in sorted(seen.items(), key=lambda x: -x[1]):
            print(f"    {n:>5}  {why}")

    if "--csv" in opts:
        with open(opts["--csv"], "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["tier", "addr", "bytes", "shipped_calls",
                        "our_calls", "calls_agree", "object", "symbol",
                        "evidence"])
            for t, a, sz, sh, ou, ag, ob, sy, ev in rows:
                w.writerow([t, "0x%08x" % a, sz, sh, ou, ag, ob, sy, ev])
        print(f"wrote {opts['--csv']}")


main()
