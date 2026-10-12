#!/usr/bin/env python3
"""The scoreboard: how much of every targeted binary we rebuild exactly.

For each shipped target this enumerates its functions (name + byte size)
and classifies our reconstruction of each as:

  identical  our bytes match the shipped function exactly (reloc-masked)
  near       we have the function but bytes differ (compiler-revision variance)
  small      we have the function but it is almost entirely relocations, so
             there is nothing for the oracle to anchor on (global-initializer
             COMDATs); reconstructed, not verified
  attempted  no match and no pairing, but there is evidence the address has
             been worked on (cited in src/, or recorded in progress/*.csv)
  todo       the shipped function has no counterpart in our sources yet
  unplaced   (ours, not theirs) a function of ours that our own link puts in
             our image, but that no shipped function is placed for, even by
             position (the join in _rows_for_image): WRITTEN BUT UNPLACED
  unlinked   (ours) a function our own link leaves out of our image too:
             compiled, but not part of this binary
  driver     (ours) a function only a scoring driver (DRIVER_OBJS) emits
  crt        outside the image's app region (the static CRT/MFC): listed,
             not counted
  middleware inside a third-party library linked into the app region
             (MIDDLEWARE: the GameSpy SDK): listed, not counted

Coverage is the pair of counts summary.json carries per target: UNWRITTEN
(todo + attempted: shipped functions with nothing of ours placed at them)
and UNPLACED. Both at zero means every shipped function has a written,
placed counterpart -- near or identical -- and nothing of ours is left
over; tools/ratchet.py keeps either from going up (and `check --covered`
requires both at zero). unplaced, unlinked and driver rows are ours, not
shipped functions: none of them is in the denominator.

Ground truth is always the SHIPPED binary, so the denominator can't drift.
The engine images (lithtech.exe, server.dll, d3d.ren, NOLF.exe) come from the
installed retail game into out/reference/ (`tools/retailextract.py
reference`), and so do the
Game of the Year game DLLs (CShell.dll, Object.lto, CRes.dll, out of
NOLFGOTY.REZ); CRes.dll holds no code of Monolith's, so it is scored
resource by resource instead (rows_for_resources); the lithshared
libraries (and RegMgr's Debug build) are compared per COFF symbol against Monolith's prebuilt
.libs from the NOLF Source Code v1.003 release, found through $NOLF2_SOURCE
and checked against progress/shipped-libs.sha256. Without NOLF2_SOURCE the
libraries are left out and only the images are scored.

What is compared is what the build left in the tree: src/engine/*/Release/,
src/game/*/Final_Release/ (CRes.dll: src/game/ClientRes/Release/) and
src/lithshared/out/. Run `make` first.

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
import csv
import glob
import json
import os
import re
import struct
import sys
import tempfile

NEAR_PAIRS = []
# (label, shipped address) -> "module.obj:symbol", for every function exematch
# PLACES. rows_for_image deliberately reports placed functions as `sub_<addr>`
# because the scoreboard only needs the count, so the symbol is dropped there;
# a tool labelling a disassembly needs it. Written alongside `matched` and
# read by nothing in this file, exactly as NEAR_PAIRS above.
PLACED_SYMS = {}
# The same for the "small" pass (functions too short to anchor, placed by
# shape): (label, shipped address) -> "module.obj:symbol". Weaker evidence
# than PLACED_SYMS, so kept apart.
SMALL_SYMS = {}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objdiff import parse_obj  # noqa: E402
from libextract import extract  # noqa: E402
from d3dcheck import strip_pad, NAMED as D3D_NAMED, SYMBOLS as D3D_SYMBOLS  # noqa: E402
from exematch import parse_obj_masked, find  # noqa: E402
from exedump import Pe  # noqa: E402
from enumfuncs import Image as EnumImage, enumerate_functions  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# The retail images every denominator and oracle comes from, extracted from
# the installed retail game by `tools/retailextract.py reference` (`make
# progress` does it); the build itself never reads them.
REFERENCE = "out/reference"

# Where this writes, and where the recorded baseline and the hand-curated
# evidence the enumeration reads live.
OUT = "out/progress"
DATA = "progress"

# lithshared libraries: (label, ours.lib); theirs is SHIPPED_LIB in the
# source release, or SHIPPED_AS's path (relative to SHIPPED_LIB's directory)
LIBS = [
    ("StdLith",         "src/lithshared/out/StdLith.lib"),
    ("CryptMgr",        "src/lithshared/out/CryptMgr.lib"),
    ("RegMgr",          "src/lithshared/out/RegMgr.lib"),
    ("RegMgr_Debug",    "src/lithshared/out/RegMgr_Debug.lib"),
    ("MFCStub",         "src/lithshared/out/MFCStub.lib"),
    ("ButeMgrNoMFC",    "src/lithshared/out/ButeMgrNoMFC.lib"),
    ("ltguimgr_LT2",    "src/lithshared/out/ltguimgr_LT2.lib"),
    ("LithFontMgr_LT2", "src/lithshared/out/LithFontMgr_LT2.lib"),
]
SHIPPED_LIB = "LT2/lithshared/libs/Release/{}.lib"
# The GOTY CShell.dll linked the Debug build of RegMgr (build/libs.sh), so
# that one is scored against the release's Debug library.
SHIPPED_AS = {"RegMgr_Debug": "../Debug/RegMgr.lib"}
SHIPPED_SUMS = DATA + "/shipped-libs.sha256"


def shipped_lib_dir():
    """The directory holding the source release's prebuilt .libs, or None.

    $NOLF2_SOURCE is the extracted NOLF Source Code v1.003 release (the
    directory holding LT2/); a directory holding the Release .libs themselves
    is accepted too, with the Debug ones (SHIPPED_AS) in ../Debug. Every library is checked against SHIPPED_SUMS: a library
    from another release would score against the wrong ground truth, so a
    mismatch is fatal rather than a skip.
    """
    root = os.environ.get("NOLF2_SOURCE", "")
    if not root:
        return None
    d = os.path.join(root, os.path.dirname(SHIPPED_LIB))
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
        sys.exit("progress.py: NOLF2_SOURCE=%s does not hold the NOLF Source "
                 "Code v1.003 libraries (%s):\n  %s" % (
                     root, SHIPPED_SUMS, "\n  ".join(bad)))
    return d

# engine binaries not yet started: tracked by .text byte scope (their functions
# have no symbols, and d3d/server use little inter-function padding so a carved
# count is only approximate — bytes are the exact, honest scope measure).
ENGINE = [
    ("lithtech.exe", REFERENCE + "/lithtech.exe"),
    ("d3d.ren",      REFERENCE + "/d3d.ren"),
    ("server.dll",   REFERENCE + "/server.dll"),
]

# The game DLLs, built from Monolith's source release (src/game/, Final
# Release: build/build.sh all final) and scored against the Game of the Year
# copies in NOLFGOTY.REZ: (label, shipped image, our objects' directory, the
# lithshared libraries it links, which are ours too -- as StdLith.lib in
# server.dll).
GAME = [
    # CShell links RegMgr_Debug, the Debug build of regmgr.lib, where the
    # others link the Release one: so did the Game of the Year CShell.dll
    # (build/libs.sh, build_regmgr_debug).
    ("CShell.dll", REFERENCE + "/CShell.dll", "src/game/ClientShellDLL/Final_Release",
     ["StdLith", "CryptMgr", "ltguimgr_LT2", "MFCStub", "ButeMgrNoMFC",
      "GameSpyClientMgr", "RegMgr_Debug", "LithFontMgr_LT2"]),
    ("Object.lto", REFERENCE + "/Object.lto", "src/game/ObjectDLL/Final_Release",
     ["StdLith", "CryptMgr", "MFCStub", "ButeMgrNoMFC", "GameSpyMgr", "RegMgr"]),
]
# CRes.dll: string tables, dialogs, bitmaps and text, and nothing but the
# CRT's DLL entry code -- so its resources are what is scored.
GAME_RES = ("CRes.dll", REFERENCE + "/CRes.dll", "src/game/ClientRes/Release/CRes.dll")
GAME_LABELS = {g[0] for g in GAME} | {GAME_RES[0]}

# Monolith's own code within each image. Everything above these ranges is the
# statically linked CRT (and MFC in NOLF.exe's case) — real code in the binary,
# but supplied by the toolchain, so it is NOT a reconstruction target. Counting
# it would understate progress as badly as counting only what we attempted
# would overstate it. Functions outside the range are recorded as "crt" and
# excluded from the totals.
#   NOLF.exe    : app region ends where the static CRT/MFC begins.
#   server.dll  : app region ends where libcmt.lib begins (_ftol); one
#                 Monolith island sits above it (APP_ISLANDS).
APP_REGION = {
    # NOLF.exe: Monolith's own code runs 0x401000 .. 0x409ed2 (the last app
    # function is CDibPal::InitRes at 0x409e70).  From 0x409ee0 on it is the
    # statically linked MFC (AfxGetMainWnd, the multi-monitor stubs, CArchive
    # operators) and then the CRT (_splitpath, strncpy, ...).
    "NOLF.exe":   (0x401000, 0x409ed2),
    # server.dll: the static CRT (libcmt.lib) begins at _ftol, 0x1003e0f0.
    # Evidence: every libcmt.lib member was searched for in .text (masked by
    # its own relocations, asm labels included); the lowest real hit is
    # __ftol at 0x1003e0f0, followed densely by _free, _malloc, _strcmp,
    # _memset, _strlen, ... Nothing between the old cut (0x10037b47, "last
    # function referencing a Class::Method error tag") and 0x1003e0f0 is
    # CRT; it is, in link order:
    #   ..0x1003a54f  engine TUs (unaligned /O1 code): CMoArray templates
    #                 byte-identical from worldbsp/collection.obj, the
    #                 BaseNew/BaseDelete pair at 0x10038329/0x10038366,
    #                 wt_VisibilityTraversal at 0x10038e77
    #   0x1003a550..  rezmgr.lib (16-aligned): rezmgr/rezmgr2/rezdir/
    #                 rezhash/rezfile/rezemu objects match 45+ functions
    #   0x1003d170..  StdLith.lib: struct_bank, l_allocator, stringholder,
    #                 dynarray, helpers, goodlinklist all match exactly
    # See also APP_ISLANDS for the one Monolith block linked after the CRT.
    "server.dll": (0x10001000, 0x1003e0f0),
    # lithtech.exe and d3d.ren are placed by a rigorous oracle rather than by
    # eye: the static CRT is the same library in every image built with this
    # toolchain, so it is byte-identical across them, and server.dll's
    # non-app region is already established. Taking each server.dll function
    # above 0x10037b47 (the server cut as it then stood -- since corrected to
    # 0x1003e0f0, so part of that sample was really rezmgr.lib/StdLith.lib,
    # which are also prebuilt and identical across images; the cut below is
    # still _ftol, as in server.dll) that is at least 32 bytes long and searching the other
    # image's .text for those exact bytes finds 71 of them in lithtech.exe and
    # 38 in d3d.ren — and in both cases they cluster into a dense tail.
    #
    # lithtech.exe's tail begins at _ftol (0x4928c0), with strncpy, _stricmp,
    # _findfirst, _vsnprintf and the CRT entry point following it. Nothing
    # Monolith wrote is identified above it: the highest error-tag literal
    # names a function at 0x48b820 and the highest function any of our objects
    # matches is a collection template at 0x4915c0. There are a few CRT hits
    # below the cut, interleaved with that template — the boundary is left
    # under them deliberately, because counting a little of the CRT against us
    # errs in the honest direction.
    #
    # d3d.ren's tail begins with the generic thunk run at 0x1007faa0, above a
    # stretch of int3 padding. Those thunks are the twenty-three functions the
    # engine objects "match" in d3d.ren by coincidence, which the project has
    # always refused to count; the boundary now says so in the denominator too.
    "lithtech.exe": (0x401000, 0x4928bf),
    "d3d.ren":      (0x10001000, 0x1007fa91),
    # The game DLLs link like server.dll: Monolith's objects, then the
    # lithshared libraries (StdLith, CryptMgr, ltguimgr_LT2, MFCStub,
    # ButeMgrNoMFC, the GameSpy library, RegMgr), then the static CRT, which
    # begins with libcimt.lib (the iostream classes) and goes on into
    # libcmt.lib. Found by taking every function of 24+ bytes in our own
    # linked image from the libraries and the CRT (our .map says which),
    # masking our relocations, and searching the retail .text for it: each
    # group's unique hits form one run, in our link order. libcimt's first
    # function is the same 43-byte function in both images (ifstream's,
    # just below ifstream::close, the group's first unique hit):
    #   CShell.dll: libcimt 0x100edab0 (close at 0x100edbd3), libcmt from
    #     0x100efd1b (??_M, our first libcmt function) to _findenv
    #     0x100fd769; above the libraries, ButeMgrNoMFC ends at
    #     ??3zSLink 0x100eb600 and GameSpyClientMgr is at 0x100eb6d0.
    #   Object.lto: libcimt 0x10141db0 (close at 0x10141ed3), libcmt from
    #     __cfltcvt_init 0x1014412f to __decomp 0x1015030e; RegMgr, the
    #     last library, ends at 0x10141d70 + 50 bytes.
    # The GameSpy library stays in the region: the retail one is the
    # GameSpy SDK, which src/lithshared/gamespy/ stands in for and will not
    # match, so those functions are honestly "todo".
    "CShell.dll":   (0x10001000, 0x100edab0),
    "Object.lto":   (0x10001000, 0x10141db0),
}


# Monolith code that the linker placed ABOVE the start of the static CRT,
# because its object was pulled from a library only after libcmt members had
# been. Scored like the app region; everything else above APP_REGION is CRT.
#   server.dll 0x1004bb20..0x1004bdcf: Lith.lib (src/lithshared/lith, built
#     by build/libs.sh lith): basehash.obj 0x1004bb20..0x1004bcfa, then
#     baselist.obj (CBaseList::InsertFirst/Delete 0x1004bd00/0x1004bd30) and
#     virtlist.obj (CVirtBaseList::InsertFirst/Delete 0x1004bd60/0x1004bd90),
#     all 13 byte-identical. The basehash iterator/bin code is what rezmgr
#     calls (CRezDir::GetNextSubDir 0x1003aca0 calls 0x1004bb20). /GX code
#     using __ehvec_ctor with rezmgr's bin dtor 0x1003b460 and the engine's
#     0x1000d25d/0x10028ace allocator pair; its twin sits after lithtech.exe's
#     CRT too (0x4a03d0..), byte-identical, so it is a prebuilt Monolith lib.
#     It is bracketed by CRT: an IAT jump thunk at 0x1004bb10 below it and
#     _strupr, __ehvec_ctor/dtor, __ArrayUnwind from 0x1004bdd0 on.
#   Deliberately NOT included: 0x1004c070..end, the C++ EH unwind funclets
#   and __ehhandler stubs (.text$x) of Monolith functions -- compiler-
#   generated, 2-5 unmasked bytes each, not separately reconstructable.
#   lithtech.exe 0x004a03d0..0x004a061f: the same library's basehash.obj
#     (CBaseHashItem::Next 0x4a03d0 .. CBaseHash::GetFirstInBin 0x4a0590)
#     and virtlist.obj (CVirtBaseList::InsertFirst 0x4a05b0, ::Delete
#     0x4a05e0), byte-identical to server.dll 0x1004bb20..0x1004bdc3 and
#     matched by src/lithshared/out/Lith.lib. Bracketed by CRT the same way:
#     an IAT jump thunk at 0x4a03be below it, __ehvec_ctor at 0x4a0620
#     above. (baselist.obj was pulled earlier here, into the app region at
#     0x0048de30..0x0048df0f.)
#   CShell.dll 0x100fd930..0x1010086f: LithFontMgr_LT2.lib, linked after
#     the CRT exactly as in our CShell.dll (our map: LithFontMgr_LT2 between
#     LIBCMT and __strupr). Its 29 unique hits run 0x100fda40 (LithFont's
#     constructor) .. 0x10100760 (LithBitmapFont::ClipFont, 250 bytes);
#     below it an import thunk (jmp [0x101080dc] at 0x100fd920, then int3
#     padding), above it, after a 4-byte nop-padded accessor at 0x10100860,
#     libcmt's __strupr at 0x10100870 (the same bytes as ours).
#   Object.lto 0x101503e0..0x101503ff: MFCStub's CRect::CRect(l, t, r, b)
#     (32 bytes, ret 0x10), linked after the CRT as in our Object.lto: an
#     import thunk at 0x101503d0 below it, CRT code from 0x10150400.
#   d3d.ren 0x1007faa0..0x1007fb1f: StdLith's l_allocator.cpp -- LAlloc's
#     three virtuals (0x1007fae0 Alloc, 0x1007faf0 Free, 0x1007fb00 the
#     scalar deleting destructor; vtable 0x100881b8) and g_DefAlloc's VC6
#     initialiser thunks (0x1007faa0 `call 0x1007fab0; jmp 0x1007fac0`,
#     the vtable store, the atexit registration, the atexit destructor).
#     Monolith's code: its Alloc and Free call the renderer's own
#     DefStdlithAlloc/DefStdlithFree (0x10021ce0/0x10021cb0), and
#     src/engine/d3d/w12_7fae0.cpp is all seven, byte-identical (cl 8447,
#     as StdLith). It opens the tail above APP_REGION; StdLith.lib's
#     struct_bank.obj follows at 0x1007fb20 (sb_Init), which d3d.ren does
#     not score (StdLith's own row does).
APP_ISLANDS = {
    "server.dll": [(0x1004bb20, 0x1004bdd0)],
    "lithtech.exe": [(0x004a03d0, 0x004a0620)],
    "CShell.dll": [(0x100fd930, 0x10100870)],
    "Object.lto": [(0x101503e0, 0x10150400)],
    "d3d.ren": [(0x1007faa0, 0x1007fb20)],
}


# Third-party middleware linked INSIDE an app region: real code in the
# binary, but not Monolith's and not a reconstruction target, so -- like the
# CRT above the region -- its functions are listed ("middleware") and not
# counted. The game DLLs link the GameSpy library between ButeMgrNoMFC and
# the CRT/RegMgr: Monolith's thin CGameSpy* wrapper over the GameSpy SDK
# (the "C Engine" server list in CShell, the query responder in Object),
# shipped prebuilt; src/lithshared/gamespy/ stands in for it from the
# headers alone and is deliberately not byte-matched (the master server it
# talked to is gone). Evidence for the ranges: the WSOCK32 imports, the
# master.gamespy.com and \gamename\%s\... strings and every caller of the
# block lie in it, and nothing else in the image calls into it except
# through the wrapper.
#   CShell.dll 0x100eb650..0x100edab0: CGameSpyClientMgr::Init (strcpy of
#     the game name and key into +8/+0x88) right after ButeMgrNoMFC's
#     zSLink::freecache, through the SDK's hash table/array helpers, to
#     libcimt's first function at 0x100edab0 (APP_REGION's end).
#   Object.lto 0x10140950..0x10141b30: CGameSpyMgr::Init (7 arguments,
#     this+0x107c) right after StdLith's MoArray_FindElementMemcmp, to the
#     end of the last function's switch table; RegMgr's CRegMgr::Init
#     starts at 0x10141b30.
MIDDLEWARE = {
    "CShell.dll": [(0x100eb650, 0x100edab0)],
    "Object.lto": [(0x10140950, 0x10141b30)],
}


def in_middleware(label, a):
    return any(l <= a < h for l, h in MIDDLEWARE.get(label, ()))


def in_app(label, a, lo, hi):
    """True when address a is Monolith code (APP_REGION or an island, less
    MIDDLEWARE)."""
    if in_middleware(label, a):
        return False
    if lo <= a < hi:
        return True
    return any(l <= a < h for l, h in APP_ISLANDS.get(label, ()))


# Where a prebuilt library linked into an image actually sits, when that has
# been established from evidence. A match for one of the library's functions
# outside its range is refused outright -- the library is linked as one
# block, so a hit elsewhere is the engine's own copy of the same bytes (a
# template instance, a 16-byte free wrapper) or a coincidence, never the
# library -- and its unanchorable functions claim "small" addresses by shape
# only inside it. The anchored-span rule in rows_for_image is the fallback
# for libraries not listed here; it is not enough on its own when one stray
# anchor stretches the span over engine code.
#   lithtech.exe StdLith.lib 0x490b50..0x4919df: every StdLith function with
#     a unique hit lands in one run, in link order struct_bank (sb_Init
#     0x490b50 .. sb_AllocateNewStructPage 0x490c20, ends 0x490c7e), helpers
#     ($E2/$E1 initializer thunks 0x490c80/0x490c90 -- `jmp` / `mov ecx,
#     &g_Helpers; jmp ??0CHelpers` -- then CHelpers::CHelpers 0x490ca0 ..
#     ExtractNames 0x490e50), stringholder (CStringHolder ctor 0x490f60 ..
#     ClearStrings 0x491270, its CMoArray<SBank> instances 0x4912d0..0x491739),
#     l_allocator ($E thunks 0x491740..0x49177b constructing the default
#     LAlloc global 0x4b4e88 with vtable 0x4a3c54, ~LAlloc 0x491780,
#     LAlloc::Alloc/Free 0x491790/0x4917a0 .. LAllocSimpleBlock::Clear
#     0x491940), dynarray (MoArray_FindElementMemcmp 0x491950) and
#     goodlinklist (GLinkedList_FindElementMemcmp 0x491990, ends 0x4919d1).
#     The same objects in the same order as server.dll 0x1003d170..0x1003e090,
#     byte-identical bar relocations (sb_Term2 0x490bd0 = 0x1003d1f0). Below
#     it, 0x490b40 is a 4-byte engine accessor after an engine function's
#     `ret`; above it, 0x4919e0 is a thiscall string copy matching no member
#     of either our or the shipped StdLith.lib (server.dll has the CRT's
#     fpinit straight after goodlinklist). Without the range, DefStdlithFree's
#     16 bytes credit the engine's own free wrapper at 0x436510, StdLith's
#     $E thunks take the engine's startup/atexit thunks 0x436880/0x4368b0,
#     and CAbstractIO::Open's 8 bytes (`mov eax,1; ret 8`) claim the tail of
#     0x4919e0 as a function at 0x491a10.
LIB_RANGE = {
    "lithtech.exe": {"StdLith.lib": (0x00490b50, 0x004919e0)},
}


def load_lib(path):
    """Return {symbol: masked_code} for a .lib (via objdiff.parse_obj)."""
    out = {}
    with tempfile.TemporaryDirectory() as td:
        extract(path, td)
        for m in sorted(glob.glob(td + "/*")):
            out.update(parse_obj(open(m, "rb").read()))
    return out


def rows_for_lib(label, ours_path, libdir):
    theirs = load_lib(os.path.join(libdir, SHIPPED_AS.get(label, label + ".lib")))
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


def _enum_with_sizes(path, label=None):
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
        sizes[a] = hi - lo
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


# progress/<prefix>-screen-exclude.csv records rows of ONE image, named by
# the file's prefix.
# They used to be read by ADDRESS ALONE, from every file, for every image --
# harmless while the only two files were lithtech.exe's (0x004xxxxx) and
# server.dll's, but d3d.ren shares server.dll's 0x10000000 base, so a d3d
# row would have dropped or relabelled whatever server.dll function sits at
# the same address. A file whose prefix is in this table applies only to its
# image; any other file (none today) keeps the old apply-everywhere reading.
_EXCLUDE_IMAGE = {
    "lithtech": "lithtech.exe",
    "server":   "server.dll",
    "d3d":      "d3d.ren",
    "cshell":   "CShell.dll",
    "object":   "Object.lto",
}


def _exclude_files(label):
    """The screen-exclude files whose rows apply to image `label`."""
    out = []
    for f in sorted(glob.glob(DATA + "/*-screen-exclude.csv")):
        prefix = os.path.basename(f)[:-len("-screen-exclude.csv")]
        img = _EXCLUDE_IMAGE.get(prefix)
        if label in GAME_LABELS:
            # only the game DLL's own file: the engine files' addresses
            # overlap the game DLLs' 0x10000000 range by coincidence
            if img == label:
                out.append(f)
        elif img is None or label is None or img == label:
            out.append(f)
    return out


_REASONS = {}


def _phantom_reasons(label=None):
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


LINKED = {   # our whole-exe link, used as a second, unmasked oracle
    "NOLF.exe": "src/engine/launcher/Release/NOLF.exe",
}

# Our own link of each image: its .map says where each of our functions went,
# which is what tells "written but not placed" (in our image, no shipped
# address) from code our linker drops too (not in our image either), and
# what the join in _rows_for_image places functions by.
OUR_MAP = {
    "NOLF.exe":     "src/engine/launcher/Release/NOLF.map",
    "server.dll":   "src/engine/server/Release/server.map",
    "lithtech.exe": "src/engine/lithtech/Release/lithtech.map",
    "d3d.ren":      "src/engine/d3d/Release/d3d.map",
    "CShell.dll":   "src/game/ClientShellDLL/Final_Release/CShell.map",
    "Object.lto":   "src/game/ObjectDLL/Final_Release/Object.map",
}


# Translation units of ours that exist only to make the compiler emit
# functions for the oracle to compare (sdkforce.cpp takes the address of
# every SDK inline, so ALL of them are out of line in our link, whether or
# not the shipped image has them so). Their functions are reported as
# "driver": not shipped code, so neither placed nor missing.
DRIVER_OBJS = {"sdkforce.obj"}


def _our_layout(label):
    """{(object, symbol): address} of the code in our linked image, from its
    .map (object lower-cased, as an object file's basename), or None when
    there is no map. Symbols the map lists twice (a static name in two
    objects) are told apart by their object."""
    m = OUR_MAP.get(label)
    if not m or not os.path.exists(os.path.join(REPO, m)):
        return None
    out = {}
    for line in open(os.path.join(REPO, m), errors="replace"):
        p = line.split()
        if len(p) < 4 or not p[0].startswith("0001:") or \
                not re.fullmatch(r"[0-9a-fA-F]{8}", p[2]):
            continue
        obj = p[-1].split(":")[-1].lower()
        out.setdefault((obj, p[1]), int(p[2], 16))
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


def rows_for_image(label, exe_path, objs):
    """Score one image, then once more with the remainders of short matches.

    A row's size is reported as the length of what matched there, so when a
    SHORT function of ours matches at a start whose enumerated extent also
    holds more code -- icl's 14-byte stack-realign stub in front of a large
    body (0x1004b720: 14 of 11,204 bytes), or a register-entry stub whose
    caller's body follows (0x10024024: 108 of 5,672) -- the rest of the
    extent dropped out of funcs and bytes_total entirely: 28 KB of d3d.ren
    had silently left the denominator that way, and the body behind a stub
    had no row to pair with even when we had written it. The code behind
    such a match is its own function (the match ended in a ret or a tail
    jump), so its first non-padding byte becomes a start, and the image is
    scored again with those starts added.
    """
    rows = _rows_for_image(label, exe_path, objs)
    extra = _remainders(label, exe_path, rows)
    if extra:
        _REMAINDER_STARTS[label] = extra
        # the second pass records its own pairs: drop the first pass's
        NEAR_PAIRS[:] = [r for r in NEAR_PAIRS if r[0] != label]
        rows = _rows_for_image(label, exe_path, objs)
    return rows


def _remainders(label, exe_path, rows):
    p = os.path.join(REPO, exe_path)
    img, starts, sizes = _enum_with_sizes(p, label)
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


# Trailing alignment encodings (tools/d3dcheck.py's PADS): VC6 pads with
# 0x90/0xCC, icl with multi-byte lea / mov nops.
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


def _own_addr(label, n, funcs=None):
    """The shipped address a symbol of ours names: `sub_<addr>` (the d3d
    convention), or for d3d.ren an engine name tools/d3dcheck.py's NAMED
    table maps (d3d_IsInOptimized2D -> 0x10034c60), or a template member its
    SYMBOLS table maps by full name. None if it names none.
    Only ever a preference: a placement there still needs the bytes to
    agree.

    d3d.ren, given our functions: icl's /Qip register entry `X$` (and the
    `X$$1` body behind a 14-byte stack-realigning entry) sits the stack
    entry X's length above the address X names, exactly as d3dcheck.py
    places it.  Without that, `sub_100124a0$` preferred 0x100124a0 -- the
    4-byte stack entry, already matched -- and an 8 KB body whose first 38
    bytes are the shipped 0x100124a4's lost the ranking to unrelated
    functions of similar length agreeing on 9% of their bytes."""
    m = re.search(r"sub_(1[0-9a-f]{7})", n)
    a = int(m.group(1), 16) if m else None
    if a is None and label == "d3d.ren":
        a = D3D_SYMBOLS.get(n.split(":", 1)[-1])
    if a is None and label == "d3d.ren":
        leaf = re.sub(r"^\?", "", n.split(":", 1)[-1]).split("@")[0]
        for k, v in sorted(D3D_NAMED.items(), key=lambda kv: -len(kv[0])):
            if k in leaf:
                a = v
                break
    if a is not None and label == "d3d.ren" and funcs is not None:
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


def _rows_for_image(label, exe_path, objs):
    """A PE image under reconstruction (exe or dll, no symbols).

    Denominator = every enumerated function inside the image's app region
    (see APP_REGION); functions outside it are the static CRT/MFC and are
    emitted as status "crt" so they stay visible but do not count.
    identical = an exematch hit for one of our objects.
    """
    p = os.path.join(REPO, exe_path)
    pe = Pe(p)
    tva, tvs, trp = pe.secs[".text"]
    text = pe.d[trp : trp + tvs]
    img, starts, sizes = _enum_with_sizes(p, label)

    # Key by module as well as symbol: compiler-generated names are numbered
    # per object, so `_$E192` exists in more than one of ours and a bare-symbol
    # dict silently drops all but the last — which loses whole initializer
    # groups from the count.
    funcs = {}
    unpadded = {}      # d3d symbols with icl lea-nop padding: the bare body
    from_lib = set()   # symbols pulled in from an already-scored .lib
    for o in objs:
        q = os.path.join(REPO, o)
        mod = os.path.basename(o)
        if o.lower().endswith(".lib"):
            with tempfile.TemporaryDirectory() as td:
                extract(q, td)
                for m in sorted(glob.glob(td + "/*")):
                    for k, v in parse_obj_masked(open(m, "rb").read()).items():
                        key = "%s:%s" % (mod, k)
                        # a .lib is many objects under ONE module name, and
                        # compiler-generated names repeat across them:
                        # StdLith's helpers.obj and l_allocator.obj both
                        # have `_$E1`/`_$E2`, and the later member silently
                        # replaced the earlier, so helpers' g_Helpers
                        # initializer (server 0x1003dd80, lithtech
                        # 0x490c90) could never claim its address. Name a
                        # repeat by its member too.
                        if key in funcs:
                            key = "%s:%s@%s" % (mod, k, os.path.basename(m))
                        funcs[key] = v
                        from_lib.add(key)
        else:
            for k, v in parse_obj_masked(open(q, "rb").read()).items():
                # instantiation drivers exist only to make VC6 emit template
                # COMDATs (packet.cpp); they are ours, not Monolith's, and
                # must neither score nor pair
                if "ForceInstantiation" in k:
                    continue
                # ??_H / ??_I are the vector constructor and destructor
                # iterators VC6 emits per object as a by-product of `new T[n]`
                # and `delete [] p`. With exceptions off it expands the loop
                # inline and never references them, so the linker drops them —
                # they are the compiler's code either way, not reconstructed
                # source, and scoring them counts a phantom against us.
                if k.startswith("??_H") or k.startswith("??_I"):
                    continue
                # icl (d3d.ren) pads a COMDAT with multi-byte lea-nops, not
                # 0x90/0xCC, and parse_obj_masked only strips the latter; the
                # leftover pad then has to match whatever the shipped image has
                # after the function, so an identical function could never be
                # found and scored "near". Strip the same set d3dcheck.py does.
                if "src/engine/d3d/" in o.replace("\\", "/"):
                    code, mask = v
                    body = strip_pad(code)
                    if body != code:
                        unpadded["%s:%s" % (mod, k)] = (
                            body, {i for i in mask if i < len(body)})
                funcs["%s:%s" % (mod, k)] = v

    # Several of our functions compile to identical code (CCard::GetName and
    # CPreview::GetName; DoDetailDialog and DoCustomizeDialog; the three
    # CDib::Init overloads), and the shipped linker folded some of those into
    # one address while emitting others separately. Assign greedily so each of
    # our functions claims a distinct shipped address rather than all of them
    # crediting the first hit.
    #
    # A library function with more than one hit (Lith.lib's CBaseList::Delete
    # has the same bytes as an engine list's Remove at 0x00442c90 in
    # lithtech.exe) takes the fresh hit nearest the addresses its library's
    # single-hit functions anchored: a library is linked as a block, so its
    # own copy is the one beside its siblings, not the first one in .text.
    matched = {}
    tiny = {}          # our functions with too few unmasked bytes to anchor
    lib_hits = {}
    lib_range = LIB_RANGE.get(label, {})
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
    # A generic shape (a d3d.ren thiscall thunk recurs at 19 addresses)
    # otherwise claims the FIRST free hit and leaves the address it was
    # written for unscored, or a same-shape neighbour takes it first. A symbol
    # named for its address (`sub_<addr>`, the d3d convention) whose bytes
    # match AT that address is placed there before anything else.
    # (d3d.ren: also a name tools/d3dcheck.py's NAMED table maps -- the
    # engine-named getters d3d_IsIn3D and d3d_IsInOptimized2D are the same
    # six bytes, and by first-fit each was credited at the other's address.)
    for n, (code, mask) in sorted(funcs.items()):
        a = _own_addr(label, n, funcs)
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
            # icl pads a COMDAT with multi-byte lea-nops, not 0x90/0xCC, and
            # parse_obj_masked strips only those two; where the shipped image
            # has different bytes after the function the padded body is
            # found nowhere. Try the body without it.
            code, mask = unpadded[n]
            if len(code) - len(mask) >= 8:
                hits = list(find(text, tva, code, mask))
        if not hits:
            continue
        fresh = [h for h in hits if h not in matched]
        # A hit that is not an enumerated function start is a byte-run
        # inside some other function (a short body's masked shape recurring
        # in a neighbour's tail): only take it when nothing better exists.
        # input_GetInputMgr's 13 bytes otherwise claim 0x00408b9e, the else
        # arm of 0x00408b80, and leave its own 0x00439fb0 unscored.
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

    # A library linked into an engine image is one contiguous block of it, so
    # a library function's hit strictly inside another matched function is a
    # coincidence (StdLith's 8-byte CAbstractIO::Open "matches" the middle of
    # rezmgr2's CRezDirX720::RemoveRezInternal in server.dll). Drop those,
    # and let the library's unanchorable functions claim addresses by shape
    # only inside the span its anchored functions occupy -- outside it,
    # StdLith's $E initializer thunks otherwise claim the engine's own.
    lib_span = {}
    for at in [a for a in matched if PLACED_SYMS.get((label, a)) in from_lib]:
        if any(b < at < b + m for b, m in matched.items() if b != at):
            del matched[at]
            del PLACED_SYMS[(label, at)]
            continue
        mod, sym = PLACED_SYMS[(label, at)].split(":", 1)
        if "?$" in sym or sym.startswith(("??_G", "??_D")):
            # template instances, deleting dtors and the iostream classes'
            # vbase dtors (ButeMgr's ??_Dstrstream matches the game objects'
            # copy at CShell 0x10085de0) are emitted by every object that
            # uses them and fold anywhere; they place nothing
            continue
        l0, h0 = lib_span.get(mod, (at, at))
        lib_span[mod] = (min(l0, at), max(h0, at + matched[at]))
    for n in [n for n in tiny if n in from_lib]:
        mod = n.split(":", 1)[0]
        if mod not in lib_span and mod not in lib_range:
            del tiny[n]
    # In a game DLL a library's block also takes in the unmatched addresses
    # around its anchored span, up to the nearest function matched from
    # anything else (or the end of .text): a library's first or last
    # function can be one too short to anchor (CryptMgr's 3-byte
    # ??0CCryptMgr ahead of its SetKey, LithBitmapFont::IsChromaKeyed after
    # its ClipFont), and the span alone leaves it no address to claim.
    lib_block = dict(lib_span)
    if label in GAME_LABELS:
        def foreign(a, mod):
            return (PLACED_SYMS.get((label, a)) or "").split(":", 1)[0] != mod
        order = sorted(matched)
        for mod, (l0, h0) in lib_span.items():
            below = [a + matched[a] for a in order if a < l0 and foreign(a, mod)]
            above = [a for a in order if a >= h0 and foreign(a, mod)]
            lib_block[mod] = (max(below) if below else tva,
                              min(above) if above else tva + len(text))

    # Second oracle: our own whole-exe link. exematch has to mask relocation
    # bytes because it compares an unlinked .obj, which leaves the global
    # initializer COMDATs — two unmasked opcodes each — unverifiable. In a
    # linked image those relocations are resolved, so a function built purely
    # from relative displacements can be compared byte for byte with nothing
    # masked at all. That is a stronger claim than the masked match, not a
    # weaker one; it just only applies to functions with no absolute operands.
    linked = None
    lp = os.path.join(REPO, LINKED.get(label, ""))
    if LINKED.get(label) and os.path.exists(lp):
        linked = EnumImage(lp).text

    lo, hi = APP_REGION.get(label, (img.tlo, img.thi))

    # Enumeration finds some starts that are not functions: exception-handler
    # funclets and jump islands inside a function we have already matched, and
    # the odd 1-byte fragment left by the padding carve. Anything strictly
    # inside a matched function's span is one of those, not a target.
    inside = set()
    for a, n in matched.items():
        for b in starts:
            if a < b < a + n:
                inside.add(b)
    starts = [a for a in starts if a not in inside]

    # Global-initializer COMDATs ($E thunks, the ??__E constructors and the
    # atexit registrations) are almost entirely relocation bytes: a `call
    # rel32; jmp rel32` pair leaves two unmasked opcodes, which anchors
    # nowhere. They cannot be verified by this oracle even when the source is
    # certainly right. Claim them by shape instead — each of our unanchorable
    # functions takes one distinct shipped address whose bytes agree outside
    # the mask — and score them "small": reconstructed, not verified.
    if linked is not None:
        for a in starts:
            if a in matched or not in_app(label, a, lo, hi):
                continue
            n = sizes.get(a, 0)
            if n < 1:
                continue
            b = text[a - tva : a - tva + n]
            if b and b in linked:
                matched[a] = n

    small = set()
    placed_small = set()

    def own_first(n):
        """d3d.ren: a symbol named for its address (`sub_<addr>`) tries that
        address first, as the exact-match placement above does -- a 6-byte
        `mov <g>,%eax ; ret` or a 1-byte `ret` fits every other one of its
        shape, and taking the first in address order steals a sibling's."""
        a0 = _own_addr(label, n, funcs) if label == "d3d.ren" else None
        if a0 is not None and a0 in starts:
            return [a0] + [a for a in starts if a != a0]
        return starts

    # Relocation-free functions first: those bytes are the whole function, so
    # a shape match is exact, while one with a relocation (`mov eax, <addr>;
    # ret`) fits every sibling of its shape. In name order the second kind
    # could take the address of the first: Object.lto's 6-byte attribute-name
    # stubs (`mov eax, "SeeEnemyDistance"; ret` beside `mov eax, 1000; ret`)
    # took each other's addresses and left 0x10073760 unwritten.
    for n, (code, mask) in sorted(tiny.items(),
                                  key=lambda kv: (len(kv[1][1]) > 0, kv[0])):
        # a COMDAT is padded out to alignment; the function is what precedes it
        end = len(code)
        while end > 0 and code[end - 1] in (0x90, 0xCC):
            end -= 1
        for a in own_first(n):
            if a in matched or a in small or not in_app(label, a, lo, hi):
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

    # d3d.ren is icl's, which pads with multi-byte lea-nops (d3dcheck.PADS)
    # as well as 0x90: a 1-byte `ret` followed by `90 8d b4 26 ..` keeps a
    # 16-byte extent once only 0x90/0xCC are stripped, so the same-length
    # test above can never pass for it. A second pass, for the tiny d3d
    # functions the first one left unplaced only, compares the bodies with
    # that padding stripped on both sides.
    if label == "d3d.ren":
        for n, (code, mask) in sorted(tiny.items()):
            if n in placed_small or n in from_lib:
                continue
            end = len(strip_pad(bytes(code)))
            for a in own_first(n):
                if a in matched or a in small or not in_app(label, a, lo, hi):
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
    # A library function in a game DLL whose bytes are found nowhere is one
    # of the few its own library's score has as near (zErrHandler::set_ef,
    # LithBitmapFont::FindOffset and Draw_Method_Timed): the shipped .lib's
    # copy is what the image links, so pair it the same way, but only inside
    # its library's block and only if our own link has it.
    lib_near_ok = set()
    if label in GAME_LABELS:
        layout_syms = {sym for (_o, sym) in (_our_layout(label) or {})}
        lib_near_ok = {n for n in funcs if n in from_lib and
                       n.split(":", 1)[0] in lib_block and
                       re.sub(r"@[^@]+\.obj$", "", n.split(":", 1)[1])
                       in layout_syms}
    if not from_lib is None:
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
            # d3d.ren: a symbol named for its address is tried THERE first,
            # as own_first does for the exact and small placements -- a 5.8 KB
            # clipper whose bytes differ mostly by register choice agrees with
            # its own address on ~12% of them and with an unrelated big
            # function on 16%, and the ranking below paired it with neither.
            a0 = _own_addr(label, n, funcs) if label == "d3d.ren" else None
            cand = starts
            if a0 is not None and a0 in start_set:
                cand = [a0] + [a for a in starts if a != a0]
            blk = lib_block.get(n.split(":", 1)[0]) if n in from_lib else None
            for a in cand:
                if a in matched or a in paired or not in_app(label, a, lo, hi):
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
                    # either a shared 16-byte opening — far more than two
                    # unrelated functions with similar prologues manage — or
                    # most of the body agreeing, with the length lining up too.
                    # Both then have to survive the epilogue and have enough
                    # unmasked bytes for the ratio above to have meant
                    # anything: a dozen agreeing bytes out of a dozen is a
                    # calling convention, not a function.
                    ok = (pfx >= 16 or agree >= 0.5) and den >= 12
                    # The shipped row's extent runs to the next start, so on
                    # d3d.ren it still carries icl's multi-byte lea/mov nop
                    # padding (`8b f6`, `8d 76 00` ...): `tail` then saw no
                    # `ret` and a correct body could never pair (0x10077680,
                    # 0x10078910). Strip that padding first, as `code` is.
                    m_end = off + m
                    if label == "d3d.ren":
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
    layout = _our_layout(label)
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

    def unplaced_sym(n):
        """Ours, linked into our image, and placed nowhere in the shipped
        one (nor folded, in our own link, onto a function that is)."""
        if n in from_lib or n in placed_at or n not in ours_at or \
                n.split(":", 1)[0].lower() in DRIVER_OBJS:
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
        return len(strip_pad(bytes(code[:end]))) if label == "d3d.ren" else end

    def chain_of(anchors):
        """The longest run of (ours, shipped) anchors, in our order, whose
        shipped addresses rise too."""
        import bisect
        anchors = sorted(anchors)
        idx, prev = [], [-1] * len(anchors)
        for k, (_o, r) in enumerate(anchors):
            j = bisect.bisect_left([anchors[i][1] for i in idx], r)
            if j > 0:
                prev[k] = idx[j - 1]
            if j == len(idx):
                idx.append(k)
            else:
                idx[j] = k
        out, k = [], idx[-1] if idx else -1
        while k >= 0:
            out.append(anchors[k])
            k = prev[k]
        return out[::-1]

    if ours_at:
        import bisect
        free = {a for a in starts if in_app(label, a, lo, hi)
                and a not in matched and a not in paired
                and a not in small and sizes.get(a, 0) > 0}
        joined = {"name": 0, "object": 0, "image": 0}

        def place(n, a, how):
            paired[a] = n
            placed_at[n] = a
            placed_names.add(fname(n))
            # ... and every other name at its address in our own link, as
            # for the placements above: icl's /Qip `X$$1` is a second label
            # at X's own offset (both at 0 of one COMDAT, a zero-length
            # "function"), so once X is joined by name (big1ef30's
            # sub_1001ef30, big4b720's sub_1004b720, d3dqip2's
            # sub_1003ad30) its $$1 is that same placed function, not a
            # surplus one -- and must not take a free address of its own.
            if n in ours_at:
                our_placed.add(ours_at[n])
            free.discard(a)
            NEAR_PAIRS.append((label, a, sizes.get(a, 0), n,
                               body_len(funcs[n][0])))
            joined[how] += 1

        # 1. By name: a function named for the shipped address it was
        # written as (`sub_<addr>`, d3d.ren's convention) is that function,
        # however differently it compiled -- a partial rebuild of an 11 KB
        # function can be half its size.
        for n in sorted(funcs):
            if not unplaced_sym(n):
                continue
            if label == "d3d.ren":
                a = _own_addr(label, n, funcs)
            else:
                m = re.search(r"\bsub_([0-9a-f]{6,8})\b", n)
                a = int(m.group(1), 16) if m else None
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
        # need not follow the shipped one (a reconstructed file is not laid
        # out in Monolith's order: our commonphysics.obj's functions run in
        # another order than the shipped ones), so X's unplaced functions
        # are matched to those shipped ones by size, closest first, within
        # a factor of two.
        import math
        owner = sorted((a, n.split(":", 1)[0]) for n, a in placed_at.items()
                       if ":" in n)
        owner_r = [a for a, _o in owner]
        cand = {}
        for a in sorted(free):
            i = bisect.bisect_left(owner_r, a)
            objs = set()
            if i:
                objs.add(owner[i - 1][1])
            if i < len(owner):
                objs.add(owner[i][1])
            for obj in objs:
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
    # Functions we wrote source for that did NOT match: instruction-equivalent
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
            # a scoring driver's own short functions (sdkforce.cpp's
            # pointer-to-member globals each get a 5-byte `_$E` initializer
            # thunk and its body) are not shipped code: counted here they
            # inflated the surplus of their shape, and the excess was then
            # reported against whichever real object's functions of that
            # shape sorted last (worldsim.obj's `_$E` thunks).
            if len(code) - len(mask) >= 8 or n in from_lib or \
                    n not in ours_at or fname(n) in seen or \
                    n.split(":", 1)[0].lower() in DRIVER_OBJS:
                continue
            seen.add(fname(n))
            mine_by_shape.setdefault(shape(code, mask), []).append(n)
        by_len = {}
        for key in mine_by_shape:
            by_len.setdefault(len(key[0]), []).append(key)
        theirs_count = dict.fromkeys(mine_by_shape, 0)
        for a in starts:
            if not in_app(label, a, lo, hi):
                continue
            off = a - tva
            body = text[off:off + sizes.get(a, 0)]
            body = strip_pad(bytes(body)) if label == "d3d.ren" else \
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
        if n.split(":", 1)[0].lower() in DRIVER_OBJS and n not in claimed \
                and n not in placed_at:
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
            # -- it is usually code this image never links. lithtech.exe
            # compiles 44 of the server's translation units, so every
            # server-only function lands here. Counting these as shipped
            # functions inflated the denominator by 1548 rows and made four
            # FINISHED libraries read 87-98% when they are at 100%: their
            # entire "near" column was this. Reported in its own column and
            # excluded from funcs/bytes_total -- as "unlinked" when our own
            # link leaves it out too (or there is no map to say).
            rows.append((label, n, len(code),
                         "unlinked" if ours_at else "unplaced"))
    for a in sorted(set(starts) | set(matched)):
        size = matched.get(a, sizes.get(a, 0))
        if in_middleware(label, a):
            rows.append((label, "sub_%x" % a, size, "middleware"))
        elif a in matched:
            rows.append((label, "sub_%x" % a, size, "identical"))
        elif a in paired:
            rows.append((label, "sub_%x" % a, size, "near"))
        elif a in small:
            rows.append((label, "sub_%x" % a, size, "small"))
        elif in_app(label, a, lo, hi):
            # SPLIT: "todo" now means nobody has looked at it. An address we
            # have evidence of working on -- written and unplaceable, decoded,
            # or recorded as not-work -- is "attempted" and counted apart.
            rows.append((label, "sub_%x" % a, size,
                         "attempted" if a in _touched_index(label) else "todo"))
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


