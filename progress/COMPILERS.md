# Which compiler built what (NOLF2 1.3)

Every retail PE carries a Rich header -- a linker-written inventory of the
tool builds that produced its objects, as (tool id, build, object count)
triples -- and every object the Microsoft compilers emit carries the same
pair in its `@comp.id` symbol. This file maps each retail binary to the
compiler and flags that built it, with the evidence. The toolchains
themselves, and NOLF's own map, are in `toolchains/README.md` and
`toolchains/COMPILERS.md` (the shared submodule).

```sh
python3 tools/richhdr.py out/reference/*.exe out/reference/*.dll   # the inventories
python3 tools/compid.py <lib or obj>       # @comp.id of each object of a library
python3 tools/libscan.py <image> <lib>...  # where a library's code is in an image
```

## The binaries

Objects counted are the Rich header's. "Monolith's" is the compiler of the
binary's own code; the rest is what came in with libraries (below).

| Binary | Monolith's objects | Built here with | Flags | Status |
|---|---|---|---|---|
| `CShell.dll` | C++ **8966** ×290 | `msvc-6.00-8966` (VC6 SP5: `cl` 12.00.8804, `c2.dll` 12.00.8966) | `/MD /W3 /GX /O2`, `/GR` in ClientShellShared (`TO2.dsw`, Final) | **Proven**: our build's Rich header is retail's, triple for triple, and 5,234 functions are byte-identical |
| `Object.lto` | C++ **8966** ×331 | `msvc-6.00-8966` | `/MD /W3 /GR /GX /O2` | **Proven** the same way (9,253 functions) |
| `ClientFx.fxd` | C++ **8966** ×25 | `msvc-6.00-8966` | `/MT /W3 /GX /O2` (static libcmt.lib: the 103 C objects of 8047) | **Proven** the same way |
| `NOLF2.exe` | C++ **8966** ×19 | `msvc-6.00-8966` | `/MD /W3 /GX /O2`, MFC in a DLL (mfcs42.lib's three objects of 8569), linked `/incremental:yes` | **Proven** the same way |
| `NOLF2Srv.exe` | C++ **8966** ×22 | `msvc-6.00-8966` | `/MD /W3 /GR /GX /O2`, MFC in a DLL | **Proven** the same way |
| `CRes.dll`, `SRes.dll` | C++ **8966** ×1 (`main.obj`) | `msvc-6.00-8966` | `/MT /W3 /GX /O2` | **Proven**: identical files but for time stamps |
| `ServerDir.dll` | C++ **8966** ×13, C **8966** ×2 | `msvc-6.00-8966` | `CServerDir_Titan.cpp` `/MD /W3 /GX /O2`; WONAPI `/MD /W2 /GR /GX /O2` | The revision is the header's; ours has one C++ object fewer (12) and two `0x04` objects fewer: the SDK's 2002 source is not quite the 1.3 one. The two C objects are GameSpy's query reporting (`gqueryreporting.c`, `nonport.c`) inside WONAPI |
| `server.dll` | C++ **8966** ×118 | `msvc-6.00-8966` | `/O1` (only 178 of its 1,694 call targets are 16-byte aligned, where `/O2` aligns every function), no `/GX` for its own objects (none of its `fs:[0]` frames is below 0x10048a10: they are rezmgr's and stdlith's, which import `__CxxFrameHandler`), not `/Ob2`, no `/GR` (no RTTI type names), `/Yu"bdefs.h"` (`/Yc` on `bdefs.cpp`; 17 `sys/win`-ish files without it: header initializers such as `math_phys.h`'s `PI` group exist only in `bdefs.obj` and those, 19 in all, as retail has them) | measured: the precompiled header takes 81 initializer groups out (unplaced 1,153 -> 15) and makes `intersectsweptsphere.obj` identical (its `#pragma optimize` above the header is skipped);  without `/GX` exematch places 2,313 of our functions instead of 2,022; `/O1 /Ob2` removes the initializer thunks but loses 86 recorded identical functions and about 30 KB of identical bytes against `/O1` |
| `Lithtech.exe` | C++ **8966** ×290 | `msvc-6.00-8966` | `/O2 /Ob2` (2,877 of 3,157 call targets aligned), no `/GX` for the exe's own objects (none of the 634 `mov eax, fs:[0]` frames is below 0x4b2370: they and the `.text$x` funclets are the libraries'), almost no `/GR` (5 RTTI type names), `/Yu"bdefs.h"` (`/Yc` on `bdefs.cpp`; the 11 files whose `math_phys.h` initializer group retail shows at their start, and udpdriver, without it) | the header's testimony; `/Ob2` measured on the exe's own objects: the interface holders' `CAPIHolder` constructors (out of the class, not `inline`) are expanded in every initializer, and with it 82 of the project's objects match more bytes and one fewer (2,683 -> 3,119 identical; without `/GX`, 3,176 -> 3,881); also D3DX, below |
| `Lithtech.exe`: D3DRender.lib (render_a) | C++ **8966** | `msvc-6.00-8966` | `/MD /W3 /GX /O2 /Ob2` (`render_a/src/sys/d3d/D3DRender.dsp`): the renderer keeps its EH frames, and inlines what `/Ob2` inlines (`ObjectDrawList::Draw` inside `d3d_FlushObjectQueues`, retail 0x519a40), `/Yu"precompile.h"` (`/Yc` on `rendererconsolevars.cpp`; `memstats_world` and `texturescriptinterpreter` without it: retail's renderer has the initializer group in those three only) | measured: `/Ob2` takes the exe from 5,566 to 5,742 identical functions (+76 KB) and its unplaced functions from 2,188 to 1,230, losing none |
| `snddrv.dll` | C++ **8966** ×5 (`counter`, `parsewavefile`, `s_dx8`, `stdafx`, and `ltmem.lib`'s `ltmem`) | `msvc-6.00-8966` | `/MD /W3 /GX /O2 /Ob2` with `/YX` (`/Ob2`: initializers expanded in place; `/YX`: where each object's header initializers sit), STLport (`src/Engine/snddrv/snddrv.dsp`); `ltmem.lib` the same without `/MD` | **Proven**: our build's Rich header is retail's, triple for triple, and 194 functions are byte-identical. The C++ object of **8168** is Creative's `eaxguid.lib` (the EAX 2.0 SDK's seven GUIDs, all in retail's `.rdata`; the copy in F.E.A.R.'s SDK tree is one C++ 8168 object): `eaxguid/eaxguid.cpp` restates it, compiled with `msvc-6.00-8168` |
| `ltmsg.dll` | C++ 8966 ×1 | -- | -- | resources only: its code is msvcrt.lib's DLL entry, so the C++ object is an empty source file |

Every binary links the C runtime as `MSVCRT.dll` (and `MSVCIRT.dll` /
`MSVCP60.dll`, `MFC42.DLL` where used) except `ClientFx.fxd`, `CRes.dll`
and `SRes.dll`, which link `libcmt.lib` statically.

## What the other entries are

| Tool id / build | What | Evidence |
|---|---|---|
| `0x0a` / `0x0b` 8047 | VC6's C runtime: the static members of `msvcrt.lib` (crtdll, atonexit, ehvec*, ...) or `libcmt.lib` | `compid.py`: `libcmt.lib` is C 8047 ×502, C++ 8047 ×22; `msvcrt.lib` C 8047 ×26, C++ 8047 ×4 (every VC6 service pack ships the same CRT objects) |
| `0x0e` 7299 | VC6's CRT assembly, `ml` 6.13.7299 (`memcpy`, `chkstk`, ...) | `libcmt.lib` has 73 such members, `msvcrt.lib` 12 |
| `0x0c` 7291 | alias objects of VC6's libraries (AliasObj 6.0) | in every image here; Microsoft's list names the id |
| `0x0b` 8569 | MFC 4.2's static part (`mfcs42.lib`), VC6 SP5's | `compid.py`: `mfcs42.lib` and `nafxcw.lib` are C++ 8569 |
| `0x06` 1735 | `cvtres` 5.00.1735: the image's resources as an object | exactly one in each image with resources, and in `CRes.dll`/`SRes.dll`, whose code is libcmt.lib only. (NOLF's `richhdr.py` called it MASM: wrong) |
| `0x01` 0 | one per imported function | |
| `0x13` 8034, `0x04` 8047/8168/8447/8569 | import-library objects made by `lib` 5.12.8034 (the Platform SDK import libraries VC6 ships: `kernel32.lib`, ...) and `lib` 6.00 (`msvcrt.lib`'s and `msvcprt.lib`'s descriptors are `0x04`/8047) | `compid.py` on the libraries; which import library each `0x04`/8447 is was not established |
| **`0x1d` 9178** (C++), **`0x1c` 9178** (C) | **cl 13.00.9178**, Microsoft's compiler of the Visual C++ .NET generation (Utc13), which built **the DirectX 8.1 SDK's static libraries** | below |
| **`0x12` 8444** | **ml 6.14.8444**: the one assembly member of `d3dx8.lib` | below |
| **`0x19` 9210** | **lib 7.00.9210** (Implib700): the import descriptors of the DirectX 8.1 SDK's import libraries | below |
| `0x00` 0 | objects with no `@comp.id`: **Intel C/C++** objects among them | below |

