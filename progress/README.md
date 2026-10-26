# progress/ -- how much of the build is byte-identical to the retail game

The goal of the legacy build is to compile to exactly the machine code of
the retail game (*No One Lives Forever 2*, version 1.3). This directory
holds the record of how far that has got, the description of what is
scored, and the evidence the scoring needs. The table in the top-level
`README.md` is generated from it.

```sh
make                       # build (the scoring reads its output)
make progress              # score it; fails on any regression
make progress-update       # record the score here and in README.md
```

## What is scored

`targets.py` lists every shipped binary, with where its own code is and
where our build of it is. `tools/progress.py` and `tools/ratchet.py` know
no binary by name; a new one (an engine binary, once its source exists) is
added there, with the evidence for its ranges.

| Binary | Compared against | Our side |
|---|---|---|
| `CShell.dll`, `Object.lto`, `ClientFx.fxd`, `NOLF2.exe`, `NOLF2Srv.exe`, `ServerDir.dll`, `snddrv.dll` | the retail 1.3 binaries, extracted from the installed game into `out/reference/` (`build/reference.sh`) | the image `make` built (`src/Game/built/Final/...`) and every object and library of ours its link read, from the link's response file beside it (`<image>.rsp`) |
| `Lithtech.exe`, `server.dll` | the same | the images built from the engine's source (`src/Engine/`, a reconstruction: `docs/engine/PLAN.md`), scored as the game's are |
| `CRes.dll`, `SRes.dll`, `ltmsg.dll` | the same | resource by resource: their only code is the C runtime's DLL entry and an empty `DllMain`. Listed after the code, not in the total. The 1.3 `SRes.dll` has no resources at all |
| `<image>:rsrc` (`Lithtech.exe`, `server.dll`, `NOLF2.exe`, `NOLF2Srv.exe`) | the same images' resources | the resources of our images, resource by resource: each image's resources are a target of their own beside its code (version blocks, dialogs, string tables, icons, bitmaps), listed after the code and not in the total, which counts code only. `identical.txt` lists them as `<image>:rsrc<TAB>rsrc:<type>/<name>/<language>`. `ServerDir.dll` and `snddrv.dll` have no resources |

The retail images have no symbols, so their functions are enumerated from
the code itself (call targets, vtables, callbacks, exports, ...), and each
of our compiled functions is searched for in the image. A function is
**identical** when our bytes equal the retail bytes everywhere except where
the linker writes an address (relocations, which an unlinked object leaves
blank). A function that is almost all relocations (fewer than 8 other
bytes) cannot be found that way, so it is placed by shape and then checked
in the two LINKED images, where the relocations are resolved: the
identical functions' relocated operands (the dword our link wrote against
the shipped one at the same offset, or the targets a rel32 reaches), their
own addresses, the slots of the vtables they install and the import slots
(by name) give a mapping of our addresses to the shipped ones, from which
anything self-contradicting (one of ours seen with two shipped addresses,
or the reverse) is dropped. A short function whose other bytes match and
whose every relocated operand maps to the shipped operand at the same
offset is **identical**; its own address then joins the mapping, and the
check repeats until nothing new is proven. It is tried at the address its
own maps to, where the shape put it, and, when every operand maps, at any
shipped function of its length (a recurring shape was given an arbitrary
one of its copies). One that is left `small` with an operand that maps
somewhere else is moved to a copy of its shape where nothing disagrees;
where none exists it is *refuted* -- a real difference, such as
initializing the wrong global -- and `tools/progress.py --refuted` lists
those. Libraries of ours (ButeMgr, StdLith, LTGuiMgr, ...) are built from
source and scored inside the binaries that link them; NOLF2's source
release ships no prebuilt library to compare them with on their own.

Each retail function gets one status (`out/progress/functions.csv`):

