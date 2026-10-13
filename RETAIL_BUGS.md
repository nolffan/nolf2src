# Bugs in the retail game

Bugs in *No One Lives Forever 2: A Spy in H.A.R.M.'s Way* (version 1.3) as it
shipped, found while rebuilding it. Each is a mistake in the code that a
source change would fix. This is a living list: add a bug when it is found,
in the format below, whether or not it is fixed yet.

The release build reproduces every one of them, on purpose: compiling to the
retail machine code means compiling its mistakes too. They are fixed in the
**modern build** (`make modern`, the `NOLF2SRC_MODERN` define; `MODERN.md`):
each fix goes behind `#ifdef NOLF2SRC_MODERN`, with the retail code kept in
the `#else`, so the release build is unchanged and still matches
(`make progress`).

An entry that is fixed says so under its heading, with the file the fix is
in and its `MODERN.md` id. One that is not says why, or which part of the
tree it waits for.

Where the bug is in the engine (`Lithtech.exe`, `server.dll`, ...), the
entry names the retail address it was read from: the engine's source here is
a reconstruction (`docs/engine/PLAN.md`), so an entry is listed only where
our source is known to do what the retail code does (the function is
byte-identical, or the source cites the retail code). The game binaries
(`CShell.dll`, `Object.lto`, `ClientFx.fxd`, `NOLF2.exe`, `NOLF2Srv.exe`) are
built from Monolith's own source as it shipped, so their entries name the
function and the source file instead. Addresses are as in the retail images
(`build/reference.sh` extracts them into `out/reference/`).

**Fixed so far** (in the modern build):

* [The launcher starts a dedicated server that does not exist](#the-launcher-starts-a-dedicated-server-that-does-not-exist)

---

## Wrong results

### The launcher starts a dedicated server that does not exist
`NOLF2.exe`, string table `IDS_SERVEREXE` ·
`src/Game/Launcher/TO2/RES/Lang/EN/Launcher.rc`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-L2): the
> string names `NOLF2Srv.exe`. The release build keeps the retail name.

The launcher's "Dedicated server" choice (and `NOLF2.exe -goserver`) runs
the program named by `IDS_SERVEREXE`, which is `NOLF2Svr.EXE`; the game
installs the dedicated server as `NOLF2Srv.exe` (`Svr` for `Srv`), so it
never starts.
