# How nolfsrc rebuilt the LithTech 2.x engine, and what carries over to NOLF2's Lithtech.exe

This was a read-only survey; no repository was modified. The intermediate files are in this
directory:

- `mac-nolf2-srcpaths.txt`: the source paths embedded in the Mac NOLF2 engine.
- `mac-nolf2-demangled.txt` and `mac-server-demangled.txt`: the Mac engine's symbols, demangled.
- `tags.txt`: the retail `Class::Method` tags.
- `*-qn*.txt` and `*-fn.txt`: name inventories of nolfsrc and of the F.E.A.R. tree.
- `*-inc.txt`: the header-set listings.

## TL;DR

1. **nolfsrc's engine was reconstructed blind from the bytes.** No engine source was used: not
   from AvP2, not from Shogo, not from any SDK. It had three kinds of input:
   - the LT2 SDK headers from the NOLF1 source release, used for types and interface names;
   - NOLF2-release library and launcher code, back-ported and "trimmed to era";
   - the retail binaries, read through a large Python toolset.

   The git history does not record the process. The whole engine (351k lines) arrives in one
   squashed commit, "First blood" (2215e97). The 128 later commits that touch `src/engine` add
   only about 3.8k net lines: closing nears, placing functions and fixing pairings. The
   process is therefore recorded in `guides/` (13 guides), `progress/README.md`,
   `toolchains/COMPILERS.md` and the long banner comments in each source file.
2. **For NOLF2 (Jupiter), the F.E.A.R. tree is the right seed almost everywhere. nolfsrc's
   engine source is not.** The evidence:
   - NOLF2's SDK headers are line-for-line the F.E.A.R. tree's for `iltmessage.h`,
     `iltserver.h`, `iltcommon.h`, `iltstream.h` and `iltrenderstyles.h`, and nearly so for
     `iltcsbase.h` and `iltmodel.h`.
   - NOLF2's file formats are the F.E.A.R. tree's: world `.dat` version 85 (NOLF1 is 66), and
     `.ltb` models of LTB version 9, model version 23. The F.E.A.R. tree loads exactly these;
     nolfsrc loads neither.
   - The retail `Class::Method` tags are Jupiter's (`CLTModelClient`, `CLTCommonShared`,
     `CUDPDriver`, `CUIVectorFont`, ...). nolfsrc has none of them.
   - **The Mac NOLF2 engine is unstripped Mach-O.** It carries about 11k demangled C++ names
     and the original source paths (`Source/Engine/Runtime/<module>/src/...`), which are
     exactly the F.E.A.R. tree's layout. Of the Mac engine's 5,470 `Class::method` names, the
     F.E.A.R. tree plus NOLF2's own libs have 3,810. nolfsrc has 667, almost all of them also
     in NOLF2's libs or SDK; only 16 are nolfsrc's alone.

   What does carry over from nolfsrc is the **method, the tools, the VC6 codegen case law, and
   a byte-proven 2000-era shape** for functions that exist in all three trees. That last part
   is a cross-check against the F.E.A.R. tree's later edits.
3. **Tooling.** 43 of nolfsrc's tools were copied unchanged, 11 were adapted (the scorer among
   them), and 3 are new (`dsp2mk`, `jupitersrc`, `libscan`). The rest is still NOLF-specific:
   - `uncovered.py` and `asmweb.py` import a `progress.APP_REGION` that no longer exists, so
     they will crash.
   - About ten tools hard-code `lithtech.exe`, `d3d.ren`, `src/engine/<t>/Release`, or NOLF1
     addresses such as `PURECALL` and the 8168/8447 compiler hints.
   - nolf2src has no `guides/`, no `build/engine.sh` (the `-one` loop), no `run_cl` in
     `env.sh`, and no Mach-O reader for the Mac names. `pef.py` is the NOLF1 Mac reader and
     was not copied.
   - `progress/targets.py` needs `built=`, `third_party` (D3DX, dinput8, dxguid), `cites` /
     `CITED_SRC` and the evidence CSVs before the engine scores.
4. **Recommended skeleton.** Mirror Monolith's Jupiter layout under
   `src/Engine/runtime/<module>/src/...`, with `src/Engine/libs/rezmgr/`. Use VC6
   `.dsw`/`.dsp` projects driven by `dsp2mk.py` in one more `build.mk` pass, as snddrv and
   ltmsg are. List the `.dsp` sources in retail address order, which nolfsrc never did: it
   linked objects alphabetically. Link a stub `Lithtech.exe` and `server.dll` on day one so
   the scorer and the loops run, then seed `server.dll` first from the F.E.A.R. tree, trimmed
   to the Mac symbol inventory. The renderer comes last, since the F.E.A.R. tree's is D3D9 and
   NOLF2's is D3D8.

---

## 1. How nolfsrc built its engine

### 1.1 What it started from

| Input | Used? | How |
|---|---|---|
| Engine source of any kind | **No** | None exists for LT2. Every engine `.cpp` was written from disassembly (`LICENSE-NOTES.md`: "written for this project, reconstructed from the retail binaries"). |
| LT2 SDK headers (`src/LT2/sdk/inc`, from NOLF Source v1.003) | Yes | Types, interface declarations, error codes. Guides 05 and 06 call these "NOLF2-era". That is wrong: they are LT2.x (`iltclient.h` has 1157 lines, against 3628 in NOLF2 and 1150 in AvP2). The lesson they drew still holds: **vtable order differs between header and binary, so verify each slot's `ret N`**. |
| NOLF2 public source release | Yes, outside the engine | `src/lithshared/` (stdlith, CryptMgr, RegMgr, MFCStub, ButeMgr parser, lith) was adapted from it. The launcher's `dibmgr`, `RezFind` and `Utils` were back-ported from NOLF2's launcher, "trimmed to the shipped era" by removing later methods until the function set matched (guide 05, step 2: "a seeded file often matches 80%+ on the first compile"). |
| RezMgr | Reconstructed | `src/lithshared/rezmgr/` was written from the bytes. It was identified as a prebuilt `.lib` because the same bytes appear in both `lithtech.exe` (/O2) and `server.dll` (/O1). |
| AvP2 `proj/LT2` | **No** | `grep` finds no reference. It holds only `sdk/` and `lithshared/` headers plus prebuilt `libs/{debug,release}/*.lib` with symbols: RezMgr, controlfilemgr, StdLith, WONAPI and others. These were never used. They are still a symbol-bearing reference for an LT2.2-era RezMgr (members `REZMGR.OBJ`, `REZHASH.OBJ`, `RezFile.obj`). |
| Shogo (`../shogo`) | **No** | Game code plus `softdib.ren`; no engine. |
| NOLF1 Mac PEF (`tools/pef.py`) | Late, and not for the engine recon | `pef.py` arrived on Oct 12 (7e4b28f), after the engine work, as a reference for the modern renderers. The engine's names came from tag strings, vtables and inference instead. |