| Status | Meaning |
|---|---|
| `identical` | our code is the retail code, relocations aside |
| `near` | we have the function, but the bytes differ |
| `small` | we have it, but it is almost all relocations (global initializers, thunks, one-line wrappers), and not everything those relocations name is known yet (below): reconstructed, not verified |
| `attempted` | no match, but the address is cited in `src/` or recorded in the CSVs here |
| `todo` | nothing of ours corresponds to it yet |
| `crt` | outside the binary's own code (`app` in `targets.py`): the C runtime's static parts, import thunks, the `.text$x` exception funclets, the launcher's incremental-link thunk table: listed, not counted |
| `middleware` | third-party code linked among the binary's own: listed, not counted (below) |
| `encrypted` | code `Lithtech.exe` keeps encrypted on disc: listed, not counted (below) |

Three more statuses are for functions of OURS, not shipped ones, so none of
them is counted in the denominator:

| Status | Meaning |
|---|---|
| `unplaced` | written, and our own link puts it in our image, but no shipped function is placed for it |
| `unlinked` | compiled, but our own link leaves it out too: a library member this binary does not pull |
| `driver` | emitted only by a scoring driver that ships nowhere (none here) |

The README's bars are identical bytes over all counted bytes, and the total
is the whole game's code, the engine's included.

### What is not counted

* **The C runtime.** Every binary but `ClientFx.fxd` and the resource DLLs
  links it as `MSVCRT.dll`, so what is linked in is small: `msvcrt.lib`'s
  startup and helper objects and the import thunks, after the binary's own
  code. `targets.py` gives each binary's boundary and how it was found (our
  `.map` names the library of each of our functions; `tools/libscan.py`
  places a library's functions in a retail image). Code of the binary's own
  that the linker put after the runtime (`GameAlloc.obj` and StdLith's
  `struct_bank.obj` in `CShell.dll`) is a second `app` range.
* **Third-party libraries** (`middleware`), as nolfsrc leaves out the
  GameSpy SDK in NOLF's game DLLs:
  * `Lithtech.exe`'s **D3DX**, statically linked from the DirectX 8.1
    SDK's `d3dx8.lib` (Microsoft's, `COMPILERS.md`);
  * `ServerDir.dll`'s **WONAPI**, the WON/Titan client library, with
    GameSpy's query reporting inside it. We build it from the LithTech
    Jupiter SDK's source, but it is not the game's code: its objects are
    left out of our side (`third_party`), so they neither match nor count
    as unplaced. `ServerDir.dll`'s score is `CServerDir_Titan.cpp`'s and
    `TitanTest.cpp`'s.
  STLport and MS STL templates instantiated in the game's own objects are
  compiled from headers here, like any inline function, and are counted.
* **SecuROM.** `Lithtech.exe`'s code at 0x565000..0x56a000 (five pages) is
  encrypted on disc. Nothing there can be compared, so it is `encrypted`.
  The protection is not removed or bypassed.

## Coverage: unwritten and unplaced

Next to identity, the scoreboard measures coverage, and the README shows it
per binary:

* **Unwritten**: shipped functions with nothing of ours placed at them
  (`todo` + `attempted`).
* **Unplaced**: functions of ours in our own image that no shipped function
  is placed for.

Both at zero means the build is complete: every shipped function has a
written, placed counterpart, near or identical, and nothing of ours is left
over. Identity is then a matter of converging the near ones.

A function is placed first by its bytes (identical, or `small` by shape and
then identical where its relocations are verified, above), then by similarity (`near`: same length within 15% and most unmasked bytes
agreeing). What both miss -- a function written right but compiled with
other registers, another block order, a different member offset -- would
otherwise be counted twice, once as an unwritten shipped function and once
as an unplaced one of ours. So the scorer also joins the two sides, and a
function joined this way is `near`:

0. **By reference**: an identical function's relocated operands name the
   same things in both images (our link's dword against the shipped dword
   at the same offset), so a function it calls is placed at the shipped
   callee, and a vtable it installs is paired with the shipped one and
   then slot for slot (a table nothing identical installs is found by the
   slots already placed identical). Self-contradicting evidence is dropped.
