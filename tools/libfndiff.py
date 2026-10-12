#!/usr/bin/env python3
"""fndiff for library COMDATs: our .lib against the shipped .lib, by symbol.

The lithshared libraries ship with their symbol tables intact, so a near
there needs no address pairing — the two sides are matched by mangled name.
This is fndiff's report (byte identity with relocations masked, the mnemonic
diff, the best callee-saved renaming, the fingerprint hints) for one such
symbol.

The shipped libraries come from the NOLF Source Code v1.003 release, found
through $NOLF2_SOURCE exactly as tools/progress.py finds them (and checked
against progress/shipped-libs.sha256); ours from src/lithshared/out/.

Usage:
  libfndiff.py <label> <symbol-substr>          # both libs found by label
  libfndiff.py --list <label>                   # every near in that library

  NOLF2_SOURCE=<dir> libfndiff.py ButeMgrNoMFC SetDouble
"""
import glob
import os
import re
import subprocess
import sys
import tempfile

HERE = __file__.rsplit("/", 1)[0]
REPO = os.path.dirname(os.path.abspath(HERE))
sys.path.insert(0, HERE)
from libextract import extract                      # noqa: E402
from objdiff import parse_obj                       # noqa: E402
import fndiff                                       # noqa: E402

OURS = "src/lithshared/out/{}.lib"


def ship_path(label):
    from progress import shipped_lib_dir
    d = shipped_lib_dir()
    if d is None:
        sys.exit("libfndiff.py: set NOLF2_SOURCE to the NOLF Source Code v1.003 "
                 "release (see progress/README.md)")
    return os.path.join(d, label + ".lib")


def members(path, td):
    extract(path, td)
    return sorted(glob.glob(td + "/*"))


def sym_map(path, td):
    """{symbol: member_path} plus {symbol: masked_code}."""
    where, code = {}, {}
    for m in members(path, td):
        d = parse_obj(open(m, "rb").read())
        for k, v in d.items():
            where.setdefault(k, m)
            code.setdefault(k, v)
    return where, code


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--list" in sys.argv:
        label = args[0]
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            _, ours = sym_map(os.path.join(REPO, OURS.format(label)), t1)
            _, ship = sym_map(ship_path(label), t2)
        rows = [(len(ours[k]) - len(v), len(v), len(ours[k]), k)
                for k, v in ship.items() if k in ours and ours[k] != v]
        rows.sort(key=lambda r: (abs(r[0]), r[1]))
        print(f"{'ship':>6} {'ours':>6} {'delta':>6}  symbol")
        for d, s, o, k in rows:
            print(f"{s:>6} {o:>6} {d:>+6}  {k}")
        print(f"\n{len(rows)} near-matches"
              f" ({sum(1 for r in rows if r[0] == 0)} size-exact)")
        return

    if len(args) != 2:
        sys.exit(__doc__)
    label, want = args
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        ow, oc = sym_map(os.path.join(REPO, OURS.format(label)), t1)
        sw, sc = sym_map(ship_path(label), t2)
        hits = [k for k in sc if want in k and k in ow]
        if len(hits) != 1:
            for k in sorted(hits):
                print(k)
            sys.exit(f"{len(hits)} symbols match {want!r}; be more specific")
        sym = hits[0]
        print(sym)
        ship = fndiff.parse_listing(
            fndiff.run(["python3", f"{HERE}/dumpfn.py", sw[sym], sym]))
        ours = fndiff.parse_listing(
            fndiff.run(["python3", f"{HERE}/dumpfn.py", ow[sym], sym]))
    if not ship or not ours:
        sys.exit("empty listing")

    sl = sum(len(b) for _, b, _, _ in ship)
    ol = sum(len(b) for _, b, _, _ in ours)
    print(f"ship {sl} bytes / {len(ship)} instructions;"
          f" ours {ol} bytes / {len(ours)} instructions")
    if sl == ol and len(ship) == len(ours):
        bad = [(sa, sb, oa, ob)
               for (sa, sb, _, _), (oa, ob, _, _) in zip(ship, ours)
               if len(sb) != len(ob)
               or any(x != y and y != "00" and x != "00"
                      for x, y in zip(sb, ob))]
        print(f"{len(bad)} instruction(s) differ at byte level:")
        for sa, sb, oa, ob in bad[:10]:
            print(f"  ship {sa}: {' '.join(sb)}   ours {oa}: {' '.join(ob)}")

    a, b = fndiff.norm(ship), fndiff.norm(ours)
    blocks = fndiff.opblocks(a, b)
    print(f"\nmnemonic diff: {len(blocks)} block(s)")
    for t, S, O in blocks[:25]:
        print(f"[{t}]")
        for x in S:
            print("  S", x)
        for x in O:
            print("  O", x)
    S = [x for _, ss, _ in blocks for x in ss]
    O = [x for _, _, oo in blocks for x in oo]
    hints = [h for cond, h in fndiff.HINTS if cond(S, O)]
    if hints:
        print("\nhints:")
        for h in hints:
            print("  *", h)


if __name__ == "__main__":
    main()
