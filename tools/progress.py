#!/usr/bin/env python3
"""The scoreboard: how much of every targeted binary we rebuild exactly.

The binaries, and where each one's code and ours is, are progress/targets.py:
this file knows none of them by name. For each shipped binary it enumerates
the functions (name + byte size) and classifies our build of each as:

  identical  our bytes match the shipped function exactly (reloc-masked)
  near       we have the function but bytes differ (compiler-revision variance)
  small      we have the function but it is almost entirely relocations, so
             there is nothing for the oracle to anchor on (global-initializer
             COMDATs); reconstructed, not verified
  attempted  no match and no pairing, but there is evidence the address has
             been worked on (cited in src/, or recorded in progress/*.csv)
  todo       the shipped function has no counterpart in our build yet
  unplaced   (ours, not theirs) a function of ours that our own link puts in
             our image, but that no shipped function is placed for, even by
             position (the join in _rows_for_image): WRITTEN BUT UNPLACED
  unlinked   (ours) a function our own link leaves out of our image too:
             compiled, but not part of this binary
  driver     (ours) a function only a scoring driver (DRIVER_OBJS) emits
  crt        outside the image's own code (`app`): the C runtime, import
             thunks and exception funclets: listed, not counted
  middleware inside a third-party library linked into `app` (D3DX in the
             engine): listed, not counted
  encrypted  in code the retail image keeps encrypted (`encrypted`, the
             SecuROM pages of Lithtech.exe): listed, not counted

Coverage is the pair of counts summary.json carries per target: UNWRITTEN
(todo + attempted: shipped functions with nothing of ours placed at them)
and UNPLACED. Both at zero means every shipped function has a written,
placed counterpart -- near or identical -- and nothing of ours is left
over; tools/ratchet.py keeps either from going up (and `check --covered`
requires both at zero). unplaced, unlinked and driver rows are ours, not
shipped functions: none of them is in the denominator.

Ground truth is always the SHIPPED binary, so the denominator can't drift:
the retail images build/reference.sh extracts into out/reference/. A
resource-only image is scored resource by resource (rows_for_resources). A
binary with no build of ours yet (the engine, until its source exists) is
enumerated all the same and scores as all unwritten. Libraries a project
can score symbol by symbol against shipped prebuilt .libs (NOLF's
lithshared) are LIBS in the config; NOLF2 has none.

What is compared is what the build left in the tree: each target's `built`
image and the objects and libraries its link read (its response file). Run
`make` first; this compiles nothing.

Outputs (under out/progress/):
  functions.csv   one row per shipped function: target, name, size, status
  summary.json    per-target and total counts + bytes

tools/ratchet.py compares those with the recorded baseline in progress/.
`make progress` runs both.

Usage:
  progress.py [--nears[=target]]
              [--todo|--attempted|--near|--small|--unplaced|--unlinked|--driver[=target]]

--nears prints the near-match worklist instead of the summary: one line per
paired function with the shipped address, both sizes and the byte delta,
closest first. That order is the order to work them in -- a function that is
already size-exact usually needs one source change, where one off by a
hundred bytes needs a different shape. --todo (and the other statuses) list
that status's rows, largest first.
"""
import bisect
import csv
import glob
import json
import os
import re
import struct
import sys
import tempfile

NEAR_PAIRS = []
# (label, shipped address) -> "module:symbol", for every function exematch
# PLACES. rows_for_image deliberately reports placed functions as `sub_<addr>`
# because the scoreboard only needs the count, so the symbol is dropped there;
# a tool labelling a disassembly needs it. Written alongside `matched` and
# read by nothing in this file, exactly as NEAR_PAIRS above.
PLACED_SYMS = {}
# The same for the "small" pass (functions too short to anchor, placed by
# shape): (label, shipped address) -> "module:symbol". Weaker evidence
# than PLACED_SYMS, so kept apart.
SMALL_SYMS = {}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objdiff import parse_obj  # noqa: E402
from libextract import extract  # noqa: E402
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402
from enumfuncs import Image as EnumImage, enumerate_functions  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "progress"))
sys.dont_write_bytecode = True     # no progress/__pycache__
import targets as cfg  # noqa: E402

REFERENCE = cfg.REFERENCE
OUT = cfg.OUT
DATA = cfg.DATA
TARGETS = cfg.TARGETS
BY_LABEL = {t["label"]: t for t in TARGETS}
LIBS = cfg.LIBS
DRIVER_OBJS = {o.lower() for o in cfg.DRIVER_OBJS}
SHIPPED_SUMS = DATA + "/shipped-libs.sha256"


def shipped_lib_dir():
    """The directory holding the shipped prebuilt .libs LIBS is scored
    against, or None: $<SHIPPED_ENV> names the extracted source release
    (the directory holding SHIPPED_LIB's path), or a directory holding the
    .libs themselves. Every library is checked against SHIPPED_SUMS: a
    library from another release would score against the wrong ground
    truth, so a mismatch is fatal rather than a skip.
    """
    if not LIBS or not cfg.SHIPPED_ENV:
        return None
    root = os.environ.get(cfg.SHIPPED_ENV, "")
    if not root:
        return None
    d = os.path.join(root, os.path.dirname(cfg.SHIPPED_LIB))
    if not os.path.isdir(d):
        d = root
    want = {}
    for line in open(os.path.join(REPO, SHIPPED_SUMS)):
        if line.strip():
            h, name = line.split()
            want[name] = h
    import hashlib
    bad = []
    for name, h in sorted(want.items()):
        p = os.path.join(d, name)
        if not os.path.isfile(p):
            bad.append("%s: missing" % name)
        elif hashlib.sha256(open(p, "rb").read()).hexdigest() != h:
            bad.append("%s: SHA-256 mismatch" % name)
    if bad:
        sys.exit("progress.py: %s=%s does not hold the shipped libraries "
                 "(%s):\n  %s" % (cfg.SHIPPED_ENV, root, SHIPPED_SUMS,
                                  "\n  ".join(bad)))
    return d


# ---------------------------------------------------------------------------
# The regions of an image (progress/targets.py: app, middleware, encrypted)

def _in(ranges, a):
    return any(lo <= a < hi for lo, hi in ranges or ())


def region(tgt, a):
    """What address a of a shipped image is: "app" (counted), or the status
    of a row there that is not: "encrypted", "middleware", "crt"."""
    if _in(tgt.get("encrypted"), a):
        return "encrypted"
    if _in(tgt.get("middleware"), a):
        return "middleware"
    if _in(tgt.get("app"), a):
        return "app"
    return "crt"


def in_app(tgt, a):
    """True when address a is the image's own code: counted."""
    return region(tgt, a) == "app"


# ---------------------------------------------------------------------------
# Our side: the build's image, its map, and what its link read

def ci_path(path):
    """`path` (relative to the repository, / or \\ separated) as it is on
    disk, matching each component without regard to case, as the Windows
    tools that wrote it did; None if there is no such file."""
    parts = [p for p in re.split(r"[\\/]+", path) if p not in ("", ".")]
    cur = REPO if not os.path.isabs(path) else "/"
    out = []
    for p in parts:
        if p == "..":
            cur = os.path.dirname(cur)
            out = out[:-1] if out and out[-1] != ".." else out + [".."]
            continue
        try:
            names = os.listdir(cur)
        except OSError:
            return None
        hit = p if p in names else next(
            (n for n in names if n.lower() == p.lower()), None)
        if hit is None:
            return None
        cur = os.path.join(cur, hit)
        out.append(hit)
    return os.path.relpath(cur, REPO)


def built_image(tgt):
    """Our build of a target (a path relative to the repository), or None."""
    pat = tgt.get("built")
    if not pat:
        return None
    hits = sorted(glob.glob(os.path.join(REPO, pat), recursive=True))
    if not hits:
        return None
    if len(hits) > 1:
        print("progress.py: %s: %d builds match %s, scoring %s" % (
            tgt["label"], len(hits), pat, os.path.relpath(hits[0], REPO)),
            file=sys.stderr)
    return os.path.relpath(hits[0], REPO)


