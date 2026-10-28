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
| 17 | `nolfsync`: nolfsrc's commits since package 16 (its history rewritten: a99873c, 549ea60, 3bc4fac, 7855bf1, a97a06c, 1a7a95c, 39d8636, bc52297, 82d0759, 4f5b3fa, 113b4f4), each ported where NOLF2 needs it | 14, 15, 16 | done: out of the water at high frame rates and a 240 default limit (M-E4; 1 `docs/RETAIL_BUGS.md` entry); the documentation in `docs/` with an install guide, console and variables, changelog and credits; the rest already here, not applicable or waiting for M-E5 (notes) |
| 18 | `console`: the developer console in the modern build (docs/MODERN.md M-E5), with nolfsrc's `GetPos`/`SetPos` (its M-P2-14) and Shift+Esc (M-P2-15) | 12, 17 | done: the engine's own console revived behind the define (keys, drawing at any resolution, completion, answers), the game paused under it in single player, `GetPos`/`SetPos`; tested in play at 640x480, 1920x1080 and 4K and over a multiplayer client (`tools/playtest-console.txt`); 2 `docs/RETAIL_BUGS.md` entries |
| 19 | `winlaunch`: issue #1 -- on Windows the launcher offered only "Install" (no installer registry) and `Lithtech.exe` typed by hand failed with "Bad Image" / "Missing shell DLL" (no `-rez custom`) | 10, 8 | done: legacy build: `windows-install.bat` registers the game, `windows-run.bat`; the modern build's launcher needs no registry and no administrator (M-L6, M-L7, M-G71); tested under Wine in fresh prefixes (notes); not yet on real Windows; 1 `docs/RETAIL_BUGS.md` entry |
| 20 | `serverdir`: why `ServerDir.dll` scored 33.8% (207 identical, 129 near, 130 unwritten) | 9 | done: the 2002 SDK `CServerDir_Titan` replaced by NOLF2's 1.3 one from the F.E.A.R. source release, with `TitanTest.cpp` linked as retail did; 207 -> 417 identical, 0 near, 130 -> 0 unwritten, 1 -> 0 unplaced (33.8% -> 99.3%; the rest is 75 rows too small to place) |
| 21 | `unwritten`: the engine's unwritten functions (Lithtech.exe 54, server.dll 5) identified and written or shown not to be functions; cjacksrc's engine cross-referenced and ported where NOLF2's retail code agrees | 9 | done: Lithtech.exe unwritten 53 -> 8, identical 5,891 -> 5,928 (+16,019 bytes); server.dll unwritten 17 -> 0, identical 2,513 -> 2,527; three tools changes (enumeration); the cjacksrc map in the notes; 1 `docs/RETAIL_BUGS.md` entry |

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

### 17. nolfsync

nolfsrc's commits since what packages 14 to 16 ported. Its history was
rewritten, so the first three are new hashes for work already here; the
old commits (9a844b4, b58cc3b, 73d2ecc, 2fdf927, 0dd4bf4, d171625) were
compared with them (`git range-diff`).

| nolfsrc | What | Here |
|---|---|---|
| a99873c controller support (P7) | 9a844b4 squashed with b58cc3b (A skips a cut-scene, goes on from the death screen) and 73d2ecc (no DirectInput joysticks) | nothing new: package 14 has all three (M-E20, M-E21, M-G61) |
| 549ea60 window mode | 2fdf927, unchanged | nothing new: package 15 (M-E30, M-G70, M-L5) |
| 3bc4fac 300 fps at real speed | 0dd4bf4 squashed with d171625 (time running backwards ticks at once) | nothing new: package 16 (M-E4), d171625's lesson included |
| 7855bf1 climbing out of water at high frame rates | the rise on surfacing, and the jump's swim-up push, per 60th of a second | ported (M-E4, `docs/RETAIL_BUGS.md`): NOLF2's `CMoveMgr` has both faults. Measured in C13S03's pool with a temporary per-frame log and a temporary teleport (not committed): 3 units lower afloat at 120 frames a second than at 60 before, as at 60 after; 472 units a second after the jump frame at 120 before, 495 after (496 at 60). The test reached about 125 frames a second under Xvfb, not 240. NOLF1's lost climb-outs (the head bob dipping the eye under) were not seen: NOLF2's swimming did not dip it. No retail ledge tried |
| a97a06c modern console: `SetPos`, `GetPos` | console commands | waits for M-E5: NOLF2 has no console to type them into, and game commands cannot come from the command line or `autoexec.cfg` (they run before the game registers its commands; `docs/CONSOLE.md`). Noted in M-E5; retail's `pos` cheat shows the position |
| 1a7a95c frame-rate limit of 60, 120, 144, 240 or none | its 300-or-none switch made a choice, 240 the default; multiplayer 60 | the choices were here (the Display screen's 30 to 300 and none; 60 in multiplayer): only the default is ported, `MaxFPS` 240 (M-E4). A config that has `MaxFPS` keeps it: no config version here to move it |
| 39d8636 the Intel graphics fix only with d3d7.ren | the fix greyed out with nolfsrc's other renderers | not applicable: NOLF2 has no Intel fix (no `EnableLightScale`/`EnableScreenTinting` option; M-G33 not ported) and one renderer |
| bc52297 32-bit textures by default | `32BitTextures` 1 for new and old configs | not applicable: NOLF2's renderer also defaults to 0, but the shipped `autoexec.cfg` sets `"32bittextures" "1"` |
| 82d0759 crouch toggle and four more fixes from ChthonVII's fork | (credited there to ChthonVII and Daniel Gibson) | none needed: the crouch toggle is retail NOLF2's own control ("Crouch toggle", `COMMAND_ID_DUCKLOCK`); each weapon keeps its ammo in retail (`KeepCurrentAmmo` 1, `CClientWeaponMgr::ChangeWeapon`); a popup closes on any new key or either mouse button in retail (`CInterfaceMgr`); NOLF2 has no sunglasses (`OVM_SS` is never made; the scope and camera are M-G34); Shift+Esc for the console waits for M-E5 (noted there) |
| 4f5b3fa documentation moves to docs/ | | ported: `BUILDING.md`, `LICENSE-NOTES.md`, `MODERN.md`, `RETAIL_BUGS.md` and `SETUP-NOTES.md` in `docs/`, every reference outside `src/` updated (the source's comments name items as "MODERN.md M-...", as nolfsrc's do); `build/package.sh` puts no document in the archives |
| 113b4f4 install guide, console and variables, changelog, credits | | ported, written for NOLF2: `docs/INSTALL.md`, `docs/CONSOLE.md`, `docs/VARIABLES.md`, `CHANGELOG.md`, README's documentation table and credits |

Found while writing `docs/CONSOLE.md` and `docs/VARIABLES.md`, not fixed:
retail's cheat table gives `gimmemod` the gear (no code gives a single
modification); `envbumpmapenable`, which the Performance screen writes, is
read by nothing (the renderer reads `EnvBumpMap`); `RunInBackground` may
not keep a single-player game running, the local server freezing game
time unless `alwaysfocused` is set (to test).

`make game` and `make modern` pass after each code commit and at the
end; `make progress` (check) passes unchanged; `make test` passes for the
release and the modern build (the release build's once judged "NO HUD"
on a first run, then passed: the run's own timing, not a change here).

### 18. console

The developer console in the modern build (docs/MODERN.md M-E5; how to
use it: `docs/CONSOLE.md`).

**Engine, not game DLL.** The Modernizer wrote a console of its own in the
game DLL, and nolfsrc did the same (its engine is a binary reconstruction;
it added `ILTClient` methods for the output and the command list). Here the
engine is source, and retail's release build already keeps nearly all of
Jupiter's console: the text buffer every print goes to (game `CPrint`s
included), the command line and its editing, the history, the command
handler, the input gating (`dsi_IsConsoleUp`: no key forwarded to the game,
the controls cleared, keys to `con_OnKeyPress`), and the development
build's backquote toggle in the window procedure (`#ifndef _FINAL`). What
was missing is the drawing and the keys, so reviving it is less new code,
needs no interface but one event id, and sees everything printed from the
first line on. What the game must do itself -- pause -- comes from an
event.

