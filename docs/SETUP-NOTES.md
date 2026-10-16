# nolf2src: how the base was set up

The base is ready, built from `nolf2-eu`. Nothing has been committed. The
game DLLs compile from Monolith's source, and the legacy, debug and modern
builds all produce game folders and tarballs. (Then, the game did not start
under Wine: the retail engine the build borrowed is copy-protected. It now
runs on the engine built from source: see "Not done yet".)

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
- **Output folders:** the game folder is audited (11 built, the engine
  included, 5 third-party, none unaccounted for), and tarballs leave out
  saves and player profiles.

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

- **The game did not start under Wine** with the retail `Lithtech.exe`
  (SecuROM asks for the disc; the protection is not removed or bypassed).
  Since package 7 of `docs/engine/PLAN.md` the game gets the engine built
  from source, which has none, and runs.
- **Launcher (`NOLF2.exe`):** builds (DirectX 8.1 SDK, `toolchains/dxsdk-8.1`)
  but `build/all.sh` does not put it in the game directory yet.
- **`make progress`:** adapted to NOLF2: `progress/targets.py` lists each
  binary, its code range and what is left out (the C runtime, D3DX, WONAPI,
  SecuROM's encrypted pages); see `progress/README.md`.
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

That is how it went: the tools became target-driven in nolf2src (step 1 is
`progress/targets.py`, step 2 the tools reading it), and the shared repository
is github.com/nolffan/tools, carried as `tools/` by nolf2src and cjacksrc,
and by nolfsrc at a commit from before the target-driven tools.

## Next steps

- **Reviewing:** `git status` here, and `git -C rez diff` for the `rez`
  changes.
- **Building:** `make` from a normal shell. In the setup session `make` was
  run under `sg docker`, which passed Docker's group id to the container and
  failed with a misleading "Value too large" error, so the same steps were
  run with `docker run` directly. Running it normally uses your own group.