def link_inputs(image):
    """The objects and libraries of ours the link of `image` read, from its
    response file (<image>.rsp, one argument a line) and the directory the
    link ran in (`cd <dir> &&` in <image>.cmd): every .obj and .lib that
    resolves to a file in the repository, in command-line order. A bare
    library name is looked for in the link's directory and its /libpath:s;
    the toolchain's own libraries (kernel32.lib, msvcrt.lib, ...) resolve
    to nothing here and are left out. None if there is no response file."""
    rsp = image + ".rsp"
    if not os.path.exists(os.path.join(REPO, rsp)):
        return None
    cwd = os.path.dirname(image)
    cmd = image + ".cmd"
    if os.path.exists(os.path.join(REPO, cmd)):
        m = re.match(r"\s*cd\s+(\S+)\s*&&", open(os.path.join(REPO, cmd)).read())
        if m:
            cwd = m.group(1)
    args = []
    for line in open(os.path.join(REPO, rsp), errors="replace"):
        args += [a.strip('"') for a in line.split()]
    libpaths = [cwd] + [os.path.join(cwd, a.split(":", 1)[1]) for a in args
                        if a.lower().startswith("/libpath:")]
    out = []
    for a in args:
        if a.startswith("/") or not a.lower().endswith((".obj", ".lib")):
            continue
        cands = [os.path.join(cwd, a)] if re.search(r"[\\/]", a) else \
            [os.path.join(d, a) for d in libpaths]
        for c in cands:
            p = ci_path(c.replace("\\", "/"))
            if p and p not in out:
                out.append(p)
                break
    return out


def our_map(image):
    """Our link's .map beside the image (any case), or None."""
    return ci_path(os.path.splitext(image)[0] + ".map")


def _module(lib, member):
    """The module name a function of ours is keyed by: an object's file name,
    or `lib(member)` for a library member -- the map names it `lib:member`."""
    return "%s(%s)" % (lib, member) if lib else member


def _our_layout(mapfile):
    """{(module, symbol): address} of the code in our linked image, from its
    .map (module lower-cased), or None when there is no map. Symbols the
    map lists twice (a static name in two objects) are told apart by their
    module."""
    if not mapfile or not os.path.exists(os.path.join(REPO, mapfile)):
        return None
    out = {}
    for line in open(os.path.join(REPO, mapfile), errors="replace"):
        p = line.split()
        if len(p) < 4 or not p[0].startswith("0001:") or \
                not re.fullmatch(r"[0-9a-fA-F]{8}", p[2]):
            continue
        lib, _, mem = p[-1].rpartition(":")
        out.setdefault((_module(lib, mem).lower(), p[1]), int(p[2], 16))
    return out


def load_lib(path):
    """Return {symbol: masked_code} for a .lib (via objdiff.parse_obj)."""
    out = {}
    with tempfile.TemporaryDirectory() as td:
        extract(path, td)
        for m in sorted(glob.glob(td + "/*")):
            out.update(parse_obj(open(m, "rb").read()))
    return out


def rows_for_lib(label, ours_path, libdir):
    theirs = load_lib(os.path.join(libdir, cfg.SHIPPED_AS.get(
        label, os.path.basename(cfg.SHIPPED_LIB).format(label))))
    ours = load_lib(os.path.join(REPO, ours_path)) if os.path.exists(
        os.path.join(REPO, ours_path)) else {}
    rows = []
    for name, code in theirs.items():
        if name not in ours:
            status = "todo"
        elif ours[name] == code:
            status = "identical"
        else:
            status = "near"
        rows.append((label, name, len(code), status))
    return rows


# ---------------------------------------------------------------------------
# The shipped side: the image's functions

# Trailing alignment encodings: VC6 pads with 0x90/0xCC, icl with
# multi-byte lea / mov nops.
PADS = [
    bytes.fromhex("8dbc2700000000"),
    bytes.fromhex("8db42600000000"),
    bytes.fromhex("8db600000000"),
    bytes.fromhex("8dbf00000000"),     # lea 0x0(%edi),%edi (6-byte form)
    bytes.fromhex("8d742600"),
    bytes.fromhex("8d7600"),
    bytes.fromhex("8bf6"),
    bytes.fromhex("8bff"),
    b"\x90",
    b"\xcc",
]


def strip_pad(b):
    """`b` without its trailing alignment padding (any of PADS)."""
    b = bytes(b)
    moved = True
    while moved and b:
        moved = False
        for pad in PADS:
            if b.endswith(pad):
                b = b[:-len(pad)]
                moved = True
                break
    return b


def _enum_with_sizes(path, label):
    img = EnumImage(path)
    starts, _src = enumerate_functions(img)
    # Proven starts the enumerator misses (progress/extent-splits.csv): a row
    # that is really two functions -- typically a 5/10-byte thunk and the
    # body it jumps into, which nothing else references -- can never pair.
    extra = set(_extent_splits().get(label, ())) | _REMAINDER_STARTS.get(label, set())
    if extra:
        starts = sorted(set(starts) | set(extra))
    # Rows PROVEN not to be code come out of the enumeration entirely -- see
    # _phantom_index. Sizes are computed from the ORIGINAL start list so that
    # dropping a phantom does not silently grow its neighbour's extent --
    # UNLESS the phantom's own exclude reason names the start just before it
    # as its container ("interior block of X (0x...)"). Then the bytes are
    # proven to be that function's, and leaving them off keeps a correct
    # reconstruction from ever pairing.
    phantom = _phantom_index(label)
    reasons = _phantom_reasons(label)
    sizes = {}
    for i, a in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else img.thi
        if a not in phantom:
            j = i + 1
            while j < len(starts) and starts[j] in phantom and \
                    _names_container(reasons.get(starts[j], ""), a):
                j += 1
                end = starts[j] if j < len(starts) else img.thi
        lo, hi = a - img.tlo, min(end - img.tlo, len(img.text))
        while hi > lo and img.text[hi - 1] in (0x90, 0xCC):
            hi -= 1
        sizes[a] = max(hi - lo, 0)
    if phantom:
        starts = [a for a in starts if a not in phantom]
    return img, starts, sizes


def _names_container(reason, a):
    """True if an exclude reason cites address `a` (any zero padding)."""
    for m in re.findall(r"0x0*([0-9a-fA-F]{5,8})\b", reason):
        if int(m, 16) == a:
            return True
    return False


_SPLITS = None


def _extent_splits():
    """progress/extent-splits.csv: image,addr,reason -- proven starts."""
    global _SPLITS
    if _SPLITS is not None:
        return _SPLITS
    out = {}
    try:
        for r in csv.DictReader(open(DATA + "/extent-splits.csv")):
            a = (r.get("addr") or "").strip().lower()
            if a.startswith("0x"):
                out.setdefault(r["image"].strip(), set()).add(int(a, 16))
    except OSError:
        pass
    _SPLITS = out
    return out


def _exclude_files(label):
    """progress/<stem>-screen-exclude.csv: the rows of image `label` (by its
    stem, any case) examined by hand. A file applies to its own image only:
    the images share address ranges (every DLL is based at 0x10000000)."""
    stem = BY_LABEL[label]["stem"].lower()
    return [f for f in sorted(glob.glob(DATA + "/*-screen-exclude.csv"))
            if os.path.basename(f)[:-len("-screen-exclude.csv")].lower() == stem]


_REASONS = {}


def _phantom_reasons(label):
    if label in _REASONS:
        return _REASONS[label]
    out = {}
    for f in _exclude_files(label):
        try:
            for r in csv.DictReader(open(f)):
                a = (r.get("addr") or "").strip().lower()
                if a.startswith("0x"):
                    try:
                        out[int(a, 16)] = (r.get("reason") or "")
                    except ValueError:
                        pass
        except OSError:
            pass
    _REASONS[label] = out
    return out


def _align(ours, theirs):
    """Pair two runs of functions in order, by size: ours and theirs are
    [(key, size)] in link order; the result is [(our key, their key)], each
    pair within a factor of two in size, chosen to maximise the summed
    agreement 1 - |ln(ratio)| (dynamic programming; either side may skip)."""
    import math
    n, m = len(ours), len(theirs)
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            v = max(best[i + 1][j], best[i][j + 1])
            su, sw = ours[i][1], theirs[j][1]
            if su > 0 and sw > 0 and 0.5 <= su / sw <= 2:
                v = max(v, 1 - abs(math.log(su / sw)) + best[i + 1][j + 1])
            best[i][j] = v
    out, i, j = [], 0, 0
    while i < n and j < m:
        su, sw = ours[i][1], theirs[j][1]
        if su > 0 and sw > 0 and 0.5 <= su / sw <= 2 and \
                abs(best[i][j] - (1 - abs(math.log(su / sw)) + best[i + 1][j + 1])) < 1e-9:
            out.append((ours[i][0], theirs[j][0]))
            i, j = i + 1, j + 1
        elif best[i][j] == best[i + 1][j]:
            i += 1
        else:
            j += 1
    return out


