# Lithtech.exe / server.dll (NOLF2 1.3): anatomy of the retail binaries

This is a read-only study to guide the reconstruction. Nothing in either repo was changed.
Intermediate files were in an analysis scratch directory (not in the repository); the scripts that matter are being rebuilt as tools/.

The images compared:

| Tag | File | PE time stamp (UTC) | Notes |
|---|---|---|---|
| **retail** | `out/reference/Lithtech.exe` (2,608,595 B), `server.dll` (397,312 B) | exe 2003-02-08 02:35:54, dll 02:35:36 | 1.3 patch, SecuROM-wrapped exe |
| **mpdemo** | `nolf2_mpdemo_en.exe` → `Resources\Lithtech.exe` (1,794,048 B), `server.dll` (397,312 B) | exe **2003-02-28 00:55:22**, dll 00:54:43 | **unprotected**. Extracted here to `mpdemo/x/Resources/` with `rez/tools/sfxcab.py` + `unshield -g Resources` |
| **prerelease** | Jupiter SDK build 51 `Game Code\TO2\Lithtech.exe` (1,605,632 B), `server.dll` (364,544 B) | exe 2002-03-15 18:30:39, dll 18:26:52 | unprotected, about 11 months older |
| **mac** | `../rez/games/nolf2-mac-usa/NOLF2.app/Contents/MacOS/NOLF2` (Mach-O PPC, 4,483,488 B; its sha256 is the one in `rez/games.sha256`) | 2003 | **not stripped: 19,467 symbols** |

The headline: **the multiplayer demo's engine is the stand-in to use.** It was built 20 days after
1.3. Its Rich header is retail's, triple for triple, and its `.rdata`, `.data` and `.data1` are the
same size as retail's. 94.5% of retail's app instructions occur verbatim in it, as do 96.3% of
`server.dll`'s. It has the plaintext of every encrypted page. The Mac build supplies names
(below). The March 2002 prerelease is too different to be useful for code (DirectInput 7 and DirectDraw, about 27% verbatim).

---

## 1. Layout, imports, exports, Rich header, static libraries

### Sections