### 1.2 Order of work

Reconstructed from the guides, `COMPILERS.md`, the file banners and the commits after the squash:

1. **Toolchain identification.** Read the Rich header (`richhdr.py`) and `@comp.id`
   (`compid.py`). The findings: cl 12.00.8447 for `server.dll`, `lithtech.exe` and the
   lithshared libs; Intel C/C++ 4.0 for `d3d.ren`; post-SP4 builds nobody has for the
   launcher. The `c2.dll` version, not the driver banner, is the one that counts.
2. **Enumeration.** `enumfuncs.py` combines call targets, vtable and data pointers,
   `push imm32` callbacks, initializer pairs, exports and padding carving. In `server.dll`
   only about 60% of functions are direct call targets, and about a third are reachable only
   through vtables. The output is `out/reference/<stem>-functions.csv`. Validation came later
   (`extentcheck.py`, `enumcheck.py`); see the defect catalogue in guide 13.
3. **Naming.** In order:
   - `tagmap.py`: the `RETURN_ERROR(…, "ILTX::Method")` literals name the function that
     pushes them;
   - `dataref.py`, for tags reached through a `static char*`;
   - `vtabmap.py`, `vtabaudit.py` and `sdkvtab.py`: anchor a vtable against the SDK's
     declaration order, then read the unknown slots;
   - the console-variable table: name to storage address, which identifies the owning module;
   - call-graph edges.
4. **`server.dll` first: the model target.** It has two exports, SDK types and many tag
   strings. Guide 06 records the discovery that it is built `/O1`: getting the flag wrong
   makes "every function nearly right".
5. **`lithtech.exe`.** It compiles about 40 of the `src/engine/server/*.cpp` files a second
   time (/O2) plus the client files. `o2gap.py` and guide 12 handle "identical in server.dll,
   near in lithtech.exe": the source is already proven, so only its /O2 shape is wrong.
6. **`d3d.ren`.** The Intel C/C++ 4.0 proof (SCCS idents from Intel's libm, lea-nop padding,
   the `/Qip` register shims) was followed by per-file flag groups. The files are named
   `w<N>_<addr>_<flags>.cpp` and `big<addr>.cpp`, a "structural" standard (guide 11,
   `callseq.py`) for functions of several KB. `d3d.ren` ended at 26%.
7. **Whole-image links and playtests.** Every engine image is linked from nolfsrc's objects
   alone and played (`make test`), so nears execute. Lesson: "a near can be the wrong
   function". A thiscall `AllocItems` paired with a cdecl allocator crashed the game.
8. **Coverage scoring** (50b771d, Oct 10) adds unwritten and unplaced counts and a ratchet.
   That same day the last 3 unwritten `lithtech.exe` functions were placed (ed2d12f), which
   brought every engine binary to **0 unwritten**.
9. **Converging nears**: guides 08, 09, 10 and 12, and the commit stream of Oct 11
   (`server: …`, `smgr: …`, `d3d: 0x… identical`).

Final state: `lithtech.exe` 77.5% of bytes identical (3,042 of 3,432 functions), `server.dll`
85.3%, `d3d.ren` 26.0%, with 12, 4 and 15 functions unplaced.

### 1.3 Source and link layout

- **No `.dsp`/`.dsw` for the engine.** `build/build.mk` section 3 holds hand-written source
  lists and flags:
  - `SERVER_SRC`: `/O1`, with `localdriver.cpp` at `/Os /Ob1`;
  - `LITHTECH_SRC`: `/O2`, with `clientmusic.cpp` without `/GF`, the copy of
    `localdriver.cpp` at `/Od /Oi /Ob1`, and `controlfile.cpp` at `/GX`;
  - `d3d` flag groups built through `run_icl`.

  `build/engine.sh` wraps it with `server|lithtech|d3d [verify]`, the `*-one <tu.cpp> [sym]`
  loop (recompile one object, then `exematch`), and `*-link test`, which loads the image
  under Wine through `tools/loadtest.c` with its base occupied.
- **Link order was never matched.** `SERVER_OBJ := $(sort …)` and
  `LITHTECH_OBJ := $(sort …)` link the objects alphabetically. `progress/README.md` says so
  ("that final, whole-file comparison is not made yet"). Scoring is per function only.
- **File boundaries are invented.** Monolith's names were unknown, so the tree has files such
  as `smgr.cpp`, `worldsim.cpp` and `commonmodel.cpp`. It also has staging and holding-pen
  files that say so in their banners: `lt2new1..4.cpp`, `ltnew1/2.cpp`, `cltnew.cpp`,
  `cltrest.cpp`, `svnew.cpp`, `svtiny.cpp`, `svlast.cpp`, `smgrnew.cpp`, `smgrmisc.cpp`,
  `worldtree2.cpp`. They are "not one translation unit; per-block banners say where each
  belongs".
