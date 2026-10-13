# 07 · Naming anonymous functions from vtables

The check-literal trick (`tools/tagmap.py`: the `Class::Method` string a
`RETURN_ERROR` pushes) names a function only if it validates its arguments. Most functions don't, so most of a
stripped engine binary stays `sub_1000xxxx`. This guide is the second naming
source, and it is bigger than the first: **a vtable is a class's method list
in the SDK header's declaration order**, sitting in `.rdata` in plain sight.
One anchored vtable names every method of that interface at once, argument
checks or not.

## The method

1. **Find the vtables.** They are runs of consecutive pointers into `.text`
   in the data sections:

   ```sh
   tools/vtabmap.py out/reference/server.dll --at <addr> \
       --names out/reference/server-functions.csv
   ```

   `--at` takes any address you already know (a matched function, a tagged
   one) and prints the run whose slots contain it. `--names` labels slots
   from the function table's name column (error-tag names and exports, as
   `build/reference.sh` writes it) so the anchors are visible.

2. **Anchor the run against an SDK header.** Count virtuals in the header
   (`src/Engine/sdk/inc/`, NOLF2's own SDK; for engine-internal classes
   the Jupiter tree's headers, `../fear/Dev/Source/runtime`), in declaration order, starting from the class's
   first virtual — `tools/sdkvtab.py` reads that order off a header for you.
   When the labelled slots land on the right names in the right order, the
   vtable is identified — and every *unlabelled* slot between them is now
   named by whatever the header declares at that position.

3. **Mind where one vtable ends and the next begins.** `vtabmap.py` merges
   back-to-back vtables into one run, because nothing separates them in
   `.rdata`. The seam shows as a discontinuity: the slot sequence stops
   following one header and starts following another. Anchors on both sides
   pin it exactly. `tools/vtabaudit.py` enumerates tables one per row from
   the evidence (the constructors that store each vptr), which is the
   reliable way to split a run.

4. **Reconstruct the newly named slots as usual**
   ([03](03-reading-disassembly.md)): they are ordinary functions that now
   have a signature — the SDK gives parameter types, return type, and often
   a doc comment.

Remember the era caveat from [05](05-exe-and-engine.md): `src/Engine/sdk/inc`
is NOLF2's own SDK and the right era, but the Jupiter tree's headers are four
years later, and vtable order is the thing that drifts. Check each slot's
argument count against its `ret N` before trusting a long stretch of header
order. The Mac engine helps here too: its vtables (`__ZTV...` symbols, read
with `tools/macho.py`) list the 2003 methods in order, by name.

**NOLF2's binaries make this easier than NOLF1's did.** `server.dll` has a
`.reloc` section, so a vtable's extent there is exact: every slot is a
relocated pointer and the next non-relocated dword ends the table.
`build/reference.sh` already writes `<stem>-vtables.csv` for both engine
images (`tools/vtabaudit.py`: 453 tables in the exe, 171 in the dll).
`Lithtech.exe` has no relocations, so its tables are found by evidence, as
in NOLF1.

## What this found in NOLF1's server.dll

(From NOLF1's engine: the addresses and the files are NOLF1's. NOLF2's
`server.dll` has the same interfaces, so expect the same two tables.)

One 407-slot run at `0x1004e24c` is two vtables back to back:

* **`0x1004e24c`, 31 slots — MyServerInterface.** Exactly
  `server_interface.h`'s declaration order, confirmed by `GetClientPing` (a
  matched function) sitting at slot 19 where the header puts it. Twenty
  previously anonymous functions got names from this one vtable:
  AddResources, LoadBinaries, GetFileList, OpenFile, CopyFile, Update,
  InitNetworking, HostGame, and the rest of the interface.

* **`0x1004e2c8`, 376 slots — CLTServer's ILTServer vtable.** The interface
  aggregates everything, and the known blocks confirm the mapping: the
  ILTCSBase message methods at slots 72–101 in header order, the math
  helpers at 127–141, the physics accessors from 197. Runs of `0x1003ea24`
  are a shared not-implemented stub — those slots exist in the header but
  were never filled in, which is information too.

## The demonstration (NOLF1's engine)

`iltphysics.h` ends with GetGlobalForce, SetGlobalForce, GetStairHeight,
SetStairHeight. The physics block of CLTServer's vtable had four anonymous
targets after IsWorldObject — `0x1002d6e9`, `0x1002d702`, `0x1002d719`,
`0x1002d727` — tiny functions no literal names and nothing else references.
Read off the header, all four reconstructed byte-identical on the first
compile, and pinned two new facts: `SPhysicsLT::m_StairHeight` lives at +0x08,
and the world's global-force state is an embedded object at +0x668 whose
current value sits at +0x67c. They are in `src/engine/server/commonphysics.cpp`
(`SPhysicsLT::GetGlobalForce` and its neighbours).

They also settled a misattribution. The image has **two** Get/SetGlobalForce
pairs. `iltserver.h` declares them taking `LTVector*` — so that pair
null-checks and forwards through the world's vtable; `iltphysics.h` declares
them taking `LTVector&` — so that pair cannot check and reads the fields
directly. The parameter type in the header dictates the whole shape of the
compiled function, and the vtable says which is which. The pointer pair had
been filed under SPhysicsLT before the vtable was mapped; it is CLTServer's
(`CLTServer::GetGlobalForce` in `src/engine/server/servermessage.cpp`).

## Why this scales

The check literals name a couple of hundred functions. The two vtables above
cover ~400 slots, and every engine interface with an SDK header (ILTServer,
ILTCommon, ILTModel, ILTPhysics, ILTLightAnim, ILTSpriteControl, ILTSoundMgr,
ILTVideoMgr…) has its implementation's vtable somewhere in `.rdata`. Each one
is a batch of named, typed, documented functions — the same thing the
literals give, but denser, and with signatures attached.

Once a target links, `tools/vtabcheck.py` closes the loop the other way: it
compares our linked image's vtables with the shipped ones slot by slot, which
catches a constructor that is byte-identical (the vptr store is a masked
relocation) while installing a stand-in table that is too short.
