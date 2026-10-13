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
| 1 | `tools`: guides, tool fixes, Mac symbol inventory, demo import map, scorer targets for the engine | -- | done (branch `tools`) |
| 2 | `skeleton`: `src/Engine/runtime/` from the Jupiter tree, `Engine.dsw` with Lithtech/server and the libraries, `build.mk` pass; first link of both (stubs allowed) | -- | todo |
| 3 | `server`: `server.dll` compiles, links and loads (`server/`, `shared/`, `world/`, `model/`, `kernel/net`, `kernel/io`) | 2 | todo |
| 4 | `client`: the exe's own objects (`client/`, `kernel/src`, input, DirectMusic, video, console) with the server objects at `/O2` | 2 (3 helps) | todo |
| 5 | `libs`: `rezmgr`, `stdlith`/`lith`, `ltmem`, `iltsound`, `ui` (Lib_UI) | 2 | todo |
| 6 | `render`: `render_b` (drawprim, texinterface) and `render_a` back-ported from D3D9 to D3D8 | 2 | todo |
| 7 | `boot`: the built `Lithtech.exe` in the game under Wine: to the menu, then a level; snddrv/ServerDir/ltmsg built ones in | 3–6 | todo |
| 8 | `modern`: the modern build of the engine (FFmpeg Bink, fixes) | 7 | todo |
| 9 | `match`: byte-matching passes per module, ratcheted by `make progress` | 3–6 | ongoing |

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
