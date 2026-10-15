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
| 3 | `server`: `server.dll` compiles, links and loads (`server/`, `shared/`, `world/`, `model/`, `kernel/net`, `kernel/io`) | 2 | done: nothing stubbed; the built dll hosts a level in NOLF2Srv.exe, the built exe plays C01S01 |
| 4 | `client`: the exe's own objects (`client/`, `kernel/src`, input, DirectMusic, video, console) with the server objects at `/O2` | 2 (3 helps) | done: no client stubs, Bink at run time; Lithtech.exe is `/O2 /Ob2` without `/GX`; the built exe reaches the main menu under Wine (`+DisableSound 1`) |
| 5 | `libs`: `rezmgr`, `stdlith`/`lith`, `ltmem`, `iltsound`, `ui` (Lib_UI) | 2 | done: no stubs left; fonts and the mem command as 2002 had them; the libraries' flags and link order as retail's |
| 6 | `render`: `render_b` (drawprim, texinterface) and `render_a` back-ported from D3D9 to D3D8 | 2 | done: all of it compiles for D3D8 and links; a device comes up under Wine (tools/rendertest); not yet seen in the game |
| 7 | `boot`: the built `Lithtech.exe` in the game under Wine: to the menu, then a level; snddrv/ServerDir/ltmsg built ones in | 3–6 | done: every engine binary in the game is built (no retail engine left); `make test` plays from the main menu into C01S01 with sound (null ALSA device); `make modern` builds and runs the same |
| 8 | `modern`: the modern build of the engine (FFmpeg Bink, fixes) | 7 | done: no RAD binary in the modern build (Bink on FFmpeg; NOLF2 has no Miles); the launcher installed in both builds; Hor+, widescreen modes, the launcher's server name (`docs/MODERN.md`) |
| 9 | `match`: byte-matching passes per module, ratcheted by `make progress` | 3–6 | ongoing |
| 9a | `net`: multiplayer with the built engine (dedicated server and client over UDP); kernel/net and the server-side modules matched | 3, 7 | done: our Lithtech.exe joins our NOLF2Srv.exe/server.dll (and retail's server.dll) over loopback, `tools/mptest.sh`; server.dll +102, Lithtech.exe +104 identical |
| 9b | `rendermatch`: render_a/render_b structures and file formats against retail, the renderer in the game, byte matching | 6, 7 | done: layouts and loaders fixed (below); Lithtech.exe 5,509 -> 5,792 identical |
| 9c | `cshell`: the game DLLs (`CShell.dll`, `Object.lto`, `ClientFx.fxd`) against retail: what the source release does not have of 1.3 | 9 | done: one layout (CInterfaceTimer) was most of CShell's gap; CShell.dll 5,234 -> 5,414 identical (91.7% -> 98.4% of its bytes), Object.lto 9,253 -> 9,254; the rest is listed below |
| 10 | `release`: public archives built by GitHub Actions, as nolfsrc does (its commits "Install scripts that copy the game's data out of the player's discs", "Package each game directory as a -private and a -public archive", "Build switches for CI: NOLF_ARCHIVES and IMAGE_BUILD", "CI: build the four public archives on GitHub Actions", "CI: check the release build for byte regressions", "CI: upload each archive unzipped") | 7, 8 and everything ported | done: -private / -public archives, install scripts from the player's own disc images (EU or USA) and 1.3 update, linux-run*.sh, the workflow as nolfsrc's now (prepare + four parallel jobs; not yet run on GitHub); ServerDir.dll's score made reproducible by package 11 |
| 11 | `bugs`: the variants (debug, modern, modern-debug) checked to build the whole game, engine included, and to play; `docs/RETAIL_BUGS.md`; the safe fixes in the modern build | 7, 8 | done: every variant builds every binary with its define and passes the playtest; 48 entries listed, 23 of them fixed in the modern build (three only on one side: see the notes) (M-G5..M-G16, M-L3, M-E7..M-E12) |
| 12 | `modernizer`: the NOLF 2 Modernizer (haekb) inventoried change by change in `docs/MODERN.md`, its fixes and features reimplemented in the modern build, its known issues answered | 8, 11 | done for the most part: no disc / CD key, its retail crash fixes, widescreen menus/HUD/FOV/zoom, mouse look (M-E3), frame limiter, windows, focus, display options (FOV, frame limit, antialiasing, 4:3 cinematics), wheel, fps counter, anisotropy, scope margins, the dedicated server without the registry; left: the console (M-E5), Internet play (M-E6), controllers (M-G47), jukebox (M-G46), the damage flash's width (M-G38) |
| 13 | `mouse`: why mouse look jumps about (a player's report, modern build on a desktop under Wine) | 7 | done: retail's `input_ReadInput` (Lithtech.exe 0x4319b0, byte-identical in both builds) adds a look axis's last event again per pass and per frame; MODERN.md M-E3 (with M-E4's frame limit) is the fix; `docs/RETAIL_BUGS.md` has it and the packages' retail bugs |
| 14 | `xinput`: controller support in the modern build (docs/MODERN.md M-G47 and the Modernizer's known issue K8), as nolfsrc's P7: an XInput pad, DirectInput joysticks removed | 8, 12 | done: `##gamepad` (M-E20), no DirectInput joysticks (M-E21), sticks, menus, cut-scenes and decisions read by the client (M-G47, M-G60, M-G61), the Controller screen (M-G62), a retail binding bug fixed (M-G63); tested with a simulated pad (`tools/playtest-pad.txt`); rumble and button prompts not started (M-G64, M-G65) |
| 15 | `winmode`: window modes in the modern build -- full screen, a window, or a borderless window at the desktop's resolution -- as nolfsrc's M-P1-22: the engine, `render_a`, the Display screen, the launcher's Display dialog, the run scripts | 8, 12 | done: `Windowed` + `WindowMode` (docs/MODERN.md M-E30, M-G70, M-L5), M-G40's toggle folded in; tested under Xvfb in each mode and switched from the menu and the launcher; `make progress` unchanged |
| 16 | `fps`: 300 frames a second in single player at real speed, as nolfsrc's M-P1-23 (its 0dd4bf4, d171625, 9780977): what goes wrong at high frame rates found, measured and fixed in the modern build, then M-E4's limit raised from 60 | 8, 12 | done: the server tick (AIs), the player's walk and crouch, particle/line systems, aim perturb, fire sparks, debris rest; MaxFPS 300, 60 in multiplayer (docs/MODERN.md M-E4; 4 `docs/RETAIL_BUGS.md` entries) |

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
| render_b (6) | `render_b/src/sys/d3d/d3ddrawprim.cpp` (exe) | render_a headers (`d3dx9.h`) | none needed yet (`d3dtexinterface.cpp` compiles). Done: in the build (6. render) |
| model (3) | `model/src/model_load.cpp` (both) | `ModelOBB_Depricated`, Jupiter's ModelOBB | `model/src/nolf2src_model_stubs.cpp`: `Model::Load` |
| server (3) | `server/src/s_net.cpp` (both) | `LTAnimTracker::m_bDirty`: `g_CV_ModelOnlyUpdateDirtyTrackers` writes a bool per tracker, a protocol change; check the client's reader (`shellnet.cpp`) too | `server/src/nolf2src_server_stubs.cpp`: `CServerMgr::NewConnectionNotify`/`DisconnectNotify`/`HandleUnknownPacket`, `WriteAnimInfo`, `FillPacketFromInfo`, `SendServerMessage`, `SendToClient`, `CreateServerEvent`, `FillSoundTrackPacketFromInfo`, `WriteEventToPacket`, `ProcessIncomingPackets`, `InitServerNetHandlers` |
| world (3) | `world/src/fullintersectline.cpp` (both) | `ModelOBB::m_Radius`, `INTERSECT_MODELOBBS`, `FLAG2_USEMODELOBBS`, `IntersectInfo::m_hNode` (Jupiter's model-OBB tests). Also: `i_BoundingBoxTest` is `inline` there but `moveobject.cpp` calls it, which VC6 does not allow | `world/src/nolf2src_world_stubs.cpp`: `i_BoundingBoxTest`, `i_IntersectSegment`, `g_Ticks_Intersect`, `g_nIntersectCalls` |
| ui (5) | (done by package 5: compiled, no stubs) | | |
| render_a (6) | (done by package 6: all of it compiles for D3D8, no stubs) | | |
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

### 3. server

Done: nothing of server/, shared/, world/, model/, kernel/net, kernel/io
is stubbed; `server.dll` 1,909 -> 2,399 identical functions, 208,508 ->
272,709 identical bytes (unwritten 104 -> 17, unplaced 1,318 -> 1,182).
What was found and changed:

- **Worklist.** `s_net.cpp`: no per-tracker dirty bit in the model info
  (retail's WriteAnimInfo, 0x10027e50, writes none; it is identical
  now), so no `ModelOnlyUpdateDirtyTrackers` console variable (retail's
  table has 105 entries, ours now too) and, to keep the exe's client and
  server speaking one protocol, no dirty bit read in the client's
  `shellnet.cpp` ReadAnimInfo either (a client/ file: the only edit
  outside these modules besides the renderer's, below). `model_load.cpp`:
  `MODEL_OBB` is 0 (model.h; retail skips OBBs with "not supported in this
  version of exe", the Mac build's OBB methods only fail), no "model
  pieces exceeds" message. `fullintersectline.cpp`: no model-OBB tests,
  `i_BoundingBoxTest` out of line, and none of Jupiter's
  `#pragma optimize("", off)` (retail's code is the project's /O1) or
  tick counter: everything in it matches but `i_IntersectSegment` (608
  vs 572: retail calls the vector constructor where we inline it).
- **Flags.** `server.dsp` is `/O1` without `/GX`: retail's own objects
  have no EH frame (the 46 `fs:[0]` uses are rezmgr's and stdlith's).
  exematch places 2,313 functions instead of 2,022. `/O1 /Ob2` was
  tried (PLAN 5's hint): it removes the `_$E` initializer thunks (unplaced
  1,318 -> 340) but loses 86 recorded identical functions and ~30 KB, so
  the thunks come from something else (not found).
  `progress/COMPILERS.md` has it.
- **game_serialize.** The "NOLF1-era saveio/savrest code" is not separate
  code: the dll's game_serialize region is Jupiter's file. What differed:
  NOLF2 keeps the save buffer in a `std::vector<uint8>` (resized per
  message, swapped empty at the end of a save or restore), objects over
  0x80000 bits are "suspicious". sm_SaveObjects/RestoreObjects identical,
  the rest a few bytes off (register choice).
- **CPacket_Read** (packet.h): NOLF2's constructors do the work
  themselves and the short ones delegate with a placement new (retail's
  out-of-line constructors at 0x1000b208/b60e/b634 show it); Jupiter's
  Init made VC6 inline the constructors everywhere and so stop inlining
  what retail inlined (`SendAllObjectsUnguaranteed` matched as soon as
  this changed). The 3-argument constructor is 2 bytes off.
- **Renderer** (render_a, `d3d_renderblock.h`): `SRBVertex` without
  Jupiter's tangent and binormal: retail reads 44 bytes a vertex. This was
  why the built exe stayed on the loading screen (a 1 GB allocation from
  misread render blocks, "Out of memory"; s_net was not the cause).

**What runs.** `build/engine.sh server test` (loads, CreateServer /
DeleteServer). `tools/srvtest.sh` (new): the built NOLF2Srv.exe with the
built server.dll hosts the first co-op level (CP_c01s01) under Xvfb and
keeps running, as with the retail dll; deathmatch needs a DMMissions.txt
the game's host screen writes. The built Lithtech.exe (game dir from
`make game`, exe copied over, `+DisableSound 1`, Xvfb screen 640x480 and
`++windowed 1` 640x480) loads C01S01, shows the briefing, plays the intro
and leaves the player in control with the HUD. The only load error,
"FX\WATERFALL2.LTB ... Invalid Header", is retail's too (the file is
model version 18, the minimum is 23). No client has joined the dedicated
server yet: the network protocol between our exe and dll is untested.

**Score notes for the merge.** `make progress` fails on one exe function,
0x4aa8b0 `CLTCommonServer::SetObjectFlags` (310 bytes, two loads in
swapped order): it matches only with both Jupiter's packet.h and
`MODEL_OBB 1`, either alone is not enough, so it is VC6's register
tie-break, not the function's source. It needs ACCEPT_LOSSES=1.

**Left.**
- The kernel/net UDP driver is the biggest unmatched code
  (`HandleUnconnectedData`, `ReallyJoinSession`, `WriteGuaranteed`,
  `HandleGuaranteed`, ...): check it against retail for protocol drift
  (fear-mapping notes retail's `Term2` takes one argument) before
  matching it; then client-to-dedicated-server joins.
- Near functions: `Model::Load` (+73), `sm_CreateNextObject` (+6),
  `sm_SaveObjectData` (+14), `sm_RestoreNextObject` (+12, registers),
  `i_IntersectSweptSphere`, `CPlayerMover::CollideWithAABB`; the
  `_$E` initializer thunks (1,100 unplaced rows).

### 4. client

**State.** Nothing of the client is stubbed: `clientde_impl.cpp`,
`winclientde_impl.cpp`, `winconsole_impl.cpp` and `binkvideomgrimpl.cpp`
build, and `nolf2src_client_stubs.cpp` is gone. What was taken out, and
why (the commits give the retail evidence):
- ILTClient: Jupiter's renderer stats, vertex/pixel shaders and
  effect-shader IDs (not in NOLF2's SDK); `QueryGraphicDevice` and the
  "d3ddevice" engine hook (neither string nor code in retail).
- The console is never drawn in retail (no `con_Draw`, nothing reads
  `ConsoleAlpha` but `CConsole::Init`, the ILTDrawPrim holder is unread),
  so its drawing routines (D3D9 device calls), `con_Draw`/`con_DrawSmall`,
  `MaybeDrawConsole` and `r_GenericTextPrint` are gone.
- Bink: always built, `Binkw32.dll` loaded at run time, ported to D3D8
  from retail (0x4036c0..0x404430: `BinkDX8SurfaceType` picks the copy
  format, `SetVertexShader(FVF)`); the few BINK declarations are in
  `binkvideomgrimpl.h`, no RAD SDK. `CClientMgr::Init` always asks for
  "BINK".
- `memorywatch.cpp` is back (the skeleton thought retail lacked it):
  `mw_ResetWatches` is 0x447f70, `g_dwSoundMemory` is counted by
  soundbuffer.cpp; only `mw_ShowMemoryWatches` (under `#ifndef _FINAL`)
  drops out.
- `sound/src/iltsound.h` (shared with Lib_ILTSound): no `CommitDeferred`,
  as snddrv.dll's header says; with it the engine called the wrong
  driver slots.
- CClientMgr: no `m_pOldShell`/`m_bInCurShellUpdate` (retail offsets).

**Flags (the big one).** `Lithtech.dsp` is `/O2 /Ob2` and *no* `/GX`
(`progress/COMPILERS.md`): the holders' CAPIHolder constructors are
expanded, and none of retail's 634 EH-frame prologues is in the exe's
own objects (all in the libraries). Lithtech.exe went 2,441 -> 3,881
identical on this branch before the merge of render/libs, 5,342 (71.1%)
after it. `make progress` FAILs only on three recorded functions:
0x45889f (a 27-byte function of ours matching mid-function: a false
pairing), 0x48d4f0 (`udp_SaveIPClientPortMRU`, server package: retail
calls it from one place and keeps it out of line, Jupiter calls it from
two and /Ob2 inlines it) and 0x4af1d0 (`CSoundMgr::Get3DProviderLists`:
retail does not inline `SoundSys`, ours does -- a source difference not
found yet). The coordinator's progress-update has to accept them
(ACCEPT_LOSSES=1). ServerDir.dll's unwritten count also moved 129 -> 131
in this run; nothing here touches it.

**Startability** (scratch game dir: the `make game` directory with the
built Lithtech.exe; Xvfb screen 640x480, `++windowed 1` 640x480, as the
renderer needs a display mode of the window's size): command line, rez
stack, ltmsg/ServerDir/cshell/cres loaded, D3D8 device up, snddrv.dll and
DirectSound loaded, DirectMusic up, the main menu drawn. Sound: the
driver's Init fails in the container ("Failed to initialize sound driver
'snddrv.dll'", a message box that stops the game) -- the container has
no audio device; run with `+DisableSound 1`. With `+runworld
Worlds\RetailSinglePlayer\C01S01` it shows the loading screen and stays
there after 90 s (the server's s_net stand-ins, package 3; not
investigated). The version line reads "LithTech build
4294967295.4294967295": retail has no RCDATA 12346 either.

**Left.**
- Other packages' headers keep Jupiter's members the exe's code reads at
  retail's offsets: `m_nEffectShaderID` in LTParticleSystem, LTPolyGrid,
  LTVolumeEffect, SpriteInstance (`world/src/de_objects.h`, objectmgr.cpp
  sets them), SharedTexture 12 bytes too big (`de_world.h`, retail
  sizeof 0x68), ModelInstance 8 bytes too big (0x5dc in retail).
- The interface holders' initializers (76/49-byte pairs, about 150 of
  them) still call the CAPIHolder constructor where retail expands it,
  even with /Ob2 (and even with `inline` on it, tried): not found why.
- `lithtech.rc`: icons differ (retail has five images in another order,
  the cursors are numbered 6 and 7) -- 18 of 28 resources identical.
- Many size-exact nears in clientmgr/soundmgr/dmusic remain; shellnet's
  2002 function order differs from Jupiter's (retail has the CClientShell
  methods first).

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

### 6. render

**State.** Every render_a file and render_b's `d3ddrawprim.cpp` compile
for Direct3D 8 and are in the build (`D3DRender.dsp`, `Lithtech.dsp`); the
stand-ins are gone and `Lithtech.exe` links. A device comes up under Wine:
`tools/rendertest/` (build.sh, run.sh, in the build container after
`build/engine.sh Lithtech link`) links a harness with Lithtech.exe's
objects, fills the engine's `g_Render` with its own callbacks and brings
the renderer up windowed: modes listed, device created (HAL), frames
cleared, a surface blitted plain and optimized, gouraud and textured
quads drawn through ILTDrawPrim, all correct on screen. The game itself
does not reach the renderer yet: `CClientMgr::Init` crashes on the null
font manager (Lib_UI stand-in, 5) and the stubbed `CreateLTClient` (4)
before `r_InitRender`. World, model, sky, polygrid, particle, sprite and
glow drawing are compiled and compared with retail but never run.

**What retail showed, and the port follows** (commit messages give the
addresses):
- `g_Device.m_pD3DDevice` is NOLF2's own device wrapper (0x196c bytes:
  174 render states, 8 x 29 stage states, no software-VP slot; retail's
  validity tables), ported as `CDirect3DDevice8Wrapper`
  (`d3d_device_wrapper.*`, retail 0x4c7ae0..). Callers use the D3D8 API
  through it.
- No vertex shaders at all (nothing calls CreateVertexShader); render
  styles that use one are reported ("These are no longer supported.")
  and skipped, as retail does. Jupiter's LTEffect, effect/vertex/pixel
  shader managers, render targets and shader device state are deleted.
- Pixel shaders: NOLF2's `CPixelShaderMgr` (`pixelshadermgr.*`, written
  from retail 0x5095e0..0x509ba0; LTPS-headed .ps files through
  IClientFileMgr) for ps\screenglow.ps, PS\BlurShadow.ps, ps\envbumpmap.ps.
- No DOT3 or effect world shaders (ERenderShader has retail's 18).
- Console variables: retail's 161, in its order, with its defaults (17
  Jupiter ones removed; 32BitTextures and DynamicLight_Backfacing are 0).
- `CD3DDrawPrim` is cut back to NOLF2's 66-slot ILTDrawPrim; CGenDrawPrim
  lost its fog and effect members.
- RenderStruct's layout matches retail's (every slot rdll_RenderDLLSetup
  fills is at retail's offset).

**Per file** (render_a/src/sys/d3d unless said):
- Checked against retail function by function (call sequence, states):
  d3d_device, d3d_device_wrapper, d3d_shell, d3d_init, common_init,
  d3d_renderstatemgr (SetRenderStyleStates), d3d_renderstyle
  (Load_LTBData), d3d_optimizedsurface (Start/EndOptimized2D),
  pixelshadermgr, the d3d_rendershader_* family and d3d_rendershader_base.h,
  screenglowmgr, drawpolygrid, d3d_drawsky, texturescriptinstance,
  d3dmeshrendobj_rigid/_skel/_vertanim, setupmodel, rendermodelpiecelist,
  rendershadowlist, render_b/d3ddrawprim.
- Compared by name/function list (Mac symbols) or only made to compile,
  Jupiter's logic kept: d3d_texture, d3d_surface, d3d_draw, d3d_utils,
  common_draw, common_stuff, d3d_renderworld, d3d_renderblock,
  d3d_renderworld_occluder, drawobjects, tagnodes, memstats_world,
  objectgroupmgr, d3d_viewparams, 3d_ops, aabb, dirtyrect, VertexBuffer-
  Controller (SetStreamSources takes the base vertex index, as the Mac
  signature has it), renderstyle lookup/map, d3d_renderstyleinterface,
  rendererconsolevars, drawsprite, drawparticles(_A), drawvolumeeffects,
  drawlinesystem, draw_canvas, drawlight, drawworldmodel, drawsky,
  drawmodel, modeldebug, modelshadowshader (GetZBias is 8 bytes on the
  Mac: probably a constant in retail, Jupiter's switch kept), devicelightlist,
  relevantlightlist, renderlight, setuptouchinglights, texturescript*,
  shadows/d3dshadowtexture.
- Known deviations, commented in the source: CD3DDrawPrim reads the
  really-close cvars with r_GetParameter where retail calls
  ci_GetConsoleVar (clientde_impl.cpp, not built yet; same behaviour) --
  switch back when it builds; SetCamera passes the new width/height to
  SetViewport (retail passes stale stack values, a bug).

**For other packages.**
- client (4): render_a's and render_b's headers are D3D8 now
  (winconsole_impl.cpp includes them through sysdrawprim.h);
  `GetFrameStats(LTRendererStats&)` is gone from rendererframestats.h
  (clientde_impl.cpp line ~1598 calls it: Jupiter's renderer stats).
  ILTDrawPrim::SetEffectShaderID/SetFogEnable are gone.
- boot (7): retail behaviour kept: windowed mode still needs a display
  mode of the requested size in the adapter's list; Xvfb lists only its
  screen size, so `++windowed 1` at 640x480 on a 1024x768 Xvfb fails
  with "Can't find an appropriate display mode!" (rendertest uses the
  screen's size). Retail's own Lithtech.exe stops at SecuROM's "No
  CD/DVD-ROM drive found." under Wine.
- match (9): `make progress` (before this package's last commits):
  Lithtech.exe identical 2441 -> 3665 (renderer 1372 of ~2020 functions,
  343 KB; drawprim 12), no recorded identical lost, but it FAILs on
  "unplaced functions went up, 3177 -> 4808": the renderer's objects
  are new to the link. `make progress-update` (the coordinator's) records
  it. The renderer is compiled with /Zm200 (VC6's default heap is too
  small for d3d_renderworld.cpp with STLport; no effect on code).

**Left.** Seeing the menu and a level drawn by this renderer (needs 4 and
5); retail comparison of the files listed as only compiled; byte
matching (431 renderer functions are near).

### 7. boot

**Installed.** `build/all.sh` assembles the built `Lithtech.exe`,
`server.dll`, `snddrv.dll` (from `SndDrv.dll`), `ServerDir.dll` and
`ltmsg.dll`; the `retailengine` step is gone from `retailextract.py`, and
the audit fails on any PE file that is neither `built` nor
`THIRD-PARTY` (a stale `RETAIL` manifest row included): 11 built, 5
third-party (binkw32, MFC42, MFC42U, MSVCP60, Msvcrt). Each built binary
was tried against the retail one in the same game directory before it
went in: none is kept retail.
- `ServerDir.dll` crashed on Multiplayer (Internet) > Cooperative: the
  SDK's `LoadDirServerList` passes a null `FILE*` to `fgets` when there is
  no `sierraup.cfg` (the game directory has none; it is the Sierra
  updater's). Retail checks (0x1000c1c6) and returns:
  `src/nolf2src/jupiter/serverdir2-sierraup.patch`. Now it shows the
  directory-server error, as retail's does; the text differs (retail:
  "Error retrieving latest version information
  (WS_ServerReq_NoServersSpecified)", ours the code alone: 1.3 takes the
  status strings from CRes, `IDS_WON_VERSION_*`; the SDK's are
  hard-coded). With the Sierra/WON master servers long gone, nothing
  further can be tested there.
- `snddrv.dll` (built) and the retail one behave the same: driver up,
  DirectSound buffers, the menu and level sounds mixed.

**Sound in the container.** Wine's winealsa needs an ALSA device; the
container has none, so `snddrv.dll`'s Init failed. `tools/playtest.sh`
now writes an `asound.conf` in the run directory (the system
`alsa.conf`, then `pcm.!default { type null }`) and sets
`ALSA_CONFIG_PATH` when there is no `/dev/snd`: Wine picks winealsa
(winepulse has no server), DirectSound mixes into the null device, the
engine runs with sound on. No `+DisableSound 1` anywhere.

**Display.** Full screen (`++windowed 0`) on an Xvfb screen of exactly
the mode (640x480; `PLAYTEST_RES` resizes both): the engine wants a
display mode of the window's size even windowed, and Xvfb lists only
its own; windowed, Wine's frame shrinks the client area to 634x448 and
the page no longer maps 1:1. `PLAYTEST_WINDOWED=1` gives a window,
`PLAYTEST_ARGS` adds engine arguments.

**make test** plays `tools/playtest-newgame.txt` on
`out/nolf2-legacy-release` (out/play/test/): main menu, Single player >
New game > Normal, loading screen and opening cinematic (skipped),
control with the HUD, look, walk, the in-game menu and back. A run whose
`skipcine` never sees the HUD is now judged NO HUD (a failure). Also
passing on the built engine: `tools/playtest-basic.txt` from
`+runworld` C01S01 (move, jump, duck, fire, weapons, F6 quicksave writes
`Save/.../QuickSave`, F9 quickload); its in-game-menu waits went from 2
to 3 s (the menu slides in; at 2 s the second Escape was lost). Bink
movies also play with the retail `binkw32.dll` (`PLAYTEST_ARGS="+DisableMovies 0"`:
the legal screen, the intro movies); the tests keep them off for timing.

**The level stall** (the reason this package was waiting) was the
renderer's 68-byte Jupiter world vertex, fixed in package 3 (merged
here). Before that merge, for the record: with the retail `server.dll`
too it stalled, and a winedbg `bt all` showed the main thread in the
engine's main loop (DirectInput polling) and CShell's loading-screen
thread in its Sleep loop: the load had not failed, the client was
never told it was in the world. The quickest way to see such a hang:
in the container, run the game under xvfb-run in the background, then
`winedbg --command "info proc"` for its Windows pid and
`printf 'attach 0x<pid>\nbt all\ndetach\n' | winedbg` (Wine's own
frames come with source lines).

**Modern.** `make modern` builds the engine with `/D NOLF2SRC_MODERN`
(every engine object's command line has it; there is no
`NOLF2SRC_MODERN` code in the engine yet) and installs it like the
legacy build; `playtest-newgame.txt` passes on
`out/nolf2-modern-release`. For package 8: the modern build still ships
retail's `binkw32.dll` and the Microsoft runtime DLLs: an FFmpeg-based
Bink player as nolfsrc's `ext/` (build/ext.sh, Zig as the
cross-compiler, already in the image) to replace binkw32; whatever
`NOLF2SRC_MODERN` fixes the engine wants (resolutions beyond Xvfb-style
mode lists, widescreen menus as nolfsrc's M-P3-01 and the `modern`
mapping in playtest.sh); `sierraup.cfg`-free server listing (the WON
directory servers are dead).

**Score.** `make progress` (check): Lithtech.exe 5,342 -> 5,509
identical, server.dll 1,909 -> 2,399, ServerDir.dll 201 -> 207 (the
patch above matches retail's). It FAILs on two counts, neither from this
package: `sub_4aa8b0` (`CLTCommonServer::SetObjectFlags`, package 3's
known register tie-break) and ServerDir.dll unwritten 129 -> 131 (already
seen by package 4, before any change here). The coordinator's
progress-update needs `ACCEPT_LOSSES=1`.

**Left.** A client joining a dedicated server (ours or retail's) and
LAN play; the launcher `NOLF2.exe` is still not put in the game; the
ServerDir status strings from CRes; longer play (later levels, a whole
mission) under `make test`.

### 8. modern

**Middleware.** `make modern` ships no RAD binary. `ext/ffmpeg` is FFmpeg
n8.1.3 as a submodule (nolfsrc's pin; `.gitmodules`, shallow), and
`build/ext.sh` builds its Bink decoders and our player on them
(`src/modern/binkw32/`, nolfsrc's player plus `BinkDX8SurfaceType` and the
D3D8 surface formats NOLF2's engine uses) with `zig cc` into `out/ext/`;
`variant.sh` sets `NOLF2_MIDDLEWARE=open`, `all.sh` step 2 installs it
(`retailextract.py openruntime`, audited as `EXT`) and only the Microsoft
runtime from retail. The engine looks up twelve Bink entry points at run
time (`binkvideomgrimpl.cpp`); no game DLL imports Bink. No OpenMiles:
nothing in NOLF2 loads `mss32.dll` (snddrv.dll is DirectSound). The movies
play (`tools/playtest-movies.txt`, about 80 s of logos to the menu; the
same with RAD's DLL); `linux-run.sh` turns them on when `MANIFEST.txt` lists our
binkw32. **For the coordinator:** the main checkout needs `git submodule
update --init ext/ffmpeg` before `make modern`; `tools/agentwt.sh` now
hard-links `ext/ffmpeg` into new worktrees (this one was populated the
same way, from nolfsrc's checkout of the same commit).

**Launcher.** `NOLF2.exe` is installed in both builds, with
`linux-run-launcher.sh` (registry values the installer wrote: `InstallDir`, and
`UpdateCommandLine1` = `-rez Update_v1x3.rez -rez custom`, since the
launcher puts `custom` before the update's zeroed DLLs). Tested in a fresh
prefix under Xvfb, both builds: detail dialog, then the game to the main
menu. In a prefix that already has a profile the launcher passes no
resolution, and the engine takes `autoexec.cfg`'s 800x600, which an Xvfb
of another size does not list (M-E2) -- a test-harness limit, not seen on
a desktop. The build container's prefix is shared (`out/wineprefix`):
give launcher tests their own `WINEPREFIX`.

**Fixes** (`docs/MODERN.md`, each tested in `make modern` + playtest against
the release build): M-E1 Hor+ in `CClientMgr::Render`, world views only
(`DRAWMODE_NORMAL`; the interface's RenderObjects art stays with the
stretched 2D layout); M-G1 wide modes in the Display screen and the
launcher; M-L2 the launcher's `NOLF2Srv.exe`. `releasesrc.py diff` is
empty; no file of net's or rendermatch's was touched (M-E2 is in
render_a and left for later).

**jupitersrc.** `src/Game/Libs/` (fetched SDK source) is hard-linked
between worktrees, and `tools/jupitersrc.py` wrote through the links: the
net worktree (without the sierraup patch) unpatched `CServerDir_Titan.cpp`
for every tree, and `make progress` here lost six ServerDir.dll
functions. It now replaces files instead. Other worktrees keep sharing
until they take this commit; rebuild ServerDir after merging.

**Score.** `make progress` (check) passes: no recorded function lost,
NOLF2.exe 309 as before. `make test` passes on the release build;
`playtest-newgame.txt` and `playtest-movies.txt` pass on the modern one.

**Left** (`docs/MODERN.md`, todo): menus and HUD in a centred 4:3 area (M-G2;
then `PLAYTEST_MAP=modern`), windowed mode at any size (M-E2, render_a),
raw mouse input (M-E3), high-frame-rate checks before a default
`MaxFPS` (M-E4), drawing the console (M-E5), Internet play without the
WON servers (M-E6), an FOV option (M-G4).

### 9a. net

Done. **Multiplayer works** with the built engine: `tools/mptest.sh`
starts NOLF2Srv.exe with a `server.dll` (ours by default;
`out/reference/server.dll` is the protocol's control) hosting the first
co-op level, and our `Lithtech.exe` joins it over UDP loopback through
the LAN menus (xdotool), both under one Xvfb in the build container. It
prints JOINED when the server keeps the client and the client enters the
world. The command line's `+join` does not work here, because it asks
WON's servers to check the CD key first. The server needs the 1.3
update's rez registered as its installer does it (`UpdateNum`,
`UpdateCommandLine0`). Without it the server's attribute files are 1.0's,
and the handshake's CRC checks kick the client.

**Protocol.** Two differences from Jupiter had to go:
- Every unconnected packet carries NOLF2's token 0x01337F10, not
  Jupiter's 0x9919D9C7. With Jupiter's, our client could not find or join
  a retail server.
- The 2002 UDP driver locks with `CWinSync_CS`, not `LCriticalSection`.
  That shifted every field of `CUDPConn` and `CUDPDriver`.

The driver also gets back its 2002 listen thread, `ReallyJoinSession`,
`SendPing` and the one-argument `Term2`. Packets are copied bit by bit
(`WriteData`/`ReadData`); Jupiter's raw-copy helpers are gone.

**The game's handshake** (cshell's notes, 9c) derives its key and mask
from the player GUID and a rotated constant in retail. Our CShell and
Object.lto still use the source release's fixed values. Our client and
our server agree, so mptest passes, whichever `server.dll` is used. A
retail Object.lto, or a retail client, would not agree with them. The
fix is in the game code, not here.

**Matching.** In server.dll, udpdriver.obj places 242 functions (165
before this package). The ones still unplaced are `ShouldSendPacket`
(nothing calls it, so retail's link dropped it) and a vector-destructor
helper. packet 30, netmgr 142 (the unplaced ones are client-only session
calls), localdriver 35/35. In Lithtech.exe: udpdriver 237 (190 before),
packet 28, netmgr 130, localdriver 40.

Also matched in the server-side modules:
- `HandleGuaranteed`
- `CPacket_Read`'s sub-range constructor (inlined into about 20 exe
  functions)
- `CModelMgr`'s loops (iterators initialised at declaration)
- the four object constructors without `m_nEffectShaderID` (as on master)
- `CWorldServerBSP::Term` (no `world_tree.Term`)
- `CLTMessage_Load::ReadObject`
- `CollideWithAABB`
- `Model::Load`
- `CLTTransform::Inverse`

`make progress` (check) passes: server.dll 2399 -> 2501 identical,
Lithtech.exe 5509 -> 5613 (against this branch's recorded baseline).

**Known nears, and why:**
- `CUDPDriver::Update`. Retail calls the three flushes directly, and
  `Term` and `GetPacket` call `FlushInternalQueues`. Written that way,
  both binaries' `Update` match, but then the exe's `Term` inlines
  `deque::pop_front`, which retail calls out of line (0x48e540, recorded
  identical). So the source stays as it is (the comment in `Update`
  says so).
- `i_IntersectSegment`. Retail calls `TVector3`'s constructor out of
  line inside `operator-` (0x100069bb), and our compile inlines it.
  That is in `ltvector.h`, which other modules share.
- `intersectsweptsphere.obj`. Several functions are 30-260 bytes off.
  Not looked into.
- The exe's /O2 shapes of `game_serialize`, `ltmessage` and the rest of
  `udpdriver` (`o2gap.py`).
- `d3d_model_load`'s `CreateModelRenderObject` and
  `spritecontrolimpl`'s `GetFrameTextureHandle` are already fixed on
  master (rendermatch: the `CDIModelDrawable` constructor and the
  `SharedTexture` layout).

**Left:**
- One exe hosting and another joining (not tried; the dedicated server
  path is what was tested).
- A retail client against our server, which SecuROM prevents under
  Wine.
- The nears above.

#### net: retail bugs

`CLTTransform::Inverse` returns its input: now in `docs/RETAIL_BUGS.md`.

### 9b. rendermatch

**Structures and file formats** (each fix in its commit, with the retail
address that shows it):
- `SharedTexture` (`world/de_world.h`) is 0x68 bytes: type at 0x18, two
  linked textures (env map/detail, bump map), no effect shader ID;
  `r_LoadSystemTexture` (kernel `render.cpp`) parses NOLF2's five texture
  commands with no argument checks. No `m_nEffectShaderID` in the sprite,
  particle system, polygrid and volume effect objects (`de_objects.h`).
  These were the client package's suspect layouts. `ModelInstance`'s size
  was not looked at.
- Model pieces: a vertex stream with basis vectors carries **3** floats
  more in NOLF2's files (`GetVertexFlags_and_Size`, `d3d_utils.h`), not
  Jupiter's 6, so skeletal, rigid and vertex-animated pieces with them
  were misread. All three loaders now match, as does
  `CD3D_RenderBlock::Load` (world render blocks, 3,052 bytes).
- Behaviour taken back to retail: polygrids use the generic dims and a
  particle system's dims are scale x radius (the object handler table);
  particle batches fill whole vertices per particle (no per-frame base
  setup); screen glow does not clear its textures afterwards;
  `MipMapBias` is an int console variable. `CDIModelDrawable`'s
  constructor assigns in its body (`model/model.h`, one line, for the
  constructor order retail inlines).

**Flags.** `D3DRender.dsp` is `/O2 /Ob2` (with `/GX`, kept): +176
identical functions on its own, unplaced 2,188 -> 1,230
(`progress/COMPILERS.md`).

**In the game.** The built exe plays C01S01, C02S01, C04S01, C06S01,
C07S01, C12S01 and CP_C03S01 (640x480 Xvfb, `+DisableSound 1`);
textures, lightmaps, models, sprites, smoke particles, the HUD all look
right, and no renderer message but retail's WATERFALL2.LTB one. A
reference: the 1.3 MP demo's engine (`out/mpdemo/Lithtech.exe`, from
`demoimports.py extract`) runs the demo's own `Game.rez`
(`-rez Game.rez +runworld Worlds\RetailMultiplayer\CP_C03S01`), whose
CP_C03S01 is the same file as retail's; our exe runs retail's. The spawn
point differs, so only a qualitative comparison was made (it matches). The
demo engine cannot run retail's cshell.dll (it asks for IClientShell
version 5, retail's is 4; patching the number crashes it) and ours cannot
run the demo's.

**Score.** Lithtech.exe 5,509 -> 5,792 identical (+152 KB), unplaced
2,190 -> 1,227, unwritten 85 -> 60; server.dll 2,399 -> 2,410 (the
SharedTexture/object layouts). `make progress` passes.

**Left.**
- The template instances of `CRenderShader_Base` (13 each): `Lock`,
  `Flush`, `vector<CRenderBlockData>::push_back`/`_M_insert_overflow`,
  the Lightmap `SortSections` differ from retail only in exception-state
  numbering (retail sets no state for the default allocator temporary of
  some vectors, ours does). Not found why; not a source difference that
  was found (an explicit instantiation of `allocator<uint32>` and a
  user-declared destructor on `CRenderBlockData` did not change it).
- `d3d_DrawPolyGrid` is one register choice away (two `movsbl` swapped in
  the inlined `GenerateBasisSpace`), but the function table splits it at
  0x547d55, so the scorer cannot count it anyway.
- Register-allocation nears: the drawprim `DrawPrim` overloads,
  `SetTransformMode`, `CD3DRenderStyle::SetDefaults`/`Load_LTBData`,
  `d3d_BlitToScreen3D_Old` (a rect copied to the stack where retail reads
  it in place).
- Scorer pairings inside the renderer are often wrong for template
  instances (same name, different instance): judge with `exematch` on the
  object and `callseq.py`, not the near list.
- `docs/MODERN.md`'s windowed mode at any size (render_a, behind
  `NOLF2SRC_MODERN`) was not done.

### 9c. cshell

**Where the gap was.** Of CShell.dll's 109 KB of non-identical code, 89 KB
was 187 nears and 19 KB `small` (global initializers, unverifiable by the
scorer: not source work). `tools/layoutscan.py --image=CShell` put 180 of
the nears, in InterfaceMgr, GameClientShell and every screen, on one field
shift of 12 bytes: retail's `CInterfaceTimer` is 0x1c bytes, without the
source release's `m_fTimeLeft`, and `CInterfaceMgr` holds three of them.
Taken back to retail's (constructor 0x100eb210, `Draw` 0x100eb260,
`SetTime` inlined at 0x1005c484 and 0x10063f4e), CShell.dll went from
5,234 to 5,414 identical functions (+88 KB). The flags were not the cause:
the Rich header already matched, triple for triple.

**Convention.** `src/Game/` is the source release, which is not quite what
retail 1.3 shipped (here it is later: the timer above is a fix retail does
not have). Where retail differs, the retail code is reconstructed from the
binary in place and marked `// RETAIL: reconstructed from the retail 1.3
<binary> (<address>)`, as nolfsrc marks its Game of the Year changes
`GOTY:` (README, LICENSE-NOTES). Not behind `NOLF2SRC_MODERN`: the release
build is retail. The source release's version of a change may be a fix
worth taking into the modern build.

**Done.**
- `InterfaceTimer.h/.cpp` (CShell): the layout above.
- `Bombable::HandleStoppedMsg` (Object.lto 0x101d45b0): retail sets
  `m_bCanDeactivate = true` after a stopped defuse; +1 function.

**Found and not committed: the handshake.** Retail's client and server
handshake is not the release's fixed key and mask
(`GAME_HANDSHAKE_PASSWORD`, `GAME_HANDSHAKE_MASK`), which Monolith seems to
have taken out of the published source. Retail, with
`K(n) = rol(0xDEADFACE, n & 0xF)` (compiled from
`(0xDEADFACE << r) + (0xDEADFACE >> (32 - r))`, `r = n & 0xF`, written as
an inline function: a macro lets VC6 share the two evaluations in the
client, which retail does not) and `name` the first four bytes of the
player GUID (the client's `m_sPlayerGuid`, copied with `LTStrCpy(sz, ..,
255)` into a 256-byte buffer whose first four bytes are zeroed first; the
server's `GetClientName`):
- client HELLO (0x1007e260) sends `(uint32)this` as its key;
- server HELLO (Object.lto 0x1002a440) answers
  `K(name) ^ clientKey ^ (uint32)this`;
- client PASSWORD: `m_nServerKey = K(name) ^ m_nServerKey ^ (uint32)this;
  nXORMask = K(name) ^ m_nServerKey; nPassword = nXORMask ^ name`; the
  CRCs are masked with `nXORMask` as before;
- server LETMEIN: `nXORMask = K(name) ^ (uint32)this`, the password must
  be `name ^ nXORMask`; the CRCs as before.
The client side compiles byte-identical (1,104 bytes). The server side
stays near (1,477 of 1,475 bytes: retail tests the loaded name dword for
zero and stores zero, which no form tried reproduces: a ternary or an `if`
folds away, `LTMAX` gives sbb/and, a pointer test gives neg/sbb), and any
change to its LETMEIN case swaps two reloads in `FindStartPoint` (Object.lto
0x1002cf80, recorded identical, 1,444 bytes), whatever the form. Both sides
have to change together, so neither was committed. Doing it means finding
the server's exact form (which should give FindStartPoint back) or
accepting that loss; it also makes our builds talk to retail clients and
servers.

**Left.**
- CShell.dll: 4 nears, 2 KB (the handshake above; `InitSound`, two spill
  slots swapped; two tiny scorer mispairings). The other 19 KB is `small`.
- Object.lto: `CAIGoalButeMgr::ReadGoalSet` (two loads in the other
  order), the server handshake; the rest of its 2% is `small` (34 KB) and
  mispaired template instances. ClientFx.fxd has no near: its 1.2% is
  `small` and one row whose extent covers an initializer thunk and the
  function after it.
- `make progress` fails, before and after this package, on six ServerDir.dll
  functions: `CServerDir_Titan.obj` built from the current
  `src/Game/Libs/` (identical in every worktree since the jupitersrc
  rewrite) differs from the one the baseline was recorded from (WONAPI
  template destructors 93 -> 45 bytes, `IPAddr`'s copy constructor); not
  the order of `/YX`'s precompiled header (recompiling with the header in
  place changes nothing). For whoever owns ServerDir.

### cshell: retail bugs

The multiplayer timer that runs on while paused, and possibly an armed
bomb that deactivates after a stopped defuse: now in `docs/RETAIL_BUGS.md`.

### 12. modernizer

The NOLF 2 Modernizer (github.com/haekb/nolf2-modernizer, read at
`76cc9cd`) was read, never built or copied; `docs/MODERN.md` lists every one of
its changes with its commits and what became of it, and answers each
known issue of its readme and itch.io page (K1-K11). Done: M-L4, M-G17
(no disc, no CD key); its crash fixes (M-G18..M-G27, M-G30); M-G1, M-G2,
M-E1, M-E15, M-G35 (wide screens); M-E2, M-G40..M-G44, M-E4, M-G4
(windows, focus, frame limit, options, wheel, fps); M-E3 (mouse look:
package 13's cause); M-E13 with K1, M-G34, M-G36, M-G45, M-G50. Decided:
M-G3, M-G21, M-G24, M-G28, M-G29, M-G32, M-G37, M-G49 and the black
window (nothing to do). Left: M-E5 (the console), M-E6 (Internet play
through a GameSpy-style master), M-G47 (controllers, with K8), M-G46
(jukebox, with K2, K5-K7), M-G38 (the damage flash is a really-close
ClientFX sprite sized for 4:3; widening it needs a scale on the FX or a
HUD item). Not ported: M-G31, M-G33.

**Mouse sensitivity.** With M-E3 the same `MouseSensitivity` turns 1.1 to
3.8 times less than in the release build. The scale is kept: in 2002 the
bug made about 1.2x, so the shipped default turns as it was tuned; the
slider's lowest step is lower (`MouseScaleBase` 0.0005). The Mouse
screen's "Input rate" (the smoothing) is not shown in the modern build.

**Build.** `ClientRes.res` does not depend on the shared string table
(`src/Game/ClientRes/Shared/Lang/EN/ClientResShared.rc`, included through
the resource compiler's include path; `build.mk`'s `rcfile` lists only the
script's own directory), so a string added there is not built into
`CRes.dll` until the `.res` is removed. For whoever owns `build.mk`.

Tested: `make modern` at 1280x720 (menus, Display screen, a new game,
antialiasing 4x full screen and windowed, the dedicated server without
the registry key, `tools/srvtest.sh` without its `reg add`); `make test`
and `make progress` unchanged.

### modernizer: retail bugs

- **Antialiasing never worked with Direct3D 8's rules.**
  `CD3D_Device::SetPresentationParams` (render_a) always asks for
  `D3DPRESENTFLAG_LOCKABLE_BACKBUFFER`, which Direct3D 8 refuses with a
  multisampled back buffer, and gives a window the copy swap effect, with
  which it does not multisample: `AntiAliasFSOverSample` could not take
  effect (Wine accepts the device). Retail never shows the setting (its
  `IDS_ANTIALIAS` strings are unused). Fixed in the modern build (M-E13).
- **The 2D interface is placed on pixel centres.** The draw primitives'
  screen-space vertices are at whole pixel coordinates, which in
  Direct3D are pixel centres; harmless without multisampling, but with it
  every 2D item's left and top edge pixels come out half covered (the
  Modernizer's known issue K1). Fixed in the modern build (M-E13).
- **Anisotropic "On" is degree 1.** The Performance screen writes
  `Anisotropic 1`, which the renderer passes as `D3DTSS_MAXANISOTROPY`:
  anisotropic filtering of degree one, no better than bilinear. Fixed in
  the modern build (M-G45: 2x to 16x).
- **The dedicated server needs the installer's registry key.**
  `CServerDlg` returns false from starting a game when
  `HKLM\Software\Monolith Productions\No One Lives Forever 2\1.0` is
  missing, though only the update's archive list and the selected mod
  come from it. Fixed in the modern build (M-G50).
- The Modernizer's other retail bugs are in `docs/MODERN.md` with "fix (retail
  bug)": M-L2, M-G18, M-G19, M-G20, M-G22, M-G23, M-G25, M-G26, M-G27,
  M-G30, M-G35, M-G42, M-E3 (already in `docs/RETAIL_BUGS.md`).

### 11. bugs

**Variants.** `make debug`, `make modern` and `make modern-debug` build
every binary of the game, the engine included (`Lithtech.exe`,
`server.dll`, `SndDrv.dll`, `ServerDir.dll`, `ltmsg.dll`, the launcher and
the dedicated server): build.mk puts `NOLF2SRC_CFLAGS` on every compile, so
each engine object's command line has `/D NOLF2SRC_DEBUG /Z7 /Oy-` or
`/D NOLF2SRC_MODERN` (checked in the `.obj.cmd` files of
`out/build-<variant>/`), and the debug variants put a `.pdb` beside every
binary. Nothing needed fixing. `make test TEST_GAME=out/<variant>` (new)
plays a variant's game directory (`out/play/test-<name>/`); all three pass
`playtest-newgame.txt`, and `tools/srvtest.sh` hosts CP_c01s01 with the
modern `NOLF2Srv.exe` and `server.dll`.

**`releasesrc.py`** now ignores directives inside `/* */` comments:
`ltdirectmusic_impl.cpp` keeps a commented-out `#else`/`#endif`, which the
stripper took for an unmatched `#endif` once the file had a variant block.
Also: the editing tool drops trailing whitespace on the lines it touches,
and retail files have plenty; `tools/releasesrc.py diff` (run in the
checkout: it uses the current directory) catches it, run it after every
edit.

**`docs/RETAIL_BUGS.md`** (48 entries) came from the porting notes, from
nolfsrc's list looked for bug by bug in NOLF2's game and engine code, and
from reading the multiplayer, gameplay and engine code for the same kinds
of mistake. Engine entries were checked with `tools/exematch.py` against
`out/reference/` (it runs on the host, read only): each names a function
byte-identical to retail at its address. NOLF2's engine fixed or rewrote
most of NOLF1's server.dll bugs (the list ends with them); the game code
carried more over, and NOLF2's multiplayer adds remote holes of its own
(chat overflows, debug messages obeyed from any client, the handshake not
enforced).

**Fixed in the modern build**: 23 entries (`docs/MODERN.md` M-G5..M-G16,
M-L3, M-E7..M-E12), each tested with `make modern` and the playtest. Three
only on one side: names and chat as formats and the chat overflow are
fixed on the server (which also cleans what it relays, so clients behind a
modern server are safe) but not in the client's own code, and only the
client's wrong function names.

**Left, by owner.**
- The server package (`server/`, `shared/`, `world/`, `model/`,
  `kernel/net`, `kernel/io`): `CLTServer::CPrint` formats its line twice
  (pass it on through `"%s"`), `ReadHStringAsString`'s seek,
  `ReadHString`'s terminator, `WriteMessage`'s 16-bit size,
  `OnHelloPacket`, `cb_LoadModule`'s double free, the world loader's
  vertex count, `ILTModel::GetNodeName`'s bound, `trk_ScanToKeyFrame`,
  `LTObject::Clear`, the codec, `CGenLTStream::WriteStream`, the property
  guard, the server's wrong function names.
- `CShell.dll` (being byte-matched): the particle and line systems at high
  frame rates, the client's chat and kill-message printing, the server
  list's `=`, the lip-sync reader, the camera clamp, the particle colour
  range.
- Not done here: the handshake and password (`KickClient` on a wrong
  password, refusing messages before the handshake) want a two-machine
  test; `CP_DAMAGE` from clients needs a design; the sprite-system timing
  and the snow rate change how the shipped effects look.

**Score.** `tools/releasesrc.py diff` is empty and `make game` recompiles
nothing for the fixes. `make progress` passes.

**ServerDir.dll was not reproducible** (six recorded functions, 0x10003cc0,
0x100043a0, 0x100044a0, 0x10008850, 0x10010060, 0x10010120, lost by every
fresh build). Two causes, both fixed:
- **The /YX precompiled header.** ServerDir compiles with `/YX` (automatic
  precompiled header), one compile after another in the .dsp's order:
  `CServerDir_Titan.cpp` first, which writes a header of everything it
  includes, then `stdafx.cpp`, which finds that inconsistent with its own
  and rewrites it with `stdafx.h` alone. A later rebuild of
  `CServerDir_Titan.cpp` alone (its source changed; the main checkout's
  14:15 rebuild) uses stdafx's header, and compiles differently: 377,910
  bytes against 375,182, eight more of its functions retail's
  (`tools/exematch.py`). The recorded score is from such a rebuild. The
  same source compiled in the two orders, by hand, gives exactly the two
  objects. `tools/dsp2mk.py` (`YX_FIRST`) now compiles ServerDir's
  `stdafx.cpp` first, so every build makes the retail-matching object.
  (The main checkout's `make game` did not rebuild the object because the
  release tree's copy of the source had not changed since 14:15 -- the
  15:27 time is `jupitersrc.py` rewriting `src/` with the same text, and
  the release tree keeps the time of the last real change. No dependency
  is missing.)
- **Anonymous-namespace numbers.** VC6 names an anonymous namespace
  `?%<source><number>` with a number drawn afresh on every compile (the
  same file compiled twice gets two numbers, 7 to 10 digits; not the time,
  the path or the text). WONAPI has three (`CDKey.cpp`, `CRC.cpp`,
  `QueueSocket.cpp`), in symbol names and, for `QueueSocket.cpp`, in an
  RTTI type name in a COMDAT data section, so the length moves code and
  data. `tools/anonns.py` rewrites them, for the libraries `build.mk`'s
  `PINNED_LIBS` names (WONAPI only: other projects' anonymous namespaces
  have not moved a recorded function), to the numbers of the WONAPI.lib the
  score was recorded on; the pinned objects are then those objects byte
  for byte, but for the time stamp and the COMDAT checksums. Whether the
  length alone moves any of the six was not separated from the first
  cause; with both fixed, fresh WONAPI and ServerDir objects score 207.

### 10. release

Done: nolfsrc's release pattern, for NOLF2 (`docs/BUILDING.md`, "Archives";
`docs/LICENSE-NOTES.md`, "The archives").

- `build/package.sh` writes `out/<name>-private.tar.gz` (the whole game
  directory, 0.9 GB) and `-public.tar.gz` (4.6 MB for the legacy release
  build): the same without every file `MANIFEST.txt` lists as `data` or
  `THIRD-PARTY` (listed in the stage's `disc-files.txt`), with
  `linux-install.sh` and `windows-install.bat`.
  `NOLF2_ARCHIVES` (default `private public`) picks them; `IMAGE_BUILD=0`
  makes `make image` take the docker image as it is.
- `tools/mkinstall.py` writes the install scripts. As nolfsrc's (its
  8a94af5, 9b6f580, b850912, 1792b21) they read the player's own *disc
  images*, nothing installed: both discs of the European or the USA
  release (`.iso`, redump `.bin`/`.cue` or `.zip`; MODE1 tracks on the
  European discs, MODE2 on the USA ones) and Sierra's
  `nolf2-update_1x3.exe`. (This replaces the first version, which read an
  installed NOLF2 through the Wine registry or InstallDir.) NOLF2's files
  are in InstallShield 6 cabinets spanning both discs (`data1.hdr`,
  `data1.cab`..`data3.cab`; GAME2.REZ is split across `data2.cab` on disc 1
  and `data3.cab` on disc 2), each file a run of 32 KB chunks, a 16-bit
  length and a raw deflate stream ending in a final block; only
  `Data/GAME.REZ` is stored plainly. mkinstall parses `data1.hdr` itself
  (file table, volume headers for split files), finds each retail file by
  its MD5 and size, and records the byte ranges of the image, per release
  (the cabinets differ between EU and USA and lie at other offsets). The
  update is a self-extractor whose overlay is one Microsoft cabinet (one
  MSZIP folder, 29.5 MB unpacked) holding its own IS6 setup; the list
  records the cabinet's offset and the unpacked folder's SHA-256, and the
  ranges of the update's files in it. Every way is read back and checked
  here against `rez/games/nolf2-eu-1.3/`. Output files are then the retail
  file in order with `C`/`Z`/`L` runs (the retail DLLs blanked in
  GAME2.REZ, GAMEDLL.REZ, Update_v1x3.rez), each checked by SHA-256; no
  optional or player's-own files any more. The scripts need an inflater
  only: `python3`'s zlib on Linux (bash and coreutils find, convert and
  check the images, as nolfsrc's), .NET's `DeflateStream` in Windows
  PowerShell 5.1 (MSZIP's 32 KB history is put in front as a stored
  block). redump's other USA disc 2 dump, `(Alt)`, has `data3.cab` at the
  same offset; it is recorded by size and SHA-256 (`ALIASES`). The list is
  about 13 KB.
- `make retail` also fetches the USA discs (`build/retail.sh`'s
  `retail_discs`), as mkinstall needs both releases' images; without them
  the public archive is skipped (an error with `NOLF2_ARCHIVES`).
- The run scripts are `linux-run.sh` and `linux-run-launcher.sh`, as in
  nolfsrc; `build/all.sh` removes the old names from a game directory.
- `make debug`/`make modern-debug` were broken on master by package 11's
  `tools/anonns.py` (with /Z7 the debug records hold the namespace names,
  with relocations after them; the tool refuses). Only the release build is
  pinned now (`build/build.mk`): variants are never scored.
- `tools/retailextract.py resources` hard-links the retail files it does
  not change (Engine/GAME/SOUND.REZ, the movies): a game directory is
  1.2 GB instead of 1.8.
- `.github/workflows/public-archives.yml`, as nolfsrc's now: a job
  "prepare" fetches the EU and USA disc zips and the SDK image only on a
  cache miss (keyed on `rez/isos/SHA256SUMS`) and writes the docker layer
  cache; then four build jobs (a matrix, fail-fast off) each build one
  variant with `NOLF2_ARCHIVES=public` (no private archive is made) and
  upload its `-public.tar.gz` itself (upload-artifact v7, `archive:
  false`); the legacy release job runs `make progress`. actionlint passes
  it.

Tested here with `NOLF2_ARCHIVES=public IMAGE_BUILD=0` (the CI switches):
`make`, `make debug`, `make modern`, `make modern-debug` write the four
public archives (4.6, 22, 5.5 and 23 MB) and no private one. Each was
unpacked into an empty directory and installed from the redump images:
legacy release by `linux-install.sh` finding the European `.zip`s and the
update in the directory above it; legacy debug from the USA disc 1 `.zip`
and the USA disc 2 `(Alt)` `.cue`/`.bin`; modern release by the .bat's
PowerShell (PowerShell 7.4 on Linux) from the USA disc 1 `.iso` and disc 2
`.zip`; modern debug from the European `.iso`s, then run again (all
kept). Each installed directory is the built game directory byte for byte
(`diff -r`, only the two install scripts extra), no temporary `.iso` is
left, and each passes the `make test` playtest (menu, new game, C01S01).
Not run: Windows PowerShell 5.1 and the .bat wrapper itself, the workflow
on GitHub (runner disk, caches, upload-artifact v7).

**`make progress` is not reproducible for `ServerDir.dll`** (found here;
the CI step will fail on it). VC6 names an anonymous namespace
`?%<source path><number>`, the number different on every compile (8 to 10
digits: retail's `QueueSocket.cpp` has `152339212`). WONAPI has such
namespaces (`QueueSocket.cpp`'s `QueueOpFastCompletion`, in
`Socket.obj`, `Common.obj`, `Auth.obj`), and the names' lengths move
`ServerDir.dll`'s layout: a fresh build of master scores 201 identical
functions, not the 207 recorded (`sub_10003cc0`, `sub_100043a0`,
`sub_100044a0`, `sub_10008850`, `sub_10010060`, `sub_10010120` lost); the
recorded score came from a WONAPI.lib built once on Oct 12 and never
rebuilt. Fix before turning CI on: pin the number (e.g. patch it in the
objects after compiling, or score `ServerDir.dll` without those
functions), or record the fresh-build score. (Done by package 11:
`stdafx.cpp` compiled first, and `tools/anonns.py` pins the names.)

### 13. mouse

**The report.** Mouse look "is not smooth... jumps around chaotically and
is hard to control" (the modern build, on a desktop under Wine). The
release build is the same: on master no input code differs between the
builds, and neither limits the frame rate (`MaxFPS` works only outside
`_FINAL`).

**The cause is retail's.** `input_ReadInput` (Lithtech.exe 0x4319b0) is
byte-identical to retail, so nothing from the Jupiter tree is missing here. The function reads the system mouse
one event at a time (x and y are separate events) and runs every trigger
after each and after the closing empty read. A relative axis hands on its
last event, blended 12% (`InputRate` 12) toward its last three, and is
zeroed only when `GetTickCount` has moved more than 1 ms past it, checked
once a frame. So an event is added two or three times, an x event again on
the y event's pass, and how many times depends on the frame rate, the
mouse's report rate and the speed: the look speed changes as you move.
`docs/RETAIL_BUGS.md` has the numbers: a model of the function (1.06 to 3.8
times the motion), and a run of the release build with a temporary
per-frame log (not committed): 2.8 times horizontally, 3.8/2.8 diagonally,
one event spread over three frames. Nothing here is Wine's: the game clips
the cursor to its window (`GameClientShell.cpp`) and DirectInput's relative
counts are what the log saw. How coarse Wine's DirectInput events are on a
desktop X server was not measured.

**The fix** is docs/MODERN.md M-E3 as reimplemented from the NOLF2 Modernizer
(read the mouse's whole buffer, add up each look axis over the frame, use
it once, no smoothing; a 1024-event buffer), which this package does not
duplicate. It helps: in the model the turn is exactly the motion at every
frame rate, speed and direction. Two side effects for whoever finishes it:
the view turns 1.1 to 3.8 times less for the same `MouseSensitivity` than
retail did (players will turn it up; `MouseScaleBase`/`MouseScaleIncrement`
could make up the usual 2x), and the Mouse screen's input-rate slider no
longer does anything for mouse look. M-E4's 60 fps default limit makes
retail's code behave better too, but is not needed once M-E3 is in.

**Retail bugs.** The net and cshell packages' lists moved into
`docs/RETAIL_BUGS.md`, with mouse look: `CLTTransform::Inverse` (fixed in the
modern build), the multiplayer timer, the bomb (not fixed).

**Score.** `make progress` (check) passes unchanged; `make test` passes.

### rcdeps

- **Resource scripts' dependencies.** A `.res` depended only on the files
  in its script's own directory, so editing a script it pulls in from
  elsewhere (`ClientRes/Shared/Lang/EN/ClientResShared.rc`, through
  ClientRes.dsp's `/i` directories; `Shared/Lang/EN/ResShared.rc`; the
  launcher's bitmaps in `RES/bmp/` and `RES/Lang/EN/bmp/`) rebuilt nothing.
  `build.mk`'s `rcfile` now hands every script to `tools/mkdeps.py` as a
  compile's source: it depends on the files in its directory and in each
  `/i` directory (resolved from the project directory, as rc.exe does), and
  on what it `#include`s and `rcinclude`s and the files its resources name
  (BITMAP, ICON, CURSOR, WAVE...), recursively. Every `.rc` the workspaces
  build is covered (the game's resource DLLs, Launcher, ServerApp,
  Lithtech/server, ltmsg), in every variant's tree. No output changes.

### 14. xinput

Controller support in the modern build, the same design and player
experience as nolfsrc's P7 (its commits "Modern build: controller support
(P7)", "Controller: A skips a cut-scene, and goes on from the death
screen", "Modern build: no DirectInput joysticks, the controller only").
Everything is behind `NOLF2SRC_MODERN`; docs/MODERN.md has the items.

- **Engine** (`src/modern/xinput/gamepad_device.h`, `padread.h`, included
  by `input.cpp`): `##gamepad`, an `IDirectInputDevice8A` of our own over
  XInput (loaded at run time, its two types declared by hand), a
  DirectInput gamepad to the game, so bindings, buffered reads and the
  Configure controls capture work unchanged (M-E20). DirectInput's game
  controllers are left out of the device list (M-E21).
- **Client** (`src/modern/xinput/clientpad.cpp`, compiled as part of
  `GameClientShell.cpp`: CShell's project files are retail's): the sticks
  (look, movement, the snowmobile), the menu keys, A in a cut-scene and on
  the death screen, a decision's choices (`HUDDecision`), the default
  layout once per profile (`[Controls] PadLayout`) (M-G47, M-G60, M-G61).
  The Controller screen replaces the retail joystick screen (M-G62).
- **Strings** 31100-31114 (`ClientResShared`, a block of their own, apart
  from the modern build's 31000 and up).
- **Retail bug**: a gamepad's buttons were bound by instance number
  (`docs/RETAIL_BUGS.md`, M-G63).
- **Testing**: `NOLF2SRC_PADTEST` makes a file the pad; `tools/playtest.sh`
  has `pad` and `tap`, and `tools/playtest-pad.txt` drives the menus,
  Configure controls (a button bound), the Controller screen, a new game
  (cut-scene, briefing and cinematic gone on from with A) and play (turn,
  run, walk, crouch, the menu with Start, back with B). Not tested: real
  hardware, a dialogue decision and the death screen (neither comes up in
  the script's first minutes of play).
- **Left**: rumble (M-G64) and button prompts (M-G65). Package 12's row
  still lists controllers among what is left; M-G47 is done.

**Score.** `make progress` (check) passes unchanged; `make test` passes on
the release and the modern build.

### 15. winmode

Done. One setting, two variables: the engine's `Windowed` (0 full screen,
1 a window; what `render_a` and the focus handling read) and `WindowMode`
(1 framed, 2 borderless; 0 or unset keeps M-G42's rule: borderless only
at the desktop's size, so old configs come up as before).

- **Engine** (M-E30): `r_InitRender` replaces the asked mode with the
  desktop's (`EnumDisplaySettings(ENUM_REGISTRY_SETTINGS)`) for a
  borderless window, before the renderer starts; `g_RMode` and
  `ScreenWidth`/`ScreenHeight` then carry it, so the game lays out for
  what it got. `d3d_Init` takes the style from `WindowMode`.
- **Display screen** (M-G70): a cycle in place of M-G40's toggle; a
  change of window mode is set by writing `Windowed`/`WindowMode`/
  `ScreenWidth`/`ScreenHeight` and one `RestartRender`
  (`ModernPrepareWindowMode`, `ModernApplyOptions`), the profile told to
  set no mode itself. `SaveDisplaySettings` keeps both variables in
  `display.cfg` for the launcher.
- **Launcher** (M-L5): a list box under the resolutions (the dialog's
  bitmap has no room for a label; the three entries say what they are),
  read from `autoexec.cfg` then `display.cfg`, passed as `+Windowed`/
  `+WindowMode` with OK. It does not move a window that is as large as the
  desktop to a smaller resolution, as the Display screen does: under Xvfb
  (one mode) a "Window" at the desktop's size puts the frame off screen.
- IDs taken: strings 31200-31202 (`IDS_MODERN_FULLSCREEN`, `_WINDOW`,
  `_BORDERLESS`; 31000-31001 renamed to `IDS_MODERN_WINDOWMODE`); the
  launcher's own table 31000-31002 and control 1100; docs/MODERN.md M-E30,
  M-G70, M-L5.
- **Testing.** `tools/playtest.sh` has `PLAYTEST_SCREEN` (a display larger
  than the mode, so a window has room around it) and a `screen` command
  (the whole display); `tools/playtest-display.txt` steps the screen
  through the three modes. Xvfb has no window manager, so a framed
  window's frame is not drawn; only its placement shows. Full screen on
  Xvfb can only be at the display's own size.
- `make progress` (check) passes unchanged; `make test` passes for the
  release and the modern build.
- **A crash report** ("crashed under borderless", details unknown) was
  chased with the modern debug build on displays of sizes no mode was
  asked for, with and without a window manager (openbox, in a scratch
  image: `PLAYTEST_WM`), antialiasing on and off, borderless from the
  command line and both ways through the in-game Display screen, Alt+Tab
  and minimise/restore (`tools/playtest-borderless.txt`). Found and fixed:
  at 3840x2160 the game crashed as it started (M-E31: a text parse, the
  HUD's radio menu; full screen at that size too, but borderless takes a
  4K desktop's size unasked); on a 5:4-only display leaving the Display
  screen crashed on an empty resolution list (M-E31); a window is placed
  on the primary monitor, not across all of them (M-E30). Fine: 1366x768,
  1920x1200, 2560x1440, 3440x1440, 1280x1024. The debug build's crash
  handler was never installed (`nolf2src.log` had no backtrace); WinMain
  installs it now.
- **Not reproduced / known.** A real GPU, a desktop window manager
  (GNOME, KDE), HiDPI scaling and real multiple monitors (Xvfb's
  Xinerama is no stand-in) were not available, nor the launcher's route
  (it passes the same `+Windowed 1 +WindowMode 2`). Under Xvfb (one mode)
  a framed window at the desktop's size has no smaller resolution to drop
  to, so the window manager shrinks it below the back buffer. Letter
  heights are `uint8`: above about 5K a large font's scaled size wraps.
  A crash that remains: the modern debug build's `nolf2src.log` (in the
  game directory) has the backtrace; with the release build, Wine's
  console output (`linux-run.sh ... 2>&1 | tee wine.log`) shows the
  faulting address.

### 16. fps

300 frames a second in single player at real speed (docs/MODERN.md M-E4), as
nolfsrc did for NOLF1. NOLF2's engine already keeps time well: client and
server frame times are whole-millisecond differences of one clock, so no
time is lost (NOLF1 clamped a tick to at least 10 ms and dropped
animation fractions; neither is here), and the game time, cut-scenes,
keyframers and timers kept real time at 700+ frames a second in retail
too. What did go wrong, each fixed under `NOLF2SRC_MODERN`:

- **Server tick** (`servermgr.cpp`): a tick every frame, and an AI
  updated every 10 ms stepping by one tick's time -- AIs a third of their
  speed at 300. A tick now runs once 10 ms have passed (nolfsrc's
  d171625 lesson included: time that runs backwards ticks at once).
- **Player movement** (`CMoveMgr.cpp`): the speed cap applied per frame
  made the walk 7% slower at 300; it is applied once a 60th of a second,
  the engine's exact friction physics doing the rest. The 0.1-unit
  minimum move, the dampings and pushers per 60th of a second.
- **Particle and line systems** (nolfsrc 9780977), **aim perturb, fire
  sparks, debris rest** (nolfsrc 0dd4bf4's per-60th amounts).
- **Not changed**: a jump's arc (the engine's quarter-a·dt², 51.5 units
  at 60, 50.0 at 300; retail ranged wider); the vehicles (`VehicleMgr`,
  not measured); multiplayer, held at 60.
- **Limit**: `MaxFPS` 300 by default, 60 at most in multiplayer; the
  Display screen offers 300. No new strings or ids (one help string
  reworded).
- **How it was measured**: a temporary per-frame log (player position and
  velocity, camera, one AI's update times, server ticks, particles added)
  and scripted runs under Xvfb with the world not drawn (`DrawWorld 0`
  and the like), which runs at 700+ frames a second; C01S01 for walking,
  crouching and jumping, the Performance world's tornado cinematic for
  cut-scene timing and the AI. The log and scripts were not committed. No
  retail single-player world places a `ParticleSystem` object; the
  weather volumes' snow and rain use the fixed classes, not measured.
- `make progress` (check) passes unchanged; `make test` passes for the
  release and the modern build.