def rows_for_resources(label, shipped, ours):
    """A resource-only image: one row per shipped resource, `type/name/lang`,
    sized by its data. identical = our resource has the same bytes; near =
    we have it, but its bytes differ; todo = we have none by that key."""
    theirs = _resources(shipped)
    mine = _resources(ours) if os.path.exists(ours) else {}
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


def calltarget_starts(path):
    """Function starts for a symbol-less PE: call rel32 targets + exports.

    More accurate than padding-carve for binaries with no inter-function
    padding (server.dll, d3d.ren). Returns (sorted starts, text_lo, text_hi).
    """
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + optsz
    tlo = thi = trp = 0
    for i in range(nsec):
        s = so + i * 40
        name = d[s : s + 8].rstrip(b"\0").decode("latin-1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, s + 8)
        if name == ".text":
            tlo, thi, trp = base + va, base + va + vs, rp
    text = d[trp : trp + (thi - tlo)]
    starts = set()
    for off in range(len(text) - 5):
        if text[off] == 0xE8:
            rel = struct.unpack_from("<i", text, off + 1)[0]
            tgt = tlo + off + 5 + rel
            if tlo <= tgt < thi:
                starts.add(tgt)
    return sorted(starts), tlo, thi


def rows_for_engine(label, path):
    """Unstarted engine binary: full function enumeration (tools/enumfuncs.py).

    Same enumerator as the started binaries, so the denominators are directly
    comparable: call targets + data pointers (vtables) + exports + code after a
    ret that nothing references. Padding-carving is NOT used — it works on
    lithtech.exe but fails on server.dll/d3d.ren, which have almost no
    inter-function padding.
    """
    img = EnumImage(os.path.join(REPO, path))
    starts, _src = enumerate_functions(img)
    rows = []
    for i, a in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else img.thi
        lo, hi = a - img.tlo, min(end - img.tlo, len(img.text))
        while hi > lo and img.text[hi - 1] in (0x90, 0xCC):
            hi -= 1
        rows.append((label, "sub_%x" % a, hi - lo, "todo"))
    return rows



# ---------------------------------------------------------------------------
# TOUCHED: is there evidence in the tree that THIS shipped address has been
# worked on? `todo` only ever meant "no exact match and no successful
# pairing", so a function we have written whose bytes drifted past the
# pairing tolerance was counted identically to code nobody has ever looked
# at. Measured across the three engine images, ~85% of `todo` is the former
# -- which made the scoreboard's red bar a picture of imperfection rather
# than of remaining effort.
#
# Evidence accepted, cheapest first: the address is cited anywhere in our
# sources, or the decoded map places a symbol there, or a screen-exclude
# row records it as not-work.
_TOUCHED = {}

_PHANTOM = {}


def _phantom_index(label=None):
    """Addresses PROVEN not to be functions, to be dropped from the count.

    The enumeration is wrong in both directions. Now that the remaining
    work is small, the error matters: a row that is an
    operand byte, an interior jump target, alignment padding or an ASCII
    accident is not code, and leaving it in the denominator makes 100%
    unreachable BY CONSTRUCTION rather than by any fact about the source.

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


_CITED = None


def _cited_addrs():
    """Every 0x... cited in our sources: one scan, shared by all images."""
    global _CITED
    if _CITED is not None:
        return _CITED
    blob = []
    for base in ("src/engine", "src/lithshared"):
        for root, _, fs in os.walk(base):
            for f in fs:
                if f.endswith((".cpp", ".h")) and "NAMEMAP" not in f:
                    try:
                        blob.append(open(os.path.join(root, f),
                                         errors="ignore").read())
                    except OSError:
                        pass
    text = "\n".join(blob)
    _CITED = set(re.findall(r"0x[0-9a-fA-F]{6,8}", text))
    return _CITED


def _touched_index(label=None):
    if label in _TOUCHED:
        return _TOUCHED[label]
    # The game DLLs are built from Monolith's own source, which cites no
    # retail address; the addresses src/engine/ cites are the engine
    # images', and server.dll's and d3d.ren's share the game DLLs' range
    # (0x10000000+), so counting them here would mark game functions
    # "attempted" by coincidence.
    if label in GAME_LABELS:
        _TOUCHED[label] = set()
        return _TOUCHED[label]
    addrs = set(_cited_addrs())
    for extra in glob.glob(DATA + "/*-decoded-map.csv") + \
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


def main():
    os.chdir(REPO)

    # A missing reference image would silently drop its target from the
    # totals; refuse instead.
    missing = [n for n in ("NOLF.exe", "lithtech.exe", "server.dll", "d3d.ren",
                           "CShell.dll", "Object.lto", "CRes.dll")
               if not os.path.exists(os.path.join(REFERENCE, n))]
    if missing:
        sys.exit("progress.py: %s missing from %s/ -- run `make progress`, or "
                 "tools/retailextract.py reference <retaildir> %s"
                 % (", ".join(missing), REFERENCE, REFERENCE))
    # ... and so would a missing build: every function would read "todo".
    unbuilt = [d for d in ("src/engine/launcher", "src/engine/server",
                           "src/engine/lithtech", "src/engine/d3d")
               if not glob.glob(d + "/Release/*.obj")] + \
              [g[2] for g in GAME if not glob.glob(g[2] + "/*.obj")] + \
              [GAME_RES[2]] * (not os.path.exists(GAME_RES[2])) + \
              [p for _l, p in LIBS if not os.path.exists(p)]
    if unbuilt:
        sys.exit("progress.py: no build output in %s -- run `make` first"
                 % ", ".join(unbuilt))

    libdir = shipped_lib_dir()
    all_rows = []
    if libdir:
        for label, ours in LIBS:
            all_rows += rows_for_lib(label, ours, libdir)
    else:
        print("progress.py: NOLF2_SOURCE not set -- the %d lithshared libraries "
              "are not scored (see progress/README.md)" % len(LIBS),
              file=sys.stderr)

    # every reconstructed launcher TU (stdafx.obj is empty -- not real
    # reconstruction)
    exe_objs = sorted(
        p for p in glob.glob("src/engine/launcher/Release/*.obj")
        if os.path.basename(p) != "stdafx.obj"
    )
    # RegMgr is linked into NOLF.exe from our own reconstructed lithshared lib,
    # so its functions in the exe are ours too
    exe_objs.append("src/lithshared/out/RegMgr.lib")
    all_rows += rows_for_image("NOLF.exe", REFERENCE + "/NOLF.exe", exe_objs)

    started = ({label for label, _ in LIBS} if libdir else set()) | {"NOLF.exe"}

    STARTED_ENGINE = {
        # StdLith.lib is linked into server.dll whole (0x1003d170..0x1003e0ef,
        # see APP_REGION); like RegMgr.lib in NOLF.exe, its functions there
        # are ours, from our reconstructed lib.
        "server.dll": (REFERENCE + "/server.dll",
                       sorted(glob.glob("src/engine/server/Release/*.obj"))
                       + ["src/lithshared/out/StdLith.lib",
                          # Lith.lib (basehash/baselist/virtlist): the
                          # APP_ISLANDS block above the CRT
                          "src/lithshared/out/Lith.lib"]),
        # The server's sources compiled a second time, with lithtech.exe's
        # own compiler revision and flags (build/engine.sh), plus its own TUs.
        "lithtech.exe": (REFERENCE + "/lithtech.exe",
                         sorted(glob.glob("src/engine/lithtech/Release/*.obj"))
                         # the same prebuilt Lith.lib as server.dll: its
                         # APP_ISLANDS block plus baselist at 0x0048de30
                         + ["src/lithshared/out/Lith.lib",
                            # StdLith.lib, confined to its block by LIB_RANGE
                            "src/lithshared/out/StdLith.lib"]),
        # Renderer-specific source only (icl 4.0; build/engine.sh).
        "d3d.ren": (REFERENCE + "/d3d.ren",
                    sorted(glob.glob("src/engine/d3d/Release/*.obj"))),
    }
    for label, path in ENGINE:
        se = STARTED_ENGINE.get(label)
        objs = [o for o in (se[1] if se else []) if os.path.exists(o)]
        if se and objs:
            all_rows += rows_for_image(label, se[0], objs)
            started.add(label)
        elif os.path.exists(path):
            all_rows += rows_for_engine(label, path)

    # the game DLLs: our objects plus the lithshared libraries each links
    for label, path, objdir, libs in GAME:
        objs = sorted(glob.glob(objdir + "/*.obj")) + \
            ["src/lithshared/out/%s.lib" % l for l in libs
             if os.path.exists("src/lithshared/out/%s.lib" % l)]
        all_rows += rows_for_image(label, path, objs)
        started.add(label)
    # scored, but not "started": resource data is not code, so it stays out
    # of the total (and the README lists it below it)
    all_rows += rows_for_resources(*GAME_RES)

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

    # aggregate
    targets = {}
    for label, name, size, status in all_rows:
        t = targets.setdefault(label, {"identical": 0, "near": 0, "todo": 0,
                                       "attempted": 0,
                                       "small": 0, "crt": 0, "crt_bytes": 0,
                                       "middleware": 0, "middleware_bytes": 0,
                                       "unplaced": 0, "unplaced_bytes": 0,
                                       "unlinked": 0, "unlinked_bytes": 0,
                                       "driver": 0, "driver_bytes": 0,
                                       "unwritten": 0, "unwritten_bytes": 0,
                                       "bytes_identical": 0, "bytes_total": 0,
                                       "funcs": 0})
        t[status] += 1
        if status in ("crt", "middleware"):  # not Monolith's: visible,
            t[status + "_bytes"] += size        # not a target
            continue
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

    for label, t in targets.items():
        t["started"] = label in started

    summary = {"libraries_scored": bool(libdir), "targets": targets}
    # "started" total = the reconstruction scoreboard (precise function metric)
    tot = {"identical": 0, "near": 0, "todo": 0, "attempted": 0,
           "small": 0, "funcs": 0,
           "unplaced": 0, "unplaced_bytes": 0,
           "unwritten": 0, "unwritten_bytes": 0,
           "bytes_identical": 0, "bytes_total": 0}
    for label, t in targets.items():
        if t["started"]:
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
    order = ([l for l, _ in LIBS] if libdir else []) + ["NOLF.exe"] + \
            [l for l, _ in ENGINE if l in targets and targets[l]["started"]] + \
            [g[0] for g in GAME]
    for label in order:
        if label not in targets:
            continue
        t = targets[label]
        pct = 100 * t["bytes_identical"] / max(t["bytes_total"], 1)
        print(f"{label:<18} {t['identical']:>6} {t['near']:>5} {t['small']:>6} "
              f"{t.get('attempted', 0):>6} {t['todo']:>5} "
              f"{t['funcs']:>6} {t['unwritten']:>5} {t['unplaced']:>5} "
              f"{t['bytes_identical']:>10} "
              f"{t['bytes_total']:>10}  {pct:>4.1f}%")
    r = targets.get(GAME_RES[0])
    if r:
        pct = 100 * r["bytes_identical"] / max(r["bytes_total"], 1)
        print(f"{GAME_RES[0]:<18} {r['identical']:>6} {r['near']:>5} "
              f"{r['small']:>6} {r.get('attempted', 0):>6} {r['todo']:>5} "
              f"{r['funcs']:>6} {r['unwritten']:>5} {r['unplaced']:>5} "
              f"{r['bytes_identical']:>10} {r['bytes_total']:>10}  {pct:>4.1f}%"
              "  (resources, not code: not in ALL)")
    print("-" * 105)
    pct = 100 * tot["bytes_identical"] / max(tot["bytes_total"], 1)
    print(f"{'ALL':<18} {tot['identical']:>6} {tot['near']:>5} "
          f"{tot['small']:>6} {tot.get('attempted', 0):>6} {tot['todo']:>5} "
          f"{tot['funcs']:>6} "
          f"{tot['unwritten']:>5} {tot['unplaced']:>5} "
          f"{tot['bytes_identical']:>10} {tot['bytes_total']:>10}  {pct:>4.1f}%")
    if not libdir:
        print("(the lithshared libraries are not included: NOLF2_SOURCE is not set)")
    print(f"wrote {OUT}/functions.csv, {OUT}/summary.json")


if __name__ == "__main__":
    main()