### The `0x1d`/9178 objects of `Lithtech.exe` and `snddrv.dll`

`Lithtech.exe` lists C++ 9178 ×68, C 9178 ×2, `0x12`/8444 ×1, `0x19`/9210
×4 and `0x00` ×12; `snddrv.dll` one C++ 9178 and one `0x00`. They are not
Intel's compilers and not Monolith's code: they are Microsoft's DirectX 8.1
SDK, statically linked.

1. **The SDK's libraries carry exactly these ids.** `compid.py` on
   `toolchains/dxsdk-8.1/lib/`: `d3dx8.lib` is C++ 9178 ×133, C 9178 ×1,
   `0x12`/8444 ×1 (and C 8685 ×1, `0x45`/9111 ×1, which `Lithtech.exe` does
   not link), and eight members with no `@comp.id`; `dxguid.lib` and
   `DxErr8.lib` are one C++ 9178 object each; `dinput8.lib` is C 9178 ×5
   (the `c_dfDI*` data formats) with one `0x19`/9210 import descriptor.
2. **Linking them reproduces the entries.** A test program calling
   `D3DXMatrixMultiply`, `DirectInput8Create` and using `c_dfDIKeyboard` and
   `IID_IDirectSound3DBuffer`, compiled with VC6 SP5 and linked with its
   linker against the SDK's libraries, has a Rich header with `0x1d`/9178
   ×11, `0x12`/8444 ×1, `0x19`/9210 ×3 and `0x00` ×8.