retail `Lithtech.exe` (image base 0x400000; there is no `.reloc`; entry point 0x5f9f8a, which is in `.cms_t`, SecuROM's):

| Section | VA | VSize | Raw | Contents |
|---|---|---|---|---|
| `.text` | 0x401000 | 0x17b000 | 0x17b000 | engine code. Encrypted pages 0x565000..0x56a000 (see §2) |
| `.rdata` | 0x57c000 | 0x1607a | 0x17000 | original IAT at 0x57c000..0x57c3c4; original import directory at 0x590cf0; export directory 0x592010 |
| `.data` | 0x593000 | 0x3cdb0 | 0x1d000 | |
| `.data1` | 0x5d0000 | 0x8e0 | 0x1000 | byte-identical to mpdemo's (presumably the static `.data1` of a linked library) |
| `.cms_t` | 0x5d1000 | 0x33000 | | **SecuROM code**, added |
| `.cms_d` | 0x604000 | 0x836f2 | | **SecuROM data**: the redirect slot 0x607ec0, Petite-packed helper modules, `sony.gif`, `SIntf32/SIntfNT/SIntf16.dll`, `CmdLineExt.dll`, `SecuExp.exe` |
| `.idata` | 0x688000 | 0x1f9c | | **SecuROM's rebuilt import table**, which the PE header's import directory now points to |
| `.rsrc` | 0x68a000 | 0x4f80 | | |

mpdemo `Lithtech.exe` has the pre-wrap layout:
`.text` 0x401000 (vsize **0x17a905**), `.rdata` 0x57c000 (0x1607a), `.data` 0x593000 (0x3cdb0),
`.data1` 0x5d0000, `.rsrc` 0x5d1000. Its entry point is 0x5677e2 (`WinMainCRTStartup`), and its IAT and
import directory are where retail's originals are. The prerelease is smaller: `.text` 0x151d55, and it has an 8-byte `.exc` section.

`server.dll` (retail = mpdemo layout): `.text` 0x10001000 (0x4ccd5), `.rdata` 0x1004e000,
`.data` 0x10051000, `.rsrc` 0x10060000, `.reloc` 0x10061000. The entry point is 0x1004d4ab (msvcrt's
`_DllMainCRTStartup`). Nothing in it is protected.

### Imports

retail `Lithtech.exe`, from the *original* import directory in `.rdata` (the one the code was linked against: 230 functions):

| DLL | n | Notable |
|---|---|---|
| WINMM | 3 | timeBeginPeriod/EndPeriod, timeGetTime |
| **DINPUT8** | 1 | `DirectInput8Create`. The prerelease used DINPUT `DirectInputCreateA` and DDRAW `DirectDrawCreateEx` |
| **d3d8** | 1 | `Direct3DCreate8`. The renderer is linked into the exe; there is no `d3d.ren` |
| KERNEL32 | 51 | CreateThread / Suspend / ResumeThread, events, critical sections, QPC, resources, LoadLibrary / GetProcAddress, IsProcessorFeaturePresent, HeapCompact |
| USER32 | 29 | window, message pump, cursor, ToAscii / GetKeyboardState |
| GDI32 | 23 | fonts: CreateFont(Indirect), AddFontResource, GetGlyphOutline, GetTextMetrics, CreateDIBSection (UI fonts) |
| ADVAPI32 | 3 | RegOpenKey / QueryValueEx / CloseKey |
| ole32 | 3 | CoInitialize / CoCreateInstance / CoUninitialize (DirectMusic) |
| MSVCRT | 89 | CRT as a DLL, plus C++ EH, `type_info`, `exception` |
| **MSVCP60** | 7 | `std::basic_string<char>` members (_Grow, _Tidy, assign, _Copy, _Xlen, _Nullstr): some objects use VC6's own `<string>`, alongside STLport |
| WSOCK32 | 20 (by ordinal) | 2 bind, 3 closesocket, 6 getsockname, 8/9/14/15 hton/ntoh, 10 inet_addr, 12 ioctlsocket, 17 recvfrom, 18 select, 20 sendto, 21 setsockopt, 23 socket, 52 gethostbyname, 57 gethostname, 111/112 WSAGet/SetLastError, 115 WSAStartup, 116 WSACleanup. UDP only |

Not imported, so loaded at run time: Binkw32.dll (`LoadLibrary("Binkw32.dll")` + `_BinkOpen@8`, ...), the sound
driver (`snddrv.dll` / `*.snd` via "SoundSysMake"), and DirectMusic/DirectSound (COM). SecuROM's `.idata`
adds `version.dll` and about 63 more kernel32 / user32 / gdi32 / advapi32 functions (the full static-libcmt set: HeapCreate,
GetEnvironmentStrings, LCMapString..., plus DeviceIoControl, CreateFileMapping, AdjustTokenPrivileges)
for its own code.

`server.dll`: WINMM 3, KERNEL32 36 (threads: CreateThread, ExitThread, TerminateThread,
SetThreadPriority; DisableThreadLibraryCalls), USER32 3, ole32 2, MSVCRT 70 (`_beginthreadex`),
WSOCK32 20. Rich `Import0` is ×145 (×252 for the exe).

### Exports

* retail `Lithtech.exe`: `LTGetILTMemory` (0x442a00), `SetMasterDatabase` (0x447190). The prerelease has only `SetMasterDatabase`.
* `server.dll`: `CreateServer` (0x1002b705), `DeleteServer` (0x1002b7a8), `SetMasterDatabase` (0x100140ec).

### Rich header (`tools/richhdr.py`)

| | retail exe | **mpdemo exe** | prerelease exe | retail dll (= mpdemo dll) | prerelease dll |
|---|---|---|---|---|---|
| C++ 8966 (Monolith) | **290** | 290 | 287 | **118** | 116 |
| C 8966 | – | – | **6** | – | – |
| C++ 9178 / C 9178 (DX 8.1 SDK libs) | 68 / 2 | 68 / 2 | 74 / 1 | – | 1 / – |
| masm 6.14 8444 (d3dx8) | 1 | 1 | 1 | – | – |
| implib 7.00 9210 | 4 | 4 | 9 | – | 2 |
| `0x00` (no @comp.id) | 12 | 12 | 13 | – | 1 |
| CRT: C 8047 / C++ 8047 / masm 7299 / alias 7291 | 11 / 3 / 7 / 4 | same | 11 / 3 / 6 / 4 | 5 / 2 / 5 / 3 | same |
| lib 5.12 8034 / link 6.00 8047, 8447 / cvtres 1735 | 15 / 4, 1 / 1 | same | 14 / 2, 1 / 1 | 11 / 2, 1 / 1 | same |
| Import0 | 252 | 252 | 249 | 145 | 142 |

The mpdemo and retail headers are identical. So about 290 Monolith objects make up the exe, including the
static libraries it links (renderer, UI, rezmgr, ltmem, sound), and 118 make up the dll. As
`progress/COMPILERS.md` already says, 8 of the 12 `0x00` objects are d3dx8.lib's Intel-compiled
SSE members and 4 are unidentified. VC6's `uuid.lib` is 0x0a/0x0b build 8447, so they are not uuid.lib.

### Statically linked third-party code and where it sits (retail addresses)

| Library | Where | Evidence |
|---|---|---|
| **D3DX 8.1** (`d3dx8.lib`, cl 13.00.9178 + 8 Intel SSE objects) | block 1 **0x4b2370..0x4c1240** (math, SSE paths 0x4b5dce..0x4bf710); block 2 **0x5675e0..0x5729ee**, whose first 10 KB are encrypted. Its d3dx8tex.obj starts at mpdemo 0x567bd8 ≙ retail ≈0x567bc8 | `libscan.py` (`progress/targets.py`), re-run here on mpdemo: 358 single hits |
| IJG libjpeg ("Copyright (C) 1996, Thomas G. Lane"), zlib error table ("need dictionary", "stream end", "incompatible version") | inside D3DX block 2 (e.g. 0x570694 loads the JPEG message table 0x582164); the tables are in `.rdata` 0x582164..0x5840xx next to D3DX's | D3DX's texture loaders. Not a separate library: the engine has no zlib or jpeg code of its own |
| `msvcrt.lib` static members (chkstk, atonexit, crtexe/WinMainCRTStartup, ehvec*, import thunks) | mpdemo 0x5675f0..0x567bd8 ≙ **retail 0x5675e0..0x567bc8: all encrypted**; `__aullshr` 0x572c40; `.text$x` funclets from 0x572c70 | libscan on mpdemo; call-target mapping (§2) |
| `dinput8.lib` (c_dfDIKeyboard/Mouse) and `dxguid.lib` | data only | Rich 0x1c/9178 ×2, 0x1d |
| **STLport 4.0** (`_STL::`) | header-only, inlined throughout; one out-of-line `basic_string` error path at 0x4c4190 | the only RTTI in both images: `exception`, `_STL::__Named_exception`, `_STL::logic_error`, `_STL::length_error`, `type_info` |
| VC6 `msvcp60` `std::string` | imported, not linked | 7 MSVCP60 imports |
| Monolith's own libs: `ltmem.lib` (0x4c14c3: "mem commands not available ... ltmem.cpp"), **rezmgr** (≈0x555980..0x558b30, "RezMgr Version 1 Copyright (C) 1995 MONOLITH INC."), stdlith / lith templates (inline) | see §3 | strings; Mac symbols |

---

## 2. SecuROM: what is wrapped, and the stand-in

**Version.** This is SecuROM 4.x ("CMS" sections; SIntf16/32/NT.dll; CmdLineExt.dll; Petite-packed payloads; sony.gif).

### What was changed in the retail image

1. **Encrypted code: exactly `.text` 0x565000..0x56a000 (5 pages).** A per-page entropy scan of
   all sections (`entropy.py`) shows 7.0+ bits/byte only in these pages of `.text` (every other
   `.text` page is ≈6.1). `.rdata`, `.data` and `.data1` are clean. The high-entropy pages of
   `.cms_t` and `.cms_d` are SecuROM's own payload. A 512-byte window scan finds nothing else.
   What the pages hold (from the mpdemo, by call-target mapping):
   * **0x565000..≈0x5675e0: the tail of the UI library** (cuibutton / cuistaticimage / cuistatictext /
     cuiwindow / cuiwidget objects: mpdemo's "CUIButton", "CUIStaticImage", "CUIStaticText",
     "CUIWindow", "CUIWidget" registrations, about 146 functions). Retail = mpdemo + 0x30 here; the encrypted
     range starts inside an initializer at 0x564ff0.
   * **≈0x5675e0..≈0x567bc8: msvcrt.lib's static code and the import thunks** (about 60 functions:
     `__chkstk` 0x567648, 907 callers ≙ mpdemo 0x567658; the `_ftol`-like thunk 0x567936 with 1,516 callers
     ≙ mpdemo 0x567946; `jmp [IAT]` stubs 0x567b50..0x567bc8; `WinMainCRTStartup` ≙ mpdemo 0x5677e2).
     Retail = mpdemo − 0x10, consistently over 900+ mapped call sites.
   * **≈0x567bc8..0x56a000: the head of D3DX block 2** (d3dx8tex.obj, ...), retail = mpdemo − 0x10.