- **Parallel work created link glue.** Guide 13, rule 5, has every new symbol in a file
  written in parallel carry a unique suffix. Classes therefore exist as per-TU stand-ins
  (`CFileMgrQ414`, `g_pErrorFormatQ40C`, …) and are tied back together at link time:
  - `link/aliases.rsp` holds `/ALTERNATENAME` lines (3,039 for lithtech, 561 for server,
    1,805 for d3d), each with its shipped-address evidence. `mkaliasobj.py` turns them into
    weak externals, because VC6 LINK has no `/ALTERNATENAME`.
  - `link/vtables.txt` (1,190 lines; `mkvtabobj.py`) gives full-length stand-in vtables for
    classes the source declares only partly.
  - `d3dviews.txt` (`mkviewobj.py`) lays out `d3d.ren`'s globals.
  - `mkimplib.py` builds the decorated Miles imports.

  This glue is debt that comes from not having the real class declarations.
- **Naming and evidence conventions.**
  - `sub_<addr>` for unknown functions (863 in d3d, 247 in lithtech, 117 in server).
  - Every decode cites shipped addresses in comments: 8,855 distinct addresses in
    `src/engine/lithtech`.
  - `sdkforce.cpp` is a scoring driver that forces SDK inlines out of line; it ships nowhere
    and has status `driver`.
  - The modern and debug code goes in `#ifdef NOLFSRC_MODERN` blocks. `releasesrc.py`
    removes them before the release compile, because VC6 output depends on line layout.

### 1.4 How the scorer places functions (`tools/progress.py`, `progress/README.md`)

A shipped function is placed in this order:

1. By bytes: masked-relocation `exematch` gives `identical`. A function made almost entirely
   of relocations is `small`.
2. By similarity: `near` means the same length within 15% and most unmasked bytes agree.
3. By joining what is still unpaired:
   - **by name**, where `sub_<addr>` or `own_names`/`own_symbols` names the address;
   - **by object**, where the shipped function's nearest placed neighbours belong to object
     X, which is then matched by size to X's unplaced functions;
   - **by link order**: gaps between functions placed in both images are aligned by size,
     using the `.map` of nolfsrc's own link.

Header inlines are deduplicated across objects. Tiny functions are counted by shape.

The statuses:

- On the shipped side: `identical`, `near`, `small`, `attempted`, `todo`, `crt`,
  `middleware`. `attempted` means the address is cited in `src/` or in the CSVs.
- On nolfsrc's side: `unplaced`, `unlinked` and `driver`. `unlinked` covers server code that
  `lithtech.exe` compiles but its link drops.

**Unwritten** is `todo` plus `attempted`. **Unplaced** is nolfsrc's linked functions that no
shipped function is placed for. The ratchet (`ratchet.py`, `make progress`) fails on:

- any identical function lost;
- a lower byte count;
- higher unwritten or unplaced counts;
- a README table out of sync.

`COVERED=1` and `COMPLETE=1` are the finish lines.

The evidence CSVs change the denominator, so each row must carry evidence:

- `*-screen-exclude.csv`: a reason of `NOT A FUNCTION` removes the row from the count;
- `extent-splits.csv`: starts the enumerator missed;
- `*-enum-suspect.csv`;
- `lithtech-decoded-map.csv`;
- `decoded-extents.csv` and `decoded-moved.csv`.

### 1.5 What the guides teach

| Guide | Teaches |
|---|---|
| 01–02 | The container, compiling one file under Wine, the verify loop and its tools, and why relocations are masked |
| 03 | The VC6 idiom dictionary: disassembly back to C++ |
| 04 / 06 / 08 | Worked examples: a library function, an engine function (and the `/O1` discovery), and a 494-byte function to identity (second-base `this`, dead parameter slots) |
| 05 | Exe and engine targets without symbols or relocations: enumerate, name, seed from era source "trimmed", resources via `.rc` and `rsrcdiff`, nears must run |
| 07 | Naming anonymous functions from vtables against the SDK's declaration order |
| 09 | The case law, about 2,300 lines: every proven asm-to-source fingerprint, the "known near classes" (shared-exit host, tail merge, callee-saved rotation, FPU ordering, …), compiler revisions, and "ORDERING is source-reachable, ALLOCATION is not" |
| 10 | Upgrading nears: triage, compiler probes, a fix catalogue in payoff order, a budget ("one experiment per byte of delta") |
| 11 | The third standard for functions of several KB: structural plus `callseq.py` and `census.py` |
| 12 | The /O2 shape of source proven at /O1: positive nested guards, immediates as struct sizes, inline visibility under `/Ob1` |
| 13 | The cluster procedure for agents: never guess, cite addresses, write incrementally, worktrees, unique suffixes, extent defects, and module identification ranked by reliability (cvar table > vtable > string pool > call graph) |

### 1.6 Hard parts and lessons

- **Function extents are wrong far more often than expected.** Guide 13 catalogues the
  shapes: success arms, shared fail blocks, guard fall-throughs, rows that cut an instruction,
  2–3 functions in one row (likeliest above 1 KB), data, ASCII accidents (the tails of string
  literals read as `0x004xxxxx`), false call targets inside displacements and immediates,
  and `setup` rows read from `.text`. A thunk can hide a function start, which goes in
  `extent-splits`.
- **The whole-binary flag decides everything.** `/O1` against `/O2` makes dozens of
  "small" diffs. Revision mismatch had to be tested, never inferred: 8168 against 8447 closed
  some nears outright, while other nears blamed on revision turned out to be source shape.
- **The SDK headers were from another era.** Signatures were mostly stable, but vtable order
  was not; argument reordering and guard sets had to be read from the bytes.
- **Shared TUs compiled twice.** A change for `lithtech.exe` must not regress `server.dll`.
  `server.dll` is the proof of semantics, `lithtech.exe` the oracle for shape. Server code
  sometimes drops a profiling timer (`LT_SERVER_TIMERS`) or calls into the client.
- **Inline placement.** VC6 places out-of-line inlines by file layout. That is why the
  variant code had to be stripped textually (`releasesrc.py`), not just `#ifdef`'d.
- **Nears that are not real pairings.** A crashing cdecl/thiscall mismatch, and
  `CloseConnection`, which was a missing argument rather than a register lottery.
- **What masking cannot see.** Wrong callees need `callcheck.py`, float constants behind
  relocations need `fpconst.py`, and short stand-in vtables need `vtabcheck.py`.
