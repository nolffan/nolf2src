# Can the "F.E.A.R." engine tree seed Lithtech.exe / server.dll?

Scope: `../fear/Dev/Source/runtime` (+ `../sdk`, `../libs`, CMake
lists, `runtime/winbuild`) against retail NOLF2 1.3 `Lithtech.exe` and
`server.dll` (`out/reference/`). Read-only study. Intermediates are in
`lithtech/fear/` (scripts `strmatch.py`, `revmatch.py`, `fnattr.py`,
`seqcmp.py`, `runs.py`, `perfile.py`, `mapparse.py`, `filesz.py`, `skel.py`;
their outputs `*-seqcmp.txt`, `*-order.txt`, `perfile.txt`, `sdkdiff.txt`,
`fearmap-objsizes.txt`, `lt-missing.txt`, `srv-missing.txt`).

## 0. Main finding: the tree is LithTech Jupiter, not Jupiter EX

`Dev/Source/runtime` is **not** F.E.A.R.'s engine. It is the plain LithTech
**Jupiter** engine. That is NOLF2's own engine line, as Touchdown Entertainment
distributed it in 2004–2006, ported to Direct3D 9 and, partly, to Linux. The
evidence:

* `runtime/winbuild/lithtech/Lithtech.map` (with its `.pdb`) is a link map of
  this runtime. Its time stamp is 2006-03-14, from `Eval_Lithtech.sln`
  (VS.NET 2003), and it links `d3d9`/`d3dx9`, `LIB_D3DRender`, `Lib_UI`,
  `Lib_DShow`, `Lib_ILTSound`. It has no Havok. F.E.A.R.'s actual engine
  (Jupiter EX) is only present as binaries, in `Dev/Runtime/EngineServer.dll`
  and the other files there. The F.E.A.R. *game* code under `Dev/Source/FEAR`
  uses Havok, but the runtime does not.
* The top-level `CMakeLists.txt` builds NOLF2 and Tron 2.0 game code
  (`BUILD_NOLF2`, `BUILD_TRON`) against this runtime. Source comments
  mention "NOLF2 issue #2008" (drawmodel.cpp) and "fast enough for Tron"
  (d3d_shell.cpp).
* **The SDK is nearly identical to NOLF2's SDK.** Of the 108 header and
  source files in `src/Engine/sdk/inc`, 76 are identical apart from
  whitespace. `iltserver.h` has 0 differing lines and `iltclient.h` 176 of
  3,628, all of them additions: `GetRendererStats`, vertex and pixel shader
  methods, dropped default arguments. `ltbasedefs.h` gains
  Unicode/Linux helpers, and `ltrect.h` was rewritten. The physics headers
  are the same apart from small changes in math_phys and vector. Nothing
  from NOLF2 is missing. The new headers are esd/, iltrendermgr,
  ilttexturestring, libltdiagnostics, ltcrashhandler, LTFontParams,
  ltgraphicscaps, ltrendererstats, memblockallocator, state_mgr and
  linuxoptim. Details: `fear/sdkdiff.txt`.
* The Mac NOLF2 engine's embedded source paths (`lithtech/mac-nolf2-srcpaths.txt`,
  from another agent) use this exact layout: `Source/Engine/Runtime/client/src/...`,
  `render_a/src/sys/d3d/...`. 29 of its 31 runtime paths exist here. The two
  missing are `qtvideomgrimpl.cpp` and `render_a/.../pixelshadermgr.cpp`.
  The latter is NOLF2's D3D8 pixel-shader manager, which Jupiter later
  replaced with `ltpixelshadermgr.cpp`.

In short, this is the same codebase as retail Lithtech.exe/server.dll, about
three to four years later. That is the same situation as with snddrv.dll.

## 1. Inventory of runtime/ (files, lines of .cpp/.h/.c)