2. **Import calls were redirected: all 1,514 `call dword ptr [IAT]` (`ff 15`) sites in `.text`**
   now read `call dword ptr [0x607ec0]`, a single SecuROM dispatcher slot in `.cms_d`. That is
   1,514 of the mpdemo's 1,524; the other 10 are inside the encrypted pages. Only `mov reg,[IAT]` (415) and `jmp [IAT]`
   thunks (16) still name their IAT slot. The masked comparison does not see this, because the 4 bytes are an
   address, but **which import each of those sites calls is not readable from retail**. The mpdemo's
   matching instruction gives it (its IAT is at the same addresses as retail's original).
3. The PE import directory points to SecuROM's `.idata`. The original import directory (0x590cf0) and
   IAT (0x57c000) are intact in `.rdata`. The entry point is SecuROM's (0x5f9f8a).

`server.dll`, `snddrv.dll`, `ServerDir.dll` and `ltmsg.dll` are not protected.

### How close each candidate stand-in is

The method: function tables from `tools/enumfuncs.py` for all six images (11,066 / 10,996 / 9,759 functions
for the retail / mpdemo / prerelease exe; 3,570 / 3,571 / 3,308 for the dll). Instructions are normalized (addresses ≥ 0x10000
→ `A`), and each retail function of at least 6 instructions in the app range is searched for verbatim in the other image's instruction stream
(`substr.py`).

| Retail | vs **mpdemo** | vs prerelease |
|---|---|---|
| Lithtech.exe app (0x401000..0x565000, 7,660 funcs) | **6,203 functions, 94.5% of instructions verbatim**; 147 differ | 2,903 functions, 26.9% |
| server.dll app (3,451 funcs) | **2,383 functions, 96.3% verbatim**; 20 differ (1,288 insns) | 963 functions, 22.6% |
| Rich header | identical | differs (C 8966 ×6, DInput7 / DDraw import libs, ...) |
| strings | same tables (console vars, commands) | 517 strings referenced only by the prerelease and 415 only by retail (perf counters, network rewrite, Bink texture video, ...) |

What the residual mpdemo differences are, from inspection of the 147 functions:
* Disassembly artifacts: jump tables decoded as code, and enumeration boundaries.
* A handful of virtual calls through a different vtable slot (`call [edx+0x60]` vs `[edx+0x34]`,
  `[eax+0x1c]` vs `[eax+0x4]`, e.g. at 0x47be50, 0x40d0c0, 0x405a40, 0x411fd0). An interface header
  differed in the demo branch.
* Object order differs in places. mpdemo links the rezmgr / sound-driver / D3D-init objects earlier
  (around 0x4c35e9..0x4c8b85), and retail has them at 0x554120..0x55c000. Contents are the same, placement is not:
  **use the mpdemo for code and data, never for addresses.**

**Conclusion.** The mpdemo `Lithtech.exe` is a readable, unprotected build of what is effectively the
1.3 engine. It supplies the encrypted 20 KB (≈146 UI functions, ≈60 CRT/thunk functions, ≈35 D3DX
functions), the import identity of all 1,514 redirected calls, and a second witness for every function. The
SP demo (`si_nolf2_demo.exe`) is a different kind of self-extractor (`sfxcab.py`: "no Microsoft cabinet")
and was not examined.

---

## 3. Source-structure evidence

### What there is, and what there is not

* **No `__FILE__`, assert or source-path strings** in the retail exe, the dll, the mpdemo or the prerelease (a release
  build). The only paths are `c:\de_cache` and `%c:\Offset.dat`.
* **RTTI: 5 type descriptors**, all library ones (above). Engine classes are compiled without `/GR`.
* Vtables: 453 tables in the exe and 171 in the dll (`*-vtables.csv`).
* **Error tags** (`RETURN_ERROR(…, "Class::Method", …)`): 133 distinct `Class::Method` literals in the exe
  (CLTClient, ILTPhysics, CLTPhysicsClient/Server, CLTServer, CommonLT, CSoundMgr,
  CLTSoundMgrServer, CLTDirectMusicMgr, CLTVideoMgr, CUDPDriver, BinkVideoInst/Mgr, CClientMgr,
  CClientShell, SpriteControl, ILTModel, ...). 143 retail functions are already named by `enumfuncs.py`.
* **Interface-manager registrations.** These are the most useful evidence. Every `define_holder` /
  `instantiate_implementation` makes a dynamic initializer that pushes the interface name, and these
  sit at the start of each object's code. There are 48 interface names in the exe and 25 in the dll:
  `ICallStack, IClientDebugGraphMgr, IClientFileMgr, IClientFormatMgr, IClientShell, ICommandLineArgs,
  ICompress, IErrorFilter, IErrorPrint, IFindObj, IInstanceHandleClient/Server, ILTBenchmarkMgr,
  ILTClient, ILTClientSoundMgr, ILTCollisionMgr.Client/.Server, ILTCommon.Client/.Server, ILTCursor,
  ILTDirectMusicMgr, ILTDrawPrim(.Internal), ILTFontManager, ILTModel.Client/.Server, ILTModelClient,
  ILTPhysics.Client/.Server, ILTRenderStyles, ILTServer, ILTSoundMgr.Client/.Server, ILTTexInterface,
  ILTTransform, ILTVideoMgr, ILTWidgetManager, IServerConsoleState, IServerFileMgr, IServerShell,
  IWorldBlindObjectData, IWorldBlockerData, IWorldClient, IWorldClientBSP, IWorldParticleBlockerData,
  IWorldServer, IWorldServerBSP, IWorldSharedBSP` (plus `IServerLoaderThread` in the dll only).
  Implementing classes are named the same way (`CClientFormatMgr`, `CD3DDrawPrim`, `CSysTexInterface`,
  `CFindObj`, `CLTBenchmarkMgr`, `CWorld*BSP`, `CLTModelClient/Server`, `CUIFontManager`, ...).
* **Console variables.**
  * Engine: `engine_vars.cpp`'s table at 0x599668 (stride 20) has **103** entries in the exe (BindIP, IP,
    Console_FontTexFile, … UDPSimulatePacketLoss, UDPSimulateCorruption). In the dll the table is at 0x10052550 with
    **105**: the same source, with `ServerFPS` and `LockServerFPS` added under a server define.
  * Renderer: **≈160** `ConVar<>` objects from `rendererconsolevars.h` (CacheTextures, FogEnable, DrawWorldTree,
    ModelShadow_Proj_*, ScreenGlow*, ...: `rcvars.txt`), each with its own initializer, 0x4c44e0..0x4c7750.
  * Console commands: a table at 0x597a38 (stride 12) with **33** (BlastServer, ListInputDevices, quit, serv,
    ModelAdd, World, EnableDevice, RangeBind, Bind, Scale, RangeScale, AddAction, SSFile, UpdateServer,
    RenderCommand, RCom, Set, ListCommands, RestartConsole, RestartRender, ResizeScreen, RebindTextures,
    LogTextureInfo, HeapCompact, ConsoleHistory, ClearHistory, WriteHistory, ReadHistory, Exec,
    ShowVersionInfo, MoveConsole, Mem, ShowTicks).