- **Disassembler traps.** objdump's AT&T x87 operand swap (use `-M intel`), and `/O2`
  canonicalising commutative float sums.
- **d3d.ren.** A non-Microsoft compiler, unknown file boundaries and flag groups. The result
  was the lowest score (26%), despite the most files (227).
- **Calibration.** People and agents predict byte identity pessimistically. Report what was
  verified.

---

## 2. What carries over from nolfsrc to NOLF2's engine (LT2.x → Jupiter → F.E.A.R. tree)

### 2.1 Evidence

| Measure | nolfsrc / LT2 (NOLF1) | NOLF2 1.3 (Jupiter) | F.E.A.R. tree (`fear/Dev/Source`) |
|---|---|---|---|
| SDK `inc/` file set | 47 files; lacks cui*, iltdrawprim, ilttexinterface, iltrenderstyles, ltmodule, libltinfo, ltobjref, ltrenderstyle, ltmem, … | 96 files | 107 files; **95 of NOLF2's 96 names** (the 96th is a Makefile) |
| `iltclient.h` lines | 1157 | 3628 | 3794 (176 diff lines: D3D9 shader API, renderer stats, default args removed) |
| `iltserver.h`, `iltmessage.h`, `iltcommon.h`, `iltstream.h`, `iltrenderstyles.h` | very different (`HMESSAGEREAD`, …) | – | **identical to NOLF2** (`diff -w` gives 0 lines) |
| `iltcsbase.h`, `iltmodel.h`, `iltsoundmgr.h` | different | – | 2–4 diff lines from NOLF2 |
| `ltbasedefs.h` | 1284 | 1870 | 2468 (620 diff lines: Linux/`MODULE_EXPORT`, wchar `LTStr*`) |
| World `.dat` version | 66 (NOLF1 `M13S02.dat`) | **85** (`CP_C04S01.dat`) | `CURRENT_WORLD_VERSION 85` |
| Models | `.abc` | `.ltb`, LTB version 9, model file version 23 | `CD3D_LTB_LOAD_VERSION 9`; `MODEL_FILE_VERSION 25`, minimum 23 |
| Interface linkage | none | `server.dll` exports `SetMasterDatabase`; `ltmodule.h` | `shared/interface_linkage.cpp` |
| Retail `Class::Method` tags (245 in `Lithtech.exe` plus `server.dll`) | no class names for `CLTModelClient/Server`, `CLTPhysicsClient/Server`, `CLTCommonClient/Server/Shared`, `CUDPDriver`, `CSoundBuffer`, `CUIVectorFont`, `CLTVideoMgr`, `ClientDE`, `ModelInstance` | – | **all 245 tag methods present** (nolfsrc: 207, matched by method name only) |
| Mac NOLF2 engine names (`Class::method`) | 667 of 5,470 (with NOLF2's libs and SDK; only 16 nolfsrc-only: LAlloc, CLTCursorInst, a few SDK inlines) | – | **3,810 of 5,470** (with NOLF2's libs). Most of the rest is Omni's Mac port layers (`Device`, `VertexBuffer`, `ODM*` DirectMusic emulation, `QTVideo*`, `IDirect3DResource8` emulation) |
| Engine source paths | invented | Mac binary strings: `Source/Engine/Runtime/{client,kernel,kernel/mem,model,render_a/src/sys/d3d,render_b/src/sys/d3d,server,shared,sound}/src/...`, `Source/Engine/libs/rezmgr`, `Source/libs/stdlith` | the same `runtime/<module>/src/` tree |

**The Mac NOLF2 engine is a significant resource that nolf2src does not use yet.**
`rez/games/nolf2-mac-usa/NOLF2.app/Contents/MacOS/NOLF2` is a GCC-built Mach-O PowerPC binary.
`rez/README.md` counts about 19,500 symbols; this survey extracted about 11k demangled
names. The NOLF2Srv Mac bundle's `server` (`Contents/Resources/server.dll/Contents/MacOS/server`)
has about 3,080 functions, 3,043 of which also appear in the Mac client engine. That confirms
the NOLF1 structure: the server TUs are linked into the client too. The Mac binaries give:

- the function inventory of Jupiter 1.3, which says what to trim from the F.E.A.R. tree;
- the true file names, for the 39 paths embedded as assert and `__FILE__` strings;
- signatures from the mangled names (argument types, const, overloads).

They do not give byte-usable code: the compiler is GCC and the platform layers are Omni's.

### 2.2 Area by area

