# tools/

Everything here serves one of two jobs: building and running the game, or
proving, function by function, that the C++ in `src/` recompiles to exactly
the machine code that shipped. The tools are plain Python 3 with no
dependencies, plus a few shell scripts, a small C program and a Ghidra
script. The ones that disassemble use `objdump` (binutils), which the build
image has.

Most came from nolfsrc (NOLF1's reconstruction), where they were written
against NOLF1's binaries. Here they **know no binary by name**: the
binaries, their regions (`app`, `middleware` for D3DX and WONAPI,
`encrypted` for SecuROM's pages), our build of each, and where that build's
objects are come from `progress/targets.py`, which `progress.py` scores
from. A tool that takes a *target* accepts its label or stem in any case
(`Lithtech`, `server.dll`, `snddrv`) or the path of its image, and
`tgt.py` resolves it. Our side of a target is the image `make` built and
every object and library its link's response file (`<image>.rsp`) names,
so a tool needs no object directory: it reads the link. The few listed
under "Not adapted" at the end are NOLF1's, kept for reference.

Run them from the repository root (most also work from anywhere), in the
build container (`make shell`) or on a host with Python 3 and binutils.
`build/engine.sh` and the `run_*` helpers need the container, because they
compile.

**The ground truth is `out/reference/`.** `build/reference.sh` extracts the
retail 1.3 binaries there from the installed game (`rez/games/nolf2-eu-1.3`),
with each image's function table (`<stem>-functions.csv`, from
`enumfuncs.py`) and, for the engine, its vtable table (`<stem>-vtables.csv`,
from `vtabaudit.py`). Every tool below that reads "the shipped image" reads it
from there. Nothing in the build reads it, and nothing in it is ever run.

The guides in `guides/` explain the method these tools serve, and
`docs/engine/` the engine binaries in particular. Read them first.

## The loop

Reconstructing one function of `server.dll` (see `guides/02-the-loop.md`):

```sh
build/reference.sh                       # once: the retail images and their tables

# 1. read the shipped code (and the Mac engine's name for it)
tools/exedump.py out/reference/server.dll 0x1002b705 0x1002b7a8
grep -i createserver progress/engine/mac-server-functions.csv

# 2. edit the source, rebuild just that file and match it
build/engine.sh server-one server_interface.cpp CreateServer

# 3. if it does not match: a structured diff, with hints
tools/fndiff.py 0x1002b705 src/Engine/built/Final/server/server_interface.obj CreateServer

# 4. when it does: make sure nothing else regressed, and record it
make progress && make progress-update
```

`build/engine.sh` needs the engine's projects in `build/build.mk` (the
skeleton package of `docs/engine/PLAN.md`); until then it says so. It
works the same for any project already there (`build/engine.sh snddrv
verify`, `snddrv-one s_dx8.cpp`).

**Most of the engine's source is compiled twice.** `server.dll` (/O1) is
the server, shared, kernel, net and world objects of `Lithtech.exe` (/O2)
compiled again without the client, renderer and UI
(`docs/engine/anatomy.md`, section 4). After changing such a file, rebuild
both objects (`server-one x.cpp` and `Lithtech-one x.cpp`). A function that
matches in `server.dll` but only nears in `Lithtech.exe` has source that is
already proven right: the difference is the compile (see `o2gap.py` and
`guides/12-o2-shape.md`), and editing the source to chase the exe will
regress the dll.

**`Lithtech.exe` is SecuROM-wrapped.** Its `.text` 0x565000..0x56a000 is
encrypted on disc, and all 1,514 of its `call dword ptr [IAT]` sites read
`call [0x607ec0]`, SecuROM's dispatcher. `demoimports.py` maps each site to
the import it really calls, from the unprotected engine of the 1.3
multiplayer demo, and writes a readable copy of the image for the
disassembling tools. The demo is evidence for code and data only, never for
addresses (`guides/05-exe-and-engine.md`).

## Per-target facts

| Tool | What it does |
|---|---|
| `tgt.py` | What the other tools ask instead of naming a binary: `find(name)` (label, stem or image path, any case), `app_span`, `region`/`in_app` (the scoreboard's), `built`, `objs` (our link's `.obj`/`.lib` inputs, from the `.rsp`), `objdirs`, `ourmap`, `obj_path` (the file behind a scoreboard module key, a library member unpacked), `funcs_csv`, `vtabs_csv`, `cited_src`. `tgt.py` alone lists every target and what it resolves to. |