# Starts found BEHIND an identical match that is shorter than its row: see
# rows_for_image. Consumed by _enum_with_sizes alongside extent-splits.csv.
_REMAINDER_STARTS = {}


def rows_for_image(tgt, objs, mapfile, linked=None):
    """Score one image, then once more with the remainders of short matches.

    A row's size is reported as the length of what matched there, so when a
    SHORT function of ours matches at a start whose enumerated extent also
    holds more code -- icl's 14-byte stack-realign stub in front of a large
    body, or a register-entry stub whose caller's body follows -- the rest
    of the extent dropped out of funcs and bytes_total entirely, and the
    body behind a stub had no row to pair with even when we had written it.
    The code behind such a match is its own function (the match ended in a
    ret or a tail jump), so its first non-padding byte becomes a start, and
    the image is scored again with those starts added.
    """
    label = tgt["label"]
    rows = _rows_for_image(tgt, objs, mapfile, linked)
    extra = _remainders(tgt, rows)
    if extra:
        _REMAINDER_STARTS[label] = extra
        # the second pass records its own pairs: drop the first pass's
        NEAR_PAIRS[:] = [r for r in NEAR_PAIRS if r[0] != label]
        rows = _rows_for_image(tgt, objs, mapfile, linked)
    return rows


def _remainders(tgt, rows):
    label = tgt["label"]
    img, starts, sizes = _enum_with_sizes(os.path.join(REPO, tgt["shipped"]), label)
    have = set(starts)
    text, tlo = img.text, img.tlo
    out = set()
    for r in rows:
        if r[3] != "identical" or not r[1].startswith("sub_"):
            continue
        a = int(r[1][4:], 16)
        n, ext = r[2], sizes.get(a)
        if not ext or ext <= n:
            continue
        pos, end = a + n, a + ext
        moved = True
        while moved and pos < end:
            moved = False
            for pad in PADS:
                o = pos - tlo
                if text[o:o + len(pad)] == pad:
                    pos += len(pad)
                    moved = True
                    break
        # below 16 bytes it is the tail of an alignment run, not a function
        if end - pos >= 16 and pos not in have:
            out.add(pos)
    return out


def _own_addr(tgt, n, funcs=None):
    """The shipped address a symbol of ours names: `sub_<addr>` (the naming
    convention for a reconstruction of an unnamed function), or a name the
    target's own_symbols (full symbol) or own_names (a substring of the
    symbol's leaf name) maps. None if it names none. Only ever a
    preference: a placement there still needs the bytes to agree.

    An icl target, given our functions: icl's /Qip register entry `X$` (and
    the `X$$1` body behind a 14-byte stack-realigning entry) sits the stack
    entry X's length above the address X names. Without that, `sub_X$`
    preferred X -- the 4-byte stack entry, already matched -- and a large
    body whose opening bytes are the shipped X+4's lost the ranking to
    unrelated functions of similar length."""
    m = re.search(r"sub_([0-9a-f]{6,8})\b", n)
    a = int(m.group(1), 16) if m else None
    if a is None and tgt.get("own_symbols"):
        a = tgt["own_symbols"].get(n.split(":", 1)[-1])
    if a is None and tgt.get("own_names"):
        leaf = re.sub(r"^\?", "", n.split(":", 1)[-1]).split("@")[0]
        for k, v in sorted(tgt["own_names"].items(), key=lambda kv: -len(kv[0])):
            if k in leaf:
                a = v
                break
    if a is not None and tgt.get("icl") and funcs is not None:
        mod, sym = n.split(":", 1) if ":" in n else ("", n)
        leaf = re.sub(r"^\?", "", sym).split("@")[0]
        for tail in ("$$1", "$"):
            if leaf.endswith(tail):
                base = "%s:%s" % (mod, sym.replace(leaf, leaf[:-len(tail)], 1))
                if base in funcs:
                    code = funcs[base][0]
                    a += len(strip_pad(bytes(code)) if tail == "$$1" else code)
                break
    return a


def _load_objs(objs, icl=False):
    """Our functions: {module:symbol: (code, mask)}, the ones from a library
    scored on its own (LIBS), and, for icl, each padded function's bare body.

    Key by module as well as symbol: compiler-generated names are numbered
    per object, so `_$E192` exists in more than one of ours and a bare-symbol
    dict silently drops all but the last -- which loses whole initializer
    groups from the count. A library member's module is `lib(member)`, as
    the map names it."""
    funcs, unpadded, from_lib = {}, {}, set()
    scored_libs = {l.lower() for l, _p in LIBS}

    def add(mod, data, lib_scored):
        for k, v in parse_obj_masked(data).items():
            # instantiation drivers exist only to make VC6 emit template
            # COMDATs; they are ours, not Monolith's, and must neither score
            # nor pair
            if "ForceInstantiation" in k:
                continue
            # ??_H / ??_I are the vector constructor and destructor
            # iterators VC6 emits per object as a by-product of `new T[n]`
            # and `delete [] p`. With exceptions off it expands the loop
            # inline and never references them, so the linker drops them --
            # they are the compiler's code either way, not reconstructed
            # source, and scoring them counts a phantom against us.
            if k.startswith("??_H") or k.startswith("??_I"):
                continue
            key = "%s:%s" % (mod, k)
            if key in funcs:
                print("progress.py: %s is in two of the link's inputs; "
                      "scoring the first" % key, file=sys.stderr)
                continue
            # icl pads a COMDAT with multi-byte lea-nops, not 0x90/0xCC, and
            # parse_obj_masked only strips the latter; the leftover pad then
            # has to match whatever the shipped image has after the function,
            # so an identical function could never be found. Keep the bare
            # body too.
            if icl:
                code, mask = v
                body = strip_pad(code)
                if body != code:
                    unpadded[key] = (body, {i for i in mask if i < len(body)})
            funcs[key] = v
            if lib_scored:
                from_lib.add(key)

    for o in objs:
        q = os.path.join(REPO, o)
        if o.lower().endswith(".lib"):
            stem = os.path.splitext(os.path.basename(o))[0]
            with tempfile.TemporaryDirectory() as td:
                extract(q, td)
                for m in sorted(glob.glob(td + "/*")):
                    add(_module(stem, os.path.basename(m)),
                        open(m, "rb").read(), stem.lower() in scored_libs)
        else:
            add(os.path.basename(o), open(q, "rb").read(), False)
    return funcs, unpadded, from_lib


