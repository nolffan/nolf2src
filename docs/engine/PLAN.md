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
| 1 | `tools`: guides, tool fixes, Mac symbol inventory, demo import map, scorer targets for the engine | -- | todo |
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