| Area (Jupiter path) | nolfsrc counterpart | Likely closer | Why |
|---|---|---|---|
| Client and server interfaces (`client/clientde_impl`, `server/serverde_impl`, `shared/impl_common`, `client_iltcommon`, `server_iltmodel`, `*_iltphysics`, …) | `clientinterface.cpp`, `servermgr`, `servermsg` | **F.E.A.R. tree** | The interfaces were split into client and server implementations in Jupiter; the headers are identical to NOLF2's |
| Messages and packets (`shared/ltmessage`, `client/ltmessage_client`, `server/ltmessage_server`, `kernel/net/packet`) | `packet.cpp`, `lmessage.cpp`, `HMESSAGEREAD` | **F.E.A.R. tree**, with care | NOLF2's `iltmessage.h` is the F.E.A.R. tree's. The Mac names `CLTMessage_Load/Save/Read/Write` are partly missing from the F.E.A.R. tree, so it was revised after 2002; check against the Mac names |
| Networking (`kernel/net`: `netmgr`, `udpdriver`, `localdriver`) | `netmgr.cpp`, `tcpdriver.cpp`, `localdriver.cpp` | **F.E.A.R. tree** | NOLF2 has `CUDPDriver` tags. Note: 26 `CBaseDriver` and 10 `CBaseConn` Mac methods are missing from the F.E.A.R. tree, so the 2002 driver base is fuller than the F.E.A.R. tree's and must be decoded |
| World and BSP (`world/*`, `world_shared_bsp`, `world_tree`, `world_*_bsp`) | `worldbsp.cpp`, `worldtree*.cpp`, `wgrid.cpp` | **F.E.A.R. tree** | World version 85 equals 85; NOLF1's 66 format is a different loader |
| Models (`model/model_load`, `animtracker`, `transformmaker`; render-side `d3d_model_load`, `d3dmeshrendobj_*`) | `commonmodel.cpp`, `modelnew.cpp`, `modelanim.cpp`, `cmodelload.cpp` | **F.E.A.R. tree** | LTB 9 and model version 23 are supported by the F.E.A.R. tree's loader; NOLF1 is `.abc` |
| Movement and collision (`shared/moveobject`, `collision`, `moveplayer`, `world/intersect_*`) | `worldsim.cpp` (`ws_*`), `commonphysics.cpp` | **F.E.A.R. tree for structure**; nolfsrc as a VC6-shape cross-check | This code is old and stable. nolfsrc's `ws_*` functions are byte-proven VC6 /O1 and /O2 bodies of the same lineage, useful when the F.E.A.R. tree has later edits. Check that the F.E.A.R. tree's `physics/` (GJK, rigid body) is in NOLF2 at all: Jupiter SDK 51 ships `Engine/sdk/lib/physics.lib` separately |
| Renderer (`render_a/src/sys/d3d`, `render_b` drawprim) | `d3d.ren` (DX7, Intel C/C++, 227 invented files) | **F.E.A.R. tree for structure only**; neither for API | NOLF2 is D3D8, inside `Lithtech.exe`, built with VC6 and D3DX8 linked in. The F.E.A.R. tree is D3D9 (10 files include d3d9, none d3d8). The Mac paths (`d3d_device.cpp`, `d3d_renderstatemgr.cpp`, `screenglowmgr.cpp`, `pixelshadermgr.cpp`, `d3ddrawprim.cpp`, …) confirm the F.E.A.R. tree's file names. nolfsrc's `d3d.ren` is useless here |
| UI and fonts (`ui/src`, CUI widgets, `CUIVectorFont`, freetype) | none (NOLF1 used `LithFontMgr` in game code) | **F.E.A.R. tree** | Jupiter introduced it |
| Sound manager (`sound/src`, `soundbuffer.cpp`) | `clientsoundmgr.cpp`, `soundinst2.cpp`, `sndmgr2.cpp` (Miles-era) | **F.E.A.R. tree** | NOLF2 loads `SndDrv.dll` (`ILTSoundSys`), already rebuilt from the F.E.A.R. tree's `s_dx8` |
| DirectMusic (`kernel/src/sys/win/ltdirectmusic_impl`, `ltdirectmusicloader`, `ltdirectmusiccontrolfile`) | `clientmusic.cpp`, `dmextra.cpp`, `dmloader.cpp` (byte-proven) | **Both are useful** | All 14 retail `CLTDirectMusicMgr` tags exist in both. A spot check: the F.E.A.R. tree's `SetVolume` adds `m_nVolumeOffset`, which nolfsrc's VC6-proven body lacks. NOLF2 sits between them, so let the bytes decide, and use nolfsrc's bodies as VC6-shape templates |
| Console, cvars and commands (`shared/concommand`, `conparse`, `client/console`, `consolecommands`, `engine_vars`) | `console.cpp`, `ccline.cpp`, `cchandler.cpp` | F.E.A.R. tree, with nolfsrc as a shape check | |
| Containers (`dhashtable`, `struct_bank`, `objectmgr`, …) and stdlith | `dhash.cpp`, `structbank.cpp`, `objbank.cpp`, `collection.cpp`, `stringbank.cpp` | **NOLF2's own `src/libs/stdlith`** first, then the F.E.A.R. tree; nolfsrc as a shape check | nolfsrc's stand-in container types (`CMoArray<…Q…>`) are reconstruction artefacts |
| RezMgr (`Source/Engine/libs/rezmgr`) | `src/lithshared/rezmgr/` (6 invented files) | **F.E.A.R. tree's `libs/rezmgr/`** (`rezmgr`, `rezfile`, `rezhash`, `rezutils`), plus AvP2's prebuilt `RezMgr.lib` (with symbols) for the object split | The F.E.A.R. tree has Monolith's source. nolfsrc proved the /O1 and /O2-independence trick: RezMgr is a prebuilt `.lib`, so the same bytes appear in both images. Expect the same in NOLF2 |
| Bink video and video manager (`kernel/src/sys/win/binkvideomgrimpl`, `videomgr`) | `binkvideo.cpp`, `lvideomgr.cpp`, `smackvideo.cpp` | F.E.A.R. tree | NOLF2 has `BinkVideoMgr`/`BinkVideoInst` and `CLTVideoMgr` tags; there is no Smacker |
| Input (DirectInput8: `kernel/src/sys/win/input.cpp`) | `clientinput.cpp` (DInput 5/7) | F.E.A.R. tree | `Lithtech.exe` imports `dinput8!DirectInput8Create` |
| Launcher, `ltmsg`, `sres` | done in nolfsrc | n/a | nolf2src already has `NOLF2.exe` (Monolith source) and `ltmsg` (rebuilt) |

**Bottom line for section 2.** Do not port nolfsrc's engine source. Seed from the F.E.A.R.
tree, as snddrv was seeded, and trim it to the Mac NOLF2 inventory. Use nolfsrc for three
things:

- its tools;
- its guides: 09, 10, 12 and 13 transfer directly, because NOLF2 is also VC6, and probably
  again `/O1` for `server.dll` and `/O2` for `Lithtech.exe` with shared TUs;
- byte-proven VC6 bodies of same-lineage functions (DirectMusic, console, movement,
  containers) as shape templates where the F.E.A.R. tree drifted.

One difference: NOLF2 is built entirely with cl **8966** (VC6 SP5). nolfsrc's 8168/8447 split
does not apply, and `fndiff.py`'s revision hints are wrong for NOLF2.

---

## 3. Tooling

### 3.1 nolfsrc tools against nolf2src's copies (`diff -r`)

