#!/usr/bin/env python3
"""List the shipped functions no object of ours accounts for -- ALL hits, not one.

exematch answers "does this COMDAT appear in the image", and for the scoreboard
it credits each symbol to ONE address. That is the right rule for counting and
the wrong rule for picking work, because a function whose bytes are identical
to a sibling's occurs several times and only the first occurrence is credited.
ServerModelLT has four such: SetPlaying, SetCurAnim, SetLooping and
SetWeightSet are the same 110 bytes, so three of their four shipped addresses
look like to-do and are in fact already written and already correct.

So this walks every COMDAT over the whole .text and marks EVERY offset it
matches, then reports the enumerated functions left over. It also drops rows
whose address is mentioned anywhere in src/engine/<target>/, since a function
already written up under an address comment is not new work either.

ONE MORE CATEGORY, and it used to hide inside "untouched": a function whose
COMDAT has fewer than eight unmasked bytes cannot be placed by exematch at
all, so the loop above skips it and the shipped address it belongs to looked
like new work. It is not. A thirteen-byte `GenRemoveAll` is
`push &g_DefAlloc; push $0; call SetSize2; ret` -- eight of those bytes are
relocations, five are not -- and server.dll has thirty-four of them. So this
also tests every candidate against the SHORT symbols by shape (same length,
every byte outside the mask equal) and reports what that claims separately,
as `unverifiable`: we have the source, the oracle cannot confirm it, and no
amount of further work will move the row. In server.dll that is 58 of the 130
rows under 32 bytes. Do not read the untouched count as remaining work
without subtracting it, and use --show-unverifiable to see which symbol
claims each one.

What is left after all four filters is genuinely untouched, and the `source`
column is worth reading before trusting a row: `gap` means the extent came
from elimination rather than from a reference, and tools/enumcheck.py will
say whether the row is sound at all.

Usage:
  uncovered.py <target> [--lo=0x..] [--hi=0x..] [--min=24] [--max=400] ...
  uncovered.py <image> <objdir> <starts.csv> [--lo=0x..] [--hi=0x..]
                                             [--min=24] [--max=400] [--csv=out]
                                             [--show-unverifiable]
                                             [--also=dir[,dir...]]

A FIFTH CATEGORY, and an easy one to miss: an
image links STATIC LIBRARIES as well as its own objects, and a function that
lives in one of those is already written -- just not in <objdir>. lithtech.exe
links StdLith.lib, and stdlith's `sb_Init2` reached a worklist as untouched
work because nothing under src/engine/ mentions it. Pass the library build
directories with --also so their COMDATs count as covered too:

  --also=src/lithshared/stdlith/Release,src/lithshared/lith/Release

A SIXTH CATEGORY, and it is the one that would have cost the most: the region
ABOVE an image's app boundary is the statically linked CRT. It is real code and
nothing of ours covers it, so it looked exactly like untouched work -- a sweep
of lithtech.exe put `acos` and the "Microsoft Visual C++ Runtime Library" error
path at the top of the worklist by density. progress.py has carried the
boundary per image all along (tools/progress.py APP_REGION, derived by matching
server.dll's established CRT tail into the other images byte for byte), so the
default --lo/--hi now come from there, keyed on the image's basename, instead of
from server.dll's constants. An image with no entry keeps the old default and
says so. Pass --lo/--hi explicitly to override, and --crt to list what the
boundary excluded rather than dropping it silently.

NOLF2: the target (its label, stem or image path: `uncovered.py Lithtech`)
is looked up in progress/targets.py (tools/tgt.py). Its shipped image, its
function table (out/reference/<stem>-functions.csv), the object directories
and static libraries of our link (the .rsp beside our image: no --also
needed) and its regions come from there: a row counts only where
progress.region() says `app`, so D3DX (`middleware`), the SecuROM pages
(`encrypted`) and the runtime (`crt`) are never offered as work, and a
second `app` range is honoured. The address comments scanned are the
target's `cited_src` (else CITED_SRC), or the objects' source tree's parent
when the target cites nothing. The three-argument form still works.
"""
import bisect
import subprocess
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402
from libextract import extract  # noqa: E402
import tgt as tools_tgt  # noqa: E402