- **Keys** (`kernel/src/sys/win/client.cpp`, `cl_ModernConsoleKey`): the
  key with scan code 0x29 (left of 1) or `VK_OEM_3`, or Shift+Esc, opens;
  either or Esc closes; repeats ignored; the key's queued `WM_CHAR` taken
  out (TranslateMessage posts it before the key down is dispatched).
  `ConsoleEnable` 0 (or the game's `SetConsoleEnable`) leaves the key to the
  game. The development build's Shift/Ctrl+tilde line counts are left out.
- **Drawing** (`winconsole_impl.cpp`, `CConsole::Draw`): Jupiter's drew
  with a bitmap font from `console\console_font.dtx` (not in NOLF2's data)
  and D3D9 calls, from `End3D`, which the game calls many times a frame.
  Now `cis_FlipScreen` draws it once, over the finished frame, in its own
  Start3D/Optimized2D: a draw-primitive band and a polystring per line,
  in a vector font from the engine's font manager (Lib_UI's GDI glyph
  rendering): the first installed of a list of fixed-pitch faces (under
  Wine, fontconfig's Liberation Mono or DejaVu Sans Mono; Wine has no
  Courier New and substitutes a proportional face for it) at a 45th of
  the screen's height, 12 to 80 pixels (letter sizes are 8-bit). Remade on
  a size change, freed with the console when the renderer goes
  (`TermConsole`, before the device). Characters the font lacks and a
  message's kept newline are drawn as spaces / dropped.
- **Lines**: `c_ModernTypedCommand` runs the line through the handler as
  before and then answers each statement that was not a command; Tab is
  `CConsole::ModernComplete` over `c_ModernEnumNames` (the command list --
  the engine's commands are on it too -- the variable hash, the engine
  variable table), sorted and unique, bash-like. The line is cleared when
  the console comes down.
- **Pause**: `cm_ModernConsoleEvent` at the start of each client frame
  sends `LTEVENT_CONSOLE` (100, `sdk/inc/ltcodes.h`) on a change.
  `CGameClientShell::OnEvent` pauses single-player play (`PauseGame`, the
  pause text and tint turned off again) and unpauses only what it paused.
  `CInterfaceMgr::OnEvent`'s default case takes an unknown event for an
  error and switches to the main menu (found the hard way: the first test
  dropped out of the level): the event is listed there. A retail
  `CShell.dll` with this engine would do just that; the modern engine needs
  the modern game DLL anyway.
- **`GetPos`/`SetPos`** (`GameClientShell.cpp`): the level's coordinates
  (`ApplyWorldOffset`, as the `pos` cheat); `SetPos` writes the
  `MID_PLAYER_TELEPORT` message `CPlayerMgr::Teleport` writes outside the
  final build; the server's `CPlayerObj::Teleport` puts the player on the
  floor below the point (`MoveObjectToFloor`) and the client follows. Single
  player only (M-G7 makes the server ignore it from remote clients anyway).
  A point in the air with nothing below is a fall: the first test's guess
  killed the player.
- **Retail bugs** (`docs/RETAIL_BUGS.md`): `IsKeyDown` tests Ctrl for any
  key (`0x497c00`, `0x4963d0`; fixed); `CClientConIterator::NextItem`
  (`0x41b130`) ends the engine-variable walk on the wrong index (not fixed:
  not used any more).
- **Not done**: the Modernizer's `help` (Tab on a first letter lists
  names), lines of console text over play (`NumConsoleLines`, Jupiter's
  `DrawSmall`), a console background image (`console.pcx`, not shipped),
  the mouse wheel to scroll. `ConsoleAlpha` is not read.
- **Testing**: `tools/playtest.sh` has `type <text>`;
  `tools/playtest-console.txt` (modern game directory) opens it over play,
  sets a variable, `GetPos`, Tab (one match, several), Up, `Cheat pos`,
  closes it and walks, `SetPos` back to the start (GetPos then reads the
  start again, on the floor), Shift+Esc and Esc, the in-game menu. Run at
  640x480, 1920x1080 and 3840x2160 (`PLAYTEST_RES`), screenshots checked.
  Multiplayer: `tools/mptest.sh` with `MPTEST_KEYS` ending
  `grave g e t p o s Return ... grave` (the modern join screen needs
  `Down Down` before the server's `Return`): over a joined client,
  `GetPos` answered, `SetPos` refused, the client stayed joined. That the
  single-player game is paused is seen only through the pause path (input
  off, no time passing visible in the shots), not measured.

`make game`, `make modern` pass; `make progress` (check) passes unchanged;
`make test` passes for the release and the modern build.

### 19. winlaunch

Issue #1 (Windows 11, a public archive, `windows-install.bat` run with the
European redump `.zip`s): the launcher showed "install", and clicking it
"Unable to launch the setup program"; `Lithtech.exe -rez Engine.rez -rez
GAME.rez ... -rez Update_v1x3.rez` by hand gave "Bad Image ... csh*.tmp"
(0xc000012f) and "Missing shell DLL cshell.dll".

