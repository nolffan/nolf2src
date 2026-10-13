# 05 · Reconstructing executables and engine binaries

The game DLLs were the easy case here: Monolith's release has their source,
and the work was getting the build right. The engine -- `Lithtech.exe` and
`server.dll` -- shipped as stripped release PE files with no source in the
release: **no symbols, no debug information, almost no RTTI.** That changes
the workflow. `docs/engine/anatomy.md` is the study of both binaries; this
guide is how to work on them.

## What's different

- **No function names.** You work by address. `.text` is carved into
  functions with synthetic names (`sub_<addr>`); `build/reference.sh` writes
  that table for every image to `out/reference/<stem>-functions.csv`, and
  `tools/progress.py` gives each row a status in `out/progress/functions.csv`.
- **Relocations: `server.dll` has them, `Lithtech.exe` does not.** NOLF2's
  DLLs (`server.dll`, the game DLLs, `snddrv.dll`) keep a real `.reloc`
  section (`server.dll`'s is 0x4c72 bytes), so every absolute address in them
  -- vtable slots, function-pointer tables, globals -- can be read exactly.
  `Lithtech.exe` has none, as NOLF1's engine had none: a dword that looks
  like an address in it may be one or may be a constant. Either way you
  verify *your* objects (which do have relocations) against the image with
  `exematch`: it masks your object's relocation bytes and scans the image's
  `.text` for the rest. A hit means that function is byte-identical in the
  shipped image.
- **Library noise.** Only Monolith's own functions count. Each image's own
  code is its `app` ranges in `progress/targets.py`, with the evidence for
  each boundary; above them are msvcrt.lib's static members, the import
  thunks and the `.text$x` funclets (`crt`). Inside `Lithtech.exe`'s app
  range is D3DX 8.1 (0x4b2370..0x4c1240; its second block, from 0x56a0cc,
  is past the app range already), which is `middleware`.

## SecuROM (`Lithtech.exe` only)

The retail `Lithtech.exe` is SecuROM 4.x-wrapped
(`docs/engine/anatomy.md`, section 2). For reconstruction that means three
things:

1. **0x565000..0x56a000 is encrypted** (five pages): the tail of the UI
   library (`CUIButton`, `CUIStaticImage`, `CUIStaticText`, `CUIWindow`,
   `CUIWidget`), msvcrt.lib's static code and the import thunks
   (`__chkstk`, the CRT entry), and the head of D3DX's second block. The
   scoreboard lists those rows as `encrypted` and counts none of them, and
   `enumfuncs` rows there are garbage. Calls into those pages from readable
   code (0x567648, `__chkstk`, has over 900 callers) show as calls to
   unknown functions.
2. **All 1,514 `call dword ptr [IAT]` sites now call SecuROM's slot
   0x607ec0.** Which import each calls is not in the retail bytes. `mov
   reg,[IAT]` (415 sites) and the `jmp [IAT]` thunks still name their slot.
3. The import directory in the PE header is SecuROM's; the original one
   (0x590cf0) and IAT (0x57c000) are intact in `.rdata`.

**The 1.3 multiplayer demo's `Lithtech.exe` is the stand-in.** It was built
20 days after retail, its Rich header is retail's triple for triple, and it
is not protected. 94.5% of retail's app instructions occur in it verbatim.
`tools/demoimports.py` extracts it from `rez/`, maps each redirected call
site to its real import (`progress/engine/Lithtech-iat-calls.csv`), and can
write a readable copy of retail with the encrypted pages filled in and the
redirected calls restored (into `out/`, never committed). Use the demo **for
code and data, never for addresses**: retail and demo link some objects in a
different order (rezmgr, the sound loader and the D3D initialisation, for
instance), and in the encrypted pages retail is the demo + 0x30 for the UI
tail and the demo − 0x10 from the CRT on.

`server.dll`, `snddrv.dll`, `ServerDir.dll` and `ltmsg.dll` are not
protected.

## The tools

All of these run inside `make shell` (or on a host with Python 3 and
binutils), after `build/reference.sh` has put the retail images in
`out/reference/`.

```sh
# annotated disassembly of a range (resolves IAT calls, inlines string/section refs)
tools/exedump.py out/reference/server.dll 0x1002b705 0x1002b7a8

# verify: does the image contain our objects' functions, byte-for-byte?
tools/exematch.py out/reference/server.dll src/Engine/built/Final/server/*.obj
```

`exedump` is your `dumpfn` here -- read a function, identify its imports and
string literals (which name what it does), and write the source. `exematch`
reports `MATCH <addr>` per function, or nothing for a miss.

## The method

1. **Enumerate and map.** `tools/enumfuncs.py` collects function starts from
   several independent sources and reports byte coverage (`build/reference.sh`
   already runs it for every image: about 11,000 rows for `Lithtech.exe`,
   3,570 for `server.dll`). Use all the sources -- none is sufficient alone.
   In NOLF1's `server.dll` only about 60% of the functions were direct `call`
   targets; nearly a third were reachable **only through vtables or function
   tables**. Check the reported coverage: well under ~99% of `.text` means
   starts are still missing.

2. **Name and place them.** NOLF2 has far better evidence than NOLF1 had:
   - **The Mac NOLF2 engine** (`tools/macho.py`) is not stripped: every
     function's mangled C++ name, class and size, and Monolith's source paths
     (`Source/Engine/Runtime/...`). `progress/engine/mac-functions.csv`
     attributes each function to its source file. It decides which files
     exist and which functions each has, before a byte is read.
   - **The Jupiter tree** (`../fear/Dev/Source/runtime`, with its `sdk/` and
     `libs/`; `docs/engine/fear-mapping.md`) is NOLF2's engine line, four
     years on: about 90% of `Lithtech.exe` and 95% of `server.dll`. It gives
     class declarations, file names and most of the code -- to be trimmed back
     to 2002 (no D3D9, DirectShow, wide strings, perf counters, ...; the Mac
     symbols say what 2002 had).
   - **Error tags and interface registrations.** `RETURN_ERROR(...,
     "Class::Method", ...)` literals name 133 functions of the exe outright
     (`tools/tagmap.py`), and every `define_holder` /
     `instantiate_implementation` pushes its interface name from an
     initializer at the start of its object (48 in the exe, 25 in the dll):
     object boundaries for free.
   - **Console-variable tables**: `engine_vars.cpp`'s (stride 20) and the
     renderer's `ConVar<>` initializers tie names to the storage the code
     uses ([13](13-cluster-recon.md)).
   - **The module map** in `docs/engine/anatomy.md` (section 3): the objects
     in link order, with anchors.

3. **Seed from the Jupiter source, then match.** A file seeded from the
   Jupiter tree and trimmed to the Mac inventory often matches most of its
   functions on the first compile (this project's `snddrv.dll`: its seeded
   code matched 68% at first, 98.7% after corrections). Everything with no
   source is read straight from `exedump` output using
   [03-reading-disassembly](03-reading-disassembly.md).

4. **Resources are separate.** Reconstruct an image's resources as an `.rc`
   and verify with `rsrcdiff` (payload by payload, layout-independent), as
   `src/Engine/ltmsg/` does.

## Compiling and verifying

All of Monolith's code in NOLF2 is cl **8966** (VC6 SP5). The engine's flags
are, until proven per file: **`server.dll` `/O1`** (or `/Os`: only 178 of
its 1,694 call targets are 16-byte aligned, where `/O2` aligns every
function), **`Lithtech.exe` `/O2`** with `/GX`; neither uses `/GR`.
`progress/COMPILERS.md` gives the evidence. In NOLF1, `/O1` for `server.dll`
was found only by byte-matching (nolfsrc's guide 06 shows how, and what the
tells look like: [03](03-reading-disassembly.md#o1-minimize-size-idioms)).

`build/engine.sh` builds each target through `build/build.mk`'s engine pass
(the projects in `src/Engine/runtime/winbuild/Engine.dsw`, turned into make
rules by `tools/dsp2mk.py`) and, with `verify`, runs `exematch` on every
object:

```sh
make shell                                # then, inside the container:
build/engine.sh server verify
build/engine.sh Lithtech verify
```

While iterating on one function, recompile only its file and match only its
object -- a few seconds per round:

```sh
build/engine.sh server-one s_net.cpp [symbol]
build/engine.sh Lithtech-one s_net.cpp [symbol]
```

The optional last argument narrows the report to the lines naming that
symbol. **`server.dll`'s files are compiled into `Lithtech.exe` too**
(server, shared, kernel, net and world objects; `docs/engine/anatomy.md`,
section 4), at `/O2`, so after changing one, check both. The two images'
code for one function is not the same -- only 7% of the dll's instructions
occur verbatim in the exe -- so a function proven in one image still has to
be matched in the other; see [12](12-o2-shape.md).

## The whole-image link

`exematch` verifies functions individually against the shipped bytes; that
is the real proof of faithfulness. A *complete* byte-identical image
additionally needs every function reconstructed and the linker settings,
order and data matched. The link order is the `.dsp`'s file order: lay the
`SOURCE=` entries out in retail address order, as `snddrv` was, because the
scorer's link-order join depends on it. The scorer reads our link through
the `.rsp` and `.map` that `build.mk`'s `binary` macro writes beside the
image (`progress/targets.py`, `built=`).

## Running the thing -- nears have to execute

A byte-identical function needs no runtime test: it *is* the shipped code. A
**near** is the opposite -- instruction-equivalent but not proven, and
therefore not shown to be correct. For NOLF2 this matters more than it did
for NOLF1: the retail `Lithtech.exe` does not run under Wine because of
SecuROM, so **a built `Lithtech.exe` that boots is the way to play the 1.3
game from this tree**, and every near in it runs. `tools/loadtest.c` loads a
linked `server.dll` under Wine and exercises `CreateServer` /
`DeleteServer`; `make test` (`tools/playtest.sh`) plays the game.

The lesson that carried over from running nears in NOLF1: **a near can be
the wrong function.** Pairing by shape once matched a thiscall `AllocItems`
(`ret 8`) against a cdecl allocator (plain `ret`), and the game crashed on
load; of the functions a return-style check then flagged, two were real bugs
in the reconstruction. Compare the return instructions before believing a
pairing.

## The engine binaries

`server.dll` is the model for the rest, as it was in NOLF1: it exports
`CreateServer`, `DeleteServer` and `SetMasterDatabase`, it has relocations,
the SDK headers type its interfaces, and its source is also `Lithtech.exe`'s.
Then the client side of the exe, and the renderer (`render_a`, `render_b`:
static libraries linked into the exe, 2,276 functions, the largest module;
NOLF2 has no separate `.ren`) last. `docs/engine/PLAN.md` has the packages.

A caution carried over from NOLF1, where the SDK headers were a later era
than the binaries: **vtable order is the thing that drifts.** Here
`src/Engine/sdk/inc` is NOLF2's own SDK and the right era, but the Jupiter
tree's class declarations are four years later, and the demo's engine already
calls through a different slot than retail in a handful of places. Verify
every slot's argument count from its `ret N` before trusting a header's
ordering.