| module | files | lines | what it is | post-2002 / not NOLF2 |
|---|---|---|---|---|
| kernel | 144 | 43,463 | `src/sys/win`: client.cpp (WinMain), input (DInput8), dsys_interface, render.cpp (renderer glue), DirectMusic, Bink video, stringmgr, interface_helpers, bindmgr, threads. `net/`: netmgr, packet, udpdriver, localdriver. `io/`: de_file. `mem/` | linux/ variants, `dshowvideomgrimpl` (DirectShow, © 2004-05 Touchdown), `ltrendermgr_impl` (D3D9 render targets), `DDPerfCounterManager`, `InputSim` (mostly), `toport/`, xbox #ifdefs |
| client | 81 | 26,214 | CLTClient (clientde_impl, winclientde_impl), CClientMgr, CClientShell, shellnet, consolecommands, console, predict, particles, polygrid, sprites, linesystem, volumeeffect, client_ilt* | texturestring/lttexturestring/texturestringimage, customfontfilemgr, memorywatch, perfcountermanager, cloaderthread/client_loaderthread, watermark.cpp (182 KB, mostly data) |
| server | 44 | 17,534 | CLTServer (serverde_impl), CServerMgr, s_client, s_net, s_object, game_serialize, classmgr, server_ilt*, soundtrack, sloaderthread | none identified |
| shared | 109 | 25,087 | objectmgr, moveobject, moveplayer, collision, engine_vars (console vars), dtxmgr, pixelformat, compress, concommand/conparse, ltmessage, classbind, ftserv/ftclient | stacktrace (release stub only), linux headers |
| world | 34 | 10,178 | world_shared_bsp, world_client/server_bsp, world_tree, world_blocker_*, particle blocker, light_table, fullintersectline, intersectsweptsphere | none identified |
| model | 17 | 5,564 | Model and CModelMgr, model_load (.ltb), animtracker, transformmaker | small additions (piece-count check) |
| physics | 19 | 4,910 | LT's own GJK/OBB/AABB collision library and LTCollisionMgr. **Not Havok** | not linked into Lithtech.exe in either version: retail has only the `ILTCollisionMgr.Client/Server` holders |
| render_a | 166 | 48,454 | the D3D renderer (`LIB_D3DRender`): device and init, textures and surfaces, render blocks and occluders, render-shader classes (gouraud, lightmap, dynamic light), model render objects (rigid, skel, vertanim), model shadows, screen glow, texture scripts, polygrids, sprites, particles, volume effects, tagnodes (visible sets), console vars, nulldib | **ported to D3D9**: 27 files use `IDirect3D*9`. New: LTEffect*/lteffectshadermgr/ltvertexshadermgr/ltpixelshadermgr/LTShaderDeviceState (HLSL effects), rendertarget(mgr), rendererframestats, SimD_* (partly). About 8.6K lines are D3D9-only |
| render_b | 6 | 3,502 | `CD3DDrawPrim` (ILTDrawPrim) and `CSysTexInterface` (ILTTexInterface). Linked into the exe objects, not the renderer library | effect-shader ID, fog enable, save/restore viewport added |
| sound | 21 | 15,590 | client CSoundMgr, soundbuffer, soundinstance, wave; `iltsound.cpp` (Lib_ILTSound); `sys/s_dx8` = snddrv.dll (already done); s_nul | DX8 effect filters (Chorus, Compressor...) |
| ui | 241 (212 of them FreeType) | 88,592 | Lib_UI: CUI widgets, polystrings, CUIFontManager, CUIBitmapFont, CUIVectorFont (GDI) | the bundled freetype-2.0.1 is not used: no FreeType strings in retail. Retail's vector font uses GDI (`GetGlyphOutlineA`, `AddFontResourceA`) |
| esd | 59 | 12,044 | RealNetworks audio/video, RealFileSystem | **absent** from retail (0 of 431 strings). LITHTECH_ESD is off |
| info | 3 | 685 | COutputRedir (ILTOutputRedir) | not in retail (no CLTOutputRedir interface) |
| controlfilemgr | 2 | 1,048 | control-file parser (DirectMusic .txt) | present, the first object of retail |
| lithtemplate | 3 | 546 | ltt_* containers | header-only |
| winbuild | – | – | lithtech.rc/res, ltmsg, server.def/.rc, **Lithtech.map + .pdb (2006)** | the map gives a size per object (below) |

There is nothing for x64 (no `_WIN64`) and no Havok in runtime/.

`libs/` holds Lib_Lith, StdLith, ltmem, RezMgr, zlib, ButeMgr, CryptMgr,
RegMgr, LTGUIMgr, ServerDir, WONAPI, dtxmgr, Lib_DShow and others. NOLF2's
own release already has most of these (`src/libs/`). RezMgr is the exception
(see section 5).

