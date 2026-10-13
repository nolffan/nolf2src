"""What the scoreboard scores: this project's binaries, and where each one's
own code, and ours, is.

tools/progress.py and tools/ratchet.py read this file and nothing else
about the project, so they know no binary by name: a binary is added here,
not in the tools. Plain data, with the evidence for every address beside
it (the CSVs in this directory are the rest of the evidence).

TARGETS, one dict per shipped binary, in the README's order:

  label      the binary's name, as the README and functions.csv show it
  what       what it is, for the README
  kind       "image": scored function by function against the shipped
             image's code; "resources": a resource-only image, scored
             resource by resource and left out of the total
  shipped    the retail binary, extracted by build/reference.sh
  stem       the prefix of its files here (<stem>-screen-exclude.csv, ...)
             and in out/reference/ (<stem>-functions.csv)
  built      our build of it: a path or glob under the repository, or None
             while it has no source. Its link is read from the response
             file beside it (<built>.rsp, and <built>.cmd for the
             directory the link ran in): every object and library of ours
             it names is scored, and its .map places our functions. A
             target without a build scores as all unwritten
  optional   True: a missing build is expected (no source yet, or another
             project's output still to come), not an error
  app        [(lo, hi)]: the image's own code -- everything the scoreboard
             counts. Above it is the C runtime (the static parts of
             msvcrt.lib, the import thunks) and the exception-handling
             funclets of .text$x: status `crt`, listed, not counted. A
             range after the first is code of the image's own that the
             linker placed above the runtime
  middleware [(lo, hi)]: third-party code linked inside `app`: status
             `middleware`, listed, not counted
  encrypted  [(lo, hi)]: code the retail image keeps encrypted (SecuROM):
             status `encrypted`, listed, not counted -- nothing can be
             compared there
  third_party  link inputs of ours (file names) that build `middleware`:
             left out of our side, so they neither match nor count as
             unplaced
  cites      True when src/ cites this image's addresses in comments: a
             cited address of an unmatched function is `attempted`
  cited_src  the source trees whose comments cite it (default CITED_SRC):
             per target, because the DLLs share the 0x10000000 range
  purecall   the shipped address of the CRT's `_purecall` (every abstract
             vtable's filler), where tools/vtabcheck.py cannot find its
             `jmp [IAT]` thunk itself

The reconstruction tools (tools/tgt.py) read the same entries: a tool is
given a target by label or stem (`Lithtech`, `server`), and its image,
build, link inputs and regions come from here.

Optional per target, for what NOLF's scoreboard needs and this one does
not yet: icl (Intel C/C++ padding and /Qip names), linked_oracle (compare
relocation-free functions against our linked image too), lib_range,
lib_block, own_names / own_symbols (names that say a function's shipped
address) -- see tools/progress.py.

How the ranges were found: `tools/libscan.py <image> <lib>...` puts each
library's functions in the image, and for a binary we build, our own .map
names the library of every function and the retail address of each
boundary is found from ours (the game DLLs are laid out as retail, at most
a few hundred bytes apart). The image's own code ends where the runtime's
first member starts: in our maps, msvcprt's `delete` thunk or an import
thunk run, then msvcrt.lib's atonexit.obj, chkstk.obj, ehvec*.obj,
crtdll.obj / crtexe*.obj. All of NOLF2 links the C runtime as a DLL
(MSVCRT.dll, with MSVCIRT/MSVCP60 and MFC42 where used), except
ClientFx.fxd and the resource DLLs, which link libcmt.lib statically.
"""

REFERENCE = "out/reference"     # build/reference.sh writes it
OUT = "out/progress"            # each run's functions.csv and summary.json
DATA = "progress"               # the recorded baseline and the evidence

# Every hex address cited in these source trees marks the address
# `attempted` in a target with `cites` (an address a reconstruction has
# been written for), unless the target names its own `cited_src` (the
# engine's do). Monolith's game source cites no retail address.
CITED_SRC = []