**Causes.** (1) The retail launcher decides "installed" from
`InstallDir` under `HKLM\SOFTWARE\Monolith Productions\No One Lives
Forever 2\1.0`, which the retail installer wrote; on Linux
`linux-run-launcher.sh` writes it, on Windows nothing did. It also opens
that key for writing (`CRegMgr32::OpenKey`, `KEY_READ | KEY_WRITE`), and so
does the game (`CRegMgr::Init`): on Windows that works without an
administrator only through UAC's registry virtualization (our `NOLF2.exe`
and `Lithtech.exe` have no manifest, so as 32-bit programs they are
virtualized: their writes go to, and their reads see first,
`HKCU\Software\Classes\VirtualStore\MACHINE\SOFTWARE\WOW6432Node\...`).
(2) `Update_v1x3.rez` holds the retail game DLLs zeroed (build/all.sh's
`resources`); our DLLs are `custom\`, which must come after it. The hand
typed stack had no `custom`, so the engine extracted a zeroed
`cshell.dll` to a temporary `csh*.tmp`. Both reproduced under Wine with
the release build: a fresh prefix shows "install" and that error; the
typed stack stops at "Missing shell DLL cshell.dll" (Wine shows no "Bad
Image" box).

**Both builds.** `windows-install.ps1` writes what `linux-run-launcher.sh`
writes (InstallDir = the game folder, NetRegionCode, UpdateNum 2,
UpdateCommandLine1 `-rez Update_v1x3.rez -rez custom`, Disable Movies 0 for
the modern build, 1 else): to HKLM's 32-bit view (`RegistryView.Registry32`)
when that can be written (an administrator), and always to the VirtualStore
copy (64-bit view of HKCU, so a 32-bit PowerShell writes the same place;
`WOW6432Node` only on 64-bit Windows), so the release build's launcher
finds it whether it runs virtualized (the usual case) or elevated after an
elevated install. Not self-elevating: the per-user copy is enough for a
virtualized launcher. `windows-run.bat` is `linux-run.sh`'s counterpart
(no registry: `Lithtech.exe -cmdfile run-cmds.txt`, nolf2cmds.txt's stack
and the arguments; installed with CRLF by build/all.sh).

**Modern build.** M-L6: the launcher's own folder is the install whenever
`Lithtech.exe` is beside it (a stale or a retail install's `InstallDir`
is ignored), Play always; no update values: `-rez Update_v1x3.rez`; `-rez
custom` after the updates unless already last; Uninstall disabled;
"Install" (only away from the game) says the game is not there. M-L7/M-G71:
launcher, game DLLs and `NOLF2Srv.exe` use the same key under HKCU (a new
one seeded from HKLM's, read only), so nothing needs an administrator or
virtualization; the dedicated server reads HKCU then HKLM and adds the
update's archive when the key has no update values. M-E32: a command line
with neither `-rez` nor `-cmdfile` gets `-cmdfile nolf2cmds.txt` first;
archives without `custom` get it last (before Engine.REZ); a game DLL from
the archives without "MZ" is not loaded, and a message says why and how to
start the game (once). Arguments after `-cmdfile` are read (tested:
`Lithtech.exe +DisableMovies 0` played the movies over nolf2cmds.txt's 1).

**Testing** (`tools/playtest.sh`: `PLAYTEST_LAUNCH` starts another program
than `Lithtech.exe -cmdfile`, and the game counts as running while it or a
`Lithtech.exe` is; `wfocus`, `wclick`, `sclick` drive the launcher's
dialogs; MANIFEST.txt is now linked into the run directory, for
`windows-run.bat`), each in a new `PLAYTEST_PREFIX` (no registry):
- modern, `tools/playtest-launcher.txt` (800x600): Play shown, Uninstall
  disabled; Display and Options (warnings, OK); Play, the detail dialog,
  the main menu. The prefix then had only the HKCU key (the launcher's
  values and the game's `ProfileName`), no HKLM key.
  `tools/playtest-launcher-again.txt` in the same prefix: no detail dialog,
  the options kept, the main menu.
- modern, a prefix with a retail install's HKLM values (`InstallDir`
  `C:\Games\NOLF2`, `UpdateCommandLine1` `-rez Update_v1x3.rez`, `EndGame`):
  copied to HKCU on the first run; played from its own folder, with
  `-rez custom` after the update.
- modern, bare `Lithtech.exe`: `tools/playtest-newgame.txt` passes (menu,
  new game, play). The issue's stack without `custom`: the main menu. With
  `custom` before the update: the new message box.
- `cmd /c windows-run.bat`: release build to the main menu (movies off);
  modern with `+DisableMovies 1` passed through (run-cmds.txt has the
  modern build's 0, then the argument).
- release build: fresh prefix, "install" and the issue's error (reproduced);
  with the values the installer writes added by `wine reg add` (HKLM,
  `/reg:32`), `tools/playtest-launcher.txt` reaches the game.
- modern `NOLF2Srv.exe` in a fresh prefix: `tools/srvtest.sh` ALIVE.

**Not tested** (no Windows here): the PowerShell itself (reviewed for
PowerShell 5.1 and ASCII only; `mkinstall.py` checks the latter); the
container's Wine prefix is 32-bit (one registry view), and Wine has no UAC,
virtualization or VirtualStore, so the VirtualStore copy, the 32-bit view
on 64-bit Windows and a non-administrator user are untested; nor a real
`cmd.exe`'s `findstr`/`for /f` (Wine's `findstr` returned success for a
missing file, so the .bat tests the output of `for /f`, not the error
level). On Windows: run the modern public archive as a standard user,
double-click `NOLF2.exe` (Play, detail dialog, game), `Lithtech.exe`,
`windows-run.bat`; and the release build's launcher after
`windows-install.bat` with and without "Run as administrator".

**Narrowed after review.** The modern build is fixed in its launcher
alone, so three things above were taken out again: M-E32 (`Lithtech.exe`
with no arguments, `custom` added to a typed stack, the blank-DLL message;
the engine is as before it); the copy of HKLM's key into a new HKCU key
(launcher and `CVersionMgr`) and the dedicated server's read of HKLM after
HKCU (modern reads and writes HKCU only); and, in the modern build,
`windows-run.bat` and the installer's registry values (`build/all.sh`
installs the .bat in the legacy build only; `windows-install.ps1` writes
the registry only when MANIFEST.txt has no `EXT` `binkw32.dll`, i.e. the
legacy build, with Disable Movies 1). The tests above of those parts no
longer apply; `tools/playtest-launcher.txt` (modern, fresh prefix) was run
again after the change.

### srvplace

`server.dll`'s 1,154 unplaced functions (1,100 of them `_$E` initializers
of 5 and 19 bytes, the rest tiny accessors and a few larger functions).

**What they were.** Almost all real extras, from one cause: retail's
`server.dsp` used the precompiled header, `/Yu"bdefs.h"` (`/Yc` on
`bdefs.cpp`), as Jupiter's and Contract J.A.C.K.'s do; ours had none.
`math_phys.h` (through `ltbasetypes.h` -> `ltrotation.h` ->
`coordinate_frame.h`) defines `PI` as `(float)(4 * atan(1.0))`, `PI_2`..,
`RADIANS_PER_DEGREE`, `DEGREES_PER_RADIAN` and the three `WORLD_*`
vectors: nine dynamic initializers (a `jmp` thunk and a body each, 0xF2
bytes) in every object at `/O1`, which cannot fold `atan`. Retail has the
group in 19 objects only (`51 51 d9 e8 dd 1c 24 e8`: 19 in retail, 100 in
ours; retail's .text 22 KB smaller): with a precompiled header VC6 emits a
header's initializers in the `/Yc` object alone, so only `bdefs.obj` and
the files compiled without the header have them. The groups' places in
retail (at each object's start, matched against ours) name those files:
`bindmgr`, `counter`, `de_file`, `de_memory`, `de_nodes`, `debugging`,
`dsys_interface`, `dutil`, `lthread`, `ltmodule`, `ltobjref`,
`server_interface`, `sounddata`, `streamsim`, `stringmgr`, `timemgr`,
`wave` -- mostly `sys/win` -- so those are `SUBTRACT CPP /YX /Yc /Yu`, with
`interface_linkage` and `ltquatbase`, which do not include `bdefs.h`. The
5- and 19-byte rows were the surplus of those shapes (the scorer counts
short functions by shape), so any 5-byte `jmp` accessor could carry the
label. A bonus: `intersectsweptsphere.cpp`'s `#pragma optimize("", off)` /
`("as", on)` sit above its `#include "bdefs.h"`, and `/Yu` skips
everything above it, as retail's compile did: all ten of its functions
are now identical (`i_IntersectSweptSphere` 2,105 bytes -> retail's 587).

**The scorer** (tools 26a8abc, progress/README.md): the real misses were
functions whose bytes cannot place them. It now pairs by reference
(each identical function's relocated operands: the callee or vtable our
link wrote against the shipped one at the same offset; a vtable then slot
for slot, found by its already-identical slots when nothing identical
installs it), and within an object aligns in order before matching by
size. That placed all 32 `CLTServerInterface` methods by their vtable
slots, where the object join had put initializer thunks (13 of them
unplaced), and `i_IntersectSweptSphere` by its caller. On master's build:
no identical change; Lithtech.exe unwritten 54 -> 49, unplaced 1,215 ->
1,212 (12 KB fewer unplaced bytes), server.dll 5 -> 4 / 1,154 -> 1,153,
ServerDir.dll unwritten 131 -> 130, Object.lto 4 -> 3 / 15 -> 14.

**Score** (server.dll, master -> now): identical 2,503 -> 2,513, bytes
295,660 -> 298,707 (95.1% -> 96.1%), near 55 -> 38, unplaced 1,154 -> 15
(14,245 -> 221 bytes), unwritten 5 -> 17. Of the 1,154: about 1,120 real
extras (the initializer groups of 81 objects and what their shapes
labelled), 32 scorer misses (`CLTServerInterface`, `i_IntersectSweptSphere`
and its object). The unwritten rise is honest: 13 shipped functions of
the same shapes (two more groups: one `/O1` group at 0x10048696, just
before ltmem's block, and one in a library at 0x1004c170) were "covered"
only by our surplus thunks.

**Left.** `interface_linkage.obj` still has a group retail's lacks (it
cannot take the header: no `bdefs.h`), and the two groups above are ours
to find (the 0x10048696 object is not identified: retail's tail order
there is transformlt_impl, server_iltphysics, shared_iltphysics, the
group, ltmem). The 15 unplaced are short accessors
(`LTLibraryLoader`'s, `CounterFinal::StartMicro`, ...) retail inlined or
folded, and `bm_CreateHandleBinding`. **Lithtech.dsp very likely needs the
same** `/Yu"bdefs.h"` (Contract J.A.C.K.'s has it); at `/O2` `PI` folds,
so there it is the `WORLD_*` vectors -- left to the package working on
Lithtech.exe's initializers.

### headerinit

Lithtech.exe's 1,212 unplaced functions were mostly the same thing as
server.dll's (srvplace): `math_phys.h`'s nine initializers (`PI` by
`fld [1.0]; fld1; fpatan` -- it does not fold at `/O2` either --, `PI_2`..
19 bytes each, the `WORLD_*` vectors 31) in every object. Counting
`fpatan` (one per group): retail 56, ours 276. Retail's groups, placed
against our objects by the unique exematch hits after them, sit in:
`controlfilemgr`, `bdefs`, `client`, `client_formatmgr`, `clientmgr`,
`compress`, `counter`, `ltmodule`, `ltobjref`, `icommandlineargs`,
`modellt_impl`, `interface_linkage` (codeless; retail links it last, after
`client_iltvideomgr`, at 0x4b2200); ltmem's two objects; three of the
renderer's (`rendererconsolevars` 0x4c43b0, `memstats_world` 0x51e990,
`texturescriptinterpreter` 0x54bf10); RezMgr's `rezmgr` and `rezhash`;
nearly every Lib_UI object (no precompiled header there, as ours). Two
retail `fpatan`s are not groups (inside `ltmessage` 0x442e28, as ours,
and D3DX 0x4b4854).

**Change.** `Lithtech.dsp` precompiles `bdefs.h` like server.dsp
(`/Yc` in `bdefs.cpp`); the files above go without it; `lterror`,
`ltquatbase` and `transformmaker`, which do not include `bdefs.h` first and
have no group in retail, get `/FI"bdefs.h"` (with `/Yu` that takes their
group away too). `interface_linkage` and `world_tree` (retail: after
`winconsole_impl`) moved to retail's link order. `D3DRender.dsp`
precompiles `precompile.h`, `/Yc` on `rendererconsolevars` (the choice
between it and `memstats_world` is arbitrary: both have retail's group).
`udpdriver` stays without the header although retail's has no group: with
`/Yu` `CUDPDriver::ReallyJoinSession` (0x48caf0, 2,548 bytes) moves one
`mov X(%esp),%esi` and stops matching -- the only function either way the
precompiled header changed for the worse. Now 61 `fpatan` (retail 56).

**Score** (Lithtech.exe, master -> now): identical 5,883 -> 5,891, bytes
1,218,828 -> 1,224,417 (90.6% -> 91.0%), near 204 -> 191, unplaced 1,212
-> 135 (32,112 -> 11,263 bytes), unwritten 49 -> 53. The unwritten rise is
the six tiny shipped rows (5-27 bytes: thunks, a group's interior) that
were "near" only against our surplus initializers. The image's layout is
now within 0x400-0x600 bytes of retail's up to the renderer (was
0x9000-0xb700: `ReallyJoinSession` +0x610, `CLTVideoMgr::
StartOnScreenVideo` +0x540, `d3d_ReadExtraConsoleVariables` +0x570);
Lib_UI is +0x2d40 (was +0x12520). Other targets unchanged.

**Left.** Our extras against retail's set: `Lib_ILTSound`'s `iltsound`
(retail has none) and `rezfile` where retail has `rezhash` (ours does not
include `ltbasedefs.h` there; RezMgr is Jupiter's, so retail's include
lists probably differ), `udpdriver` (above). 54 of the 135 unplaced are
group members of retail's holder objects that the scorer leaves (the
19-byte `PI_x` twins: five per object), the rest Lib_UI `*_impl` functions
past the SecuROM pages and folded small functions. No other header
initializer shape has a surplus worth a change.

### 20. serverdir

**The cause was the source, not the compile.** Our `CServerDir_Titan.cpp`
was the LithTech Jupiter SDK's (March 2002), patched by hand to the 1.3
interface (`src/nolf2src/jupiter/serverdir.patch`): an earlier version
than retail's. Retail's strings (`ping_%d`, `frags_%d`, `hostport`,
`mapname`: GameSpy query keys) are not in it. The F.E.A.R. source release
carries NOLF2's own 1.3 server directory in `Dev/Source/libs/ServerDir/`:
the same `IServerDir.h` and `IServerDir_Titan.h` as the 1.3 release, byte
for byte, `DEFAULT_TITAN_PRODUCT_STRING ("NOLF2")`, `ClientResShared.h`
(its CMakeLists points at `../../NOLF2/ClientRes/Shared`), the GameSpy
support. Its WONAPI is the SDK's but for modern-compiler edits. With it
(`src/Game/Libs/ServerDir/`, committed; jupitersrc.py now copies WONAPI
alone and the patches are gone) 396 functions matched at once. The flags
(`/MD /W3 /GX /O2`, `/YX`) were right; the pch order no longer changes the
object (no pch, its own pch and stdafx's give the same code).

What was left, and why:
- `SetActivePeer` (+145 bytes): retail calls STLport's no-argument
  `push_back()`, which default-constructs in place; F.E.A.R.'s copy pushes
  a local `SPeerData` (a modern-STL edit). Changed back.
- The object's tail (37 unwritten, 0x10016d70..0x10017a40, and the lost
  `operator+(const string&, const char*)` at 0x100178a0) is `TitanTest.obj`:
  the initializers of its globals (`g_sWONCommunity = L"NOLF2"`,
  `g_sWONProduct`, `g_sWONCurPath = L"/NOLF2"`, `g_lWONServerList`,
  `g_sWONCDKey`) and the STLport code instantiated first there (the
  `operator+` is called only from WONAPI; its COMDAT comes from
  TitanTest.obj, first in link order). Retail linked `TitanTest.cpp` even
  with `_FINAL`: the console program is unreferenced and dropped by
  `/OPT:REF` (its strings too, `/O2` implies `/GF /Gy`), the globals stay.
  The .dsp now lists it. The Rich header agrees: retail has 13 cl 8966 C++
  objects; ours had 12 and now has 13, and the `0x04` counts match too.
  The built DLL is retail's size (479,232 bytes) and `CServerDir_Titan.obj`
  + `TitanTest.obj` (to 0x10017a40) differ from retail only in addresses.
- 4 unplaced (`~CWinSync_CSAuto`, `~CWinSync_CS`, `~CWinSync_Event`,
  `~_Node_Alloc_Lock`): in retail at the same addresses, but reached only by
  `jmp` from exception-unwind funclets, which `tools/enumfuncs.py` did not
  follow, so they merged into the rows before them. New rule 4e: the jump
  target of a funclet (`lea/mov ecx,<slot>` or `mov ecx,imm32`, optionally
  `add ecx,imm`, then `jmp rel32`) is a start. Every target gains
  (measured on master after headerinit): unplaced CShell 9 -> 2, Object
  14 -> 6, NOLF2Srv 9 -> 1, ClientFx 3 -> 1, Lithtech 135 -> 126, server
  15 -> 13; unwritten NOLF2Srv 2 -> 1; no recorded function lost.

**The function tables are derived** (`out/reference/*-functions.csv`), so
a tree with the old tables would score the new baseline wrong:
`build/progress.sh` now rebuilds them (`build/reference.sh tables`) when
`tools/enumfuncs.py` is newer than they are, and enumfuncs writes a new file
over the old one, never through a worktree's hard link.

Left: 75 `small` rows (647 bytes), functions too short to place by bytes.
WONAPI (middleware, not scored) was not examined: `exematch.py` finds
1,794 of our WONAPI.lib's functions in retail and not 858 (unreferenced
COMDATs among them), and the image's .rdata/.data differ from retail's.

### 21. unwritten

**Result** (against master after srvplace and headerinit, whose scorer
and precompiled headers had moved Lithtech.exe's unwritten 54 -> 53 and
server.dll's 5 -> 17). Lithtech.exe: unwritten 53 -> 8, identical 5,891 ->
5,928 (1,224,417 -> 1,240,436 bytes), near 191 -> 145, unplaced 135 -> 131
(false starts gone). server.dll:
unwritten 17 -> 0, identical 2,513 -> 2,527 (298,707 -> 299,415 bytes),
near 38 -> 34, unplaced 15 -> 9. The other images: unplaced down by 1-3 in five of
them, a launcher's unwritten 2 -> 1 (the enumeration fixes). One recorded
identical row lost on purpose: server.dll `sub_10009c15` was the body of
`dalloc` behind a zero-size test we did not have; `dalloc` now matches the
whole function at 0x10009c0b.

**What the unwritten rows were.** Most were not functions of their own:
- *False starts* (the enumeration): 74 dwords of `.rsrc` UTF-16 text in
  `.text`'s range, dwords in the copy protection's code section `.cms_t`,
  E8/68 bytes inside operands read as call/push targets, `gap` starts behind
  an operand's C3, and coincidental dwords in `.data`/`.cms_d`. They cut
  `CSoundMgr::Update` (0x4afb50), `CLTDirectMusicMgr::InitLevel`
  (0x43cdf0), `DrawDynamicParticles` (0x544960, four pieces),
  `d3d_DrawPolyGrid`, `d3d_D3DFormatToString`, `CD3D_Shell::BuildDeviceList`,
  `i_IntersectSweptSphere`, three shader `Flush`es, ltmem's and
  clientshell's header-constant initializers and more into pieces nothing
  could pair. Fixed generally in tools (`enumfuncs.py`: no pointers from the
  resource/relocation directories or a second code section; rule 4f, a
  lone `movl $vtbl,(%ecx) ; ret` behind padding), the rest by hand in the
  new `progress/Lithtech-screen-exclude.csv` (each row "NOT A FUNCTION:
  interior of X (0x...)", so its bytes go to X) and two
  `progress/extent-splits.csv` starts (~CPixelShaderMgr 0x509620, reached
  only by a thunk's jmp; 0x5546c0 is now rule 4f's).
- *The compiler's vector iterators* `??_H`/`??_I` (0x401000, 0x404920;
  server.dll 0x10001537): ours were there, identical, but `progress.py`
  dropped them from our side; now scored (`unlinked` where not linked).
- *`LockPVS`* (0x4c6c10): a console variable commented out in the fear
  tree; `d3d_TagVisibleLeaves` reads it.
- *ltmem's heap* (0x51eab0..0x51ec18, server.dll 0x10048cd0..0x10048def):
  `g_arySimpleHeaps[4]` and `g_GeneralHeap` of the fear tree's
  `ltmemheap.cpp`, unused, kept by their initializers (eh vector
  constructor: ltmem is /GX). `src/libs/ltmem/ltmemheap.cpp` with the fear
  tree's heap headers; nothing references it, so both links `/include` it
  (what pulled it into retail's links is not known; in the exe it lies after
  `d3d_optimizedsurface.obj`, ours after ltmemstats).
- *`dalloc`'s zero-size test* (server.dll 0x10009c0b), commented out in
  the fear tree.
- *The swept-sphere module* (0x437910 = SweptSphereToPolyEdges with Edge
  inlined, 0x438060 = SweptSphereToObjectCB with WorldModel inlined,
  server.dll 0x100109a6 = SweptSphereToPoint): retail compiles
  `intersectsweptsphere.cpp` with full optimisation; the fear tree's
  `#pragma optimize("", off)` / `("as", on)` is later. Without it all ten
  functions are identical in server.dll, and all six of Lithtech.exe's
  (where four of the ten are inlined).

**Left (8, Lithtech.exe).** 0x4cb620 and 0x4cc680: two of
the 14 `CRenderShader_*` destructors (retail has ten of 409 bytes, which
expand `~_Vector_base<CInternalSection>` inline, and three of 382, which
call it, 0x4cff70; all of ours are 382: a VC6 inlining-order question, see
guide 09); 0x4e6b00, a 97-byte `~_Vector_base` (72-byte elements) retail
keeps out of line, and 0x4f0720 (87) the same for 8-byte elements
(`SSectionRBIndex`); 0x501010 (117), `__unguarded_linear_insert` of a
shader's `SSectionRBIndex` sort (68-byte sections), out of line in retail;
0x4e94a0 (93, a shader member that releases the section vector and the
vertex buffer, many callers). All template code of `d3d_renderworld.obj`
whose inlining differs from ours (guide 09's budget and forward-only
inliner), or whose counterparts are among its wrongly paired instances --
the scorer's pairings inside that object are unreliable (package 9b), so
pair them by `callseq.py` before writing anything. The other two,
0x50a0c0 (27) and 0x558b20 (11), are small initializer-group rows that
became unwritten with headerinit's precompiled headers; not looked at.

**Merged with package 20** (serverdir), whose rule 4e (funclet jump
targets) and this package's tools are both in: Lithtech.exe has 9 unwritten,
not 8, and 128 unplaced. The ninth is 0x4e6760 (260 bytes), which rule 4e
splits off 0x4e6670: a destructor of a vector of 12-byte elements (two
pointers and a vector; it calls 0x458950, 0x505e50 and 0x49a340), right
after `CRenderModelInfoList::FreeListMemory`. Package 20 alone had paired it
(near) with `~CPixelShaderMgr`, which this package places at 0x509620, so
it is honestly unwritten now. Unplaced is this package's 131 less the three
functions rule 4e places (`~CClassMgr`, `ci_Term`, `~CSAccess`).

**cjacksrc** (`~/src/cjacksrc`, Contract J.A.C.K.'s engine, seeded from
this tree and then matched to CJ's retail with VC7.1). 446 of its 566
engine sources are still ours byte for byte; 120 differ. Its `RETAIL:`
hunks are CJ's code, so each one was checked against NOLF2's retail code
(imports at the site, the call sequence, a constant) before it was ported,
and measured. Ported and confirmed (identical unless said):
- `kernel/mem/.../de_memory.cpp`: `dalloc`'s zero-size test (both images).
- `world/src/intersectsweptsphere.cpp`: no optimizer pragmas.
- `kernel/src/sys/win/bindmgr.cpp/.h`: kernel32 directly, no
  `LTLibraryLoader` and no `bm_CreateHandleBinding`; `ltlibraryloader.cpp`
  left out of both projects (its functions were all unplaced; its 12-byte
  `OpenLibrary` had been standing in for `cnt_StartCounterFinal`, which now
  takes 0x41b3d0).
- `render_a`: `pixelshadermgr.cpp` (FreeShader tests the slot and re-reads
  the vector; the destructor at 0x509620), `tagnodes.cpp` (LockPVS),
  `modelshadowshader.cpp` (Direct3D 8's `D3DRS_ZBIAS`, both functions),
  `VertexBufferController.cpp` (streams before indices),
  `d3d_rendershader_lightmap.cpp` (ValidateShader's clamp order),
  `rendershadowlist.cpp` (RenderModelPieces leaves fog alone),
  `d3d_renderworld_occluder.cpp` (SplitPlane/SplitPlane2D go on over every
  outline), `d3d_optimizedsurface.cpp` + `d3d_surface.cpp` +
  `shared/.../renderstruct.h` (one 3D blit, whole tiles, no 0.51 clamp, no
  `BlitRequest::m_bUseOld`; `d3d_OptimizeSurface`'s tile edges),
  `3d_ops.cpp` (PVModelAspect; near, closer), `devicelightlist.cpp` (bytes;
  near, closer).
- `client`: `clientde_impl.cpp` (GetVersionInfoExt/GetPerformanceInfo left
  NULL), `consolecommands.cpp` (ShowVersionInfo's missing test;
  `docs/RETAIL_BUGS.md`), `clientmgr.cpp` (Render without the DrawPrim
  camera), `winclientde_impl.cpp` (cis_MaskedDraw's 16-bit template form;
  no `m_bUseOld`, which made cis_InternalScale/TransformSurfaceToSurface and
  cis_DoDrawSurfaceToSurface identical too).
- `kernel/src/sys/win/ltdirectmusic_impl.cpp`: CommandThread without COM
  set-up (now inlined in its bootstrap, identical), the constructor without
  `m_hThread = NULL` (identical), Term without CloseHandle and
  ChangeIntensity without the segment-state test (both read off retail's
  code, 0x43cc21.. and 0x43df17; still near, so not yet in
  `docs/RETAIL_BUGS.md`: the handle leak and the unchecked pointer are
  retail bugs to list once they match).
- `model/src/model.cpp`: no server-side deletion in ModelPiece::Term
  (server.dll 0x10015415 has no loop; size-exact near now).
Each retail-only difference is kept behind `#ifdef NOLF2SRC_MODERN` with the
fear tree's code (handle closed, pointer tested, function pointers set,
DrawPrim camera, the server's deletion, COM in the music thread, the
screen's aspect for the player-view model).

Tried and reverted: `clientshell.cpp`'s Term (CJ unhooks the net handler
only if it is still the shell's; NOLF2's does not: 0.98 -> 0.67).

**Where the two engines differ** (do not port): CJ's 24-byte engine
variables and anti-cheat list, the unguaranteed-data protocol (`s_client`,
`packetdefs.h`, `udpdriver`, `netmgr.h`), `GetUDPSocket`/`OpenSocket`, the
shared shader draw range and per-world sections (`d3d_rendershader_base.h`,
`d3d_renderworld.*`), CJ's render-style file layout
(`d3d_renderstyle.cpp`), ATI caps (`d3d_device.cpp`), the shadow tween slot
(`rendershadowlist.cpp`'s queue), `ps_UpdateParticleBoundingBox`,
`D3DFMT_W11V11U10` (NOLF2's image has none), CJ's console (`console.*`,
`winconsole_impl.*`), `clientmgr.h`'s resource-tree vector, the extra render
console variables, `ReallyClose_far` 10, VC7.1's MS STL instead of STLport.

**For later passes: cjacksrc functions to try next** (NOLF2 near, a cjacksrc
`RETAIL:` hunk not yet checked against NOLF2): `CD3DDrawPrim::DrawPrim`
(POLYGT4/FT4/G4/F4: only the last draw's result checked) and
`SetCamera`, `CD3D_Shell::BuildDeviceList` (the Intel T&L rule),
`CLightTable::LoadLightGroup`, `CD3DRenderStyle::CopyRenderStyle` /
`SetDefaults` (no Direct3D options), `CD3D_RenderBlock::ExtendSkyBounds`,
`CD3D_Device::PreCalcSomeDeviceCaps` (the SurfDesc size), and the
`d3dmeshrendobj_skel.cpp` signed bone index. The method that worked:
scratch scripts joined our scorer's pairs with cjacksrc's (`progress.py`'s
PLACED_SYMS/NEAR_PAIRS, cjacksrc's read with its own tools under
`python3 -B` so nothing is written there), listed every cj hunk marked
`RETAIL` beside our status for that function, and compared each near
function's masked bytes before and after a change.

### exeplace

Lithtech.exe's larger unplaced functions, rebased onto `integrate` (7057491):
where unwritten made the same change (bind manager, the 3D blit and
`m_bUseOld`, the client function slots, the DirectMusic thread,
intersectsweptsphere's pragmas, tile edges, the split rows), master's is kept.

**Added here.**
- `SoundSys` keeps retail's null-pointer `Term` (RETAIL_BUGS.md, M-E64):
  the extra block keeps it out of its callers, so `CSoundMgr::Update`
  (2,427 bytes) and `SoundSys` match.
- `d3d_SwapBuffers` locks a pixel of the back buffer under `VSyncOnFlip`
  before presenting (0x51cfef; release build only, M-E63).
- `CD3DRenderStyle` has no Direct3D options until they are set, and
  `CopyRenderStyle` does not copy them (both match).
- `ps_UpdateParticleBoundingBox` is retail's (moved to the system's
  position, not rotated or scaled) and `inline`, expanded in both callers;
  `ps_EndUpdatingPositions` pairs with 0x460230 (x87 order of the half-box
  left).
- `ReleaseTextureHandle` only counts down in the release build (0x421b50);
  the modern build keeps Jupiter's free (M-E65). M-E66 documents the
  DirectMusic thread's COM set-up kept in the modern build.

**Score against 7057491.** Lithtech.exe 5,928 -> 5,936 identical (+5,211
bytes), unplaced 128 -> 126, unwritten 9.

**Left.**
- The CRenderShader_Base template family: 13 `~CRenderShader_*` (409
  bytes; ours calls `~_Vector_base<CInternalSection>` out of line, retail
  expands it: one unit of inline budget short, shown by padding the base
  destructor), `Lock`, `push_back()` (ours sets an EH state after
  `_M_insert_overflow` for the `_Tp()` temporary; removing `~allocator`
  loses 185 functions of the object, a user-declared `CRenderBlockData()`
  changes nothing), `SortSections`.
- Twelve catch blocks of vector reallocations after a `ret $0xc`
  (0x4f0d6d..0x4f45cd) are scored as near to our `FinalizeUnlock`s;
  marking them NOT A FUNCTION frees eight `FinalizeUnlock` instances retail
  seems to expand, so unplaced rises.
- The Lib_UI tail in the SecuROM pages could be placed against the MP
  demo's plaintext (`tools/demoimports.py plain`) if progress.py matched
  the `encrypted` range against it.

### rendershader

The CRenderShader_Base template family (d3d_rendershader_base.h).

**Found.** Retail's d3d_renderworld.obj compiles the shader template in a
different order from ours: each `CRenderShader_Base<X>`'s virtual functions
follow its destructor (`~Base` at 0x4d1ce0, then PreviewRenderBlock,
PreviewSection, Lock...) and come after the STL helpers ours compiles later,
and InitRenderBlocks/SortSections come after the `_M_insert_overflow` group.
VC6 instantiates an out-of-class template member later than an in-class one:
with every member function of `CRenderShader_Base` defined outside the class
(the constructor stays in it) ours takes retail's order. The order decides
exception states: a function compiled after the implicit
`~_STL_alloc_proxy<T>` (an empty `ret`) registers no state for it (measured
with throwaway files: `~_Vector_base<uint>` compiled after the proxy's
destructor has no EH frame, one compiled before has). That was the extra
state in `push_back()` (the `_Tp()` temporary's vector) and the EH frames of
`~CRenderBlockData` (0x4f0780) and `~vector<SSectionRBIndex>` (0x4f0720,
which ICF folds twelve instances into). Lock's locked-vertex push is the
default `push_back()` (retail stores nothing on the fast path; no `plv`).

**Score** (master a906dd0): Lithtech.exe identical 5,936 -> 5,983 (+30,909
bytes), near 137 -> 81, unwritten 9 -> 6, unplaced 126 -> 118. Now
identical: all 12 Lock and push_back(), the 12 `_M_insert_overflow` of the
render-block vector (0x4f0b90.., whose catch blocks at 0x4f0d6d.. were the
"FinalizeUnlock" nears), FinalizeUnlock (0x4e94a0), 0x4e6b00, 0x4f0720,
six SortSections.

**Left.**
- The destructors: ours still 382 bytes for the ten direct ones (0x4cb620
  and 0x4cc680 unwritten, eight near) and ~CRenderShader_Gouraud (404).
  The inline budget is tight: dropping `m_aVBs.clear()` (a probe) inlines
  the last `~_Vector_base<CInternalSection>` in all of them, fullbright ones
  included (retail's three fullbright destructors, 0x4cca40.., must stay 382
  and do now). A dead `ASSERT` in `~Base` moved the fullbright cut to the
  render-block vector instead: the decision is per call site against the
  size so far, not a fixed depth. `std::vector<SVertex*>` for the locked
  vertices also inlines it in all 13 but loses Lock and FinalizeUnlock.
  Next to try: CInternalSection's and CRenderBlockData's members out of
  class like the shader's (it changes which callees are compiled before the
  derived destructors, compiled right after AllocShader).
- 0x501010 (`__unguarded_linear_insert`) and the other SortSections; Flush
  (+53, register allocation, not inlining).
- exematch counts over one object are inflated by ICF duplicates; measure
  with `make progress`.

### smallverify

A measurement change, no code work. `small` functions (fewer than 8
unmasked bytes, placed by shape) are now verified in the linked images:
tools/progress.py builds a mapping of our addresses to shipped ones from
the identical functions (their relocated operands, typed by the COFF
relocation -- exematch.parse_obj_masked can now return the types --, their
own addresses, the slots of vtables they pair, import slots by name; any
contradiction dropped), and a small function whose unmasked bytes match
and whose every operand maps to the shipped operand at the same offset
is identical. Repeated to a fixed point (a verified function's address
maps too). It is tried at the address its own maps to, at its shape
placement, and (all operands mapped) at any same-length function, so many
are moved off the arbitrary sibling the shape placement gave them.

**Score against 87380c5.** small -> identical: Lithtech.exe +278,
server.dll +306, ServerDir +40, snddrv +16, NOLF2.exe +28, NOLF2Srv +75,
CShell +921, Object.lto +2,515, ClientFx +24 (4,203 functions, +26.7 KB).
No recorded identical lost. server.dll unwritten 0 -> 2, accepted: the
join had placed ReadObject (CLTMessage_Read_Server) at 0x100135f2 by
object order, and it is now proven identical elsewhere; transformlt_impl's
`_$E29` sat at 0x10048b60 by shape and an operand refutes it there.
Lithtech.exe unplaced 118 -> 119, accepted: with the new anchors the
join's link-order alignment no longer places d3d_renderworld's
`CRenderShader_Base<..DualTexture..>::PreviewSection` (458 bytes); the
short initializers counted by shape only change names.

**Left.**
- About 1,500 functions stay small: an operand of theirs (mostly a BSS
  global or a string only initializers reference) is in no identical
  function. A mapping by symbol + offset from our .map (a reference to
  g+8 when identical code only names g+4) would verify more; so would
  mapping the C runtime's statics (`_atexit`) by name or bytes.
- `tools/progress.py --refuted[=target]` lists ~205 refuted ones
  (Lithtech 62, server 34, CShell 52, Object 39, ClientFx 7, snddrv 5,
  NOLF2Srv 5, ServerDir 1). Most are still shape misplacements among
  sibling initializers whose right address is held by another unverified
  one (e.g. CShell's `_$E` of VehicleMgr.obj, Lithtech's model.obj
  `_$E34..40` each naming g_ModelMgr's neighbour). A swap whenever the
  holder is merely unmapped at the vacated address made the count worse
  (1,357) in a first try -- something in that pass is wrong; worth
  redoing as an assignment. Candidates for real differences:
  ServerDir `??1CSDTitan_RequestEntry_Noop` installs
  `??_7CSDTitan_RequestEntry` where retail installs another table;
  Lithtech `??1CRezTypeHashTable` calls a `~CBaseHash` other than the one
  identical code calls; the `ObjectBank<..>::AllocVoid` instances in
  CShell, Object.lto and NOLF2Srv call another `Allocate` than ours.

### enginenear

The engine's near functions outside the `CRenderShader_Base` template
family (that family is package rendershader's).

**Matched.**
- `server_interface.cpp` (server.dll, 28 functions at once): retail's
  `CLTServerInterface` methods have no `CSEntry` wait. Jupiter's file
  defines `#define CSENTRY CSEntry entry(CLTServerInterface *pInterface);`,
  which declares a function: retail's source used the macro, ours the
  object. The release build uses the macro; the modern build keeps the
  wait (MODERN.md M-E67).
- `game_serialize.cpp`: `sm_SaveObjectData` (2,459 bytes) names the buffer
  size in a local before `resize`; `sm_SaveObjects` and `sm_RestoreObjects`
  free the buffer with `s_cTempBuffer.swap(std::vector<uint8>())` (a
  temporary, `this` the global: retail loads the global's fields first).
- `d3ddrawprim.cpp` (as cjacksrc): the `LT_POLYGT4`/`FT4`/`G4`/`F4`
  `DrawPrim`s check only the last draw's result; the batched `GT4` path
  colours all six vertices from vertex 0 (RETAIL_BUGS.md); `SetCamera`
  leaves the local viewport's size unset (RETAIL_BUGS.md); both fixed in
  the modern build (M-E68). `SetTransformMode` tests `m_pCamera`, not
  `pCamera`, in the world case.
- `light_table.cpp` `LoadLightGroup`: STLport's no-argument `push_back()` /
  `push_front()` (the 0x4395a0 "near" was list `insert(pos)`, not
  `TVector3::operator+`).
- `d3d_device.cpp`: `PreCalcSomeDeviceCaps` sets `SurfDesc.Size`;
  `FreeDevice` does not clear `m_pD3DDevice` itself (`ResetDeviceVars`
  does). `clientshell.cpp` `Term` leaves `m_hFileIDTable` (modern keeps
  the clear, M-E67).

**Score** (against a906dd0): Lithtech.exe identical 5,936 -> 5,951
(+10,097 bytes), near 137 -> 122, unplaced 126 -> 125, unwritten 9;
server.dll 2,527 -> 2,555 (+1,566 bytes), near 34 -> 6, unplaced 8 -> 7.
Rebased onto 1d8f505 (tools 0593529): Lithtech.exe 6,261 -> 6,279
(+10,135 bytes), unwritten 6 -> 5, unplaced 119 -> 117; server.dll 2,833
-> 2,860 (+1,563 bytes), unplaced 8 -> 7. The release build's `make test`
(main menu into C01S01) plays and draws normally with `SetCamera`'s
viewport size left unset, as in retail.

**Left** (not started: the package was stopped here).
- Size-exact, register or reload order only: `CLTCommonServer::
  SetObjectFlags` (three parameter reloads after calls in another order),
  `CUIBitmapFont`'s constructor, `d3d_DrawPolyGrid`. `ICommandLineArgs
  CommonImp`'s constructor and `CUIInterval_Impl::GetRange` are mispaired
  (0x4ef3e0 is another class's constructor).
- cjacksrc hunks not yet checked against NOLF2's bytes: `CD3D_Shell::
  BuildDeviceList` (the Intel T&L list, -34), `CD3D_RenderBlock::
  ExtendSkyBounds` (+36), `d3dmeshrendobj_skel.cpp` (signed bone index,
  device `SetTransform`), `rendermodelinfolist`/`rendermodelpiecelist`/
  `classmgr`/`world_blocker_data` `resize(0)` for `clear()` (cj's
  `FreeListMemory` neighbour 0x4e6760 is still unwritten), `CD3DRender
  Style::SetDefaults` (-27), `ltdirectmusic_impl` Term (+42) /
  ChangeIntensity (+8).
- `CD3D_Device::FreeAll` (+2) and `~CD3D_Device` (-14) were not re-checked
  after the `FreeDevice` change; `OnConsoleVar` (+3) and `LoadPixelShader`
  (+2) differ inside inlined `CPacket_Read`/vector code.
- server.dll's remaining six: `LAlloc::~LAlloc`, `CLTServer::CLTServer`,
  `ReadObject` are pairing artifacts against initializer-like retail rows;
  `ModelPiece::Term` (size-exact), `CUDPDriver::Update`,
  `i_IntersectSegment`.
- The unwritten 0x50a0c0/0x558b20 initializer rows were not looked at.

### exersrc

Lithtech.exe's resources (the `Lithtech.exe:rsrc` target). Nine of the 27
differed, all from one cause: `lithtech.rc`'s `IDR_MAINFRAME` was the
Jupiter tree's `idr_main.ico`, four images, where retail's group icon 128
has five (32x32 16 colours, 16x16 256, 32x32 256, 16x16 16, 48x48 256, in
that order). rc.exe numbers icon and cursor images from 1 in one sequence,
so ours had icons 1-4 and MFC's help cursor (`AFX_IDC_CONTEXTHELP`, 30977,
two images) as cursors 5-6; retail has icons 1-5 and cursors 6-7. The
cursor itself is the toolchain's `afxres.rc` `res\help.cur`, byte for
byte. build/all.sh now reads retail's icon out of the retail Lithtech.exe
at build time (step 2c, `tools/retailextract.py art`, a new general
command) into `src/Engine/runtime/winbuild/lithtech/res/lithtech.ico`
(ignored, not committed), and `lithtech.rc` names it; `idr_main.ico` is
gone. The modern build shares the script and the step.

**Score** (against dcd50ad): Lithtech.exe:rsrc 18 -> 27 of 27 identical,
9,772 -> 18,762 bytes (100%), near 7 -> 0, unwritten 2 -> 0. Code
unchanged.

### unwritten2

The last twelve unwritten rows (Lithtech.exe 5, server.dll 2, Object.lto
2, NOLF2.exe, NOLF2Srv.exe, ClientFx 1 each). 0x4e6760 and 0x558b20 of
the earlier lists were already identical at 3de813c.

**Fixed: rows that were two functions.**
- *atexit exit thunks.* `mov $&obj,%ecx ; jmp ??1Class` (10 bytes), its
  address pushed and handed to atexit, and the destructor it jumps to,
  inlined everywhere else so nothing else references it: one row matching
  neither. Lithtech.exe 0x50a0c0 (~CScreenGlowMgr at 0x50a0d0, `add
  ecx,0x220 ; jmp ~CRenderStyleMap`; ours was always identical), server.dll
  0x100135f2 (ltmodule's `_FILE_SHUTDOWN` destructor at 0x100135fc behind
  a `jmp $+5`), NOLF2Srv.exe 0x4014e0, Object.lto 0x100047a0 and ClientFx
  0x10011b40 (the same, check_delete_pointers inlined). tools enumfuncs
  rule 4g; it also finds ~CPixelShaderMgr 0x509620, so that extent split
  is gone. Rule 4c now takes the initializer a `$E` thunk calls (`call
  ??__E ; jmp registrar`) as well: Object.lto 0x1016c1f0's row held
  CDebrisMgrPlugin's constructor 0x1016c200. 9 to 27 new starts per
  image, each checked.
- NOLF2.exe 0x407950 held the launcher's dummy `Direct3DCreate8`
  (0x407980, `xor eax,eax ; ret 4`, unreferenced) behind its int3 padding:
  an extent split.
- The three DLLs' old identical rows at 0x4013cd / 0x1000468d /
  0x10011a2d were our shutdown destructor matching as a twin INSIDE
  DatabaseItemCountDec (its inlined check_delete_pointers); dropped, the
  destructor is identical at its own address.

**Fixed: server.dll 0x10048b60** (`movl $0,0x1005eee8`). The last
initializer of ltmemtrack.obj, after its nine header-constant
initializers (0x10048a40..): g_curAllocInfo (0x1005eed0, 100 bytes,
ending where the constants' data start, 0x1005ef34) with the fear tree's
constructor clearing m_nFlags (+0x18). Retail's server.dll links ltmem,
ltmemstats, ltmemtrack, ltmemheap in that order; nothing calls ltmemtrack
or ltmemheap, /OPT:REF keeps only data and initializers. ltmem.lib now
has the fear tree's `ltmemtrack.cpp`/`.h`; server.dll `/include`-s
`g_curAllocInfo` (in place of `g_GeneralHeap`), and ltmemtrack's
references pull ltmemheap in after it. Lithtech.exe still `/include`-s
g_GeneralHeap; its retail image shows no such store after ltmemstats.

**Score** (against 3de813c): unwritten 12 -> 4; identical Lithtech.exe
+1, server.dll +2, Object.lto +2, NOLF2.exe +1 (+9 functions, 3 twins
re-paired); unplaced Lithtech.exe 117 -> 115, server.dll 7 -> 3,
NOLF2.exe 7 -> 6, Object.lto 6 -> 4, NOLF2Srv 1 -> 0, ClientFx 1 -> 0.

**Left (Lithtech.exe 4, all d3d_renderworld.obj inlining).**
- 0x4cb620, 0x4cb7f0, 0x4cc680: three of the ten 409-byte
  `~CRenderShader_*` (the s_bValidateRequired ones). Ours are 382 for all
  ten: the last member destructor, `~_Vector_base<CInternalSection>`, is a
  call, retail expands it (seven pair as near, three have nothing left to
  pair). Probe: `m_aVBs.erase(begin(), end())` for `clear()` (same code,
  one level less) frees budget, but VC6 spends it at the top, expanding
  `copy` into `__copy` (392 bytes, still calling ~_Vector_base): the budget
  is spent top-down here, so a saving must come after the VB loop.
- 0x501010: `__unguarded_linear_insert` of the Lightmap_Texture family's
  sort (68-byte sections; texture, fullbright, texture effect). Retail's
  `__final_insertion_sort` there (0x4fced0, near) expands
  `CSection_Lightmap_Texture::operator==` inside the unguarded insertion
  loop and then calls `__unguarded_linear_insert` out of line in the
  short-range `__insertion_sort`; ours calls `??8` in the loop and expands
  the last insert (690 bytes). The Gouraud_Texture family (three-field
  operator==, no section constructor) does what ours does in both, and is
  identical (0x4f70c0) -- so the Lightmap_Texture difference is about
  that operator== (or its section's constructor), perhaps whether it was
  compiled before the sort; not resolved.

### sortlead

Both halves of that lead tried (Lithtech.exe, against 68d25fb):
- **The order of `CSection_Lightmap_Texture`'s operators** (`==` before
  `!=`, so `!=` could inline it): no change at all, not one byte; `??8`
  stays out of line and folded with the EnvMap and EnvBumpMap twins.
  VC6 does not decide this by declaration order. Reverted.
- **No user-declared constructor** on the Lightmap_Texture family's
  sections (`CSection_Lightmap_Texture`, `_Detail`, `_EnvMap`,
  `_EnvBumpMap`, `_DualTexture`; each `FillSection` sets every field, so
  nothing reads them unset; `CSection_Lightmap`, which holds a texture
  reference, keeps its constructor): kept. Identical 6,280 -> 6,285
  (+1,781 bytes, 7 new: 0x4ddad0 436 bytes, 0x4df560, 0x4e0ff0, 0x4e2ce0,
  0x4ef3e0 -- the "another class's constructor" pairing of enginenear --
  0x4f4a20, 0x4068b0), unwritten 4 -> 3 (0x4cb620 and 0x4cb7f0 now pair as
  near; 0x4cb9c0 and 0x4cc680 are the two left), unplaced 115 -> 113. Two
  6-byte `mov eax,N / ret` rows counted by shape (0x448110, 0x4cb7c0) went
  from identical to small, a re-pairing (ACCEPT_LOSSES). Retail's sections
  were plain structs, as the Gouraud family's are.
- 0x501010 itself is still unwritten and 0x4fced0 still near: with the
  sections plain, ours still calls `??8` in the unguarded loop and
  expands the last insert. Not the constructor, not the order; what is
  left to try is the CInternalSection side (its `operator<` written with
  `==` rather than `!=`, or the texture-effect compare first), or
  CShaderSection being the section itself rather than a base.

### remaining (the encrypted pages; what is left)

- **The encrypted pages read for placement.** progress/targets.py gives
  Lithtech.exe `readable` (out/mpdemo/Lithtech-readable.exe, made by
  build/progress.sh from rez/'s demo chunks with tools/demoimports.py
  extract + plain); tools/progress.py enumerates and compares from it,
  the rows there stay `encrypted`. Lithtech.exe unplaced 113 -> 64 (tools
  433cecf); then the shape count (short functions covered by count) also
  takes the shipped supply from those pages: 64 -> 27 (tools c3a8d77).
  The whole project: unwritten 3, unplaced 128 -> 42.
- **`CInternalSection::operator<` with `!(a == b)`** for `a != b`: not one
  byte different; reverted (VC6 flattens the `!=` already).
- **0x4fced0 / 0x501010, read again.** Retail's sort there is over 8-byte
  index entries (an index into the 68-byte sections and one more dword)
  through a comparator object: in the guarded insertion it calls
  CInternalSection's `operator<` (0x4ff050) and the comparator (0x4feeb0)
  out of line, and in the unguarded part it inlines the comparator's
  first-field test (`cmp edx,ebx` at 0x4fd031, the sections' m_pTexture).
  The notes above took it for a sort of the sections themselves; the
  comparator's shape (SSectionRBIndex and its functor in
  d3d_renderworld.cpp) is where to look next. The four out-of-line
  `??8CSection_Lightmap_Texture*` (37 bytes, unplaced) are the same
  question: retail has no out-of-line copy.
- **Left, Lithtech.exe (27 unplaced):** about 11 PI-group initializers,
  the surplus of about two groups (readable retail 62 groups against our
  64: `udpdriver`, kept for CUDPDriver::ReallyJoinSession, and `iltsound`
  or `ltmemheap`); six 10-byte `_$E` initializers (D3DRender's
  common_draw/d3d_draw/drawvolumeeffects, Lib_UI's cuiwidget_impl and
  cuiwidgetmanager); the four `??8` above; CSegmentState's 64-byte
  `??_E` (our link keeps its vtable while everything that creates one is
  dropped); `CLTClient::Math`, `r_IncObjectFrameCode`. Elsewhere 15, all
  1-13 bytes but Object.lto's `~CSoundButeMgr` (276).

### round2

- **`__forceinline` on the Lightmap_Texture sections' `operator==`**
  (`CSection_Lightmap_Texture`, `_Detail`, `_EnvMap`, `_EnvBumpMap`; not
  `_DualTexture`, whose copy retail has): retail has no out-of-line copy.
  Lithtech.exe unplaced 27 -> 23, identical +10. The sort (0x4fced0) now
  has retail's main part (its first `ret` at the same offset, the same
  calls); only the short-range tail differs: retail calls
  `__unguarded_linear_insert` (0x501010) and `__copy_backward` out of
  line, ours inlines the first. Its inline budget runs out later than
  retail's for a reason not found.
- **Build 124.** Retail 1.3 is build 124 ("Build 124",
  `GetSaveVersion` = 0x7c at CShell.dll 0x1003d1e0); the source release
  says 123. Now 124 in both builds; the modern build keeps
  `kSaveVersion__1_3` at 123 for saves of this project's earlier builds
  (MODERN.md M-G91). CShell.dll and Object.lto +1 identical, -1 unplaced.
- **Tried, reverted:**
  - `iltsound` without the physics header (`/D __COORDINATE_FRAME_H__`):
    `ltrotation.h` needs it (line 37). The group stays.
  - `ltmemheap`'s group is not surplus: retail has it, after
    d3d_optimizedsurface (0x51e990; its header comment). The PI surplus is
    `udpdriver`'s (kept) and `iltsound`'s.
  - The 10-byte `_$E` (D3DRender, Lib_UI) are `mov ecx,&holder / jmp
    ~CAPIHolder` thunks of `define_holder`s. Removing the six unused
    D3DRender holders (common_draw, d3d_draw x2, drawsky,
    drawvolumeeffects, tagnodes) unplaced 23 -> 17 but unwritten 3 -> 8:
    retail has five of them (new rows beside d3d_draw, tagnodes,
    drawvolumeeffects and two more); drawsky's alone cost two identical
    10-byte rows. The thunks are all one shape, so which holder is the
    extra one cannot be read from the score.
  - Object.lto's `~CSoundButeMgr` (276 bytes) is retail's 0x1016c9f0 but
    two stack slots (`[esp+0x10]`/`[esp+0x14]`) swapped; the same source is
    identical in CShell.dll, so it is how Object.lto's build compiles
    SoundButeMgr.cpp (its defines or inline budget), not the source.