## The engine's evidence

| Tool | What it does |
|---|---|
| `macho.py` | Reader for the Mac NOLF2 engine (`NOLF2.app/Contents/MacOS/NOLF2`, Mach-O PowerPC, not stripped) and the Mac dedicated server's `server.dll` bundle: `info`, `syms`, `funcs [regex]` (extents, demangled), `paths` (Monolith's source paths in the strings and the functions that use them), `refs <addr>`, `demangle`. Its Itanium demangler prints every name in both binaries as `c++filt` does. The counterpart of nolfsrc's `pef.py`. The release is not installed by default: `rez/fetch-isos.sh nolf2-mac-usa && rez/install-games.sh nolf2-mac-usa` (or `--root`/`$NOLF2_MAC`). |
| `macinventory.py` | The inventory built on `macho.py`: every Mac engine and server function with its demangled name, size and the Jupiter source file it belongs to, with its category (engine, omni, stl, runtime, unknown) and the evidence (`defn`: the file that defines the name, `path`, `neighbour`), written to `progress/engine/mac-functions.csv`, `mac-server-functions.csv` and the per-file and per-module summary `mac-modules.md`. `macinventory.py --jupiter ../fear/Dev/Source` regenerates them byte for byte. |
| `demoimports.py` | The 1.3 multiplayer demo's unprotected `Lithtech.exe` as the key to retail's SecuROM changes: `extract` unpacks the demo's engine from `rez/artifacts/demos/`, `map` writes `progress/engine/Lithtech-iat-calls.csv` (each redirected `call [IAT]` site of retail and the import it calls), `plain` writes `out/mpdemo/Lithtech-readable.exe`, retail with the encrypted pages filled from the demo and the redirected calls restored, for reading only (data addresses inside the filled pages stay the demo's). Only the map is committed; the demo's code never is. |

## Building and running the game

| Tool | Used by | What it does |
|---|---|---|
| `retailextract.py` | `build/all.sh`, `build/reference.sh` | Takes what is needed from the retail game, as `rez/` installs it (`rez/games/nolf2-eu-1.3/`, see `build/retail.sh`): game data, the third-party binaries, the retail engine images for checking only (`out/reference/`), and an audit of every PE file in the game directory. |
| `rezextract.py` | `retailextract.py` | Reader for Monolith's REZ archives. Also a CLI: `rezextract.py list <rez>`. |
| `dsp2mk.py` | `build/build.mk` | Monolith's Visual C++ 6 workspace as make rules: every project of a `.dsw` and its dependencies, every compile with its configuration's flags (per-file `ADD CPP`/`SUBTRACT CPP`, `/Yc`/`/Yu`), every library and link (`P_<project>_OUT`, `P_<project>_OBJS`), the custom build steps. `CL_<project>` overrides the compiler. |
| `dsp2files.py` | by hand | Lists a VC6 `.dsp` project's source files for one configuration. |
| `jupitersrc.py` | `build/all.sh`, `build/jupiter.sh` | Copies the LithTech Jupiter SDK's source (WONAPI, CServerDir_Titan) from `rez/sdk/` into `src/Game/Libs/`. |
| `mkdeps.py` | `build/build.mk` | Header dependencies, which VC6 cannot report: follows every `#include` the way MSVC resolves it and writes the Makefile rules. |
| `mkimplib.py` | by hand | Writes a COFF import library for a few named imports. |
| `mkaliasobj.py`, `mkvtabobj.py`, `mkviewobj.py` | by hand | nolfsrc's link stand-ins: an object of weak externals (one function reached under two names), full-length vtables for classes the source only partly declares, a laid-out view of a binary's globals. Fallbacks only: with the Jupiter tree's real class declarations they should be unnecessary. Their docstrings' paths are NOLF1's examples. |
| `buildcmp.py` | by hand | Compares two directories of build outputs byte for byte, ignoring the time stamps VC6's tools write. |
| `loadtest.c` | `build/engine.sh server test` | A Win32 program run under Wine: occupies `server.dll`'s preferred base so the loader relocates it, loads it, and calls `CreateServer` / `DeleteServer`. |
| `srvtest.sh` | by hand | The dedicated server's runtime test: NOLF2Srv.exe of a game directory, with a given `server.dll` (default ours; `out/reference/server.dll` is the control), hosts the first co-op level under Xvfb in the build container; ALIVE / EXITED, message boxes reported. `srvtest.sh [server.dll] [seconds] [gamedir]`. |
| `playtest.sh`, `playtest-basic.txt` | `make test` | Runs a game directory under Xvfb in the build container, optionally driving it with an input script; reports ALIVE / EXITED / CRASHED. |
| `releasesrc.py` | `build/env.sh`, `build/variant.sh` | The source the release build compiles: `src/` with every `NOLF2SRC_MODERN`/`NOLF2SRC_DEBUG` block resolved (`sync`, `outputs`, `strip`, `diff`). |
| `mapaddr.py` | by hand | Names the function an address falls in, from a linker `.map`. |
| `agentwt.sh` | by hand | A git worktree under `.worktrees/<name>` on branch `<name>` that can build and verify on its own: `toolchains/`, `rez/` and `out/reference/` hard-linked in (a symbolic link would not resolve in the container, which mounts the worktree alone). `add <name> [start]`, `rm <name>`, `list`. |