1. **By name**: a function named for the shipped address it reconstructs
   (`sub_<addr>`) is placed there, however differently it compiled.
2. **By object**: the linker lays an object's functions out together, so a
   shipped function nothing is placed at, whose nearest placed neighbours are
   object X's, is one of X's; X's unplaced functions are first aligned with
   those in order between X's own placed functions, and what is left is
   matched by size, closest first (within a factor of two).
3. **By link order**: what is left, between two neighbouring functions placed
   in both images (our `.map` gives our addresses), is aligned in order by
   size.

An inline function from a header is compiled into every object that
includes it; the linker keeps one copy, so placing one places them all.
Functions too short to tell apart (`mov eax,8 / ret`, a one-`jmp`
initializer thunk) are counted by shape: of each exact shape, ours are
unplaced only by as many as our image has more of than the shipped one. A
start the enumeration missed (a function reached only through a thunk,
which the launcher's incremental link puts in front of every call) is found
where one of our functions matches inside another row, and the row ends
there.

`make progress` fails if either count goes up; `make progress COVERED=1`
fails unless both are zero everywhere. `tools/progress.py --unplaced=<target>`
and `--todo=<target>` (and `--attempted`, `--near`, `--small`) list them,
`--nears` lists the near matches closest first, and `--refuted[=<target>]`
the small functions a verified relocation contradicts.

This is the per-function measure. A whole binary is byte-perfect only once
every function is identical *and* it links in the same order, with the same
data and headers; `tools/bindiff.py` makes that whole-file comparison.

## The test

Only the release (legacy) build is scored. The debug and modern builds are
built elsewhere (`build/variant.sh`), and the scoring never reads them.

`progress/identical.txt` lists every function verified identical, and
`progress/summary.json` the figures they add up to. `make progress`
(`build/progress.sh check`) re-scores the current build and fails if:

* a function listed in `identical.txt` is no longer identical,
* a target's identical byte count went down,
* its unwritten or unplaced count went up, or
* `README.md`'s table is not the one `summary.json` renders.

Newly identical functions pass, with a reminder to record them:
`make progress-update` rewrites `identical.txt`, `summary.json` and the
README table, so the improvement is locked in from then on. It refuses a
run that lost a recorded function unless `ACCEPT_LOSSES=1` is given (when a
change rightly gives one up -- say, a function was matched by coincidence).

`make progress COMPLETE=1` also fails unless every function of every target
is identical: the finish line.

The scoring compiles nothing; it reads what the last `make` left in the
tree. Run `make` after changing the source, then `make progress`. It needs
Python 3 only, so inside `make shell` (or on a host with Python)
`build/progress.sh check` works directly. A full run takes about three
minutes.

## Files

| File | What |
|---|---|
| `targets.py` | the binaries scored: for each, its retail image, our build, its own code (`app`), and what is left out (`middleware`, `encrypted`), with the evidence |
| `identical.txt` | every function verified identical (`target<TAB>function`): the baseline the test holds the build to. Written by `make progress-update` |
| `summary.json` | per-target counts and bytes of the recorded run; the README table is rendered from it |
| `COMPILERS.md` | which compiler and flags built each retail binary, and the evidence |
| `<stem>-screen-exclude.csv` | (`Lithtech-screen-exclude.csv`: stray pointers that split a function's extent) per image, enumerated addresses examined by hand. A reason that starts `NOT A FUNCTION` or `NOT GAME CODE` removes the row from the count; any other reason marks the address `attempted` in an image whose addresses `src/` cites |
| `extent-splits.csv` | function starts the enumeration misses, with the evidence (`snddrv.dll`'s small destructors, which only exception funclets reach) |

The CSVs change what is counted, so a change to them is a change to the
denominator: give the evidence in the reason.

The per-image function and vtable tables (`out/reference/<stem>-functions.csv`,
`-vtables.csv`) are not kept here: `build/reference.sh` derives them from
the retail images.

Per run, in `out/progress/`: `functions.csv` (every retail function and its
status) and `summary.json`.