def _rows_for_image(tgt, objs, mapfile, linked_path):
    """A PE image under reconstruction (exe or dll, no symbols).

    Denominator = every enumerated function inside the image's own code
    (`app`); functions elsewhere are emitted with the status of their
    region (crt, middleware, encrypted) so they stay visible but do not
    count. identical = an exematch hit for one of our objects.
    """
    label = tgt["label"]
    icl = bool(tgt.get("icl"))
    p = os.path.join(REPO, tgt["shipped"])
    pe = Pe(p)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp : trp + tvs]
    img, starts, sizes = _enum_with_sizes(p, label)

    funcs, unpadded, from_lib = _load_objs(objs, icl)

    # Several of our functions compile to identical code, and the shipped
    # linker folded some of those into one address while emitting others
    # separately. Assign greedily so each of our functions claims a distinct
    # shipped address rather than all of them crediting the first hit.
    #
    # A library function with more than one hit takes the fresh hit nearest
    # the addresses its library's single-hit functions anchored: a library
    # is linked as a block, so its own copy is the one beside its siblings,
    # not the first one in .text.
    matched = {}
    tiny = {}          # our functions with too few unmasked bytes to anchor
    lib_hits = {}
    lib_range = tgt.get("lib_range", {})
    for n, (code, mask) in funcs.items():
        if n in from_lib and len(code) - len(mask) >= 8:
            lib_hits[n] = list(find(text, tva, code, mask))
            rng = lib_range.get(n.split(":", 1)[0])
            if rng:
                # outside the library's established block: not the library
                lib_hits[n] = [h for h in lib_hits[n] if rng[0] <= h < rng[1]]
    start_set = set(starts)
    anchors = {}
    for n, h in lib_hits.items():
        if len(h) == 1:
            anchors.setdefault(n.split(":", 1)[0], []).append(h[0])
    placed = set()
    # A generic shape (a thiscall thunk can recur at 19 addresses) otherwise
    # claims the FIRST free hit and leaves the address it was written for
    # unscored, or a same-shape neighbour takes it first. A symbol named for
    # its address (`sub_<addr>`) whose bytes match AT that address is placed
    # there before anything else.
    for n, (code, mask) in sorted(funcs.items()):
        a = _own_addr(tgt, n, funcs)
        if a is None or n in from_lib or len(code) - len(mask) < 8:
            continue
        off = a - tva
        for c, m in [(code, mask)] + ([unpadded[n]] if n in unpadded else []):
            if a in matched or off < 0 or off + len(c) > len(text):
                continue
            if all(i in m or text[off + i] == c[i] for i in range(len(c))):
                matched[a] = len(c)
                PLACED_SYMS[(label, a)] = n
                placed.add(n)
    for n, (code, mask) in sorted(funcs.items()):
        if n in placed:
            continue
        if len(code) - len(mask) < 8:
            tiny[n] = (code, mask)
            continue
        hits = lib_hits[n] if n in lib_hits else list(find(text, tva, code, mask))
        if not hits and n in unpadded:
            # icl pads a COMDAT with multi-byte lea-nops; where the shipped
            # image has different bytes after the function the padded body
            # is found nowhere. Try the body without it.
            code, mask = unpadded[n]
            if len(code) - len(mask) >= 8:
                hits = list(find(text, tva, code, mask))
        if not hits:
            continue
        fresh = [h for h in hits if h not in matched]
        # A hit that is not an enumerated function start is a byte-run
        # inside some other function (a short body's masked shape recurring
        # in a neighbour's tail): only take it when nothing better exists.
        if len(fresh) > 1:
            at_start = [h for h in fresh if h in start_set]
            if at_start:
                fresh = at_start
        anc = anchors.get(n.split(":", 1)[0]) if n in from_lib else None
        if anc and len(fresh) > 1:
            fresh.sort(key=lambda h: min(abs(h - a) for a in anc))
        at = (fresh or hits)[0]
        matched[at] = len(code)
        PLACED_SYMS[(label, at)] = n

    # A library linked into an image is one contiguous block of it, so a
    # library function's hit strictly inside another matched function is a
    # coincidence. Drop those, and let the library's unanchorable functions
    # claim addresses by shape only inside the span its anchored functions
    # occupy.
    lib_span = {}
    for at in [a for a in matched if PLACED_SYMS.get((label, a)) in from_lib]:
        if any(b < at < b + m for b, m in matched.items() if b != at):
            del matched[at]
            del PLACED_SYMS[(label, at)]
            continue
        mod, sym = PLACED_SYMS[(label, at)].split(":", 1)
        if "?$" in sym or sym.startswith(("??_G", "??_D")):
            # template instances, deleting dtors and the iostream classes'
            # vbase dtors are emitted by every object that uses them and fold
            # anywhere; they place nothing
            continue
        l0, h0 = lib_span.get(mod, (at, at))
        lib_span[mod] = (min(l0, at), max(h0, at + matched[at]))
    for n in [n for n in tiny if n in from_lib]:
        mod = n.split(":", 1)[0]
        if mod not in lib_span and mod not in lib_range:
            del tiny[n]
    # With lib_block, a library's block also takes in the unmatched
    # addresses around its anchored span, up to the nearest function matched
    # from anything else (or the end of .text): a library's first or last
    # function can be one too short to anchor, and the span alone leaves it
    # no address to claim.
    lib_block = dict(lib_span)
    if tgt.get("lib_block"):
        def foreign(a, mod):
            return (PLACED_SYMS.get((label, a)) or "").split(":", 1)[0] != mod
        order = sorted(matched)
        for mod, (l0, h0) in lib_span.items():
            below = [a + matched[a] for a in order if a < l0 and foreign(a, mod)]
            above = [a for a in order if a >= h0 and foreign(a, mod)]
            lib_block[mod] = (max(below) if below else tva,
                              min(above) if above else tva + len(text))

    # A function of ours matched where the enumeration has no start is a
    # start it missed (a function reached only through a thunk or a table
    # it cannot see: the incremental link's jump table, an initializer
    # called through atexit): the row it lies in ends there. Left whole, the
    # row would count the matched bytes a second time, as unwritten, and
    # be too long for the function that really starts there to place.
    for m in sorted(matched):
        if m in start_set:
            continue
        i = bisect.bisect_right(starts, m) - 1
        if i < 0:
            continue
        a = starts[i]
        if a < m < a + sizes.get(a, 0) and a not in matched:
            hi = m - tva
            while hi > a - tva and text[hi - 1] in (0x90, 0xCC):
                hi -= 1
            sizes[a] = hi - (a - tva)

    # Second oracle (linked_oracle): our own whole-image link. exematch has
    # to mask relocation bytes because it compares an unlinked .obj, which
    # leaves the global initializer COMDATs -- two unmasked opcodes each --
    # unverifiable. In a linked image those relocations are resolved, so a
    # function built purely from relative displacements can be compared
    # byte for byte with nothing masked at all.
    linked = None
    if linked_path and os.path.exists(os.path.join(REPO, linked_path)):
        linked = EnumImage(os.path.join(REPO, linked_path)).text

    # Enumeration finds some starts that are not functions: exception-handler
    # funclets and jump islands inside a function we have already matched, and
    # the odd 1-byte fragment left by the padding carve. Anything strictly
    # inside a matched function's span is one of those, not a target.
    inside = set()
    for a, n in matched.items():
        i = bisect.bisect_right(starts, a)
        while i < len(starts) and starts[i] < a + n:
            inside.add(starts[i])
            i += 1
    starts = [a for a in starts if a not in inside]

    if linked is not None:
        for a in starts:
            if a in matched or not in_app(tgt, a):
                continue
            n = sizes.get(a, 0)
            if n < 1:
                continue
            b = text[a - tva : a - tva + n]
            if b and b in linked:
                matched[a] = n

    # Global-initializer COMDATs ($E thunks, the ??__E constructors and the
    # atexit registrations) are almost entirely relocation bytes: a `call
    # rel32; jmp rel32` pair leaves two unmasked opcodes, which anchors
    # nowhere. They cannot be verified by this oracle even when the source is
    # certainly right. Claim them by shape instead -- each of our unanchorable
    # functions takes one distinct shipped address whose bytes agree outside
    # the mask -- and score them "small": reconstructed, not verified.
    small = set()
    placed_small = set()

    def own_first(n):
        """A symbol named for its address tries that address first, as the
        exact-match placement above does -- a 6-byte `mov <g>,%eax ; ret` or
        a 1-byte `ret` fits every other one of its shape, and taking the
        first in address order steals a sibling's."""
        a0 = _own_addr(tgt, n, funcs)
        if a0 is not None and a0 in start_set:
            return [a0] + [a for a in starts if a != a0]
        return starts

    # Relocation-free functions first: those bytes are the whole function, so
    # a shape match is exact, while one with a relocation (`mov eax, <addr>;
    # ret`) fits every sibling of its shape. In name order the second kind
    # could take the address of the first.
    for n, (code, mask) in sorted(tiny.items(),
                                  key=lambda kv: (len(kv[1][1]) > 0, kv[0])):
        # a COMDAT is padded out to alignment; the function is what precedes it
        end = len(code)
        while end > 0 and code[end - 1] in (0x90, 0xCC):
            end -= 1
        for a in own_first(n):
            if a in matched or a in small or not in_app(tgt, a):
                continue
            if n in from_lib:
                mod = n.split(":", 1)[0]
                l0, h0 = lib_range.get(mod) or lib_block[mod]
                if not l0 <= a < h0:
                    continue
            if sizes.get(a) != end:            # same length, exactly
                continue
            off = a - tva
            if all(i in mask or text[off + i] == code[i] for i in range(end)):
                small.add(a)
                placed_small.add(n)
                SMALL_SYMS[(label, a)] = n
                break

    # icl pads with multi-byte lea-nops as well as 0x90: a 1-byte `ret`
    # followed by `90 8d b4 26 ..` keeps a 16-byte extent once only
    # 0x90/0xCC are stripped, so the same-length test above can never pass
    # for it. A second pass, for the tiny functions the first one left
    # unplaced only, compares the bodies with that padding stripped on both
    # sides.
    if icl:
        for n, (code, mask) in sorted(tiny.items()):
            if n in placed_small or n in from_lib:
                continue
            end = len(strip_pad(bytes(code)))
            for a in own_first(n):
                if a in matched or a in small or not in_app(tgt, a):
                    continue
                off = a - tva
                body = strip_pad(bytes(text[off:off + sizes.get(a, 0)]))
                if len(body) != end:
                    continue
                if all(i in mask or text[off + i] == code[i]
                       for i in range(end)):
                    small.add(a)
                    placed_small.add(n)
                    SMALL_SYMS[(label, a)] = n
                    break

    # A function we wrote that does not match still corresponds to a shipped
    # address, and leaving that address in "todo" says we have no source for it
    # when we do. Pair each unmatched object function with its best remaining
    # candidate: same length to within 15%, and at least half the unmasked
    # bytes equal. This only ever relabels todo -> near; it never claims a
    # match.
    def tail(buf, i, j):
        """The callee-pop epilogue: `ret` or `ret imm16`, whichever ends it.

        Never a relocation, and a hard ABI fact -- two functions that pop
        different argument bytes cannot be the same function however much
        of their prologue coincides. On small functions that is most of the
        discriminating signal there is, because masking removes the rest.
        """
        if j - i >= 3 and buf[j - 3] == 0xC2:
            return bytes(buf[j - 3:j])
        if j - i >= 1 and buf[j - 1] == 0xC3:
            return b"\xc3"
        return None

    paired = {}
    occurs = {}        # symbol -> its bytes occur somewhere in the image
    rejected = 0
    # A function of a separately scored library whose bytes are found
    # nowhere is one its own library's score has as near: the shipped
    # .lib's copy is what the image links, so pair it the same way, but
    # only inside its library's block and only if our own link has it.
    lib_near_ok = set()
    if tgt.get("lib_block"):
        layout_syms = {sym for (_o, sym) in (_our_layout(mapfile) or {})}
        lib_near_ok = {n for n in funcs if n in from_lib and
                       n.split(":", 1)[0] in lib_block and
                       n.split(":", 1)[1] in layout_syms}
    for n, (code, mask) in sorted(funcs.items()):
        if len(code) - len(mask) < 8 or \
                (n in from_lib and n not in lib_near_ok):
            continue
        occurs[n] = bool(list(find(text, tva, code, mask))) or bool(
            n in unpadded and list(find(text, tva, *unpadded[n])))
        if occurs[n]:
            continue
        end = len(code)
        while end > 0 and code[end - 1] in (0x90, 0xCC):
            end -= 1
        best, best_rank, best_ok = None, 0.0, False
        # A symbol named for its address is tried THERE first, as own_first
        # does for the exact and small placements -- a large function whose
        # bytes differ mostly by register choice can agree with its own
        # address on fewer bytes than with an unrelated one.
        a0 = _own_addr(tgt, n, funcs)
        cand = starts
        if a0 is not None and a0 in start_set:
            cand = [a0] + [a for a in starts if a != a0]
        blk = lib_block.get(n.split(":", 1)[0]) if n in from_lib else None
        for a in cand:
            if a in matched or a in paired or not in_app(tgt, a):
                continue
            if blk and not blk[0] <= a < blk[1]:
                continue
            m = sizes.get(a, 0)
            if not m or abs(m - end) > 0.15 * max(m, end):
                continue
            off, k = a - tva, min(m, end)
            pfx = 0
            while pfx < k and (pfx in mask or text[off + pfx] == code[pfx]):
                pfx += 1
            same = sum(1 for i in range(k)
                       if i not in mask and text[off + i] == code[i])
            den = sum(1 for i in range(k) if i not in mask) or 1
            agree = same / den
            rank = max(agree, pfx / max(k, 1))
            if rank > best_rank:
                # either a shared 16-byte opening -- far more than two
                # unrelated functions with similar prologues manage -- or
                # most of the body agreeing, with the length lining up too.
                # Both then have to survive the epilogue and have enough
                # unmasked bytes for the ratio above to have meant
                # anything: a dozen agreeing bytes out of a dozen is a
                # calling convention, not a function.
                ok = (pfx >= 16 or agree >= 0.5) and den >= 12
                # The shipped row's extent runs to the next start, so in an
                # icl image it still carries the multi-byte nop padding:
                # `tail` would see no `ret`. Strip that padding first, as
                # `code` is.
                m_end = off + m
                if icl:
                    m_end = off + len(strip_pad(text[off:off + m]))
                ours, theirs = tail(code, 0, end), tail(text, off, m_end)
                if ok and ours is not None and ours != theirs:
                    ok = False
                    rejected += 1
                best, best_rank, best_ok = a, rank, ok
            if a == a0:
                ok0 = (pfx >= 16 or agree >= 0.5) and den >= 12
                o0, t0 = tail(code, 0, end), tail(text, off, off + m)
                if ok0 and (o0 is None or o0 == t0):
                    best, best_rank, best_ok = a, rank, True
                    break
        if best is not None and best_ok:
            paired[best] = n
            NEAR_PAIRS.append((label, best, sizes.get(best, 0), n, end))
    if rejected:
        print(f"  {label}: {rejected} candidate pairing(s) rejected on "
              f"argument-pop mismatch", file=sys.stderr)

    # THE JOIN. The passes above pair by content, so a function we wrote
    # whose bytes came out too different -- other registers, another block
    # order, a member offset -- is left with no shipped address, and the
    # shipped function it IS is left looking unwritten: one function, two
    # rows, counted on both sides. Our image links the same objects in the
    # same order as the shipped one (that is why the identical functions line
    # up), so place such functions by POSITION instead: take every function
    # already placed (identical, small or near) as an anchor -- its address
    # in our link (our .map) beside its shipped address -- keep the longest
    # chain of anchors whose order agrees in both images, and in each gap
    # between two neighbouring anchors align our unplaced functions with the
    # unpaired shipped ones in order, by size (_align: within a factor of
    # two). A function placed this way is "near": written and placed, not
    # yet identical.
    layout = _our_layout(mapfile)
    ours_at = {}       # symbol -> our address
    if layout:
        for n in funcs:
            if n in from_lib or ":" not in n:
                continue
            mod, sym = n.split(":", 1)
            a = layout.get((mod.lower(), sym))
            if a is not None:
                ours_at[n] = a
    placed_at = {}     # symbol -> shipped address
    for (lb, a), n in PLACED_SYMS.items():
        if lb == label and a in matched:
            placed_at[n] = a
    for (lb, a), n in SMALL_SYMS.items():
        if lb == label and a in small:
            placed_at[n] = a
    for a, n in paired.items():
        placed_at[n] = a
    our_placed = {ours_at[n] for n in placed_at if n in ours_at}

    # An inline function from a header is a COMDAT in every object that
    # includes it, and every copy is the same function: the linker keeps one.
    # Placing any copy places them all. Not so the names the compiler makes
    # up per object -- `_$E12` (a global initializer) and the ??__E/??__F
    # initializer/atexit thunks: the same name in two objects is two
    # functions -- so those keep their object.
    def fname(n):
        mod, sym = n.split(":", 1)
        return n if re.match(r"_?\$E|\?\?__[EF]", sym) else sym

    placed_names = {fname(n) for n in placed_at if ":" in n}

    def is_driver(n):
        return n.split(":", 1)[0].lower() in DRIVER_OBJS

    def unplaced_sym(n):
        """Ours, linked into our image, and placed nowhere in the shipped
        one (nor folded, in our own link, onto a function that is)."""
        if n in from_lib or n in placed_at or n not in ours_at or is_driver(n):
            return False
        if fname(n) in placed_names or ours_at[n] in our_placed:
            return False
        code, mask = funcs[n]
        if len(code) - len(mask) < 8:
            return n not in placed_small
        return not occurs.get(n, True)

    def body_len(code):
        end = len(code)
        while end > 0 and code[end - 1] in (0x90, 0xCC):
            end -= 1
        return len(strip_pad(bytes(code[:end]))) if icl else end

    def chain_of(anchors):
        """The longest run of (ours, shipped) anchors, in our order, whose
        shipped addresses rise too."""
        anchors = sorted(anchors)
        idx, prev = [], [-1] * len(anchors)
        tails = []
        for k, (_o, r) in enumerate(anchors):
            j = bisect.bisect_left(tails, r)
            if j > 0:
                prev[k] = idx[j - 1]
            if j == len(idx):
                idx.append(k)
                tails.append(r)
            else:
                idx[j] = k
                tails[j] = r
        out, k = [], idx[-1] if idx else -1
        while k >= 0:
            out.append(anchors[k])
            k = prev[k]
        return out[::-1]

    if ours_at:
        app = [r for r in tgt.get("app", ())]
        lo = min(r[0] for r in app) if app else img.tlo
        hi = max(r[1] for r in app) if app else img.thi
        free = {a for a in starts if in_app(tgt, a)
                and a not in matched and a not in paired
                and a not in small and sizes.get(a, 0) > 0}
        joined = {"name": 0, "object": 0, "image": 0}

        def place(n, a, how):
            paired[a] = n
            placed_at[n] = a
            placed_names.add(fname(n))
            # ... and every other name at its address in our own link, as
            # for the placements above: icl's /Qip `X$$1` is a second label
            # at X's own offset, so once X is joined its $$1 is that same
            # placed function, not a surplus one -- and must not take a free
            # address of its own.
            if n in ours_at:
                our_placed.add(ours_at[n])
            free.discard(a)
            NEAR_PAIRS.append((label, a, sizes.get(a, 0), n,
                               body_len(funcs[n][0])))
            joined[how] += 1

        # 1. By name: a function named for the shipped address it was
        # written as (`sub_<addr>`) is that function, however differently it
        # compiled -- a partial rebuild of a large function can be half its
        # size.
        for n in sorted(funcs):
            if not unplaced_sym(n):
                continue
            a = _own_addr(tgt, n, funcs)
            if a in free:
                place(n, a, "name")

        def mine_now(keep=lambda n: True):
            out, seen = [], set()
            for o, n in sorted((ours_at[n], n) for n in funcs
                               if unplaced_sym(n) and keep(n)):
                if fname(n) not in seen:            # one per function
                    seen.add(fname(n))
                    out.append((o, n))
            return out

        def align_gap(mine, o1, r1, o2, r2, how):
            u = [(n, body_len(funcs[n][0])) for o, n in mine
                 if o1 < o < o2 and n not in placed_at]
            w = [(a, sizes[a]) for a in sorted(free) if r1 < a < r2]
            if not u or not w or len(u) * len(w) > 250000:
                return
            for n, a in _align(u, w):
                place(n, a, how)

        # 2. Within each object, by neighbourhood: a shipped function no one
        # is placed at, whose nearest placed neighbours (below or above) are
        # functions of object X, is one of X's -- the linker lays an
        # object's functions out together. Our own order within an object
        # need not follow the shipped one, so X's unplaced functions are
        # matched to those shipped ones by size, closest first, within a
        # factor of two.
        import math
        owner = sorted((a, n.split(":", 1)[0]) for n, a in placed_at.items()
                       if ":" in n)
        owner_r = [a for a, _o in owner]
        cand = {}
        for a in sorted(free):
            i = bisect.bisect_left(owner_r, a)
            objs_near = set()
            if i:
                objs_near.add(owner[i - 1][1])
            if i < len(owner):
                objs_near.add(owner[i][1])
            for obj in objs_near:
                cand.setdefault(obj, []).append(a)
        for obj, ws in sorted(cand.items()):
            us = [n for _o, n in mine_now(
                lambda n, obj=obj: n.split(":", 1)[0] == obj)]
            pairs = []
            for n in us:
                su = body_len(funcs[n][0])
                for a in ws:
                    sw = sizes.get(a, 0)
                    if su > 0 and sw > 0 and 0.5 <= su / sw <= 2:
                        pairs.append((abs(math.log(su / sw)), n, a))
            for _d, n, a in sorted(pairs):
                if n not in placed_at and a in free:
                    place(n, a, "object")

        # 3. Across the image: what is left, between neighbouring anchors of
        # any object in our whole link.
        ch = [(-1, lo)] + chain_of((ours_at[n], a) for n, a in placed_at.items()
                                   if n in ours_at) + [(1 << 40, hi)]
        mine = mine_now()
        for (o1, r1), (o2, r2) in zip(ch, ch[1:]):
            align_gap(mine, o1, r1, o2, r2, "image")
        if any(joined.values()):
            print(f"  {label}: placed {joined['name']} by name, "
                  f"{joined['object']} by object order, {joined['image']} by "
                  f"link order", file=sys.stderr)

    rows = []
    # Functions we wrote that did NOT match: instruction-equivalent
    # near-matches, or code simply not linked into this image. Keyed by symbol
    # since we have no address for them.
    claimed = set(paired.values())
    unplaced_named = set()

    # The short functions (fewer than 8 unmasked bytes: `mov eax,8 / ret`,
    # an initializer thunk that is one jmp) cannot be told apart: a dozen
    # GetType()s return the same constant, so which shipped copy is whose is
    # arbitrary, and placing them one by one leaves an arbitrary few over.
    # For them coverage is a COUNT: of each exact shape, ours are short of
    # the shipped image only by as many as we link more of than it has.
    def shape(code, mask):
        end = body_len(code)
        return bytes(0 if i in mask else code[i] for i in range(end)), \
            frozenset(i for i in mask if i < end)

    short_over = {}    # shape -> how many of ours have no shipped copy
    if ours_at:
        mine_by_shape = {}
        seen = set()
        for n, (code, mask) in funcs.items():
            # a scoring driver's own short functions are not shipped code:
            # counted here they would inflate the surplus of their shape
            if len(code) - len(mask) >= 8 or n in from_lib or \
                    n not in ours_at or fname(n) in seen or is_driver(n):
                continue
            seen.add(fname(n))
            mine_by_shape.setdefault(shape(code, mask), []).append(n)
        by_len = {}
        for key in mine_by_shape:
            by_len.setdefault(len(key[0]), []).append(key)
        theirs_count = dict.fromkeys(mine_by_shape, 0)
        for a in starts:
            if not in_app(tgt, a):
                continue
            off = a - tva
            body = text[off:off + sizes.get(a, 0)]
            body = strip_pad(bytes(body)) if icl else \
                bytes(body).rstrip(b"\x90\xcc")
            for key in by_len.get(len(body), ()):
                b, m = key
                if all(i in m or body[i] == b[i] for i in range(len(b))):
                    theirs_count[key] += 1
        for key, ns in mine_by_shape.items():
            # functions, not names: several names can share one address in
            # our own link
            n_ours = len({ours_at[n] for n in ns})
            short_over[key] = max(0, n_ours - theirs_count[key])

    for n, (code, mask) in sorted(funcs.items()):
        if is_driver(n) and n not in claimed and n not in placed_at:
            rows.append((label, n, len(code), "driver"))
            continue
        if ours_at and len(code) - len(mask) < 8 and n not in from_lib \
                and unplaced_sym(n):
            key = shape(code, mask)
            if short_over.get(key, 0) > 0 and fname(n) not in unplaced_named:
                short_over[key] -= 1
                unplaced_named.add(fname(n))
                rows.append((label, n, len(code), "unplaced"))
            continue
        if ours_at and unplaced_sym(n):
            # written, linked into our image, and placed nowhere in the
            # shipped one even by the join: WRITTEN BUT UNPLACED (once per
            # function, however many objects carry a copy)
            if fname(n) not in unplaced_named:
                unplaced_named.add(fname(n))
                rows.append((label, n, len(code), "unplaced"))
            continue
        if len(code) - len(mask) < 8 or n in from_lib:
            # lib functions are scored in their own row; the linker drops the
            # ones this image never calls, and a dropped function is not a
            # near-match
            continue
        if n in claimed:
            # already counted once, at the shipped address it pairs with
            continue
        if not list(find(text, tva, code, mask)) and not (
                n in unpadded and list(find(text, tva, *unpadded[n]))):
            # UNPLACED, not "near". This function's bytes occur NOWHERE in
            # the image, so it is not a shipped function missed by a little
            # -- it is usually code this image never links (a library
            # member the link did not pull). Reported in its own column and
            # excluded from funcs/bytes_total -- as "unlinked" when our own
            # link leaves it out too (or there is no map to say).
            rows.append((label, n, len(code),
                         "unlinked" if ours_at else "unplaced"))
    touched = _touched_index(tgt)
    for a in sorted(set(starts) | set(matched)):
        size = matched.get(a, sizes.get(a, 0))
        if not size:
            # a start whose extent is all padding: not a function
            continue
        where = region(tgt, a)
        if where in ("encrypted", "middleware"):
            rows.append((label, "sub_%x" % a, size, where))
        elif a in matched:
            rows.append((label, "sub_%x" % a, size, "identical"))
        elif a in paired:
            rows.append((label, "sub_%x" % a, size, "near"))
        elif a in small:
            rows.append((label, "sub_%x" % a, size, "small"))
        elif where == "app":
            # SPLIT: "todo" now means nobody has looked at it. An address we
            # have evidence of working on -- written and unplaceable, decoded,
            # or recorded as not-work -- is "attempted" and counted apart.
            rows.append((label, "sub_%x" % a, size,
                         "attempted" if a in touched else "todo"))
        else:
            rows.append((label, "sub_%x" % a, size, "crt"))
    return rows