- **Copied unchanged (43):** agentwt.sh, asmweb.py, bindiff.py, buildcmp.py, callcheck.py,
  callseam.py, callseq.py, census.py, dataref.py, decoded.py, decodedlt.py, dsp2files.py,
  dumpfn.py, dupes.py, enumcheck.py, enumfuncs.py, exedump.py, exematch.py, extentcheck.py,
  fndiff.py, fpconst.py, ghidra/, layoutscan.py, libextract.py, linkresolve.py, loadtest.c,
  mkaliasobj.py, mkimplib.py, mkviewobj.py, msvcdemangle.py, nearpos.py, nearscan.py,
  o2gap.py, objdiff.py, playtest-basic.txt, rezextract.py, rsrcdiff.py, sdkvtab.py,
  tagmap.py, uncovered.py, vtabaudit.py, vtabcheck.py, vtabmap.py.
- **Adapted:**
  - `progress.py`, the rewrite: driven by `progress/targets.py`, with `encrypted`,
    `middleware`, `third_party`, and `.rsp`/`.cmd`/`.map`-based link inputs;
  - `ratchet.py`, `releasesrc.py` (NOLF2SRC_*), `retailextract.py`, `richhdr.py`;
  - small edits in `compid`, `mkdeps`, `mapaddr`, `mkvtabobj`, `libfndiff`, `playtest.sh`,
    `README.md`.
- **New:** `dsp2mk.py`, `jupitersrc.py`, `libscan.py`.
- **Not copied:**
  - the d3d tools (`d3dcheck`, `d3dwork`, `d3dflags.sh`, `d3dsplit`, `d3ddata`,
    `d3dloadtest.c`), which are not needed: NOLF2 has no Intel-compiled renderer;
  - `pef.py` (the NOLF1 Mac PEF reader);
  - `moddata.py`;
  - the modern playtest scripts `p1..p5*.txt`;
  - **`guides/`**: none of it is in nolf2src, although `tools/README.md` refers readers to it.
- **Not ported from `build/`:**
  - `build/engine.sh` (the `server|lithtech verify`, `*-one`, `*-link test` loop);
  - `env.sh`'s `run_cl`, `run_link`, `run_lib`, `run_rc` and `CL_REV`; nolf2src's `env.sh`
    has only `nolf2src_release_tree` and `nolf2src_make`;
  - `libs.sh`.

### 3.2 Engine-specific tools that still need adapting

Grep of nolf2src/tools for hard-coded NOLF1 facts (comments excluded where noted):

| Tool | What is hard-coded | Needed |
|---|---|---|
| `uncovered.py`, `asmweb.py` | `from progress import APP_REGION`, which nolf2src's `progress.py` no longer defines. **They crash.** `uncovered.py` also scans `src/engine/<target>/` for cited addresses | Read the `app`, `crt`, `middleware` and `encrypted` ranges from `targets.py` (`progress.region()`/`in_app()`), and take the source root from `CITED_SRC` |
| `vtabcheck.py` | `PURECALL = {"lithtech.exe": 0x004928e7}` (NOLF1), `TWIN_ADDRS` (NOLF1 addresses), an image to (`src/engine/...`, `lithtech.map`) table | NOLF2's `_purecall` (an msvcrt import thunk under /MD), its own twin list, and the built paths `src/Engine/built/Final/<proj>/` |
| `o2gap.py` | `server.dll` against `lithtech.exe` names and `src/engine/{server,lithtech}/Release` object directories | `server.dll` against `Lithtech.exe` (case) and the new object directories. The method holds if NOLF2's `server.dll` is again /O1 or /Os (COMPILERS.md: only 178 of 1,694 call targets are 16-byte aligned) |
| `decoded.py`, `decodedlt.py` | `IMAGES`/`ENUM` dicts for d3d, server and lithtech; `progress/lithtech-decoded-map.csv`; `OBJDIR = src/engine/lithtech/Release` | Rename to `Lithtech` and new object directories; drop d3d |
| `nearscan.py`, `layoutscan.py`, `tagmap.py` | `OBJDIR`/`IMAGE` dicts and `rel = {"lithtech.exe": "src/engine/lithtech/Release", …}` | The same remap; better, derive the object directories from the built image's `.rsp` as `progress.py` does |
| `fndiff.py` | default `--image=out/reference/server.dll`; hints naming 8168/8447 ("server.dll is a mixed 8168/8447 build") | NOLF2 is uniformly 8966, so drop or retarget the revision hints |
| `sdkvtab.py` | `src/LT2/sdk/inc` | `src/Engine/sdk/inc` |
| `agentwt.sh` | checks `out/reference/server.dll`; assumes outputs in `src/*/Release` and `src/lithshared/out` | NOLF2 builds into `src/Game/built`, `src/Engine/built` and `src/libs/built`; `rez/sdk` (the Jupiter SDK) must also be linked in |
| `exedump.py`, `enumfuncs.py`, `extentcheck.py` | generic; d3d notes only | **SecuROM:** `Lithtech.exe` 0x565000–0x56a000 is encrypted and holds the CRT entry, chkstk- and atexit-like targets (0x567648 has 401 callers). Calls into it will show as unknown; `enumfuncs` rows there are garbage, and the scorer already marks them `encrypted`. The `.cms_t`/`.cms_d` sections should be skipped by any section scan |
| `mkaliasobj.py`, `mkvtabobj.py`, `mkviewobj.py`, `linkresolve.py` | generic | Keep as fallbacks only. With real class declarations from the F.E.A.R. tree, the stand-in vtables and aliases should mostly be unnecessary |
| `loadtest.c` | `CreateServer`/`DeleteServer` | Usable for NOLF2's `server.dll` as is. NOLF2 also exports `SetMasterDatabase`, which could be exercised |
| (missing) `macho.py` | – | A Mach-O reader for the Mac NOLF2 engine and `server`, the counterpart of `pef.py`: symbols with addresses and sizes, demangling, embedded paths, call references. It is the naming and inventory oracle that NOLF1's engine recon lacked. `objdump` here does not recognise Mach-O PPC, so it must be pure Python |