3. **The code is in the image.** `libscan.py` places 322 of `d3dx8.lib`'s
   functions at single addresses in `Lithtech.exe`, in two blocks
   (0x4b2370.., 0x56a0cc..); see `progress/targets.py`, which leaves D3DX
   out of the count as `middleware`.
4. **Intel's compilers cannot have made them.** Each of `icl-4.0`,
   `icl-4.5`, `icl-5.0.1`, `icl-6.0.078`, `icl-8.0.046` and `icl-9.0.022`
   compiled a small C and C++ file; none of the objects has an `@comp.id`,
   and VC6's linker lists each of them as `0x00`/0 ("unmarked"). An Intel
   object can only ever be a `0x00` entry.

So `snddrv.dll`'s one C++ 9178 object is `dxguid.lib` (the DirectSound
interface ids; there is no code of it to find), and `0x1c`/9178 ×2 in
`Lithtech.exe` are `dinput8.lib`'s keyboard and mouse data formats.

The eight `0x00` members of `d3dx8.lib` are D3DX's SSE and SSE2 paths
(`d3dxmathsse.obj`, `d3dxmathsse2.obj`, `d3dxquatsse*.obj`,
`d3dxtrigsse*.obj`, `ssefasttable*.obj`), and they were compiled by
**Intel C/C++**: their functions carry icl's `/Qip` names (`X$$1`, as in
NOLF's `d3d.ren`), and no Microsoft compiler of the time emitted SSE. They
are in `Lithtech.exe` (0x4b5dce..0x4bf710, inside the first D3DX block), so
8 of its 12 `0x00` objects are D3DX's. `snddrv.dll`'s one `0x00` is `uuid.lib`'s
`cguid_i_guid0.obj` (`GUID_NULL`, which `DS3DALG_DEFAULT` is): our link
pulls it and has the same entry. **The other four `0x00` objects of
`Lithtech.exe` are not identified**: objects
without `@comp.id` -- Intel-compiled, hand assembly from an assembler that
does not write one, or a pre-VC6 compiler. `NOLF2Srv.exe`'s three `0x00`
are from VC6's own libraries (our build, from the same sources, has the
same three).

## Notes

* `richhdr.py` names the ids above; its table is Microsoft's list,
  annotated with what each id is in this project's images.
* The linker records itself nowhere in a VC6-era Rich header. Every image
  here was linked by a 6.00 linker (the PE header's linker version).
* `Lithtech.exe` is copy-protected: 0x565000..0x56a000 of its code is
  encrypted on disc (SecuROM), and its CRT entry is among those pages. The
  scoreboard leaves those pages out (`encrypted`), and no comparison of the
  engine's code can see into them.