def _resources(path):
    """{(type, name, language): data} of a PE image's resources."""
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    rva = struct.unpack_from("<I", d, pe + 24 + 96 + 2 * 8)[0]
    if not rva:
        return {}
    secs = []
    for i in range(nsec):
        s = pe + 24 + optsz + i * 40
        vs, va, rs, rp = struct.unpack_from("<IIII", d, s + 8)
        secs.append((va, max(vs, rs), rp))

    def off(r):
        for va, sz, rp in secs:
            if va <= r < va + sz:
                return r - va + rp
        raise ValueError("resource RVA 0x%x outside every section" % r)

    base = off(rva)

    def name(v):
        if v & 0x80000000:
            o = base + (v & 0x7FFFFFFF)
            n = struct.unpack_from("<H", d, o)[0]
            return d[o + 2:o + 2 + 2 * n].decode("utf-16-le")
        return v

    def walk(o, path):
        out = {}
        n = sum(struct.unpack_from("<HH", d, o + 12))
        for i in range(n):
            nm, ptr = struct.unpack_from("<II", d, o + 16 + 8 * i)
            key = path + (name(nm),)
            if ptr & 0x80000000:
                out.update(walk(base + (ptr & 0x7FFFFFFF), key))
            else:
                drva, dsz = struct.unpack_from("<II", d, base + ptr)
                out[key] = d[off(drva):off(drva) + dsz]
        return out

    return walk(base, ())


