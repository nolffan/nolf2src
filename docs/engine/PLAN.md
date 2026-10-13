# The engine: plan and status

The work to build `Lithtech.exe` and `server.dll` from source, split into
packages that can each be picked up again after an interruption. **The aim is
a game that runs**: a `Lithtech.exe` without SecuROM, built here. Byte-identity
with retail is the second aim: match where it comes cheaply, but don't block
progress on it.

Background, in this directory:

- `anatomy.md`: the retail binaries; SecuROM; the 1.3 multiplayer demo's
  unprotected engine as a stand-in for the encrypted pages; the module map and
  link order.
- `fear-mapping.md`: the `fear/Dev/Source/runtime` tree is LithTech Jupiter
  (NOLF2's engine line, a 2006 VS2003/D3D9 build), not Jupiter EX. It covers
  about 90% of `Lithtech.exe` and 95% of `server.dll`; `render_a` is NOLF2's
  renderer, ported to D3D9.
- `nolfsrc-process.md`: how nolfsrc rebuilt NOLF1's engine; what carries over
  (the method, tools and guides, not the code); the recommended skeleton.

## Ground rules (every package)

- **Source.** Start from the Jupiter tree (`../fear/Dev/Source/runtime`, and
  its `sdk/`, `libs/`), trimmed back to 2002: drop what the Mac NOLF2 engine's
  symbols and the retail image don't have (D3D9, DirectShow, texture strings,
  custom font files, memory watch, perf counters, Linux/Xbox, wide strings),
  restore what NOLF2 had. Keep Monolith's comments where the code is kept.
  Where Jupiter has nothing, write it from the retail disassembly (and the 1.3
  MP demo's engine for the SecuROM pages and the real imports).
- **Compilers.** VC6 SP5 (cl 8966), DirectX 8.1 SDK; `Lithtech.exe` `/O2`,
  `server.dll` `/O1`; prove per-file exceptions.
- **Legacy vs modern.** The legacy build links the retail third-party
  libraries (D3DX8 from the DX 8.1 SDK; Bink loaded at run time as retail
  does). The modern build (`NOLF2SRC_MODERN`) may replace them, as nolfsrc
  does: FFmpeg for Bink video, OpenMiles where Miles is needed.
- **Commits.** Small commits, each leaving the tree building.
- **Agents.** One package per agent, in its own worktree
  (`.worktrees/<package>`, branch `<package>`), Docker containers named
  `<package>-*`. The merge into master, the score commit and the worktree's
  removal are the coordinator's.
- **Restarting.** The table below is the state. A package's agent updates its
  own row and its notes section in its last commit; the coordinator updates
  it on merge. To resume a package, start a new agent on its branch with this
  file and its notes.

## Packages

| # | Package | Depends on | Status |
|---|---|---|---|
| 1 | `tools`: guides, tool fixes, Mac symbol inventory, demo import map, scorer targets for the engine | -- | done |
| 2 | `skeleton`: `src/Engine/runtime/` from the Jupiter tree, `Engine.dsw` with Lithtech/server and the libraries, `build.mk` pass; first link of both (stubs allowed) | -- | done: both link, with the excluded files below stubbed |
| 3 | `server`: `server.dll` compiles, links and loads (`server/`, `shared/`, `world/`, `model/`, `kernel/net`, `kernel/io`) | 2 | todo |
| 4 | `client`: the exe's own objects (`client/`, `kernel/src`, input, DirectMusic, video, console) with the server objects at `/O2` | 2 (3 helps) | todo |
| 5 | `libs`: `rezmgr`, `stdlith`/`lith`, `ltmem`, `iltsound`, `ui` (Lib_UI) | 2 | done: no stubs left; fonts and the mem command as 2002 had them; the libraries' flags and link order as retail's |
| 6 | `render`: `render_b` (drawprim, texinterface) and `render_a` back-ported from D3D9 to D3D8 | 2 | todo |
| 7 | `boot`: the built `Lithtech.exe` in the game under Wine: to the menu, then a level; snddrv/ServerDir/ltmsg built ones in | 3–6 | todo |
| 8 | `modern`: the modern build of the engine (FFmpeg Bink, fixes) | 7 | todo |
| 9 | `match`: byte-matching passes per module, ratcheted by `make progress` | 3–6 | ongoing |

## Notes per package

(Each package appends what the next person needs: where it stopped, what is
stubbed, what is known not to match and why.)

### 1. tools

Done. What there is now:

- `guides/` (02, 03, 05, 07, 09, 10, 11, 12, 13, README), adapted to NOLF2;
  01, 04, 06 and 08 were left out (README says why). NOLF1 worked examples
  are kept where the lesson is general and labelled "from NOLF1's engine".
- `tools/tgt.py`: per-target facts from `progress/targets.py`. uncovered,
  asmweb, vtabcheck, o2gap, decoded, decodedlt, nearscan, layoutscan,
  tagmap, fndiff and sdkvtab take a target (`Lithtech`, `server`, ...) and
  read our objects from the link's `.rsp`, so they work as soon as the
  engine links through build.mk's `binary` macro. `libfndiff.py` is not
  adapted (NOLF2 ships no prebuilt library; tools/README.md says so).
  `agentwt.sh` makes worktrees the way this plan does (branch `<name>`,
  hard links).
- `progress/engine/`: `mac-functions.csv` / `mac-server-functions.csv`
  (every Mac engine and server function, demangled, with its Jupiter file
  and the evidence) and `mac-modules.md` (per module and file; the Jupiter
  files the Mac build lacks, the Mac classes Jupiter lacks). Use them to
  decide which Jupiter files exist in 2002 and which functions to drop.
  Regenerate with `tools/macinventory.py --jupiter ../fear/Dev/Source`; it
  needs the Mac release, which this repo's `rez/games` does not have:
  `rez/fetch-isos.sh nolf2-mac-usa && rez/install-games.sh nolf2-mac-usa`.
- `progress/engine/Lithtech-iat-calls.csv`: the import behind each of the
  1,514 redirected `call [IAT]` sites (all paired with the demo).
  `tools/demoimports.py extract|map|plain`; `plain` gives
  `out/mpdemo/Lithtech-readable.exe` to read with exedump/objdump. Shifts in
  the encrypted pages: retail = demo + 0x40 to 0x565250, + 0x30 to
  0x5675e0, - 0x10 after.
- `progress/targets.py`: Lithtech.exe and server.dll have `built=`
  `src/Engine/built/Final/Lithtech/Lithtech.exe` and
  `.../server/server.dll` (optional: all unwritten while absent),
  `third_party=["d3dx8.lib"]`, `cites` with `cited_src=["src/Engine/runtime"]`,
  and Lithtech's `purecall` (0x567616). If the skeleton names its projects
  or outputs differently, change `built=` only.
- `build/env.sh`: `run_cl` (`CL_REV=`), `run_link`, `run_lib`, `run_rc`.
  `build/engine.sh <project> [link|objs|verify]`, `<project>-one <file.cpp>
  [symbol]`, `server test`: generic over build.mk's projects (it reads
  dsp2mk's `P_<project>_OUT`/`_OBJS`), so it works for `Lithtech` and
  `server` once Engine.dsw is included; until then it says so. Tested on
  snddrv.

Not done: `server test` is untested (no server project yet); the second
`app` range question (`nolfsrc-process.md` 3.3, item 7) waits for our own
`.map`; no `*-screen-exclude.csv` or `-decoded-map.csv` exist for the
engine yet; exedump.py on the retail exe still shows `call [0x607ec0]`
(read the `plain` copy instead).

### 2. skeleton

**Where things are.** `src/Engine/runtime/` is the Jupiter runtime, imported
as it was (LF line endings) in one commit, then back-ported; RezMgr is
Jupiter's, in `src/Engine/libs/rezmgr/` (Monolith's
`Source/Engine/libs/rezmgr`; it has the whole library, about 126 methods
against retail's 129 functions, where nolfsrc's is NOLF1's "lite" one).
Only the files the retail engine links were taken, with the headers they
include. Not imported, as retail lacks them: `customfontfilemgr`,
`dshowvideomgrimpl`, `InputSim`, `ltrendermgr_impl`, `lttexturestring`,
`texturestring(image)`, `memorywatch`, `watermark` (eval only),
`systeminfo`; in render_a `LTEffect*`, `lteffectshadermgr`,
`ltpixelshadermgr`, `LTShaderDeviceStateImp`, `ltvertexshadermgr`,
`rendererframestats`, `rendertarget(mgr)`, `SimD_*`, `precompile.cpp`; in
ui `cuidebug`; the `esd`, `info` and `physics` modules (one physics header,
`lt_collision_mgr.h`, is included), FreeType, Lib_DShow, Lib_Info, zlib.

**Projects** (`src/Engine/runtime/winbuild/Engine.dsw`; build.mk's
`ENGINE_WANTED`; targets `Lithtech`, `server`, and the libraries by name):

| project | file | output (`src/Engine/built/Final/`) | flags |
|---|---|---|---|
| Lithtech | `winbuild/lithtech/Lithtech.dsp` | `Lithtech/Lithtech.exe` | `/MD /W3 /GX /O2`; `DE_CLIENT_COMPILE DE_LOCAL_SERVERBIND DIRECTENGINE_COMPILE DSNDMGR_NO_MFC MODEL_SUPPORT_ABC` |
| server | `winbuild/server/server.dsp` (+ `server.def`) | `server/server.dll` | `/MD /W3 /GX /O1`; `_USRDLL DE_SERVER_COMPILE DIRECTENGINE_COMPILE STDLITH_ALLOC_OVERRIDE LT15_COMPAT NO_PRAGMA_LIBS` |
| D3DRender | `render_a/src/sys/d3d/D3DRender.dsp` | `D3DRender/D3DRender.lib` | `/MD /W3 /GX /O2` |
| Lib_UI | `ui/Lib_UI.dsp` | `Lib_UI/Lib_UI.lib` | same |
| Lib_ILTSound | `sound/Lib_ILTSound.dsp` | `Lib_ILTSound/Lib_ILTSound.lib` | same |
| Lib_RezMgr | `../libs/rezmgr/Lib_RezMgr.dsp` | `Lib_RezMgr/Lib_RezMgr.lib` | same |
| ltmem, Lib_StdLith, Lib_Lith | `src/libs/` (built by the snddrv and game workspaces' rules: `dsp2mk.py --have`) | | theirs |

All: `WIN32 NDEBUG _WINDOWS _MBCS _FINAL __D3D __D3DREND`, STLport 4.0 first
on the include path, then the runtime's directories, NOLF2's
`src/Engine/sdk/inc` (and `physics/`), `src/libs/stdlith`, `src/libs/lith`,
RezMgr. Each project lists its files flat, in the retail link order
(`anatomy.md`): the exe `controlfilemgr`, the rest alphabetically, then the
interface implementations (`icommandlineargs` ... `client_iltvideomgr`); the
dll alphabetically, then its interface implementations; the renderer and UI
in the order their retail functions start. The exe links `d3dx8.lib` first,
then ltmem, D3DRender, Lib_ILTSound, Lib_RezMgr, Lib_UI, Lib_StdLith,
Lib_Lith. None of that order is proven yet. The exports already match
retail's (`CreateServer` @1, `DeleteServer` @2, `SetMasterDatabase` @3;
the exe's `LTGetILTMemory` and `SetMasterDatabase`). One project cannot
have two sources with the same name (one intermediate directory), so the
stubs are `nolf2src_<module>_stubs.cpp`.

**Excluded files: each module's worklist.** A file that does not compile
is kept in its project, marked `# PROP Exclude_From_Build 1` (inside an
`!IF "$(CFG)" == "<project> - Win32 Final"` block in its `Begin Source
File`); what the link needs of it is a stand-in in the module's
`nolf2src_<module>_stubs.cpp`, which does nothing and fails. To take one on:
remove the exclusion, make it compile, delete its block of stubs.

| module (package) | excluded | why (first errors) | stubs |
|---|---|---|---|
| client (4) | `client/src/clientde_impl.cpp` | `ltrendererstats.h`; Jupiter's ILTClient additions (renderer stats, vertex/pixel shaders, texture effect vars, render groups) | `client/src/nolf2src_client_stubs.cpp`: `CreateLTClient`, `ci_Term` |
| client (4) | `client/src/sys/win/winclientde_impl.cpp` | `ltgraphicscaps.h`; `cis_QueryGraphicDevice` (D3D9 caps) | the `g_Screen*`/`g_*Color` globals, `cis_RendererIsHere`, `cis_RendererGoingAway`, `cis_InternalCreateSurface` |
| client (4) | `client/src/sys/win/winconsole_impl.cpp` | includes render_a headers (`d3dx9.h`) | `CConsole`, `CConIterator`, `CConHistory`, `CConCommandBox`, `g_Console` |
| client (4) | (memorywatch.cpp, not imported) | `clientmgr.cpp` calls `mw_ResetWatches`, `soundbuffer.cpp` counts `g_dwSoundMemory`: take them out | `mw_ResetWatches`, `g_dwSoundMemory` |
| kernel (4) | `kernel/src/sys/win/binkvideomgrimpl.cpp` | `d3d9.h`; Jupiter compiles Bink only under `IHAVEPURCHASEDBINK`, retail loads `Binkw32.dll` at run time | none needed (`videomgr.cpp` makes no Bink player without it) |
| render_b (6) | `render_b/src/sys/d3d/d3ddrawprim.cpp` (exe) | render_a headers (`d3dx9.h`) | none needed yet (`d3dtexinterface.cpp` compiles) |
| model (3) | `model/src/model_load.cpp` (both) | `ModelOBB_Depricated`, Jupiter's ModelOBB | `model/src/nolf2src_model_stubs.cpp`: `Model::Load` |
| server (3) | `server/src/s_net.cpp` (both) | `LTAnimTracker::m_bDirty`: `g_CV_ModelOnlyUpdateDirtyTrackers` writes a bool per tracker, a protocol change; check the client's reader (`shellnet.cpp`) too | `server/src/nolf2src_server_stubs.cpp`: `CServerMgr::NewConnectionNotify`/`DisconnectNotify`/`HandleUnknownPacket`, `WriteAnimInfo`, `FillPacketFromInfo`, `SendServerMessage`, `SendToClient`, `CreateServerEvent`, `FillSoundTrackPacketFromInfo`, `WriteEventToPacket`, `ProcessIncomingPackets`, `InitServerNetHandlers` |
| world (3) | `world/src/fullintersectline.cpp` (both) | `ModelOBB::m_Radius`, `INTERSECT_MODELOBBS`, `FLAG2_USEMODELOBBS`, `IntersectInfo::m_hNode` (Jupiter's model-OBB tests). Also: `i_BoundingBoxTest` is `inline` there but `moveobject.cpp` calls it, which VC6 does not allow | `world/src/nolf2src_world_stubs.cpp`: `i_BoundingBoxTest`, `i_IntersectSegment`, `g_Ticks_Intersect`, `g_nIntersectCalls` |
| ui (5) | (done by package 5: compiled, no stubs) | | |
| render_a (6) | all 65 but `texturescriptinterpreter.cpp` | Direct3D 9 throughout (`precompile.h`, `d3d_defs.h`, `d3d_device.h`, ... include `d3d9.h`/`d3dx9.h`/`dxerr9.h`) | `render_a/src/sys/d3d/nolf2src_render_stubs.cpp`: `rdll_RenderDLLSetup` (sets nothing up: no renderer), `rdll_GetSupportedModes`, `rdll_FreeModeList`, the `D3DRenderStyles` implementation pointer |
| libs (5) | (done by package 5: `LTMemConsole` is ltmemstats.cpp's, a second object in ltmem.lib) | | |

Everything else in the lists compiles as imported, or after the back-port
commit (lith's `CBaseList`, which Jupiter renamed `CLTBaseList`; Direct3D 8
in `d3dddstructs.h` and `renderstruct.h`; no shader pointers in models;
no tracker dirty flag in ILTModel; no DirectShow in `videomgr.cpp`).
Compiling is not matching: none of it has been compared with retail yet.

**SDK.** The engine compiles against NOLF2's `src/Engine/sdk/inc`, never
Jupiter's (`lterror.cpp`, `ltmodule.cpp`, `ltobjref.cpp` and
`ltquatbase.cpp` are NOLF2's copies). What the imported code wants that
NOLF2's SDK lacks: the headers `ltrendererstats.h` (clientde_impl),
`ltgraphicscaps.h` (winclientde_impl), `LTFontParams.h` (cuivectorfont),
`iltrendermgr.h` (render targets, not built); and, in headers both have,
Jupiter's later members: ILTClient's renderer-stats and shader methods,
`CUIFont`'s getters and `ILTFontManager::CreateFont`, `LTAnimTracker::m_bDirty`,
`ModelOBB` and the model-OBB intersect flags. Each is to be taken out of the
engine, not added to the SDK: the game DLLs are built against NOLF2's.

**Left for the module packages, besides the worklists.** What retail has and
Jupiter does not (`fear-mapping.md`): NOLF2's `pixelshadermgr.cpp` and the
D3D8 vertex-shader path (6); the NOLF1-era saveio/savrest code in
server.dll's game_serialize (3); `ltlibraryloader.cpp` (2004) is kept,
compiled, as Jupiter's code calls it, but is not 2002's. Nothing of the
engine is in the game yet (build/all.sh checks both are built and keeps
the retail ones, as for SndDrv.dll), and neither is scored
(`progress/targets.py` is package 1's).

### 5. libs

Done: nothing of the libraries is stubbed any more, and both images link
them in retail's order. What was found and changed:

- **Flags.** Retail compiled Lib_UI, Lib_ILTSound and Lib_RezMgr with
  `/O2 /Ob2` (auto-inlining), as Monolith's own StdLith and Lith projects
  say: retail has none of the `_$E2: jmp _$E1` initializer thunks `/O2`
  alone leaves in every object, small helpers (`DisplaySoundSysError`,
  `CUIBitmapFont::BuildFontTable`, `CUIVectorFont::Term`, the font
  writers) exist only inlined, and RezMgr's accessors are inlined into
  their callers. **The same evidence holds for the engine's own
  projects**: our `Lithtech.exe` still has 1,411 such 5-byte thunks
  unplaced, `server.dll` 700, retail none. `Lithtech.dsp`/`server.dsp`
  (packages 3, 4) are very likely `/Ob2` too (`server.dll` `/O1 /Ob2`?):
  worth one experiment before matching much more there. Lib_UI is built
  without STLport: `cuivectorfont.cpp`'s `std::string` calls MSVCP60.dll
  in retail, the only code in `Lithtech.exe` that does.
- **ltmem.** One flavour serves all three images: retail's `Lithtech.exe`
  and `server.dll` call `malloc`/`free` from ltmem.obj through import
  thunks, as SndDrv.dll does (no `/MD`; LNK4098 is retail's too).
  `LTMemConsole` is `ltmemstats.cpp`'s (a second member, after ltmem.obj
  in both images; the skeleton's note that it was ltmem.cpp's was the
  message text), reading ltmem.cpp's `g_bLTMemInitialized`. SndDrv.dll
  never references it, so its objects and score are unchanged.
- **Fonts** (`cuibitmapfont`, `cuifont_impl`, `cuifontmanager`,
  `cuivectorfont`): back-ported to NOLF2's `cuifont.h` (int8 metric
  getters/setters; the members stay uint8, retail shifts them unsigned)
  and `iltfontmanager.h` (no `LTFontParams`: GDI is always asked for
  FW_NORMAL, ANSI_CHARSET, OUT_TT_PRECIS, ANTIALIASED_QUALITY). 2002's
  code, from the retail bytes: no default font map, the base class frees
  nothing but the shared draw string, the bitmap font frees its own
  table, `CreatePropFont` with byte-sized u/v, no `GreenDot`/TGA debug
  output. Polystrings: `ApplyFont` has no newline case, `Parse` scales
  every letter the same way. Nearly all of this is now byte-identical
  (`CreateFontTextureAndTable`, 2262 bytes, included); the
  texture-only `CUIBitmapFont` constructor is three stack slots off
  (declaration order does not move them).
- **Link order.** `Engine.dsw` links Lib_StdLith before Lib_UI: retail
  has StdLith's members between RezMgr and the UI (exe
  0x557960..0x558b30; dll after RezMgr, 0x1004b750). Lib_Lith's few
  out-of-line members are much later in the exe (0x572a50, after
  D3DX's second block), so it stays last. The libraries in retail's
  exe: D3DX 1, ltmem (0x4c1240: ltmem.obj, ltmemstats.obj), renderer,
  sound (from 0x553aa0, not 0x553ca0), RezMgr (from about 0x554680, not
  0x555980: rezmgr.obj, rezhash.obj, rezfile.obj), StdLith, UI.
- **Score** (against the master recording): `Lithtech.exe` 2,441 -> 2,575
  identical (+22 KB), unplaced 3,177 -> 2,855; `server.dll` 1,877 ->
  1,909, unwritten 107 -> 104, unplaced 1,366 -> 1,318; SndDrv.dll
  unchanged. In the libraries' ranges only a handful of rows are not
  identical or small. **`make progress` fails on one count**:
  `Lithtech.exe`'s unwritten functions, 2,465 -> 2,484. No identical
  function is lost. The increase is the scorer's placement by object and
  link order, which pairs leftover functions of ours (stubs, initializer
  thunks) with shipped rows: the libraries' ranges went down (UI 36 -> 6,
  RezMgr 15 -> 3), the stubbed renderer's rows went up (1,302 -> 1,348, as
  the stubs and thunks it was paired with went away or got matched) and
  the core's 1,110 -> 1,121 (the removed mem stub object). It needs
  recording with `ACCEPT_LOSSES=1` at the merge.

Left, and for other packages:

- `shared/src/debuggeometry.cpp` (package 4): `CDIDebugText::Render`
  constructs a `CUIPolyString`; that reference is why our link pulls
  cuipolystring.obj first. Retail pulls cuifontmanager.obj first and
  has cuipolystring.obj after the vector font (0x55d210), so 2002's
  debug text did not use a polystring (probably the commented-out
  `r_GenericTextPrint`).
- `ltmemheap.obj` (Jupiter's `libs/ltmem/ltmemheap.cpp`: the
  `g_arySimpleHeaps[4]` and `g_GeneralHeap` objects, their initializers
  and destructors) is linked in retail but not here: in `server.dll`
  right after ltmemstats (0x10048b60..0x10048df8), in `Lithtech.exe` in
  the middle of the renderer's range (0x51e990..0x51ec20). The exe's
  placement suggests D3DRender.lib carried it (a lib project can merge
  another .lib) or the renderer referenced the heap; what referenced it
  in the dll is unknown. Not added: nothing here references it yet.
- Lithtech.exe's UI from 0x565000 (cuibutton ... cuiwidget) is in
  SecuROM's pages: scored `encrypted`, our functions there count as
  unplaced, but they match the demo's plaintext (exematch on
  `out/mpdemo/Lithtech-readable.exe`).
- The interface-registration initializers (56 and 26 bytes) are
  identical up to relocations in every object that defines an
  interface, so the scorer places ours at the first copy it finds:
  0x558b30/0x558b70, 0x559fc0, 0x55a020/0x55a060 stay unwritten. A
  relocation-aware tie-break in `progress.py` (tools) would place them.
- Not matched: the RezMgr utilities (`rezutils.cpp`: the rez compiler,
  never linked), StdLith's `g_DefAlloc` initializer (0x557d20/0x557d40)
  and the object before the UI (0x558b20).