The executable's project lists the files it compiles: `runtime/client/CMakeLists.txt`
(EXE_Lithtech) and `runtime/server/CMakeLists.txt` (DLL_Server). In those
lists, server-side sources are compiled into the exe a second time, as in
retail.

## 2. Evidence each module is in retail

### 2a. Strings in both directions

**Retail to Jupiter.** Of the 2,490 strings of 8 or more characters in
Lithtech.exe's `.rdata`/`.data`, 1,937 occur literally in the Jupiter source.
Of the 556 that do not, 330 are made by macros, so their text is not
literal in the source:
* `I*.Default` and `__search_marker_*` come from the interface macros.
* `LT_INVALIDPARAMS` comes from `#err` in RETURN_ERROR.

The rest are not engine code:
* IJG libjpeg 6 messages, which belong to d3dx8.lib.
* D3DX's CPU detection (`DisableD3DXPSGP`, `AuthenticAMD`).
* Import names and MSVC runtime symbols.

**Every engine-authored string in retail exists in Jupiter.** The only
differences are whitespace ones: `(CLTSoundMgrServer::PlaySound:
PLAYSOUND_GETHANDLE ...)` with one space where Jupiter has two. server.dll
gives the same picture (758 of 910; the misses are of the same kinds).
Lists: `fear/lt-missing.txt`, `fear/srv-missing.txt`.

**Jupiter to retail** (`fear/strmatch.py`; literals with `#include` lines
removed; "any" means found in Lithtech.exe, server.dll or the pre-release
exe):

| module | literals | found | % |
|---|---|---|---|
| kernel/net | 84 | 79 | 94 |
| model | 50 | 48 | 96 |
| server | 80 | 72 | 90 |
| world | 17 | 15 | 88 |
| shared | 141 | 114 | 81 |
| render_a | 511 | 396 | 77 |
| client | 207 | 156 | 75 |
| kernel/src | 290 | 179 | 62 |
| sound (not s_dx8) | 51 | 31 | 61 |
| ui (not FreeType) | 59 | 27 | 46 |
| esd / info / physics / render_b / freetype | 431 / 3 / 17 / 4 / 728 | 0 | 0 |

Most misses are `ASSERT(!"...")` and debug output compiled out of the
`_FINAL` build. The render shaders, texturestring and ui widget-manager
literals are all of that kind. The misses that are real absences are
DShow, rendermgr, ESD, memorywatch, customfontfilemgr, InputSim, the DX8
sound filters and linux CSysThreads. Per-file figures: `fear/perfile.txt`.

**Console variables.** `shared/engine_vars.cpp` has 104 of 106 names in
retail, and `render_a/rendererconsolevars.h` 157 of 174. The cvar sets are
essentially NOLF2's.

**Interfaces.** These are registered by name in retail, so they can be
counted exactly.

* *Retail interfaces with a Jupiter implementation:*
  ILTClient, ILTServer, ILTCommon, ILTModel, ILTPhysics (Client and Server
  variants where they exist), ILTSoundMgr, ILTClientSoundMgr,
  ILTTransform, ILTDrawPrim, ILTTexInterface, ILTFontManager,
  ILTWidgetManager, ILTVideoMgr, ILTDirectMusicMgr, ILTBenchmarkMgr,
  ILTCursor, ILTRenderStyles, IClientFileMgr, IServerFileMgr,
  IClientFormatMgr, IClientDebugGraphMgr, ICompress, IFindObj,
  ICommandLineArgs, IServerConsoleState, IServerLoaderThread (server.dll),
  IWorld{Client,Server,Shared}BSP, IWorld{Blocker,ParticleBlocker,BlindObject}Data.
* *Jupiter interfaces absent from retail:* ILTMath, ILTPerfCounter,
  ILTRenderMgr, ILTTextureString, ILTOutputRedir, IClientLoaderThread.

### 2b. Function level

Retail functions were attributed by the strings they reference
(`fear/seqcmp.py`). The test compares the set of string or error-tag
references in a retail function with the literals and RETURN_ERROR tags of
the best-matching Jupiter function body.