def rows_for_resources(tgt, ours):
    """A resource-only image: one row per shipped resource, `type/name/lang`,
    sized by its data. identical = our resource has the same bytes; near =
    we have it, but its bytes differ; todo = we have none by that key."""
    label = tgt["label"]
    theirs = _resources(os.path.join(REPO, tgt["shipped"]))
    mine = _resources(os.path.join(REPO, ours)) if ours else {}
    rows = []
    for key in sorted(theirs, key=str):
        data = theirs[key]
        if key not in mine:
            status = "todo"
        elif mine[key] == data:
            status = "identical"
        else:
            status = "near"
        rows.append((label, "rsrc:" + "/".join(str(k) for k in key), len(data), status))
    return rows


def rows_for_unbuilt(tgt):
    """A binary with no build of ours yet: the same enumeration as the built
    ones, so the denominators are directly comparable -- call targets + data
    pointers (vtables) + exports + code after a ret that nothing references
    -- with every function of its own code `todo` (or `attempted`, where
    there is evidence of work on it) and the rest in its region's status."""
    label = tgt["label"]
    img, starts, sizes = _enum_with_sizes(os.path.join(REPO, tgt["shipped"]), label)
    touched = _touched_index(tgt)
    rows = []
    for a in starts:
        if not sizes.get(a):
            continue            # all padding: not a function
        where = region(tgt, a)
        if where == "app":
            where = "attempted" if a in touched else "todo"
        rows.append((label, "sub_%x" % a, sizes.get(a, 0), where))
    return rows


