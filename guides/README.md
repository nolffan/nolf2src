# Reconstruction guides

How to take one function from a retail NOLF2 binary and write C++ that the
original toolchain compiles to **byte-identical machine code**.

These guides come from nolfsrc, where they were written while rebuilding
NOLF1's engine (`lithtech.exe`, `server.dll`, `d3d.ren`). The method carries
over unchanged; the binaries, compilers and paths do not, and the text here
has been adapted to NOLF2. Where a lesson was learned on a NOLF1 function and
nothing in NOLF2 has replaced it yet, the example is kept and labelled **from
NOLF1's engine**: its addresses, function names and file names are NOLF1's
(`src/engine/server/...`, `0x1003...` in NOLF1's `server.dll`) and do not
exist in this tree. Read them for the codegen, never for the address.

For NOLF2, the engine aim comes first: `docs/engine/PLAN.md` says **a game
that runs** (a `Lithtech.exe` without SecuROM, built here) is the first aim
and byte identity the second. These guides are about the second; they are
also the fastest way to get code that is right, because a function the
oracle calls identical needs no other test.

How far the work has got is the table in the top-level
[README](../README.md); `make progress` re-measures it (see
[`progress/README.md`](../progress/README.md)).

## The loop

Every function follows the same cycle:

```
   pick a target ─▶ disassemble it ─▶ read the codegen back into C++
        ▲                                        │
        │                                        ▼
   verify (diff) ◀── compile it ◀────────── write the source
        │
        └─▶ identical? next function.   near? adjust source, loop.
```

You are done with a function when the tools report it **identical** (machine
code equal, relocation targets masked). A **near** match --
instruction-equivalent but a few bytes off -- is acceptable only when the
remaining difference belongs to one of the
[known near classes](09-codegen-patterns.md#known-near-classes); document it
in a comment beside the function and move on. Coming back to close one later
is its own job, with its own method -- see
[10-upgrading-nears](10-upgrading-nears.md).

There is a **third standard**, for one specific kind of work: a function of
several kilobytes, where byte identity is out of reach but the decode is the
valuable part. Those are reconstructed to be *structurally* right and proved
with the call-sequence check rather than the byte oracle -- see
[11-large-functions](11-large-functions.md). It relaxes codegen exactness and
nothing else: guessing is still forbidden, and an undecoded region is still
declared rather than filled in.

Companion documents outside this directory:
[`docs/engine/`](../docs/engine/) (the plan, the anatomy of the retail
engine, the mapping onto the Jupiter tree, and what nolfsrc's process
was), [`tools/README.md`](../tools/README.md) (what each tool does),
[`progress/COMPILERS.md`](../progress/COMPILERS.md) (which compiler and flags
built each retail binary) and [`SETUP-NOTES.md`](../SETUP-NOTES.md) (the
build container and toolchains).

## The guides

1. **[02-the-loop](02-the-loop.md)** -- the verification tools (dumpfn,
   exedump, exematch, fndiff, bindiff, rsrcdiff) and how to drive the
   compile-diff cycle.
2. **[03-reading-disassembly](03-reading-disassembly.md)** -- the reference:
   how VC6 codegen idioms map back to C++ source constructs. The heart of the
   work.
3. **[05-exe-and-engine](05-exe-and-engine.md)** -- binaries with no
   symbols: `Lithtech.exe` (no relocations, SecuROM) and `server.dll`, and
   the evidence that names their functions (the Mac engine's symbols, the
   1.3 multiplayer demo, the Jupiter tree).
4. **[07-vtables](07-vtables.md)** -- naming *anonymous* functions: find the
   class's vtable in `.rdata` (`tools/vtabmap.py`), anchor it against the SDK
   header's declaration order, and read the unknown slots' names and
   signatures straight out of the header.
5. **[09-codegen-patterns](09-codegen-patterns.md)** -- the case law: every
   proven asm-to-source fingerprint, organised by what you see in the
   disassembly, plus the near classes not worth chasing. Read it before
   writing a function and again when one is stuck a few bytes off.
6. **[10-upgrading-nears](10-upgrading-nears.md)** -- taking a function that
   is *nearly* right and closing the gap.
7. **[11-large-functions](11-large-functions.md)** -- the third standard:
   reconstructing a function of several kilobytes to be *structurally* right
   and proving it with the call-sequence check (`tools/callseq.py`). Learned
   on NOLF1's Intel-compiled renderer; read its last section for what holds
   on an MSVC target, which is everything in NOLF2 (the renderer's biggest
   functions are where it will be used).
8. **[12-o2-shape](12-o2-shape.md)** -- functions already byte-identical in
   `server.dll` (`/O1`) but not in `Lithtech.exe` (`/O2`): the source is
   proven, only its `/O2` shape is wrong (`tools/o2gap.py`).
9. **[13-cluster-recon](13-cluster-recon.md)** -- the procedure for
   reconstructing a whole untouched cluster of functions from scratch.

### Not brought over from nolfsrc

The numbering is nolfsrc's, so references between guides keep working.
Missing numbers:

- **01-environment**: NOLF1's toolchain table (four cl revisions and Intel
  C/C++ 4.0) and its build scripts. NOLF2 has one compiler for all of
  Monolith's code (below); the container and toolchains are in
  `SETUP-NOTES.md`, the compile and link command lines in `build/build.mk`,
  and the one-file loop in `build/engine.sh` (with `run_cl` and the rest in
  `build/env.sh` for compiling by hand).
- **04-worked-example** (a NOLF1 lithshared library function, matched
  against the prebuilt `.lib` the NOLF1 source release shipped: NOLF2's
  release ships no prebuilt library), **06-worked-example-engine** and
  **08-worked-example-playsound** (NOLF1 engine functions, start to finish).
  They are worth reading in nolfsrc for the method, but every command in
  them names NOLF1's files. Their lessons are in 05, 07, 09 and 12 here.

## Picking a target

`tools/progress.py` scores every function of every target that
`progress/targets.py` lists and writes `out/progress/functions.csv`: one row
per retail function, with its size and status (`identical`, `near`, `small`,
`attempted`, `todo`, and the uncounted `crt`, `middleware` and `encrypted`;
see [`progress/README.md`](../progress/README.md)). Run `make progress` first,
after a `make`.

**What counts as a target.** Each image's own code is its `app` ranges in
`progress/targets.py`. What is outside them -- msvcrt.lib's static members,
import thunks, `.text$x` funclets -- is `crt`. Inside them, third-party code
is `middleware`: in `Lithtech.exe`, D3DX (`d3dx8.lib` from the DirectX 8.1
SDK, with libjpeg and zlib inside it). `Lithtech.exe`'s five SecuROM pages,
0x565000..0x56a000, are `encrypted`. None of these is counted, and none is
reconstructed.

To find work:

```sh
python3 tools/progress.py --todo=server.dll      # untouched, largest first
python3 tools/progress.py --nears=server.dll     # near matches, closest first
grep ',todo$' out/progress/functions.csv | grep '^server.dll,' | sort -t, -k3 -n | head
```

When you have moved the numbers, `make progress-update` records them (and
rewrites the README table); `make progress` fails if a function that was
recorded as identical stops matching, so run it before you hand work in.

Start small, and prefer a target that is the **first of a family**: the first
function in a cluster is expensive (you are modelling macros, object layouts
and flags), and the rest of the cluster then costs almost nothing.
`server.dll` first, as in nolfsrc: it is smaller, it has relocations, and its
source is also `Lithtech.exe`'s (`docs/engine/nolfsrc-process.md`, 4.3).

The flags decide everything before you start. All of Monolith's code in NOLF2
was compiled by **one** compiler, VC6 SP5 (`cl` build **8966**,
`toolchains/msvc-6.00-8966`); NOLF1's mixed revisions are history:

| target | compiler | optimisation |
|---|---|---|
| game DLLs, `NOLF2.exe`, `NOLF2Srv.exe`, `ServerDir.dll`, `snddrv.dll` | cl 8966 | `/O2`, as their `.dsp` files say (proven) |
| `server.dll` | cl 8966 | `/O1` or `/Os` (178 of 1,694 call targets 16-byte aligned) |
| `Lithtech.exe` | cl 8966 | `/O2` (2,877 of 3,157 call targets aligned), `/GX` |
| `d3dx8.lib` in `Lithtech.exe` | Microsoft cl 13.00.9178 and Intel C/C++ | not ours: `middleware` |

The engine's flags are the Rich header's testimony and alignment counts
until files compile and match; prove per-file exceptions as they turn up,
and record them in `progress/COMPILERS.md`.

## Never change what the retail code does

The legacy build is the retail game, bugs included: a function that behaves
differently from the retail one is wrong there even when the retail one is
the buggy one. A fix goes behind `#ifdef NOLF2SRC_MODERN`, with the retail
code kept unchanged in the `#else` (see the top-level README, "modern"), so
the release build -- the only one that is scored -- still matches.

## Ground truth is `out/reference/`

The retail binaries are extracted from the installed game into
`out/reference/` by `build/reference.sh` (`make progress` does it too),
alongside a function table per image (`<stem>-functions.csv`) and a vtable
table (`<stem>-vtables.csv`). Every check and every hand-run tool reads them
from there. Never point a tool at one of our own builds
(`src/Engine/built/...`, `out/nolf2-legacy-release/`): it will read our code
back and report a match that proves nothing.

Two stand-ins sit beside the retail images, for reading only:

- **the 1.3 multiplayer demo's engine** (`tools/demoimports.py`), built 20
  days after retail with the same Rich header, unprotected. It has the
  plaintext of the encrypted pages and the real import of each of the 1,514
  `call [IAT]` sites SecuROM redirected (`progress/engine/Lithtech-iat-calls.csv`).
  Use it for code and data, **never for addresses**: some objects are
  linked in another order.
- **the Mac NOLF2 engine** (`tools/macho.py`), a PowerPC Mach-O that kept its
  symbols: the name, class and source file of nearly every function
  (`progress/engine/mac-functions.csv`).