| | Lithtech.exe | server.dll |
|---|---|---|
| functions referencing a string (not generic) | 710 | 217 |
| no literal match | 216 (all macro-made: interface or cvar names) | 19 (same) |
| same set (one string) | 268 | 138 |
| same set (two or more strings) | 106 | 52 |
| retail ⊂ Jupiter (Jupiter added messages) | 26 | 2 |
| Jupiter ⊂ retail | 55 | 3 |
| partial overlap | 39 | 3 |

No string-referencing function lacks a Jupiter counterpart. In all,
1,068 Lithtech.exe functions (267 KB, 19% of the code) and 381 server.dll
functions are anchored this way.

**Hand comparisons** of disassembly against source (`fear/skel.py`,
`tools/exedump.py`):

* **kernel/net `CUDPDriver::HostSession`** (0x48b8b0): the same sequence:
  * Term2, then the default port 0x6cf0
  * udp_SetupLocalSockaddr inlined, then bind
  * on failure, `LTSNPrintF` and `RETURN_ERROR_PARAM(LT_CANTBINDTOPORT)`
  * the listen thread, then the `g_CV_UDPDebug` print
  * the critical section, SetSessionName, SetHasPassword, SetGameType

  The vtable slots match the class declarations exactly: SetSessionName
  +0x38 (CBaseDriver slot 14), SetHasPassword +0x80 (slot 32), SetGameType
  +0x88 (slot 34). The one drift is that retail's `Term2` takes one argument
  where Jupiter's takes two.
* **world `CWorldSharedBSP::AddStaticLights`** (0x4a5510, 2.7 KB): the same
  23 property names in the same order and the same stream reads. Identical
  in design.
* **model `Model::ParseCommandString`** (0x4499e0): ConParse, then
  `"ShadowEnable"`. Identical.
  **`Model::Load`** has the same messages, plus Jupiter's "model pieces
  exceeds %d" check. Small drift.
* **server `sm_RestoreAttachments`** (server.dll 0x1000e81e): stream reads
  of 2, 12, 16, 2 and 4 bytes, the `RestoreAttachments`/LT_ERROR tag, then
  om_CreateAttachment. Identical.
* **render_a `CTextureManager::CreateRTexture`** (0x50ea70): the same
  control flow (AlphaRef, MipMapBias, cube or plain texture, the same
  messages). But it calls `IDirect3DDevice8` slots: CreateTexture +0x50
  and CreateCubeTexture +0x58, with no D3D9 shared-handle argument.
  Retail imports `Direct3DCreate8`. Same design, D3D8.
