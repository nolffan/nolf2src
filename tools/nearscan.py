#!/usr/bin/env python3
"""Classify a whole near worklist in one pass, so the list can be triaged.

Runs `fndiff`/`libfndiff` over every near of a target and prints one line per
function: the two sizes, the residual block count, and a *class* guess derived
from the mnemonic-count difference between the two sides. The classes are the
ones catalogued in guides/09, and the point of the report is to separate the
nears that are worth a source experiment from the ones that are the register
allocator's:

  CALL        the two sides disagree on how many calls they make - always a
              source fact (a missing statement, a wrong prototype, a free
              function where the shipped code has a thiscall). Work these first.
  STORE       a member/frame store on one side with no counterpart. Usually a
              statement the shipped source did or did not have.
  FRAME       `sub $N,%esp` differs, or every differing byte is a displacement:
              a local model or slot-assignment question.
  FPU         the same arithmetic with a different memory-vs-x87-stack split.
  COUNT-EXACT same size and same instruction count: the shape is right and the
              residual belongs below the source. Write it up and stop.
  REGS        same mnemonics throughout, different registers.

Usage:
  nearscan.py server                 # a PE target (progress.py --nears=<t>)
  nearscan.py lib ButeMgrNoMFC       # a static library (libfndiff --list)
"""
import re
import subprocess
import sys

HERE = __file__.rsplit("/", 1)[0]
OBJDIR = {"server": "src/engine/server/Release",
          "lithtech": "src/engine/lithtech/Release",
          "NOLF": "src/engine/launcher/Release"}
IMAGE = {"server": "out/reference/server.dll",
         "lithtech": "out/reference/lithtech.exe",
         "NOLF": "out/reference/NOLF.exe"}

MNEM = ("call", "push", "pop", "sub", "add", "test", "cmp", "mov", "lea",
        "fld", "fst", "fmul", "fadd", "fsub", "fdiv", "imul", "div", "xor",
        "and", "or", "inc", "dec", "shl", "sar", "not", "neg", "set", "movz",
        "movs", "rep", "fcom", "fild", "fistp")


def run(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def classify(head, out):
    lines = out.splitlines()
    S = [l.strip()[2:] for l in lines if l.strip().startswith("S ")]
    O = [l.strip()[2:] for l in lines if l.strip().startswith("O ")]
    blocks = 0
    for l in lines:
        m = re.match(r"mnemonic diff: (\d+)", l)
        if m:
            blocks = int(m.group(1))
            break
    m = re.search(r"ship (\d+) bytes / (\d+) instructions;"
                  r" ours (\d+) bytes / (\d+) instructions", out)
    ss, si, os_, oi = (int(x) for x in m.groups()) if m else (0, 0, 0, 0)

    def c(L, p):
        return sum(1 for x in L if x.split()[0].startswith(p))

    diffs = {p: (c(S, p), c(O, p)) for p in MNEM if c(S, p) != c(O, p)}
    if "call" in diffs:
        cls = "CALL"
    elif "sub" in diffs or "add" in diffs and ss == os_:
        cls = "FRAME"
    elif any(k.startswith(("fld", "fst", "fmul", "fadd", "fsub", "fdiv",
                           "fcom", "fild")) for k in diffs):
        cls = "FPU"
    elif "mov" in diffs or "movz" in diffs:
        cls = "STORE"
    elif ss == os_ and si == oi:
        cls = "COUNT-EXACT"
    elif not diffs:
        cls = "REGS"
    else:
        cls = "OTHER"
    note = " ".join(f"{k}:{a}/{b}" for k, (a, b) in sorted(diffs.items()))
    return ss, os_, si, oi, blocks, cls, note


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    rows = []
    if args[0] == "lib":
        label = args[1]
        lst = run(["python3", f"{HERE}/libfndiff.py", "--list", label])
        for l in lst.splitlines()[1:]:
            f = l.split()
            if len(f) != 4:
                continue
            sym = f[3]
            out = run(["python3", f"{HERE}/libfndiff.py", label, sym])
            rows.append((sym,) + classify(sym, out))
    else:
        t = args[0]
        lst = run(["python3", f"{HERE}/progress.py", f"--nears={t}"])
        for l in lst.splitlines()[1:]:
            f = l.split()
            if len(f) != 6 or not f[1].startswith("0x"):
                continue
            obj, sym = f[5].split(":", 1)
            out = run(["python3", f"{HERE}/fndiff.py", f[1],
                       f"{OBJDIR[t]}/{obj}", sym, f"--image={IMAGE[t]}"])
            rows.append((sym,) + classify(sym, out))

    rows.sort(key=lambda r: (r[6], abs(r[2] - r[1])))
    print(f"{'ship':>6} {'ours':>6} {'ins':>9} {'blk':>4}  {'class':<12} symbol")
    for sym, ss, os_, si, oi, blk, cls, note in rows:
        print(f"{ss:>6} {os_:>6} {si:>4}/{oi:<4} {blk:>4}  {cls:<12} {sym[:64]}")
        if note:
            print(f"{'':>34}{note}")
    from collections import Counter
    print()
    for cls, n in Counter(r[6] for r in rows).most_common():
        print(f"  {n:>4}  {cls}")


if __name__ == "__main__":
    main()