* **Debug and error strings**: about 1,500 distinct strings referenced from code (`ret-Lithtech.strx`), for example
  "model-rez: client CacheModelFile %s", "Regained focus.. initializing renderer.",
  "UDP: Got invalid unconnected message …", "LithTech build %s initialized in %.2f seconds.".

### Better sources for names and file list (all local)

1. **Mac NOLF2 engine** (`../rez/games/nolf2-mac-usa/NOLF2.app/Contents/MacOS/NOLF2`, already
   installed in the sibling `../rez`; nolf2src's own `rez/games/` has only `nolf2-eu-1.3`).
   * It is not stripped: 11,485 text symbols with full Itanium-mangled C++ names (8,207 in `__text` and 3,278 coalesced
     templates/inlines). `mac-text-dem.tsv` is the address-ordered, demangled list (a 30-line Mach-O reader,
     `macho.py`).
   * It has the whole engine: client, server, renderer and UI (CLTClient 101 methods, CClientMgr 92,
     CServerMgr 49, CD3DDrawPrim 53, CRezMgr 32, CUI*), compiled for PPC on top of The Omni Group's D3D8 /
     DirectMusic / DInput8 emulation (`OD3D8`, `ODM*`), with QuickTime in place of Bink.
   * Its strings carry **real source paths**:
     `Source/Engine/Runtime/{kernel/src/sys/win/{videomgr,text_mgr,stringmgr}.cpp, model/src/model_load.cpp,
     server/src/s_net.cpp, shared/src/{ftserv,pixelformat}.cpp, sound/src/soundbuffer.cpp,
     render_a/src/sys/d3d/{d3d_device,d3d_surface,d3d_renderstatemgr,d3d_optimizedsurface,
     d3dmeshrendobj_skel,dirtyrect,drawsprite,pixelshadermgr,screenglowmgr}.cpp,
     render_b/src/sys/d3d/d3ddrawprim.cpp}`, `Source/Engine/libs/rezmgr/rezmgr.cpp`,
     `Source/libs/stdlith/helpers.cpp`.
2. **F.E.A.R.'s Jupiter EX runtime** (`../fear/Dev/Source/runtime`: 381 .cpp in the same
   module layout `kernel{,/io,/mem,/net}`, `client`, `server`, `shared`, `world`, `model`, `physics`,
   `sound`, `render_a`, `render_b`, `ui`, `info`, `controlfilemgr`, `esd`) and its `winbuild/lithtech/Lithtech.map`
   (2006). It is a later generation, but most NOLF2 string literals occur verbatim in it, so it names files.