def _objects(dirs):
    """Every .obj in each directory; a .lib named instead of a directory
    is unpacked into a scratch directory under out/ first."""
    out = []
    for d in dirs:
        if d.lower().endswith(".lib") and os.path.isfile(d):
            dest = os.path.join("out", "uncovered-lib",
                                os.path.basename(d).rsplit(".", 1)[0])
            os.makedirs(dest, exist_ok=True)
            extract(d, dest)
            out += sorted(glob.glob(os.path.join(dest, "*.obj")))
        else:
            out += sorted(glob.glob(os.path.join(d, "*.obj")))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # `a.split("=", 1) if "=" in a else (a, True)` so a bare flag works
    # alongside the --key=value options.
    opts = dict(a.split("=", 1) if "=" in a else (a, True)
                for a in sys.argv[1:] if a.startswith("--"))
    tgt = None
    if len(args) == 1:
        tgt = tools_tgt.find(args[0])
        os.chdir(tools_tgt.REPO)
        image = tgt["shipped"]
        starts = tools_tgt.funcs_csv(tgt)
        tools_tgt.require_built(tgt)
        dirs = tools_tgt.objdirs(tgt)
        objdir = dirs[0]
        extra = dirs[1:] + tools_tgt.libs(tgt)
        if extra and "--also" not in opts:
            opts["--also"] = ",".join(dict.fromkeys(extra))
        if "--src" not in opts and tools_tgt.cited_src(tgt):
            opts["--src"] = ",".join(tools_tgt.cited_src(tgt))
    elif len(args) == 3:
        image, objdir, starts = args
        tgt = tools_tgt.find_or_none(image)
    else:
        sys.exit(__doc__)
    # Rows the enumeration gets WRONG. An address that is really an operand
    # byte, or a jump target inside a function, looks exactly like a function
    # start to enumfuncs, and every reconstruction pass that has been handed
    # one has spent real analysis before recognising it. progress/*-enum-
    # suspect.csv carries the verdicts -- tools/enumcheck.py's automated ones
    # plus the rows confirmed by hand -- and `bogus` rows are dropped here so
    # they never reach a worklist again. Pass --keep-bogus to see them.
    oversize = []            # in range, unclaimed, but above --max
    bogus = set()
    # Derived from the IMAGE, not from the starts filename: the verdicts are
    # curated (progress/), the starts table is generated (out/reference/).
    sus = ("progress/%s-enum-suspect.csv"
           % os.path.basename(image).split(".")[0])
    if os.path.exists(sus) and not opts.get("--keep-bogus"):
        for r in csv.DictReader(open(sus)):
            if r.get("severity") == "bogus":
                bogus.add(int(r["addr"], 16))

    # The app/CRT boundary is progress.py's, not a second opinion: a worklist
    # that disagreed with the scoreboard about what counts as our code would
    # send people to write functions the scoreboard will never credit.
    region = tools_tgt.app_span(tgt) if tgt else None
    if region is None:
        sys.exit(f"{image}: not a target of progress/targets.py with an "
                 f"`app` range; pass --lo/--hi")
    lo = int(opts.get("--lo", hex(region[0])), 16)
    hi = int(opts.get("--hi", hex(region[1])), 16)
    nmin = int(opts.get("--min", 24))
    nmax = int(opts.get("--max", 400))

    pe = Pe(image)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp:trp + tvs]

    # Object directories beyond <objdir>: the static libraries the image
    # links. Their functions are written and must not be offered as new work.
    objdirs = [objdir]
    for d in (opts.get("--also") or "").split(","):
        if d.strip():
            objdirs.append(d.strip())

    covered = set()
    spans = []                    # (start, end, name) of every placed COMDAT
    # The symbols exematch cannot place, indexed by the length it would
    # compare -- trailing 0x90/0xCC is COMDAT padding, not the function.
    short = {}
    for obj in _objects(objdirs):
        try:
            fns = parse_obj_masked(open(obj, "rb").read())
        except Exception:
            continue
        for name, (code, mask) in fns.items():
            if len(code) - len(mask) < 8:
                end = len(code)
                while end > 0 and code[end - 1] in (0x90, 0xCC):
                    end -= 1
                if end:
                    short.setdefault(end, []).append(
                        (name, os.path.basename(obj), code, mask))
                continue
            # Record the SPAN, not just the start. A row whose address falls
            # strictly INSIDE a function we already match is not new work --
            # it is an enumeration artefact (an ASCII accident, a shared tail,
            # an interior jump target). Two of six rows in cluster 0x00454000
            # were exactly this, both inside byte-identical functions, and
            # nothing here noticed because only starts were being tested.
            end = len(code)
            while end > 0 and code[end - 1] in (0x90, 0xCC):
                end -= 1          # COMDAT padding is not part of the body
            for hit in find(text, tva, code, mask):
                covered.add(hit)
                if end:
                    spans.append((hit, hit + end, name))


    # A row that progress.py pairs to one of our symbols as a NEAR is not
    # new work either -- we HAVE the function, its bytes just differ. This
    # was the sixth defect found in this screen and the largest: our sources
    # cite the server.dll /O1 address of a shared-TU function and never the
    # lithtech /O2 one, so a near in lithtech has neither a matching COMDAT
    # nor an address comment and read as untouched. One cluster came back
    # with all twelve of its rows already written.
    nears = {}
    bridged = {}
    try:
        base = tgt["label"] if tgt else os.path.basename(image)
        out = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "progress.py"),
             "--nears=" + base],
            capture_output=True, text=True, timeout=1800).stdout
        for line in out.splitlines():
            f = line.split()
            if len(f) >= 6 and f[1].startswith("0x"):
                nears[int(f[1], 16)] = f[-1]
    except Exception as e:
        print(f"  (near pairing unavailable: {e})")

    # HAND-RECORDED EXCLUSIONS. progress/<image>-screen-exclude.csv is where
    # a finding that a row is already written gets made PERMANENT, so it is
    # never rediscovered by the next person at the same address. Each row
    # carries its reason.
    excluded = {}
    xname = ("progress/%s-screen-exclude.csv"
             % os.path.basename(image).split(".")[0])
    if os.path.exists(xname):
        for r in csv.DictReader(open(xname)):
            a = (r.get("addr") or "").strip().lower()
            if a.startswith("0x"):
                excluded[int(a, 16)] = (r.get("reason") or "").strip()

    spans.sort()
    _span_starts = [t[0] for t in spans]

    def interior_of(a):
        """The matched function this address falls strictly inside, if any."""
        i = bisect.bisect_right(_span_starts, a)
        # Spans can nest or overlap (identical bodies at several addresses),
        # so walk back far enough to clear the longest one seen.
        for st, en, nm in reversed(spans[max(0, i - 64):i]):
            if st < a < en:
                return (st, nm)
        return None

    def claimed_by_short(a, n):
        """The short symbol whose shape fits this address, if any."""
        off = a - tva
        if off < 0 or off + n > len(text):
            return None
        for name, obj, code, mask in short.get(n, ()):
            if all(i in mask or text[off + i] == code[i] for i in range(n)):
                return (name, obj)
        return None

    # Anything already written up under an address comment is not new work.
    #
    # THE SHARED-TU GAP. This used to glob only `os.path.dirname(objdir)`, i.e. src/engine/lithtech.
    # But lithtech.exe COMPILES ~40 translation units out of src/engine/server
    # (build/engine.sh's lithtech target lists them as ..\server\*.cpp), and
    # those files cite their CLIENT addresses in comments perfectly well --
    # 0x00451720, 0x00451e10, 0x004526f0, 0x00452cd0 all appear verbatim in
    # src/engine/server/commonphysics.cpp. The citations existed; the scanner
    # was pointed at one directory, and five functions that were all already
    # written came back as work.
    #
    # `--also` does not help: it extends objdirs, never the source scan. So
    # scan every src/engine subdirectory by default, and let --src= override.
    srcdirs = [d for d in (opts.get("--src") or "").split(",") if d]
    if not srcdirs:
        base = os.path.dirname(os.path.dirname(objdir.rstrip("/")))
        srcdirs = [d for d in glob.glob(os.path.join(base, "*"))
                   if os.path.isdir(d)] or [os.path.dirname(objdir.rstrip("/"))]
    blob = ""
    for srcdir in srcdirs:
        for root, _, fs in os.walk(srcdir):
            for f in fs:
                if f.lower().endswith((".cpp", ".c", ".h")):
                    blob += open(os.path.join(root, f), encoding="utf-8",
                                 errors="replace").read()
    mentioned = {m.lower() for m in re.findall(r"0x[0-9a-fA-F]{8}", blob)}

    # SECOND GAP: a row already carried in the decoded map is work someone has
    # done, whether or not any comment cites its address. 0x00453f90 is cited
    # nowhere and is nonetheless wm_SetObjectDims, written at
    # commonphysics.cpp:438.
    #
    # A `bridged-*` row is NAME INFERENCE -- the address was attached through
    # a caller, a vtable slot or a function pointer rather than by matching
    # bytes -- so it is not proof. It used to stay silently on the worklist
    # for that reason, and three such rows turned out to be existing
    # worldsim.cpp functions, one of them carried here as
    # `bridged-callseq-j1.00` under its real name. The placement being
    # inferred does not make the FUNCTION unwritten.
    #
    # So bridged rows are now reported as their own category rather than
    # retired or hidden. They are work of a different kind: check the named
    # symbol first, and only reconstruct if the inference turns out wrong.
    for mapname in ("progress/%s-decoded-map.csv"
                    % os.path.basename(image).split(".")[0],):
        if os.path.exists(mapname):
            for r in csv.DictReader(open(mapname)):
                a = (r.get("addr") or "").strip().lower()
                ev = (r.get("evidence") or "")
                if not a.startswith("0x"):
                    continue
                if ev.startswith("bridged"):
                    bridged[int(a, 16)] = ((r.get("symbol") or "?"), ev)
                else:
                    mentioned.add(a)

    # A function can be written, correct, and UNMATCHED -- a documented near --
    # and if nobody wrote its address in a comment neither filter above sees
    # it. enumfuncs recovers a name for some rows from the argument-check
    # literals, so use it: if the method part of that name appears in any
    # symbol our objects define, the function exists in the source already.
    # This is what stopped ServerInterface::GetConsoleVar and
    # si_GetPropRotationEuler being offered as new work twice each.
    defined = set()
    for obj in _objects(objdirs):
        try:
            fns = parse_obj_masked(open(obj, "rb").read())
        except Exception:
            continue
        defined.update(fns)
    symblob = "\n".join(defined)

    rows = []
    unverifiable = []
    interior = []
    near_rows = []
    bridged_rows = []
    excluded_rows = []
    n_mentioned = 0
    n_named = 0
    n_bogus = 0
    for r in csv.DictReader(open(starts)):
        a = int(r["addr"], 16)
        n = int(r["size"])
        # Count what the SIZE BAND hides, separately from what the address
        # range hides. A 3.2KB run of genuinely unclaimed CCollElemC0Rec
        # functions sat unreported for the whole project because every one of
        # them is larger than the 400-byte default and nothing said so.
        if lo <= a < hi and n > nmax and a not in covered and a not in bogus:
            oversize.append((a, n))
        if not (lo <= a < hi) or not (nmin <= n <= nmax):
            continue
        if tgt and not tools_tgt.in_app(tgt, a):
            continue        # middleware, encrypted, or the runtime
        if a in bogus:
            n_bogus += 1
            continue
        if a in covered:
            continue
        if a in excluded:
            excluded_rows.append((a, n, excluded[a]))
            continue
        if a in bridged:
            bridged_rows.append((a, n) + bridged[a])
            continue
        if a in nears:
            near_rows.append((a, n, nears[a]))
            continue
        host = interior_of(a)
        if host:
            interior.append((a, n, host[0], host[1]))
            continue
        # Strongest evidence first: actual byte agreement with a symbol the
        # oracle is unable to place. Checked before the comment and name
        # filters so the count means "we have this", not "somebody wrote the
        # address down".
        hit = claimed_by_short(a, n)
        if hit:
            unverifiable.append((a, n, hit[1], hit[0]))
            continue
        if f"0x{a:08x}" in mentioned:
            n_mentioned += 1
            continue
        nm = (r.get("name") or "").strip()
        if nm:
            leaf = nm.rsplit("::", 1)[-1]
            if leaf and leaf in symblob:
                n_named += 1
                continue
        rows.append((a, n, (r.get("source") or "").strip(),
                     (r.get("name") or "").strip()))
    rows.sort(key=lambda t: t[0])
    unverifiable.sort(key=lambda t: t[0])

    print(f"{len(covered)} shipped offsets covered by our objects "
          f"(every hit, not one per symbol)")
    print(f"in [{lo:#x},{hi:#x}) of {nmin}-{nmax} bytes, excluding those:")
    print(f"  {n_bogus:>4} NOT FUNCTIONS — operand bytes or interior jump "
          f"targets the enumeration mistook for starts")
    print(f"  {len(unverifiable):>4} unverifiable — we have a same-length "
          f"mask-compatible symbol below exematch's 8-byte floor")
    print(f"  {len(excluded_rows):>4} EXCLUDED by hand — already "
          f"established as written (see progress/*-screen-exclude.csv)")
    print(f"  {len(bridged_rows):>4} BRIDGED — the decoded map names a symbol here by "
          f"inference; check it before reconstructing")
    print(f"  {len(near_rows):>4} NEAR — we have the function, the bytes differ")
    print(f"  {len(interior):>4} INSIDE a function we already match — an "
          f"enumeration artefact, not work")
    print(f"  {n_mentioned:>4} written up under an address comment")
    print(f"  {n_named:>4} matched by name against one of our symbols")
    print(f"  {len(rows):>4} UNTOUCHED — this is the remaining work\n")

    if excluded_rows and "--show-excluded" in opts:
        print("  rows excluded by hand:")
        for a, n, why in excluded_rows:
            print(f"    0x{a:08x} {n:>5}  {why[:100]}")
        print()

    if bridged_rows and "--show-bridged" in opts:
        print("  rows the decoded map places here by inference:")
        for a, n, sym, ev in bridged_rows:
            print(f"    0x{a:08x} {n:>5}  {ev:<24} {sym[:58]}")
        print()

    if near_rows and "--show-near" in opts:
        print("  rows we already have as near-matches:")
        for a, n, nm in near_rows:
            print(f"    0x{a:08x} {n:>5}  {nm}")
        print()

    if interior and "--show-interior" in opts:
        print("  rows falling strictly inside a matched function:")
        for a, n, st, nm in interior:
            print(f"    0x{a:08x} {n:>5}  inside 0x{st:08x} {nm}")
        print()
    for a, n, src, nm in rows:
        print(f"  0x{a:08x} {n:>4}  {src:<6} {nm}")

    if oversize:
        tot = sum(n for _, n in oversize)
        print(f"\n  NOTE: {len(oversize)} unclaimed function(s) totalling "
              f"{tot:,} bytes are ABOVE --max={nmax} and not listed above.")
        print(f"  Re-run with --max={max(n for _, n in oversize) + 1} to see "
              f"them; the largest is {max(n for _, n in oversize):,} bytes at "
              f"0x{max(oversize, key=lambda r: r[1])[0]:08x}.")

    if opts.get("--show-unverifiable"):
        print(f"\nunverifiable ({len(unverifiable)}), and the symbol that "
              f"claims each:")
        for a, n, obj, name in unverifiable:
            print(f"  0x{a:08x} {n:>4}  {obj:<18} {name[:70]}")

    out = opts.get("--csv")
    if out:
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["addr", "size", "source", "name"])
            for a, n, src, nm in rows:
                w.writerow([f"0x{a:08x}", n, src, nm])
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