`build/reference.sh` already enumerates `Lithtech.exe` and `server.dll` and writes
`Lithtech-functions.csv` (11,073 rows) and `server-` and `Lithtech-vtables.csv`.
`server.dll` has a real `.reloc` (0x4c72 bytes), unlike nolfsrc's exe-only experience, so
its pointers and vtables can be read exactly. `Lithtech.exe` has no relocations.

### 3.3 What `progress/targets.py` needs before the engine scores

`Lithtech.exe` currently has `built=None, optional=True`, so `rows_for_unbuilt` gives all
7,393 functions as todo. To score it:

1. **`built=`** the linked image, for example `src/Engine/built/Final/lithtech/Lithtech.exe`
   (and `server.dll` likewise). It must be linked through `build.mk`'s `binary` macro, so
   that `<image>.rsp`, `<image>.cmd` and `<image>.map` exist: `progress.py` reads link inputs
   from the `.rsp` (`link_inputs`) and places functions with the `.map` (`our_map`). Keep
   `optional=True` until the link is in `make all`.
2. **`third_party`** = the link inputs that build `middleware`, so they are neither matched
   nor counted as unplaced: at least `d3dx8.lib`. Import and data libraries such as
   `dxguid.lib`, `dinput8.lib`, `uuid.lib`, `d3d8.lib`, `winmm.lib` and `wsock32.lib` add no
   app code, but list any that contribute objects. The current `middleware` range
   (0x4b2370–0x4c1240) covers the first D3DX block; the second (0x56a0cc on) is already
   outside `app`.
3. **`cites=True`** and **`CITED_SRC = ["src/Engine"]`**, if the reconstruction keeps
   nolfsrc's convention of citing shipped addresses in comments. `Lithtech` and `server` are
   in different ranges (0x4… against 0x1000…), but ServerDir, snddrv and the game DLLs share
   0x1000… with `server.dll`, which is why `cites` is per-target. Only enable it for
   `Lithtech` and `server`, or scope the citations per directory. `progress.py` currently
   applies one global `CITED_SRC`, so this may need a per-target `cited_src`.
4. **Naming convention for unknowns.** `sub_<addr>` already works through `_own_addr`. Add
   `own_names`/`own_symbols` if names from the Mac map are used for functions whose address
   is otherwise unproven.
5. **`DRIVER_OBJS`**, if an `sdkforce.cpp`-style driver is needed to emit SDK inlines.
6. **Evidence CSVs:** `progress/Lithtech-screen-exclude.csv`,
   `progress/server-screen-exclude.csv`, `extent-splits.csv` rows (the file exists; it has
   snddrv rows), and optionally `Lithtech-decoded-map.csv` and `*-enum-suspect.csv`.
   `progress.py` already finds them by stem (`_exclude_files`).
7. **A second `app` range?** For `Lithtech.exe`, code of Monolith's placed after the runtime
   would sit in the encrypted pages or past D3DX. Revisit once nolf2src's own `.map` shows
   where its last engine object lands relative to msvcrt's static members.
8. **`linked_oracle=True`** is optional. nolfsrc used it for the launcher, to compare
   relocation-free functions against the linked image unmasked.

---

## 4. Recommended skeleton for nolf2src's engine

### 4.1 Directory layout

Mirror Monolith's own tree. The NOLF2 release is rooted where Monolith's `Source/` was (the
Mac strings give `Source/Engine/Runtime/...`, `Source/Engine/libs/rezmgr`,
`Source/libs/stdlith`), and the snddrv and ltmsg projects already live under `src/Engine/`:

```
src/Engine/
  sdk/                       (Monolith's, as released)
  ltmsg/  snddrv/            (done)
  runtime/                   Monolith spells it "Runtime" in the Mac paths; Windows does not care
    client/src/ (+ sys/win/)     clientmgr, clientshell, clientde_impl, client_ilt*, console, ...
    server/src/                  servermgr, s_client, s_net, serverde_impl, server_ilt*, ...
    shared/src/ (+ sys/win/)     ltmessage, concommand, moveobject, collision, objectmgr, ...
    kernel/src/sys/win/          client.cpp (WinMain), input, render, videomgr, ltdirectmusic_*, ...
    kernel/mem/src/ (+sys/win/)  de_memory
    kernel/net/src/ (+sys/win/)  netmgr, packet, localdriver, udpdriver
    kernel/io/src/
    world/src/                   world_shared_bsp, world_tree, de_mainworld, intersect_*
    model/src/                   model, model_load, animtracker, transformmaker
    render_a/src/sys/d3d/        the D3D8 renderer (static lib)
    render_b/src/sys/d3d/        d3ddrawprim
    sound/src/                   soundmgr, soundbuffer (engine side; SndDrv is separate)
    ui/src/                      CUI*, vector fonts (+ freetype, if retail links it)
    info/src/  controlfilemgr/  lithtemplate/  (esd/ only if the retail binary has RealAudio code)
    winbuild/
      lithtech/   Lithtech.dsp, lithtech.rc, resource.h        -> Lithtech.exe
      server/     server.dsp, server.def (CreateServer, DeleteServer, SetMasterDatabase), server.rc
      Engine.dsw  (Lithtech, server, D3DRender, UI, rezmgr; ../../../libs/{ltmem,stdlith,lith,zlib})
  libs/rezmgr/   rezmgr.dsp + rezmgr/rezfile/rezhash/rezutils.cpp  (prebuilt-lib role, as in NOLF1)
```

**Project granularity.** The F.E.A.R. `Lithtech.map` shows the exe linking static libraries:
`LIB_D3DRender`, `Lib_UI`, `Lib_Lith`, `Lib_RezMgr`, `Lib_StdLith`, `ltmem` and `Lib_DShow`.
Everything else (client, kernel, shared, server, world, model, sound) is direct `.obj`s. Use
the same split for Jupiter, but let NOLF2's retail layout decide, since the F.E.A.R. map is
VC7.1 and 2006: libraries are contiguous runs in the image, which `libscan.py` can test once
they compile.