3. NOLF1's reconstructed engine (`../nolfsrc/src/engine/{lithtech,server}`), for the older file names
   (`clientmgr2.cpp`, `smgr.cpp`, `cmodelload.cpp`, ...).

### Module map of retail `Lithtech.exe`

The map comes from string literals unique to one file in (2)/(3) (`attrib2.py` → `runs-ret-Lithtech.txt`, 530
functions attributed), interface registrations, and object-start clusters (`objstarts-ret-Lithtech.txt`:
95 clusters).

**The explicit objects (the exe project) end where D3DX begins (0x4b2370).** Library members follow,
in resolution order. The objects run in two alphabetical sequences, the order of the files in Monolith's
project:

*Group 1, 0x401000..0x4a6590 (3,731 functions, 677 KB). Order by first anchored address, with FEAR file names:*
controlfilemgr (0x4017ea: `#ifdef/#ifndef/#endif` parser) → bindmgr (0x402a50) → binkvideomgrimpl (0x4036c0) →
classbind (0x404440) → classmgr (0x4049a0) → client.cpp (WinMain / focus / `-cmdfile`, 0x4052e0) →
client format and debug-graph managers (0x4066f0) → clientde_impl / CLTClient (0x407840..0x40be70) → clientmgr
(0x40cc90..0x410e80) → clientshell (0x4110c0) → cmoveabstract (0x412890) → collision (0x412b10) → compress
(CCompress 0x418100) → concommand (0x418d90) → consolecommands (0x419dc0..0x41b420) → **d3ddrawprim**
(CD3DDrawPrim 0x41d080, render_b) → **d3dtexinterface** (CSysTexInterface 0x4211a0) → de_file
(0x422100) → [3 unanchored objects 0x422d60..0x428440] → dsys_interface (0x428600) → errorlog (0x42a190) →
findobj (CFindObj 0x42a220) → game_serialize (0x42c8d0) → input (DInput8, 0x431470..0x434f80) → [a dib blitter,
0x4359a0] → localdriver (0x43b0d0) → ltbenchmark (0x43b630) → ltdirectmusic_impl (0x43c9f0..0x43fe10) →
ltdirectmusicloader (0x440ea0) → [3 objects 0x442540..0x447a10, including `LTGetILTMemory` 0x442a00 and `SetMasterDatabase`
0x447190] → model (0x448fd0) → model_load (0x44ddc0) → moveobject (0x452af0) → netmgr (0x453cb0..0x45a0d0)
→ objectmgr (0x45af70) → parse_world_info (0x45f4d0) → [0x45f5f0..0x465c40] → render (0x465c40) →
s_client (0x466db0) → s_concommand (0x46acc0) → s_net (0x46b6f0) → s_object (0x46d530) →
server_consolestate (0x46f650) → server_extradata (0x46f940) → serverde_impl / CLTServer (0x470d40..0x475d50)
→ servermgr (0x476020..0x47ace0) → setupobject (0x47b2b0) → shellnet (0x47b870) → smoveabstract (0x47eb70) →
soundbuffer (0x47f120) → sprite (0x482720) → stringmgr (0x4834b0) → udpdriver (0x483920..0x491890, 230
funcs) → version_info (0x4911a0) → videomgr (0x491280) → winclientde_impl (0x4919b0) → winconsole_impl
(0x495bc0) → world_blind_object_data (0x499be0) → world_blocker_data → world_client_bsp (0x4a2c30) →
world_particle_blocker_data (0x4a3d70) → world_server_bsp (0x4a4570) → world_shared_bsp (0x4a4cd0..0x4a62f0).

