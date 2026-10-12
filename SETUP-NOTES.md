# nolf2src: how the base was set up

The base is ready, built from `nolf2-eu`. Nothing has been committed. The
game DLLs compile from Monolith's source, and the legacy, debug and modern
builds all produce game folders and tarballs. The game does not start under
Wine yet: the retail engine the build borrows is copy-protected (see "Not
done yet").

## First results (legacy build vs retail 1.3)

| Built | Against retail |
|---|---|
| `CRes.dll`, `SRes.dll`, `NOLF2Srv.exe` (dedicated server) | code byte-identical at every offset |
| `CShell.dll`, `Object.lto`, `ClientFx.fxd` | exact file size; code 16, 144 and 96 bytes off |

These were SP6 builds. The build now uses VC6 SP5 (build 8966), as retail
did (`toolchains/msvc-6.00-8966`), which makes `ClientFx.fxd` exact too; see
README.md for the current state.

## What is in the repo

- **Submodules:** `rez` and `toolchains`, staged with their GitHub URLs. They
  were cloned from local copies to avoid downloading.
- **Disc images:** the NOLF2 zips and isos are hard-linked into
  `rez/isos/` from another local copy of rez, so they take no extra space,
  and all verified against `isos/SHA256SUMS`.
- **Source:** Monolith's release in `src/`, keeping the `Game/`, `Engine/`,
  `libs/` layout so their project files work unmodified. Text is converted to
  LF, except the credits and intro files, which the game embeds byte for
  byte.
- **Build chain:** the same style as nolfsrc, with `NOLF2SRC_MODERN` /
  `NOLF2SRC_DEBUG` and outputs `out/nolf2-{legacy,modern}-{release,debug}`.
  The new part is `tools/dsp2mk.py`, which reads Monolith's workspace and
  project files (Final configuration) and generates the build rules, compile
  for compile.
- **Output folders:** the game folder is audited (7 built, 4 retail engine
  files, 5 third-party, none unaccounted for), and tarballs leave out saves
  and player profiles.

## Changes to `rez` (in the submodule only, uncommitted)

- A new release, `nolf2-eu-1.3`: the European install with the English 1.3
  update applied.
- `tools/sfxcab.py`, which unpacks the update's self-extractor.
- The update's registry values (`UpdateNum` 2, `UpdateCommandLine1`).
- Its file hashes in `games.sha256`.
- The README updated.

The update is plain replacement files. One quirk: its `SndDrv.dll` overwrites
`snddrv.dll` keeping the old name, as Windows would.

## Departures from Monolith's compile flags (both checked)

- `/Zm1000` becomes `/Zm200`. Under Wine, `/Zm1000` fails about half the
  time. Objects built both ways are identical apart from the timestamp.
- `/FD` is dropped. It only writes a dependency file, which parallel
  compiles would fight over.

Separately, a rare Wine compiler crash under parallel load (`C1001` /
`C1060`) gets up to three tries, logged.

## Not done yet

- **The game does not start under Wine.** The retail `Lithtech.exe` has
  SecuROM and asks for the disc. The protection is not removed or bypassed.
  The real fix is the reconstructed engine, which will not have it. The
  multiplayer demo's unprotected engine was tried, but it rejects the retail
  game DLLs.
- **Launcher (`NOLF2.exe`):** builds (DirectX 8.1 SDK, `toolchains/dxsdk-8.1`)
  but `build/all.sh` does not put it in the game directory yet.
- **`make progress`:** adapted to NOLF2: `progress/targets.py` lists each
  binary, its code range and what is left out (the C runtime, D3DX, WONAPI,
  SecuROM's encrypted pages); see `progress/README.md`. The engine binaries
  score 0% until they have source.
- **`ServerDir.dll`:** builds from the Jupiter SDK's source
  (`src/Game/Libs/ServerDir/ServerDir.dsw`, `build/jupiter.sh`), but the
  game still gets the retail one.
- **DirectX SDK version:** 8.1 is a guess; if the launcher's or game DLLs'
  remaining differences point at the headers, try 8.0 (archive.org `dx8sdk`).

## A shared `decomp` submodule?

Yes, but not as a straight move. Of the ~56 tools copied, about 30 have NOLF
names or paths built in: `lithtech.exe`, `d3d.ren`, `src/engine/`, and
per-image facts such as where the C runtime starts. Moving them unchanged
would just share NOLF's assumptions. Suggested order:

1. Give each repo a small config file describing its binaries, regions and
   source paths.
2. Make the tools read that config instead of having NOLF built in.
3. Move the generic tools and `guides/` into a shared `decomp` repo used by
   nolfsrc, nolf2src and cjacksrc.

Doing it once nolf2src's scorer works means two real users shape the config.
In the meantime nolf2src keeps renamed copies, and its tools README says they
are not adapted yet.

## Next steps

- **Reviewing:** `git status` here, and `git -C rez diff` for the `rez`
  changes.
- **Building:** `make` from a normal shell. In the setup session `make` was
  run under `sg docker`, which passed Docker's group id to the container and
  failed with a misleading "Value too large" error, so the same steps were
  run with `docker run` directly. Running it normally uses your own group.