# ---------------------------------------------------------------------------
# TOUCHED: is there evidence in the tree that THIS shipped address has been
# worked on? `todo` only ever meant "no exact match and no successful
# pairing", so a function we have written whose bytes drifted past the
# pairing tolerance was counted identically to code nobody has ever looked
# at.
#
# Evidence accepted, cheapest first: the address is cited anywhere in our
# sources (CITED_SRC), or a decoded map places a symbol there, or a
# screen-exclude row records it as not-work.
_TOUCHED = {}

_PHANTOM = {}


def _phantom_index(label):
    """Addresses PROVEN not to be functions, to be dropped from the count.

    The enumeration is wrong in both directions. A row that is an operand
    byte, an interior jump target, alignment padding or an ASCII accident is
    not code, and leaving it in the denominator makes 100% unreachable BY
    CONSTRUCTION rather than by any fact about the source.

    Only rows whose screen-exclude reason opens with an explicit NOT A
    FUNCTION / NOT GAME CODE marker are dropped. "Already written" rows are
    NOT dropped -- those are real functions that happen to be credited at a
    sibling address, and removing them would flatter the figure. The marker
    has to be at the START of the reason so that a reason merely MENTIONING
    the phrase cannot silently delete a row.
    """
    if label in _PHANTOM:
        return _PHANTOM[label]
    out = set()
    for f in _exclude_files(label):
        try:
            for r in csv.DictReader(open(f)):
                a = (r.get("addr") or "").strip().lower()
                why = (r.get("reason") or "").strip()
                if not a.startswith("0x"):
                    continue
                if re.match(r"(?i)^(not a function|not game code)\b", why):
                    try:
                        out.add(int(a, 16))
                    except ValueError:
                        pass
        except OSError:
            pass
    _PHANTOM[label] = out
    return out


_CITED = {}


def _cited_addrs(bases=None):
    """Every 0x... cited in these source trees (CITED_SRC by default, or a
    target's own `cited_src`): one scan per set of trees."""
    bases = tuple(bases or cfg.CITED_SRC)
    if bases in _CITED:
        return _CITED[bases]
    blob = []
    for base in bases:
        for root, _, fs in os.walk(os.path.join(REPO, base)):
            for f in fs:
                if f.endswith((".cpp", ".h", ".c")) and "NAMEMAP" not in f:
                    try:
                        blob.append(open(os.path.join(root, f),
                                         errors="ignore").read())
                    except OSError:
                        pass
    text = "\n".join(blob)
    _CITED[bases] = set(re.findall(r"0x[0-9a-fA-F]{6,8}", text))
    return _CITED[bases]


def _touched_index(tgt):
    label = tgt["label"]
    if label in _TOUCHED:
        return _TOUCHED[label]
    # Only an image whose addresses our sources cite: the DLLs all share the
    # 0x10000000 range, so an address cited for one would mark another's
    # functions "attempted" by coincidence.
    if not tgt.get("cites"):
        _TOUCHED[label] = set()
        return _TOUCHED[label]
    addrs = set(_cited_addrs(tgt.get("cited_src")))
    for extra in glob.glob(DATA + "/%s-decoded-map.csv" % tgt["stem"]) + \
            _exclude_files(label):
        try:
            for r in csv.DictReader(open(extra)):
                a = (r.get("addr") or "").strip().lower()
                if a.startswith("0x"):
                    addrs.add(a)
        except OSError:
            pass
    # normalise to a set of ints so 0x456400 and 0x00456400 are one key
    out = set()
    for a in addrs:
        try:
            out.add(int(a, 16))
        except ValueError:
            pass
    _TOUCHED[label] = out
    return out