`build/env.sh` also gives the tools by hand, for experiments and the
one-object loop: `run_cl` (cl 8966, or `CL_REV=<build>`), `run_link`,
`run_lib`, `run_rc`, in build.mk's environment (S: and T: drives, the DX 8.1
SDK first), with their own Wine prefix (`out/tools-wine`).

## Scoring

| Tool | What it does |
|---|---|
| `progress.py` | The scoreboard: enumerates every function of each retail binary `progress/targets.py` lists and classifies each against our build (`identical`, `near`, `small`, `attempted`, `todo`; `crt`, `middleware` and `encrypted` are listed, not counted). `--nears[=<target>]`, `--todo`, `--attempted`, `--small`, `--unplaced` list rows. See `progress/README.md`. |
| `ratchet.py` | Holds a scoring run to the baseline in `progress/`: `check`, `update`, `readme`. `make progress` runs both tools. |
| `libscan.py` | Where each library's code sits in a retail image: every function of the given `.lib`s found at exactly one address, grouped into runs. How `targets.py`'s boundaries (the C runtime, D3DX, WONAPI) were found. |
| `decoded.py` | Bytes under *structural* reconstruction: an object `big<addr>.obj` among a target's link inputs holding a function with the shipped control flow and calls but not yet byte-exact, scored by `callseq.py`. Never added to `progress.py`'s figure. |
| `decodedlt.py` | The same for a target whose reconstructions are ordinary named functions, placed by `progress/<stem>-decoded-map.csv`. `decodedlt.py <target>`. |

## Reading the retail code

| Tool | What it does |
|---|---|
| `exedump.py` | Annotated disassembly of a range of a retail image: imports resolved, string operands inline, data references tagged with their section. For `Lithtech.exe`, read `demoimports.py plain`'s copy, whose import calls are restored. |
| `dumpfn.py` | Disassembles one function of one of our objects, relocation targets annotated. |
| `enumfuncs.py` | Enumerates the functions of a symbol-less image (call targets, data pointers, callbacks, initializer pairs, exports, code after a `ret`), with sizes and a coverage figure; `--csv` writes the function table. Rows in `Lithtech.exe`'s encrypted pages are noise (the scoreboard marks them `encrypted`). |
| `tagmap.py` | Names functions from the engine's error-tag literals (`RETURN_ERROR(1, "ILTPhysics::SetVelocity", ...)`). `tagmap.py <target> [--undone]`. |
| `dataref.py` | Reads initialised data at an address, following pointers to strings. |
| `vtabmap.py` | Finds runs of pointers into `.text` (vtables) and prints each slot, labelled from a function table. |
| `vtabaudit.py` | Vtables from evidence, one table per row: table starts are the addresses constructors store; each slot records how many argument bytes its `ret` pops. |
| `sdkvtab.py` | The virtual-function order of an SDK interface, read off its header in `src/Engine/sdk/inc` (`--inc=` for another tree, such as the Jupiter one). |
| `msvcdemangle.py` | A conservative MSVC (VC6) demangler. |
| `richhdr.py` | Decodes the "Rich" header: which compiler and linker builds produced an image. The source of `progress/COMPILERS.md`. |
| `compid.py` | The compiler build of each object in a COFF object or `.lib` (`@comp.id`). |
| `asmweb.py` | Renders a target's whole `app` region as one scrollable web page (`out/asmweb-<stem>.html`): every instruction, every function with its status and, where ours, its signature and object. `asmweb.py <target> [--stats]`. |
| `ghidra/decomp.sh` | Batch-decompiles an image's app region with headless Ghidra. A reading aid, never source. |