# Libraries scored on their own, symbol by symbol, against prebuilt
# shipped .libs (NOLF's lithshared libraries, which came with its source
# release): (label, ours.lib). The NOLF2 release ships no prebuilt static
# library -- only the import libraries of server.dll and ServerDir.dll --
# so every library here is built from source and scored inside the
# binaries that link it.
LIBS = []
SHIPPED_LIB = None
SHIPPED_AS = {}
SHIPPED_ENV = None              # the variable that names their directory

# Objects of ours that exist only to make the compiler emit functions for
# the oracle (NOLF's sdkforce.obj): reported as `driver`. None here.
DRIVER_OBJS = set()

TARGETS = [
    # ---- the engine ------------------------------------------------------
    # src/Engine/runtime/winbuild/Engine.dsw (docs/engine/PLAN.md, the
    # skeleton package), linked through build/build.mk's `binary` macro so
    # that the .rsp, .cmd and .map the scoreboard reads are beside the
    # image. Optional until the engine's link is part of `make all`: while
    # the image does not exist the target scores as all unwritten, as
    # before. Its sources cite shipped addresses in comments (nolfsrc's
    # convention): src/Engine/runtime only, so that ServerDir's, snddrv's
    # and the game's 0x1000.... addresses are never read as server.dll's.
    dict(label="Lithtech.exe", what="the engine", kind="image",
         shipped=REFERENCE + "/Lithtech.exe", stem="Lithtech",
         built="src/Engine/built/Final/Lithtech/Lithtech.exe", optional=True,
         cites=True, cited_src=["src/Engine/runtime"],
         # The engine's own code runs from .text's start to the SecuROM
         # pages. 0x565000..0x56a000 (five 4 KB pages) is encrypted on
         # disc: its bytes have the entropy of random data (over 7 bits a
         # byte, against under 6 for code) and decode as nonsense from
         # 0x565004 on, in the middle of an initializer at 0x564ff0, while
         # code calls into it (0x567648 has 401 callers, 0x567968 184:
         # chkstk- and atexit-like). Past it, 0x56a000..0x5729ee is D3DX
         # (below) and 0x5729ee.. the import thunks, msvcrt.lib's
         # 64-bit helpers (__aullshr at 0x572c40) and from 0x572c70 the
         # .text$x funclets. So the runtime's static code, normally the
         # start of the tail, is inside the encrypted pages.
         app=[(0x00401000, 0x00565000)],
         encrypted=[(0x00565000, 0x0056a000)],
         # D3DX, statically linked from the DirectX 8.1 SDK's d3dx8.lib
         # (Microsoft's, compiled with cl 13.00.9178: the 68 Rich-header
         # objects of tool 0x1d build 9178, progress/COMPILERS.md).
         # libscan.py places 322 of d3dx8.lib's functions at a single
         # address each, in two runs: 0x4b2370 (d3dxmath.obj's
         # WithinEpsilon, straight after a run of VC6 global initializers)
         # .. 0x4c0538 (math.obj's _a_pow), then an import thunk and 3 KB
         # of the library's constant tables to 0x4c1240, where VC6
         # initializers resume; and 0x56a0cc (cd3dxblt.obj's BltBox3D) ..
         # 0x5729ee (dxtn.obj's DXT encoders), linked after the runtime
         # and so outside `app` already (its start is in the encrypted
         # pages). The other 12 single hits are D3DX's inline vector and
         # colour operators, compiled into the engine's own objects from
         # d3dx8math.inl: the engine's code, and counted.
         middleware=[(0x004b2370, 0x004c1240)],
         # our link's D3DX: the DirectX 8.1 SDK's d3dx8.lib, which builds
         # both blocks. The SDK's import and data libraries (d3d8.lib,
         # dinput8.lib, dxguid.lib) and the system import libraries add no
         # code of anyone's to `app` and resolve to nothing in the
         # repository, so they need no entry.
         third_party=["d3dx8.lib"],
         # MSVCRT!_purecall's `jmp [IAT]` thunk, in the encrypted pages:
         # the demo's thunk, placed by tools/demoimports.py's shift for
         # 0x5675e0.. (retail = demo - 0x10)
         purecall=0x00567616),
    dict(label="server.dll", what="the engine's server", kind="image",
         shipped=REFERENCE + "/server.dll", stem="server",
         built="src/Engine/built/Final/server/server.dll", optional=True,
         cites=True, cited_src=["src/Engine/runtime"],
         # the import thunks from 0x1004d1d0, then msvcrt.lib's atonexit
         # (__onexit 0x1004d1e2), chkstk, the 64-bit helpers, crtdll,
         # ehvec*, dllmain (0x1004d6dc)
         app=[(0x10001000, 0x1004d1d0)]),
    dict(label="ServerDir.dll", what="the server directory (WON Titan)",
         kind="image", shipped=REFERENCE + "/ServerDir.dll", stem="ServerDir",
         # src/Game/Libs/ServerDir/ServerDir.dsw: CServerDir_Titan.cpp
         # (Monolith's) and WONAPI.lib, the WON/Titan client library, both
         # from the LithTech Jupiter SDK (tools/jupitersrc.py)
         built="src/Game/built/Final/libs/ServerDir/ServerDir.dll",
         # Monolith's code is CServerDir_Titan.obj, 0x10001000..0x10017a40
         # (its last functions are global initializers). WONAPI.lib follows
         # as one block: its Common.obj's AsyncOp::AsyncOp at 0x10017a40 is
         # the first function of the library in our link too, and
         # libscan.py puts WONAPI.lib's functions at single addresses up to
         # nonport.obj's SocketStartUp (0x1004bd80, a WSAStartup(0x101)
         # wrapper; then an atexit registration at 0x1004bda0). The
         # library includes GameSpy's query-reporting SDK
         # (gqueryreporting.obj, 0x10043240.., and nonport.obj). Then the
         # import thunks from 0x1004bdac, ehvecdtr.obj (0x1004bdc6) ..
         # dllmain.obj (0x1004c1c0).
         app=[(0x10001000, 0x1004bdac)],
         # WONAPI and its GameSpy files: third-party, like the GameSpy SDK
         # in NOLF's game DLLs -- listed, not counted, and our build of it
         # is left out of our side (third_party)
         middleware=[(0x10017a40, 0x1004bdac)],
         third_party=["WONAPI.lib"]),
    dict(label="snddrv.dll", what="the sound driver", kind="image",
         shipped=REFERENCE + "/snddrv.dll", stem="snddrv",
         # src/Engine/snddrv/snddrv.dsw: the reconstruction (s_dx8.cpp,
         # parsewavefile.cpp, counter.cpp) and src/libs/ltmem/ltmem.cpp
         built="src/Engine/built/Final/snddrv/SndDrv.dll",
         # s_dx8.obj's code ends at 0x1000a05f; then the MSACM32 import
         # thunks (0x1000a060..0x1000a0b4, the driver calls msacm.h's
         # functions without dllimport), ltmem.lib's ltmem.obj
         # (0x1000a0c0..0x1000a21b: its math-constant initializers, the
         # atexit registration of its global, LTMemAlloc, LTMemFree), and
         # msvcrt.lib from __aulldiv at 0x1000a220 (ulldiv, lldiv, llmul,
         # ehvec*, atonexit, crtdll)
         app=[(0x10001000, 0x1000a060), (0x1000a0c0, 0x1000a220)]),
    dict(label="ltmsg.dll", what="the engine's messages", kind="resources",
         # its only code is msvcrt.lib's DLL entry (crtdll.obj, dllmain.obj
         # at 0x10001000..0x1000116e): resources and nothing of Monolith's
         shipped=REFERENCE + "/ltmsg.dll", stem="ltmsg",
         built="src/Engine/built/Final/ltmsg/ltmsg.dll"),
    # ---- the launcher and the dedicated server ------------------------
    dict(label="NOLF2.exe", what="the launcher", kind="image",
         shipped=REFERENCE + "/NOLF2.exe", stem="NOLF2",
         built="src/Game/built/Final/Launcher/NOLF2.exe",
         # Linked /incremental:yes (Launcher.dsp), so .text opens with the
         # linker's incremental thunk table, one `jmp rel32` per function,
         # 0x401005..0x401df0: not code of anyone's source. The objects
         # start at 0x401df0 (BitmapCheckButton.obj), and our map has
         # MFC42.DLL thunks from 0x412a70 (CButton::DrawItem), then
         # MSVCRT.dll and the system DLLs' thunks, mfcs42.lib's WinMain
         # (0x413270); .text$x from 0x414600. Retail is at the same
         # addresses.
         app=[(0x00401df0, 0x00412a70)]),
    dict(label="NOLF2Srv.exe", what="the dedicated server", kind="image",
         shipped=REFERENCE + "/NOLF2Srv.exe", stem="NOLF2Srv",
         built="src/Game/built/Final/ServerApp/NOLF2Srv.exe",
         # our map: MFC42.DLL thunks from 0x4175f0, msvcrt.lib's atonexit
         # (0x417a40) .. crtexew.obj, mfcs42.lib's WinMain (0x417e00);
         # .text$x from 0x417e60. Retail is at the same addresses.
         app=[(0x00401000, 0x004175f0)]),
    # ---- the game ------------------------------------------------------
    dict(label="CShell.dll", what="the game: client", kind="image",
         shipped=REFERENCE + "/CShell.dll", stem="CShell",
         built="src/Game/built/Final/ClientShellDLL/TO2/CShell.dll",
         # our map: ButeMgr's last function, then msvcprt.lib's delete
         # thunk (delop_s.obj), MSVCIRT.dll's thunks, msvcrt.lib's
         # atonexit .. dllmain (retail 0x10152b10..0x10152f5a, 16 bytes
         # below ours); above them GameAlloc.obj's DefStdlithAlloc/Free and
         # Lib_StdLith's struct_bank.obj, pulled in after the runtime
         # (retail 0x10152f60), to the first .text$x funclet (retail
         # 0x10153130, `mov ecx,[ebp-0x10]; jmp`)
         app=[(0x10001000, 0x10152b10), (0x10152f60, 0x10153130)]),
    dict(label="Object.lto", what="the game: server objects", kind="image",
         shipped=REFERENCE + "/Object.lto", stem="Object",
         built="src/Game/built/Final/ObjectDll/TO2/Object.lto",
         # the same order as CShell.dll's: the runtime from retail
         # 0x101ee310 (128 bytes above ours), GameAlloc.obj's two functions
         # after it (retail 0x101ee750), .text$x from 0x101ee790
         app=[(0x10001000, 0x101ee310), (0x101ee750, 0x101ee790)]),
    dict(label="ClientFx.fxd", what="the game: client effects", kind="image",
         shipped=REFERENCE + "/ClientFx.fxd", stem="ClientFx",
         built="src/Game/built/Final/ClientFxDll/ClientFx.fxd",
         # links libcmt.lib statically: libcpmt.lib's delete (0x1001f6d0),
         # then libcmt.lib (fpinit.obj ...) to the import thunks
         # (0x10029e40) and .text$x (0x10029e50). Retail is at the same
         # addresses.
         app=[(0x10001000, 0x1001f6d0)]),
    dict(label="CRes.dll", what="the game's client resources",
         kind="resources", shipped=REFERENCE + "/CRes.dll", stem="CRes",
         # code: an empty DllMain and libcmt.lib's DLL entry
         built="src/Game/built/Final/ClientRes/TO2/CRes.dll"),
    dict(label="SRes.dll", what="the game's server resources",
         kind="resources", shipped=REFERENCE + "/SRes.dll", stem="SRes",
         # the 1.3 SRes.dll has an empty resource directory: nothing to
         # score but its presence
         built="src/Game/built/Final/ServerRes/TO2/SRes.dll"),
]