* **render_a drawpolygrid** (0x546210, 7 KB): retail loads
  `"ps\envbumpmap.ps"`, Jupiter `"ps\\envbumpmap.psh"`. Same feature,
  different shader-file convention (NOLF2's `pixelshadermgr.cpp`).

### 2c. Link order (the strongest structural evidence)

The functions anchored by source file, taken in address order
(`fear/lt-order.txt`), show the retail layout:

* **Exe objects, 0x401000–0x4b2370:** controlfilemgr, then alphabetical
  bindmgr, binkvideomgrimpl, classbind, classmgr, client, client_formatmgr,
  client_graphmgr, clientde_impl ... world_shared_bsp. Then the "ILT
  interface" group: icommandlineargs, client_filemgr, client_iltmodel,
  modellt_impl, server_iltmodel, client/server/shared_iltcommon,
  lt_cursor_impl, client/server/shared_iltphysics, transformlt_impl,
  server_iltsoundmgr, soundmgr, client_iltvideomgr. This is exactly the
  file set and grouping of Jupiter's `EXE_Lithtech` list, including the odd
  files such as client_formatmgr, client_graphmgr, cmoveabstract and the
  server .cpps compiled into the client.
* **D3DX math, 0x4b2370–0x4c1240:** middleware.
* **0x4c1240 onward:** initializers, then ltmem.
* **Renderer, 0x4c1850–0x553ea0:** order d3d_device, common_init,
  d3d_renderstyleinterface, d3d_texture, d3d_init, d3d_renderworld, ...,
  d3d_draw, d3d_utils, d3d_shell, screenglowmgr, d3dmeshrendobj_rigid,
  rendershadowlist, drawobjects, tagnodes, d3d_surface, memstats_world,
  d3d_renderblock, modelshadowshader, d3d_rendershader_dynamiclight,
  d3d_renderworld_occluder, texturescriptmgr, drawpolygrid. That is NOLF2's
  own .dsp order: not alphabetical, and not the order of the CMake list.
* **0x553ea0 onward:** iltsound.cpp (Lib_ILTSound), then rezmgr (0x556220).
* **0x5591c0 onward:** Lib_UI (cuifontmanager, cuiwidgetmanager, ...,
  cuislider_impl). It runs on into the encrypted pages at 0x565000.

server.dll has the same shape (`fear/srv-order.txt`): alphabetical
bindmgr ... world_shared_bsp, then the interface group. This is the file
set of `DLL_Server`, with server_interface, server_loaderthread and
nonport.c in their places.

**Sizes compared with the 2006 map** (VS2003 and D3D9, so this only gives
orders of magnitude):

| part | retail 1.3 (VC6) | Jupiter 2006 map |
|---|---|---|
| exe objects | 4,134 functions / 696 KB | 4,559 publics / 691 KB, including about 48 KB of post-NOLF2 objects (DShow, texturestring, rendermgr) |
| renderer | 2,278 functions / 585 KB | LIB_D3DRender 527 KB |
| Lib_UI | 749 functions / 43 KB | 48 KB |

Per-object sizes agree within about 10% where the anchors bound an object
cleanly: model.cpp 19.9/19.6 KB, input 17.7/17.5, ltdirectmusic_impl
17.6/17.2, serverde_impl 17.3/18.7, clientmgr 17.0/18.8, soundmgr
15.8/14.4, s_client 15.6/16.1, objectmgr 14.0/14.6, clientshell 5.3/5.4,
client_filemgr 3.1/3.1. The exception is d3ddrawprim, 17 KB in retail
against 33 KB in Jupiter, where the D3D9 version grew.

### 2d. Classification

| module | verdict |
|---|---|
| server, shared, world, model, kernel/net, kernel/io, controlfilemgr, sdk/inc (ltmodule, lterror, ltobjref, ltquatbase) | **near-identical.** Expect snddrv-like drift: changed signatures, small added checks, later refactors |
| client, kernel/src (win) | **near-identical core, with post-2002 extras to strip**: DShow video, texturestring, customfontfilemgr, memorywatch, perfcounters, loader thread, InputSim, rendermgr glue, ltinfo/diagnostics additions |
| sound (client soundmgr, Lib_ILTSound) | near-identical, minus the DX8 effect filters. s_dx8 is done (snddrv) |
| ui (Lib_UI, without FreeType) | near-identical. The cui SDK headers are identical except `cuifont.h` (LTFontParams) |
| render_b (drawprim, texinterface) | same design, ported to D3D9 and extended (effect shader, fog, viewport save) |
| render_a | **same design, heavily changed**: D3D9 port in 27 files, HLSL effect and shader managers added, render targets added, the vertex/pixel shader path rewritten (NOLF2 had `pixelshadermgr` and `.ps` files), RSD3DRenderPass layout changed |
| physics | not linked into either exe (holders only). Header parity with the NOLF2 SDK |
| esd, info/outputredir, s_nul | absent from retail |

## 3. Which renderer?

**render_a** is the renderer: `LIB_D3DRender`, retail 0x4c1850–0x553ea0,
about 585 KB and 2,278 functions. **render_b** is not an alternative
renderer. It holds the two client-side interface implementations (`CD3DDrawPrim`,
`CSysTexInterface`), which are compiled into the exe's own objects. They sit
at 0x41d080 and 0x4212d0, in alphabetical place among the exe objects, as
both the retail layout and Jupiter's list show. Both are needed.

The work is a **D3D9-to-D3D8 back-port**:
* Every device and resource call goes through D3D8 vtable slots.
* CreateTexture, CreateVertexBuffer and CreateIndexBuffer lose the shared
  handle.
* `Lock` takes `BYTE**`.
* `SetStreamSource` has no offset.
* Sampler states merge back into texture-stage states.
* D3D8 vertex shaders take a declaration DWORD array, not a
  `D3DVERTEXELEMENT9` declaration.
* `ps\*.ps` pixel shaders return.

The LTEffect, effect-shader-manager, vertex/pixel-shader-manager and
render-target files (about 8.6K lines) are removed. A NOLF2-era
`pixelshadermgr.cpp` and an older vertex-shader path are written instead.
The DX8.1 SDK headers are already in the project (d3dx8 is in the image).

## 4. Coverage estimate

The counted region is 7,410 functions and 1,345 KB: the `app` range minus
the D3DX middleware. A further 20 KB is encrypted; the unprotected
pre-release `Lithtech.exe` covers it.

| part | retail functions / bytes | Jupiter counterpart |
|---|---|---|
| exe objects | 4,134 / 696 KB | about 95%: file set and order identical. Strip about 48 KB of post-2002 objects and post-2002 functions inside files. Write the NOLF2-only remnants that later disappeared (e.g. one-argument Term2 paths, removed console commands): estimated 3–5% |
| renderer | 2,278 / 585 KB | about 85–90% recognisable at function level. The D3D8 back-port touches most functions. Write from scratch, or from the Mac build: pixelshadermgr, D3D8 vertex-shader setup, any render-style pass code that changed: estimated 40–80 KB |
| Lib_UI | 749 / 43 KB | about 95% or more |
| iltsound, rezmgr, ltmem, initializers | 249 / 21 KB | about 95%. RezMgr also has a byte-proven source in nolfsrc |
| server.dll | 3,451 / 310 KB (app 0x10001000–0x1004d1d0; WONAPI/nonport pieces included) | about 95%. Same file set and order as DLL_Server; the hand comparisons match exactly |

**Overall:** about 90% of Lithtech.exe's functions (about 6,700 of 7,410)
and about 90% of its bytes have a recognisable Jupiter counterpart.
server.dll is about 95%.

**To write from scratch:** roughly 100–150 KB of Lithtech.exe code. Most
of it is the D3D8-specific renderer pieces and NOLF2-only functions that
Jupiter later deleted or rewrote. Finding those is a matter of the retail
functions left over once the Jupiter objects are compiled and placed. The
largest effort is not writing new code but the D3D8 back-port and
removing post-2002 changes function by function, as was done for snddrv.

These percentages are estimates. What was measured:
* Every string-anchored function (19% of bytes) has a counterpart.
* The file sets and link order agree.
* Per-object sizes agree.
* Six hand comparisons line up.

Nothing beyond that was measured at function level. The first real figure
will come from compiling the server.dll files with VC6 and running
`progress.py`. Start with server.dll: it is the closest match and has no
renderer.

## 5. Other NOLF2-era sources (brief)

* **avp2/proj/LT2** (Talon, 2001): no engine runtime, only `lithshared`
  (butemgr, cryptmgr, rezmgr headers, stdlith, lith, zlib, wonapi, ...) and
  an SDK. It beats Jupiter only for library code dated close to 2001. Its
  SDK is an older LT2 SDK, not Jupiter's interface set. NOLF2's own
  `src/libs` already has lith, stdlith, zlib and ltmem, so AvP2 adds little.
* **nolfsrc/src/engine** (NOLF1, LithTech 2.x, 2000; reconstructed with
  reconstruction-specific file names): a different engine generation. It
  has the old networking, .abc models, the DX7 `d3d.ren` and a different
  ILTClient. It beats Jupiter for:
  * `lithshared/rezmgr`: byte-proven against NOLF1. RezMgr
    ("RezMgr Version 1 Copyright (C) 1995 MONO...", retail 0x556220) has
    probably changed little, and Jupiter's `libs/rezmgr` is 2006.
  * A few base utilities that persisted: dhash, conparse, console
    parsing, StdLith allocators, DirectMusic glue (possibly).
  * Above all, the method: VC6 compile quirks, /YX initializer
    placement, the o2gap and fndiff tools, the structure of
    lithtech-decoded-map.

  For the Jupiter subsystems (CLTClient/CLTServer, interface manager, net,
  world BSP, .ltb models, the D3D8 render-block renderer, CUI), Jupiter
  wins outright.
* **Mac NOLF2 engine symbols** (another agent's `lithtech/mac-nolf2-*`):
  NOLF2-era names for exactly this tree. They are the best way to name the
  functions Jupiter changed (e.g. `pixelshadermgr.cpp`) and the
  NOLF2-only functions.