*Group 2, 0x4a6590..0x4b2370 (403 functions, 49 KB), the interface implementations:* client_filemgr
(0x4a6590) → ILTModel client (0x4a7110) → ILTModel server (0x4a91c0) → ILTCommon client (0x4a9c70) →
ILTCommon server (0x4aa650) → shared_iltcommon (0x4ab100) → ILTCursor (0x4abb00) → ILTPhysics client
(0x4abdf0) → ILTPhysics server (0x4ac6c0) → ILTTransform (0x4ad040) → ILTSoundMgr server (0x4adca0) →
CSoundMgr / client sound (0x4ae4d0..0x4b1de0, EAX, DirectSound defaults) → CLTVideoMgr (0x4b1e80) → global
initializers.

**Libraries, in the order the linker pulled them:**

| Range | Functions | What |
|---|---|---|
| 0x4b2370..0x4c1240 | 279 | D3DX block 1 (third-party) |
| 0x4c1240..0x4c1850 | 47 | initializers; `ltmem.lib` (ltmemstats) |
| 0x4c1850..0x553ca0 | 2,276 (599 KB) | **renderer library** (render_a `src/sys/d3d`): d3d_device, common_init, d3d_renderstyleinterface, rendererconsolevars (≈160 ConVars), d3d_init, d3d_renderworld, d3d_draw, d3d_utils, d3d_shell, screenglowmgr, d3d_texture, rendershadowlist, drawobjects, tagnodes, d3d_surface, memstats_world, d3d_renderblock, modelshadowshader, d3d_rendershader_*, d3d_renderworld_occluder, texturescriptmgr, ... (not alphabetical: pulled in dependency order) |
| 0x553ca0..0x555980 | 50 | **sound library**: iltsound.cpp (".SND" driver loader: "SoundSysMake", "SoundSysDesc"), EAX parameter names |
| 0x555980..0x558b30 | 129 | **rezmgr library** |
| 0x558b30..0x565000 (+ ≈0x565000..0x5675e0 encrypted) | 774 (+ ≈146 in the encrypted pages) | **UI library** (`ui/src`: cuifontmanager, cuiwidgetmanager, cuimessagequeue, cuibitmapfont, cuivectorfont, cuipolystring, cuidropdownlist, cuilist, cuioption, cuicheck, cuiprogress, cuislider, then cuibutton, cuistaticimage, cuistatictext, cuiwindow, cuiwidget) |
| ≈0x5675e0..≈0x567bc8 | ≈60 | msvcrt.lib static members and import thunks (encrypted) |
| ≈0x567bc8..0x5729ee | ≈35 encrypted + 154 | D3DX block 2 (third-party) |
| 0x5729ee..0x57c000 | – | thunks, `__aullshr`, `.text$x` EH funclets (1,090 "cb" rows in the CSV) |