**Defines** (from the F.E.A.R. tree's build and code):

- client: `DE_CLIENT_COMPILE`, `DE_LOCAL_SERVERBIND`, `DIRECTENGINE_COMPILE`, `__D3D`,
  `__D3DREND`;
- server: `DE_SERVER_COMPILE`, `DIRECTENGINE_COMPILE`, `STDLITH_ALLOC_OVERRIDE`,
  `NO_PRAGMA_LIBS`;
- both: `_FINAL` (snddrv proved `_FINAL` is set in the Final build).

**Flags** (starting point, from COMPILERS.md):

- `Lithtech.exe`: `/MD /W3 /GX /O2` with cl 8966; it imports `msvcp60.dll`, so MS STL is
  used, not only STLport;
- `server.dll`: `/MD /W3 /O1` (or `/Os`), with some `/GX`.

As in nolfsrc, expect per-file exceptions. Prove them per file, as guide 06 did for `/O1`.

### 4.2 build.mk integration

Follow the snddrv and ltmsg pattern exactly (`build/build.mk`):

```make
ENGINE_WANTED := Lithtech server
DSP_OK := $(shell python3 tools/dsp2mk.py src/Engine/runtime/winbuild/Engine.dsw Final \
            $(DEPDIR)/engine.mk $(ENGINE_WANTED) 2>$(DEPDIR)/dsp2mk-engine.log && echo ok)
ifneq ($(DSP_OK),ok)
$(error tools/dsp2mk.py failed: $(file <$(DEPDIR)/dsp2mk-engine.log))
endif
include $(DEPDIR)/engine.mk
all game: ... $(ENGINE_WANTED)
```

- `dsp2mk.py` already handles libraries plus a DLL or exe with workspace dependencies,
  per-file `ADD CPP`/`SUBTRACT CPP`, per-file `/Fp` (the snddrv `/YX`-as-`/Yc` trick), and
  `CL_<project>` overrides. The `binary` macro writes the `.rsp` and `.map` the scorer needs.
- The workspace needs `ltmem` (already in `src/libs/ltmem`, added for snddrv), `stdlith` and
  `lith` (Monolith's, in `src/libs`), and `rezmgr` (new).
- Link libraries: from `toolchains/dxsdk-8.1`, `d3d8.lib`, `d3dx8.lib`, `dinput8.lib` and
  `dxguid.lib`; plus `wsock32`, `winmm`, `version`, `ole32`, `advapi32`, `gdi32`, `user32`
  and `kernel32`. Bink is not imported by the retail exe, so it is presumably loaded
  dynamically.
- **Link order:** VC6 links `.obj` files in `.dsp` order. Unlike nolfsrc, order the
  `SOURCE=` entries to the retail address order of each TU's functions. Do it as snddrv's
  "lay the objects out as retail" commit did, and order the libraries as they appear.
  `progress.py`'s link-order join and any later whole-image comparison both depend on it.
- Add a `build/engine.sh` equivalent: `Lithtech|server [verify]`, `*-one <tu.cpp> [sym]`
  (rebuild one object through `nolf2src_make <object>`, then `exematch`), and
  `server-link test` (`loadtest.c`). Restore `run_cl`, `run_link` and the others in
  `build/env.sh`, with the S:/T: drive mapping that `build.mk` uses.
- `build/all.sh` step 2b keeps the RETAIL engine in the game directory until the built
  engine runs. Add an audit line for the built-but-not-installed engine, as was done for
  snddrv.

### 4.3 Getting a first linking (not identical) Lithtech.exe early

1. **Day 0: the pipeline.**
   - Create `Engine.dsw`, `Lithtech.dsp` and `server.dsp` with empty or near-empty TUs.
   - Write a `WinMain` (`kernel/src/sys/win/client.cpp`, trimmed from the F.E.A.R. tree) and
     a `server.def` exporting stub `CreateServer`, `DeleteServer` and `SetMasterDatabase`.
   - Link. Set `built=` and `optional=True` in `targets.py` and run `make progress`. The
     target now scores (still about 0%), and the `.rsp`, `.map` and unplaced machinery is
     exercised.
2. **Build the Mach-O reader and the inventory.** Write `macho.py`. Generate per-module
   function lists from the Mac `NOLF2` and `server` binaries, grouping functions into TUs by
   the F.E.A.R. file that defines each name. This decides which F.E.A.R. files exist in 2002
   and which functions to delete or add.
3. **Seed `server.dll` first.** It is the right first target, as in nolfsrc:
   - it is smaller (3,451 functions, 310 KB);
   - it has full relocations;
   - it has three exports, a load test, and tag strings;
   - its TUs are compiled again into `Lithtech.exe`, so the work pays twice.

   Seed `server/`, `shared/`, `world/`, `model/` and `kernel/net` from the F.E.A.R. tree,
   back-ported to VC6 and the 2002 interfaces:
   - drop the D3D9, Linux, Xbox and wchar additions;
   - restore default arguments to match NOLF2's SDK;
   - trim to the Mac inventory.

   Get it linking, then iterate with `server-one` and `exematch`. Expect the snddrv
   experience: seeded code matched 68% at first and 98.7% after corrections.
4. **Then the client side of `Lithtech.exe`**: client, kernel, sound engine side, UI and
   video. Add the server TUs a second time at /O2. Use `o2gap.py` once both images have
   matches.
5. **Renderer last.** `render_a`/`render_b` hold the largest code mass. The F.E.A.R. tree is
   D3D9, so this is a real back-port to D3D8 and D3DX8. A stub renderer that links (null
   device) lets the exe link and load before then; nolfsrc never had that option, because
   its renderer was a separate `.ren`.
6. **Running it.** The retail exe cannot run under Wine because of SecuROM, so a built
   `Lithtech.exe` that boots, even with nears, is the only way to play the 1.3 game from
   this tree. Treat "boots to the menu" as a milestone and keep nolfsrc's rule that nears
   must execute (`make test`).

**Guides to bring over first:** 02, 05 (with corrections: NOLF2 DLLs have `.reloc`; it is
all 8966; the SDK headers are the right era), 07, 09, 10, 12 and 13.