## Comparing ours with theirs

All of these mask the bytes relocations cover before comparing: a masked
match means identical up to addresses.

| Tool | What it does |
|---|---|
| `exematch.py` | Searches an image's `.text` for each function of our objects; `MATCH 0x<addr>` per function placed. What `build/engine.sh <project> verify` and the `*-one` loops run. Its totals are not authoritative; `progress.py`'s are. |
| `objdiff.py` | Compares two COFF objects or `.lib`s symbol by symbol. |
| `bindiff.py` | Compares two whole linked PE images with addresses masked, matching functions across them whatever the link order. |
| `rsrcdiff.py` | Compares two images' resources payload by payload. |
| `callcheck.py` | Checks that our calls go where the shipped calls go (a masked comparison sees a `call` as one opcode and four holes). |
| `fpconst.py` | Checks the floating-point constants a function loads through relocations. |
| `linkresolve.py` | After a whole-image link, maps each unresolved symbol onto the definition it really means and writes alias lines. |
| `vtabcheck.py` | Compares our linked image's vtables with the shipped ones slot by slot. `vtabcheck.py <target>`; `_purecall` is found as the image's `jmp [IAT]` thunk, or from `targets.py`'s `purecall`. |

## Diagnosing a function that does not match

| Tool | What it does |
|---|---|
| `fndiff.py` | The main diff: byte identity if the sizes agree, otherwise the mnemonic diff, the best renaming of callee-saved registers, and hints from the fingerprints `guides/09-codegen-patterns.md` catalogues. `fndiff.py <ship-addr> <obj> <symbol> [--image=<target>]`; without `--image` the target is the one whose link read the object. |
| `nearpos.py` | Slides each unmatched function of an object over `.text` and reports where the fewest unmasked bytes differ. Reach for it first. |
| `layoutscan.py` | Finds nears whose every difference is a field displacement shifted by one constant: a struct layout error. `--image=<target>`. |
| `nearscan.py` | Runs `fndiff` over a whole near list and classifies each. `nearscan.py <target>`. |
| `o2gap.py` | Functions identical in `server.dll` (/O1) but not in `Lithtech.exe` (/O2): their source is proven, so what is missing is the shape /O2 sees. |
| `callseq.py` | Does our function call what the shipped one calls, in order? `--count` gives a shipped range's call count. |
| `census.py` | Compares the instruction census of a shipped function and ours. |
| `extentcheck.py` | Tests whether an enumerated row is really one function. |
| `enumcheck.py` | Validates a whole function table against a real disassembly. |
| `dupes.py` | Finds shipped addresses more than one of our symbols reconstructs. `dupes.py <image> <objdir>`. |

## Picking work

| Tool | What it does |
|---|---|
| `uncovered.py` | The shipped functions nothing of ours accounts for, counting every address a function of ours matches; reports what it excludes, and why, each as its own count. `uncovered.py <target>`: only rows the scoreboard counts (`app`) are offered. |
| `callseam.py` | Ranks unreconstructed functions by how many byte-identical functions call them. |

## Not adapted

Kept from nolfsrc, not worth adapting for NOLF2, and left as they are:

* `libfndiff.py`: `fndiff.py` for a library scored against a *shipped*
  prebuilt `.lib` (NOLF's lithshared, from its source release). NOLF2's
  release ships no static library, so `progress/targets.py`'s `LIBS` is
  empty and there is nothing to compare against; library code is scored
  inside the binaries that link it, where `fndiff.py` serves.
* nolfsrc's `d3d*` tools, `pef.py` and `moddata.py` were never copied:
  NOLF2 has no Intel-compiled `d3d.ren` (the renderer is linked into
  `Lithtech.exe`) and its Mac engine is Mach-O (`macho.py`).