### Module map of `server.dll`

It is the same order: the server-side subset of the same files, then `ltmem`, then rezmgr
(`runs-ret-server.txt`). bindmgr 0x1000173d → classbind → classmgr → collision → concommand → de_file
→ dsys_interface → client.cpp's shared bits → game_serialize (+ the NOLF1-era saveio/savrest code) →
localdriver → **ltthread** (CSysThread, 0x10014a5d) → model → model_load → moveobject → netmgr →
objectmgr → parse_world_info → s_client → s_concommand → s_net → s_object → server_extradata →
**server_interface** (ServerInterface::*, `CreateServer`/`DeleteServer`, CServerLoaderThread, 0x1002b06d) →
serverde_impl → servermgr → smoveabstract → stringmgr → udpdriver (0x10035b82..0x1003a29d) → world_* →
group 2's server halves (server_iltmodel 0x10046047, server_iltcommon, shared_iltcommon, physics,
transform, sound server) → ltmem (0x10048a10) → rezmgr (0x1004a8e0) → msvcrt (0x1004d1d0..).

---

## 4. What server.dll shares with Lithtech.exe

* **The source.** 399 of the 415 distinct strings `server.dll`'s code references are also referenced by `Lithtech.exe`'s.
  The 16 that are not are all `ServerInterface::*`, `CServerLoaderThread`, `CSysThread::Run`, "Can't
  create/resume thread", `IServerLoaderThread`. The object order is the same (above). The engine-var table is the same
  plus 2 server variables. `server.dll` is the exe's server, shared, kernel, net and world objects, plus
  `server_interface.cpp` and `ltthread.cpp`, compiled a second time without the client, renderer and UI.
