# tools/

**Copied from nolfsrc, not yet adapted.** Of what is here, the build uses
`dsp2mk.py` (new: Monolith's workspace as make rules), `mkdeps.py`,
`releasesrc.py`, `retailextract.py` (rewritten for NOLF2), `rezextract.py`
and `playtest.sh`, and `build/reference.sh` uses `enumfuncs.py` and
`vtabaudit.py`. The rest -- the scoreboard (`progress.py`, `ratchet.py`) and
the reconstruction tools -- still know NOLF's binaries and paths
(`lithtech.exe`, `d3d.ren`, `src/engine/`): the text below is nolfsrc's.

Everything here serves one of two jobs: building and running the game, or
proving, function by function, that the C++ in `src/engine/` recompiles to
exactly the machine code that shipped. The tools are plain Python 3 with no
dependencies, plus a few shell scripts, two small C programs and a Ghidra
script. The ones that disassemble use `objdump` (binutils), which the build
image has.

Run them from the repository root, in the build container (`make shell`) or
on a host with Python 3 and binutils. The `build/engine.sh` loops and
`tools/agentwt.sh` worktrees need the container, because they compile.

**The ground truth is `out/reference/`.** `build/reference.sh` extracts the
retail `lithtech.exe`, `server.dll`, `d3d.ren`, `NOLF.exe` and `ltmsg.dll`
there from disc 2, together with each image's function table
(`<stem>-functions.csv`, from `enumfuncs.py`) and vtable table
(`<stem>-vtables.csv`, from `vtabaudit.py`). Every tool below that reads
"the shipped image" reads it from there. Nothing in the build reads it, and
nothing in it is ever run.

The guides in `guides/` explain the method these tools serve. Read them
first.

## The loop

Reconstructing one function of `server.dll` (see `guides/02-the-loop.md`):

```sh
build/reference.sh                       # once: the retail images and their tables

# 1. read the shipped code
tools/exedump.py out/reference/server.dll 0x10034037 0x10034120

# 2. edit the source, rebuild just that file and match it (~3 s)
build/engine.sh server-one smgr.cpp PlaySound

# 3. if it does not match: a structured diff, with hints
tools/fndiff.py 0x10034037 src/engine/server/Release/smgr.obj PlaySound \
    --image=out/reference/server.dll

# 4. when it does: make sure nothing else regressed, and record it
make progress && make progress-update NOLF2_SOURCE=<dir>
```

**`src/engine/server/*.cpp` is the client's source too.** `lithtech.exe`
compiles about 40 of those files a second time, with its own compiler
revision and flags. After changing one, rebuild both
(`build/engine.sh server-one x.cpp` and `lithtech-one x.cpp`), or the
client's objects go stale. A function that matches in `server.dll` but only
nears in `lithtech.exe` has source that is already proven right: the
difference is the compile (see `o2gap.py`), and editing the source to chase
the client will regress the server.

## Building and running the game

| Tool | Used by | What it does |
|---|---|---|
| `retailextract.py` | `build/all.sh`, `build/reference.sh` | Takes what is needed from the retail game, as `rez/` installs it (`rez/games/nolf-eu-goty/`, see `build/retail.sh`): `resources` (game data, with the retail game DLLs inside the `.rez` archives zeroed), `thirdparty` (Miles and Bink, the only binaries not built from source), `openruntime` (the modern build's replacements for them, from `build/ext.sh`), `launcherres` (the launcher's bitmap, palette, music, icon and cursors, read out of the retail `NOLF.exe`'s resources), `reference` (the retail engine images, for checking only: `out/reference/`) and `audit` (lists every PE file in the game directory with its origin, and fails on any it cannot account for). |
| `rezextract.py` | `retailextract.py` | Reader for Monolith's REZ archives. Also a CLI: `rezextract.py list <rez>`. |
| `dsp2files.py` | `build/build.mk` | Lists a VC6 `.dsp` project's source files for one configuration, so the game DLLs compile exactly the files the original project did. |
| `mkimplib.py` | `build/build.mk` | Writes a COFF import library for a few named imports (Miles' decorated names, `DirectDrawCreateEx`). |
| `mkaliasobj.py` | `build/build.mk` | Turns `src/engine/*/link/aliases.rsp` into an object of weak externals: one function or global reached under two names. |
| `mkvtabobj.py` | `build/build.mk` | Turns `src/engine/lithtech/link/vtables.txt` into an object holding full-length vtables for classes the source only partly declares. Slots between `%ifdef NOLF2SRC_MODERN` and `%endif` are added only in the modern build (`--define NOLF2SRC_MODERN`: the modern `ILTClient`'s extra slots). |
| `mkviewobj.py` | `build/build.mk` | Turns `src/engine/d3d/link/d3dviews.txt` into an object laying out `d3d.ren`'s globals as the original did. |
| `mkdeps.py` | `build/build.mk` | Header dependencies, which VC6 cannot report: follows every `#include` of a source the way MSVC resolves it (case-insensitively, `\\` as a separator) and writes the Makefile rules, caching each file's `#include` lines. |
| `buildcmp.py` | by hand | Compares two directories of build outputs byte for byte, ignoring only the time stamps VC6's tools write (and `.pdb`/`.idb`/`.pch` files): for checking that a change to how the game is built does not change what it builds. |
| `loadtest.c`, `d3dloadtest.c` | `build/engine.sh server-link test`, `d3d-link test` | Small Win32 programs run under Wine: each occupies the module's preferred base first, so the loader has to relocate it, then loads it and exercises its exports (`CreateServer` / `DeleteServer`; the display-mode list and `RenderDLLSetup`). |
| `playtest.sh` | `make test` | Runs a game directory under Xvfb in the build container, optionally driving it with an input script, and reports ALIVE / EXITED / CRASHED (plus `wine.log` and screenshots in `out/play/<name>/`). Usage in its header. |
| `playtest-basic.txt` | `make test` | The input script: skip the opening cinematic, look, move, jump, duck, fire, switch weapons, open the menu, quicksave and quickload. |
| `releasesrc.py` | `build/env.sh` (`compile.sh`, `libs.sh`, `build.sh`, `engine.sh`), `build/variant.sh` | The source the release build compiles: `sync` mirrors `src/` into `out/release-tree/src/` with every `NOLF2SRC_MODERN`/`NOLF2SRC_DEBUG` block resolved as the release build sees it (`mirror`: the same, unchanged, for a variant tree), `outputs` copies build outputs between the trees, `strip <file>` prints one file as the release build compiles it, and `diff [rev]` lists the release-visible changes to `src/` since `rev` (lines added outside a block). See BUILDING.md, "The modern build". |
| `mapaddr.py` | by hand | Names the function an address falls in, from a linker `.map`: for the frames of the debug build's crash log that no `.pdb` names (`tools/mapaddr.py out/nolf2-legacy-debug/d3d.map 0x10036d1c`). See BUILDING.md, "The debug build". |
| `agentwt.sh` | by hand | Creates a git worktree under `.worktrees/<name>` that can build and verify on its own (the compilers, `out/reference/` and the installed retail game linked in), so several people or agents can work in parallel without one's half-finished edit changing what another measures. Each worktree is a branch, `wt/<name>`: commit verified work there and merge it from the main checkout (`rm` keeps the branch). `agentwt.sh add <name>`, `rm <name>`, `list`. |

## Scoring

| Tool | What it does |
|---|---|
| `progress.py` | The scoreboard: enumerates every function of the retail images and libraries and classifies each against our build (`identical`, `near`, `small`, `attempted`, `todo`), writing `out/progress/functions.csv` and `summary.json`. `--nears[=<target>]` lists the near matches closest first (the order to work them in); `--todo`, `--attempted`, `--small` list those rows. See `progress/README.md`. |
| `ratchet.py` | Holds a scoring run to the baseline in `progress/`: `check` fails if a recorded identical function stopped matching, `update` records the run and rewrites `README.md`'s table, `readme` rewrites only the table. `make progress` runs both tools. |
| `decoded.py` | Bytes under *structural* reconstruction in `d3d.ren` (and big functions elsewhere): a file named `big<addr>.cpp` holding a function that has the shipped control flow and calls but is not yet byte-exact, scored by how many of its calls agree with the shipped ones (`callseq.py`). Never added to `progress.py`'s figure: understood is not reproduced. Reads `progress/decoded-extents.csv` and `decoded-moved.csv`; writes `out/progress/decoded.csv`. |
| `decodedlt.py` | The same for `lithtech.exe`, whose reconstructions are ordinary named functions: the address of each comes from `progress/lithtech-decoded-map.csv`. |

## Reading the retail code

The engine binaries shipped with no symbols, no RTTI and no debug
information. These turn raw bytes into something source can be read back
out of.

| Tool | What it does |
|---|---|
| `exedump.py` | Annotated disassembly of a range of a retail image: imports resolved, string operands printed inline, data references tagged with their section. `exedump.py <image> [start [end]]`. The primary way to read a shipped function. |
| `dumpfn.py` | The other side: disassembles one function of one of our objects, from its own COMDAT section, with relocation targets annotated. `dumpfn.py <obj> <symbol-substring> [--all]`. |
| `enumfuncs.py` | Enumerates the functions of a symbol-less image from several independent sources (call targets, data pointers such as vtables, `push imm32` callbacks, initializer pairs, exports, code after a `ret`), with sizes and a coverage figure. `--csv` writes the function table `build/reference.sh` keeps in `out/reference/`; its name column comes from exports and from the `Class::Method` error-tag literals the engine's argument checks push. |
| `tagmap.py` | Names functions from those error-tag literals (`RETURN_ERROR(1, "ILTPhysics::SetVelocity", ...)`): the function that pushes a tag is the method it names. `--undone` restricts it to rows the scoreboard still has as `todo`. |
| `dataref.py` | Reads initialised data at an address, following pointers to strings: half the error checks push a `static char*` rather than a literal, and one dereference recovers the name. |
| `vtabmap.py` | Finds runs of pointers into `.text` (vtables) and prints each slot, labelled from a function table, so an unknown slot between two known ones can be read off the SDK header's declaration order. |
| `vtabaudit.py` | Vtables from evidence, one table per row, where `vtabmap.py` sees only runs (adjacent tables run together): table starts are the addresses constructors store, and each slot records how many argument bytes its `ret` pops. |
| `sdkvtab.py` | The virtual-function order of an LT2 SDK interface, read off its header in `src/LT2/sdk/inc`: the name list for a vtable's slots. |
| `msvcdemangle.py` | A conservative MSVC (VC6) demangler: it covers what this codebase contains and refuses everything else rather than guessing. |
| `richhdr.py` | Decodes the "Rich" header: which compiler and linker builds produced an image, with object counts. The source of the per-binary compiler revisions (8168, 8447, ...) the build pins. |
| `compid.py` | The compiler build number of each object in a COFF object or `.lib` (`@comp.id`): direct evidence of which compiler built a static library. |
| `asmweb.py` | Renders a retail image's whole app region as one scrollable web page (`out/asmweb.html`): every instruction, every recovered function labelled with its demangled signature, its status and its source file, and calls annotated with their target's name. `--stats` prints counts only. |
| `ghidra/decomp.sh` | Batch-decompiles an image's app region to one `.c` file with headless Ghidra (`DumpDecomp.java`). A reading aid for control flow and field offsets, never source: Ghidra normalises away exactly what byte-matching depends on. Optionally seeded with a function table. Needs `ghidra.analyzeHeadless` and about 2 GB of RAM. |
| `pef.py` | Reads the Mac release's engine (`rez/games/nolf-mac-usa/NOLF/LithTech`, a PowerPC PEF built with CodeWarrior), where every function keeps its name in its traceback table. `info`, `funcs [regex]` (every named function, with its extent), `imports [regex]` (with their library: `OpenGLLibrary`, `CarbonLib`, ...), `dis <name\|0xaddr>` (annotated disassembly: TOC loads named as the function, import, string or float constant they reach, calls named, glue stubs followed) and `refs <name>` (who takes its address or calls it). `-` for the file means the Mac engine. The reference for the modern build's renderer (`src/modern/render/`). `dis` and `refs` need capstone on `PYTHONPATH` (see the header). |

## Comparing ours with theirs

All of these mask the bytes relocations cover (4 per fixup) before
comparing, because an unlinked object has zeros where the linker later
writes addresses: a masked match means identical up to addresses.

| Tool | What it does |
|---|---|
| `exematch.py` | Searches an image's `.text` for each function of our objects. `MATCH 0x<addr>` per function placed; functions with fewer than 8 unmasked bytes are too small to anchor. What `build/engine.sh <target> verify` and the `*-one` loops run. Its totals are not authoritative (functions with identical code each count a match at the same address); `progress.py`'s are. |
| `objdiff.py` | Compares two COFF objects or `.lib`s symbol by symbol: the strictest check, for the lithshared libraries, which shipped with their symbols. |
| `bindiff.py` | Compares two whole linked PE images with absolute and relative addresses masked, matching functions across them whatever the link order (`ltmsg verify`). |
| `rsrcdiff.py` | Compares two images' resources payload by payload, ignoring the layout of the resource section. |
| `callcheck.py` | Checks that our calls go where the shipped calls go. A masked comparison sees a `call` as one opcode and four holes, so a function calling the wrong callee still "matches"; this resolves both sides' targets. |
| `fpconst.py` | Checks the floating-point constants a function loads through relocations, which masking cannot see (`+= 0.001f` and `+= 1.0f` mask to the same bytes). |
| `linkresolve.py` | After a whole-image link, maps each unresolved symbol onto the definition it really means (the same shipped address under another spelling) and writes the alias lines for `link/aliases.rsp`. |
| `vtabcheck.py` | Compares our linked image's vtables with the shipped ones slot by slot: a constructor can match while the table it installs is a short stand-in, which only a run (or this) notices. |

## Diagnosing a function that does not match

| Tool | What it does |
|---|---|
| `fndiff.py` | The main diff. Byte identity (masked) if the sizes agree; otherwise the mnemonic diff, the best renaming of our callee-saved registers (a diff that vanishes under renaming is register-allocation lottery, not structure), and hints: the residual matched against the codegen fingerprints `guides/09-codegen-patterns.md` catalogues, each naming the source construct that has fixed it before. `fndiff.py <ship-addr> <obj> <symbol> [--image=...] [--end=0xADDR] [--csv=...]` (the `=` is required); the shipped size comes from `out/reference/<stem>-functions.csv`. |
| `libfndiff.py` | `fndiff.py` for a library function, matched by symbol against the shipped `.lib` (from `NOLF2_SOURCE`). `--list <lib>` lists that library's nears. |
| `nearpos.py` | Slides each unmatched function of an object over `.text` and reports where the fewest unmasked bytes differ, naming them. Reach for it first: a function whose source is right and whose class layout is wrong lands at its true address with a few displacement bytes off, all by the same amount, and one field fixes every function of that class. |
| `layoutscan.py` | Finds nears whose every difference is a field displacement shifted by one constant: a struct layout error, fixed by one line, rather than codegen. |
| `nearscan.py` | Runs `fndiff`/`libfndiff` over a whole near list and classifies each (count-exact, register lottery, FPU split, ...), to separate the nears worth a source experiment from the register allocator's. |
| `o2gap.py` | Functions identical in `server.dll` (/O1) but not in `lithtech.exe` (/O2): their source is already proven, so what is missing is the shape /O2 sees, which is cheaper to fix than reconstructing from bytes. |
| `callseq.py` | Does our function call what the shipped one calls, in order? For big functions that are structurally right but not yet exact, where `callcheck.py` cannot place them. `--count` gives a shipped range's call count and bytes per call. |
| `census.py` | Compares the instruction census (count per mnemonic) of a shipped function and ours: the measure for call-free code, and for big functions alongside `callseq.py`. |
| `extentcheck.py` | Tests whether an enumerated row is really one function before you decode it: rets, prologues, references from outside, padding, a row ending mid-instruction. |
| `enumcheck.py` | Validates a whole function table against a real disassembly: starts that are not instruction boundaries, rows that hide a second function. |
| `dupes.py` | Finds shipped addresses more than one of our symbols reconstructs: the same function written twice, under two names. |

## Picking work

| Tool | What it does |
|---|---|
| `uncovered.py` | The shipped functions nothing of ours accounts for, counting every address a function of ours matches (where the scoreboard credits each once). It reports what it excludes, and why, each as its own count: not functions (`progress/*-enum-suspect.csv`), unverifiable (a same-length function of ours below the 8-byte floor), excluded by hand (`progress/*-screen-exclude.csv`), bridged (named by inference in a decoded map), near, inside a function already matched, written up under an address comment, matched by name. Only the last count, UNTOUCHED, is new work. |
| `callseam.py` | Ranks unreconstructed functions by how many byte-identical functions call them: a call site we understand gives the callee's arguments, convention and usually its types. |

## d3d.ren

`d3d.ren` was built by the Intel C/C++ compiler 4.0 with per-file flag
groups (see `build/engine.sh`), and its file boundaries in `src/engine/d3d/`
are ours, so these exist for it alone.

| Tool | What it does |
|---|---|
| `d3dcheck.py` | Checks each `src/engine/d3d` function at the address its name gives (`sub_<addr>`, or a table of named functions), with icl's padding stripped: most of what reproduces in `d3d.ren` is too short for `exematch.py` to place by search. `--obj=<stem>` for one file. |
| `d3dwork.py` | Ranks `d3d.ren`'s remaining functions by what they are worth doing next. |
| `d3dflags.sh` | Measures every `src/engine/d3d` file at /O2 and at /Os and prints the /Os list for `build/engine.sh`. Recompiles everything: rebuild `d3d` afterwards. |
| `d3dsplit.py` | Splits a file in two so that some of its functions can be built with another flag group. |
| `d3ddata.py` | Generates `src/engine/d3d/d3ddata.cpp` (one definition per `d3d.ren` global, with its shipped initial bytes), `link/d3dviews.txt` and the alias block of `link/aliases.rsp`, from the retail image and the d3d objects. `--write` after a d3d build; `--probe` (in the container) measures the struct sizes into `link/d3dsizes.txt`. |