def score_target(tgt):
    """(rows, our build or None) for one target."""
    ours = built_image(tgt)
    if tgt["kind"] == "resources":
        return rows_for_resources(tgt, ours), ours
    if not ours:
        return rows_for_unbuilt(tgt), None
    objs = link_inputs(ours)
    if objs is None:
        objs = sorted({os.path.relpath(p, REPO) for g in tgt.get("objs", ())
                       for p in glob.glob(os.path.join(REPO, g), recursive=True)})
    skip = {s.lower() for s in tgt.get("third_party", ())}
    objs = [o for o in objs if os.path.basename(o).lower() not in skip]
    if not objs:
        sys.exit("progress.py: %s: %s has no link response file (%s.rsp) and "
                 "the target lists no objs" % (tgt["label"], ours, ours))
    linked = ours if tgt.get("linked_oracle") else None
    return rows_for_image(tgt, objs, our_map(ours), linked), ours


def main():
    os.chdir(REPO)

    # A missing reference image would silently drop its target from the
    # totals; refuse instead.
    missing = [t["shipped"] for t in TARGETS if not os.path.exists(t["shipped"])]
    if missing:
        sys.exit("progress.py: %s missing -- run build/reference.sh "
                 "(`make progress` does)" % ", ".join(missing))
    # ... and so would a missing build: every function would read "todo".
    unbuilt = [t["built"] for t in TARGETS
               if t.get("built") and not t.get("optional") and not built_image(t)]
    if unbuilt:
        sys.exit("progress.py: no build output %s -- run `make` first"
                 % ", ".join(unbuilt))

    libdir = shipped_lib_dir()
    all_rows = []
    started = set()
    if LIBS:
        if libdir:
            for label, ours in LIBS:
                all_rows += rows_for_lib(label, ours, libdir)
                started.add(label)
        else:
            print("progress.py: %s not set -- the %d shipped libraries are not "
                  "scored (see progress/README.md)" % (cfg.SHIPPED_ENV, len(LIBS)),
                  file=sys.stderr)

    for tgt in TARGETS:
        rows, ours = score_target(tgt)
        all_rows += rows
        if ours:
            started.add(tgt["label"])
        else:
            print("progress.py: %s: no build of ours (%s), scored as unwritten"
                  % (tgt["label"], tgt.get("built") or "no source yet"),
                  file=sys.stderr)

    # --todo[=<target>] (or --attempted, --near, --small): the rows of one
    # status. The table gives a number and the number alone is not a
    # worklist.
    want_cls = None
    for a in sys.argv[1:]:
        for cls in ("todo", "attempted", "near", "small", "unplaced",
                    "unlinked", "driver"):
            if a == "--" + cls or a.startswith("--" + cls + "="):
                want_cls = cls
    if want_cls:
        pick = ""
        for a in sys.argv[1:]:
            if a.startswith("--" + want_cls + "="):
                pick = a.split("=", 1)[1]
        sel = [r for r in all_rows
               if r[3] == want_cls and (not pick or r[0].startswith(pick))]
        sel.sort(key=lambda r: (r[0], -r[2]))
        print(f"{'target':<14} {'symbol':<16} {'bytes':>7}")
        for r in sel:
            print(f"{r[0]:<14} {r[1]:<16} {r[2]:>7}")
        print(f"\n{len(sel)} row(s), {sum(r[2] for r in sel)} bytes")
        return

    want = None
    for a in sys.argv[1:]:
        if a == "--nears":
            want = ""
        elif a.startswith("--nears="):
            want = a.split("=", 1)[1]
    if want is not None:
        sel = [r for r in NEAR_PAIRS if not want or r[0].startswith(want)]
        sel.sort(key=lambda r: (abs(r[4] - r[2]), r[2]))
        print(f"{'target':<14} {'shipped':<12} {'ship':>6} {'ours':>6} "
              f"{'delta':>6}  symbol")
        for label, addr, ssize, sym, osize in sel:
            print(f"{label:<14} 0x{addr:08x} {ssize:>6} {osize:>6} "
                  f"{osize - ssize:>+6}  {sym}")
        print(f"\n{len(sel)} near-matches"
              f" ({sum(1 for r in sel if r[4] == r[2])} already size-exact)")
        return

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "functions.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["target", "function", "size", "status"])
        for r in sorted(all_rows, key=lambda r: (r[0], r[1])):
            w.writerow(r)

    # aggregate: every target has an entry, rows or not (an empty resource
    # directory)
    def blank():
        return {"identical": 0, "near": 0, "todo": 0, "attempted": 0,
                "small": 0, "crt": 0, "crt_bytes": 0,
                "middleware": 0, "middleware_bytes": 0,
                "encrypted": 0, "encrypted_bytes": 0,
                "unplaced": 0, "unplaced_bytes": 0,
                "unlinked": 0, "unlinked_bytes": 0,
                "driver": 0, "driver_bytes": 0,
                "unwritten": 0, "unwritten_bytes": 0,
                "bytes_identical": 0, "bytes_total": 0,
                "funcs": 0}
    targets = {t["label"]: blank() for t in TARGETS}
    for label, name, size, status in all_rows:
        t = targets.setdefault(label, blank())
        t[status] += 1
        if status in ("crt", "middleware", "encrypted"):  # not Monolith's,
            t[status + "_bytes"] += size                   # or not readable:
            continue                                       # visible, not a target
        if status in ("unplaced", "unlinked", "driver"):  # ours, no shipped
            t[status + "_bytes"] += size        # address: not a shipped
            continue                            # function, not a denominator
        if status in ("todo", "attempted"):     # nothing of ours placed there
            t["unwritten"] += 1
            t["unwritten_bytes"] += size
        t["funcs"] += 1
        t["bytes_total"] += size
        if status == "identical":
            t["bytes_identical"] += size

    kinds = {t["label"]: t["kind"] for t in TARGETS}
    kinds.update({label: "lib" for label, _p in LIBS})
    for label, t in targets.items():
        t["started"] = label in started
        t["kind"] = kinds.get(label, "image")

    summary = {"libraries_scored": not LIBS or bool(libdir), "targets": targets}
    # the total: code, every binary (resources are data, and left out)
    tot = {"identical": 0, "near": 0, "todo": 0, "attempted": 0,
           "small": 0, "funcs": 0,
           "unplaced": 0, "unplaced_bytes": 0,
           "unwritten": 0, "unwritten_bytes": 0,
           "bytes_identical": 0, "bytes_total": 0}
    for label, t in targets.items():
        if t["kind"] != "resources":
            for k in tot:
                tot[k] += t[k]
    summary["total"] = tot

    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"{'target':<18} {'ident':>6} {'near':>5} {'small':>6} "
          f"{'attem':>6} {'todo':>5} "
          f"{'funcs':>6} {'unwr':>5} {'unpl':>5} {'bytes id':>10} "
          f"{'bytes tot':>10}  {'%':>5}")
    print("-" * 105)

    def line(label, t, note=""):
        pct = 100 * t["bytes_identical"] / max(t["bytes_total"], 1)
        print(f"{label:<18} {t['identical']:>6} {t['near']:>5} {t['small']:>6} "
              f"{t.get('attempted', 0):>6} {t['todo']:>5} "
              f"{t['funcs']:>6} {t['unwritten']:>5} {t['unplaced']:>5} "
              f"{t['bytes_identical']:>10} "
              f"{t['bytes_total']:>10}  {pct:>4.1f}%{note}")

    order = ([l for l, _ in LIBS] if libdir else []) + \
        [t["label"] for t in TARGETS if t["kind"] != "resources"]
    for label in order:
        line(label, targets[label],
             "" if targets[label]["started"] else "  (no build yet)")
    for t in TARGETS:
        if t["kind"] == "resources":
            line(t["label"], targets[t["label"]],
                 "  (resources, not code: not in ALL)")
    print("-" * 105)
    line("ALL", tot)
    if LIBS and not libdir:
        print("(the shipped libraries are not included: %s is not set)"
              % cfg.SHIPPED_ENV)
    print(f"wrote {OUT}/functions.csv, {OUT}/summary.json")


if __name__ == "__main__":
    main()