* **Not the code.** The same functions compile differently. Of the dll's functions of 6+ instructions, only 7.1% of instructions are
  verbatim in the exe; of the exe's, 2.1% are in the dll. This fits `/O1`-ish for the dll (178 of 1,694
  call targets 16-aligned) and `/O2` for the exe, as `COMPILERS.md` says. It is the same situation as NOLF1, where
  `lithtech.exe` recompiled about 40 of `server/*.cpp`: a function proven in one image still has to be matched in the other
  with that image's flags.
* The dll links no D3DX, no STLport-throwing code beyond the same 4 exception types, no renderer and no UI. Its static libraries
  are `ltmem` and rezmgr.

---

## 5. Size of the job

| | Functions (enumfuncs) | Bytes | Notes |
|---|---|---|---|
| exe core objects, group 1 | 3,731 | 677 KB | client, kernel, net, shared, server-in-exe, world, model, input, DirectMusic |
| exe core objects, group 2 | 403 | 49 KB | ILT* client/server implementations, sound manager, video manager |
| renderer library | 2,276 | 599 KB | the largest single module; no NOLF1 counterpart in the exe (NOLF1's renderer was `d3d.ren`) |
| UI library | 774 + ≈146 encrypted | ≈60 KB | many tiny accessors |
| rezmgr + sound loader + ltmem | 129 + 50 + small | ≈22 KB | |
| **Monolith code in Lithtech.exe** | **≈7,560** | **≈1.41 MB** | plus initializers |
| **server.dll app** | **3,451** | **0.31 MB** | same source as a subset of the exe, compiled again |
| third-party in the exe | D3DX ≈470 functions (≈105 KB, incl. libjpeg, zlib, DXTn, Intel SSE), msvcrt static ≈60, STLport inline, DX data libs | | middleware; not to be written |

For scale: 11,066 enumerated rows in the exe (96.3% byte coverage), 3,570 in the dll (99.5%), 453 and
171 vtables.

What helps:
* mpdemo: a plaintext twin of 94.5% / 96.3% of the instructions, including the encrypted 20 KB.
* The Mac build: names for nearly every class and method, and real source paths.
* FEAR's runtime: file names, module layout, and literals for attribution.
* The Jupiter SDK's `Engine/sdk/inc` and the release's `src/Engine/sdk`: the ILT* interface headers, which give vtable order.

---

## Files here (`scratchpad/lithtech/`)

`pe.py` (PE reader), `origimp.py` (original imports from `.rdata`), `entropy.py`, `cmsrefs.py`,
`iatuse.py`, `fnorm.py` / `align.py` / `substr.py` / `streamnorm.py` (function matching), `strx.py`
(function → string xrefs: `{ret,demo,pre}-{Lithtech,server}.strx`), `litidx.py` / `lits.pk` (literal index of the FEAR,
NOLF1 and nolf2src trees), `attrib2.py` → `attr2-ret-*.tsv`, `runs-ret-*.txt`, `objstarts.py` →
`objstarts-ret-Lithtech.txt`, `cvars.py`, `rcvars.txt`, `macho.py` → `mac-syms.tsv`, `mac-text-dem.tsv`,
`pe-info.txt`, `retail-origimports.txt`, `{pre,demo}-*-functions.csv`, `sub-ret-{demo,pre}-{L,S}.csv`
(per-function verbatim status), `map-ret-{demo,pre}-*.csv`, and the extracted demo engine in
`mpdemo/x/Resources/` (Lithtech.exe, server.dll, SndDrv.dll, ServerDir.dll, NOLF2.exe, ...).
