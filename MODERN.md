# The modern build

`NOLF2SRC_MODERN` is the project's define for everything that departs from
the retail game: bug fixes, new features, and open-source middleware in
place of RAD's. It is set only in the modern build (`make modern`,
`make modern-debug`; `build/variant.sh`), never in the release build, which
stays the retail game as far as it can be rebuilt and is the only build
`make progress` scores. Every change goes behind `#ifdef NOLF2SRC_MODERN`
with the retail code kept, unchanged, in the `#else`.

This file is the inventory: what the modern build changes, what it could
change next, and what was looked at and left alone, and why. It follows
nolfsrc's `MODERN.md` (NOLF1's modern build) in its rules; the items are
NOLF2's own.

## Rules for this work

* **Reimplement, never copy.** Fan fixes and patches for NOLF2 (widescreen
  patches, the community's FOV and resolution tweaks) are a fine source for
  *what* is wrong and *why*; their code is not copied here unless it comes
  with a licence that allows it, and none so far has. Write the change in
  this project's style, from the source we have. The same goes for
  nolfsrc's NOLF1 fixes: NOLF2's engine and game code are a different
  generation, so the idea carries over, the code rarely does.
* **The 2002 compilers.** The modern build uses the release build's
  toolchain (VC6 SP5, the DirectX 8.1 SDK). Nothing newer than VC6 accepts
  -- no C++11, no SDL, no Detours: the engine is ours, so an engine change is
  a change to `src/Engine/`. Only the replacements for third-party binaries
  (`src/modern/`) are built with `zig cc` (`build/ext.sh`).
* **Release unchanged.** The release build compiles `src/` with every
  variant block taken out (`tools/releasesrc.py`, `out/release-tree/`), so a
  block cannot move a byte of the release binaries -- provided nothing is
  added *outside* a block, not even a blank line: `tools/releasesrc.py diff`
  must stay empty. After every change `make` and `make test` pass and
  `make progress` loses no recorded function; `make modern` builds and
  plays (`tools/playtest.sh out/nolf2-modern-release ...`).
* **Each block names its item**, by the id below (`// MODERN.md M-E1: ...`).
* **Game data comes from the retail game.** No game data is committed.

## Open middleware

The modern build ships no RAD binary:

| Retail | Modern | |
|---|---|---|
| `binkw32.dll`, Bink (RAD Game Tools) | our Bink player, `src/modern/binkw32/`, on FFmpeg's Bink demuxer and decoders (`ext/ffmpeg`, FFmpeg n8.1.3, a submodule; LGPL-2.1-or-later as configured), built by `build/ext.sh` into `out/ext/` | the movies play (`run.sh`, `run-launcher.sh` turn them on) |
| Miles Sound System | -- | NOLF2 has none: the engine's sound driver `snddrv.dll` (built here) plays through DirectSound, and no retail binary imports or loads `mss32.dll`. So no OpenMiles. |
| `MFC42.DLL`, `MFC42U.DLL`, `MSVCP60.DLL`, `Msvcrt.dll` (Microsoft) | the same, from the retail game | the C/C++ runtime the compilers link against; kept in both builds |

The Bink interface NOLF2's engine uses is twelve entry points, looked up by
name at run time (`binkvideomgrimpl.cpp`); no game DLL imports Bink. The
player is nolfsrc's, with what NOLF2's engine asks for beyond NOLF1's:
`BinkDX8SurfaceType` (the engine copies each frame into a locked Direct3D 8
texture and asks Bink which surface type that is) and the 24-bit, alpha and
16-bit-alpha copies it can name; the Miles and sound-track entry points
NOLF2 never calls are gone.

## Status legend

| Status | Meaning |
|---|---|
| todo | not started |
| done | implemented behind `NOLF2SRC_MODERN` (or, for tooling, in both builds), release verified unchanged, modern build tested |
| decided | a question settled rather than code to write |

## Items

Ids: M-X middleware, M-L launcher, M-E engine (`src/Engine/`), M-G game
code (`src/Game/`).

| Id | Item | Kind | Where | Status |
|---|---|---|---|---|
| M-X1 | **Bink on FFmpeg.** The modern build's `binkw32.dll` is ours (above). Retail's movies stall under some Wine setups, so `run.sh` turns them off for the release build; the modern build plays them (the four logo movies at start). | middleware | `src/modern/binkw32/`, `build/ext.sh`, `tools/retailextract.py openruntime` | done |
| M-X2 | **No OpenMiles.** NOLF2 has no Miles (above). | middleware | -- | decided |
| M-X3 | **The Microsoft runtime DLLs.** Wine has its own `msvcrt`, `msvcp60` and `mfc42`, so a Wine-only modern build could leave them out; Windows needs them beside the game. Kept in both builds. | middleware | `tools/retailextract.py` | decided |
| M-L1 | **The launcher in the game directory.** `NOLF2.exe` (built from `src/Game/Launcher`) is installed in both builds, with `run-launcher.sh`, which writes the registry values the retail installer left (install directory; the 1.3 update's archive, then `custom/` again so the update's zeroed DLLs cannot override ours) and starts it in a window. NOLF2's launcher has no disc check for play. Tested under Wine: the first-run detail dialog, then `Lithtech.exe -cmdfile launchcmds.txt` to the main menu. This is tooling, so not behind the define. | feature | `build/all.sh`, `build/game-scripts/run-launcher.sh` | done |
| M-L2 | **Launcher's dedicated-server name.** The launcher starts the dedicated server (`-goserver`) as `NOLF2Svr.EXE`; the game ships `NOLF2Srv.exe`, so it never started (retail bug). Tested: `NOLF2.exe -goserver` starts the dedicated server in the modern build, and stays at the launcher in the release build. | fix | `src/Game/Launcher/TO2/RES/Lang/EN/Launcher.rc` | done |
| M-E1 | **Widescreen field of view (Hor+).** The game sets one pair of view angles for every screen (`FovX` 90, `FovY` 78, a 4:3 view), so on a wider screen the same view was stretched sideways. A full-screen view of the world (`RenderCamera`) wider than 4:3 now keeps the vertical angle and widens the horizontal one to the screen's shape (`tan(x/2)` scaled by the width over 4:3): more is seen at the sides, nothing is stretched. Not the interface's 3D objects (`RenderObjects`: the menus' and briefings' art), which belong to the 2D layout and stretch with it until M-G2 (widening them too put the briefing art out of line with its text). The camera's own angles, which the game reads back for zoom, the underwater wobble and damage effects, are not changed -- only the scene the renderer is given -- so every game-side FOV effect works on top of it. At 4:3 nothing changes. Tested at 1280x720 against the release build (C01S01: the same briefing, a wider view in play). | fix | `src/Engine/runtime/client/src/clientmgr.cpp` (`CClientMgr::Render`) | done |
| M-G1 | **Widescreen resolutions.** The game's Display screen and the launcher's Display dialog list only exact 4:3 modes. Both now list every mode at least as wide as 4:3 (narrower ones, 5:4, stay out: M-E1 only widens). Tested at 1280x720: the release build's Display screen shows no resolution at all, the modern one 1280x720x32. | fix | `src/Game/ClientShellDLL/TO2/ScreenDisplay.cpp`, `src/Game/Launcher/DisplayMgr.cpp` | done |
| M-G2 | **Menus and HUD at wide resolutions.** The interface is laid out on a 640x480 page scaled by `width/640` and `height/480` (`CInterfaceResMgr`), so at 16:9 the menus, the HUD and the loading screens are stretched sideways. Lay the page out in the centred 4:3 area (x ratio = y ratio, x offset the side margin), with the side margins filled, as nolfsrc's M-P3-01/02 did for NOLF1; then switch `tools/playtest.sh`'s `PLAYTEST_MAP=modern` mapping (already there, from nolfsrc) on for the modern build. Large: every screen and HUD item that uses the ratios. | feature | `InterfaceResMgr`, the screens, the HUD | todo |
| M-E2 | **Windowed mode at any size.** The renderer wants a display mode of the window's size in the adapter's list even when windowed (`PickDefaultMode`, "Can't find an appropriate display mode!"), so a window can only be a size the desktop could switch to. Windowed, accept any size up to the desktop's. In the renderer (`render_a`, `common_init.cpp`): coordinate with the renderer work there. | fix | `src/Engine/runtime/render_a/src/sys/d3d/common_init.cpp`, `d3d_shell.cpp` | todo |
| M-E3 | **Raw mouse input.** Mouse look reads DirectInput's mouse axes (`input.cpp`). Raw input (`WM_INPUT`, loaded by `GetProcAddress`: VC6's headers predate it) is smoother at high polling rates and in windowed mode; keep DirectInput as the fallback. | feature | `src/Engine/runtime/kernel/src/sys/win/input.cpp` | todo |
| M-E4 | **High frame rates.** The engine already has a frame limiter, `MaxFPS` (0, the default, is off; up to 200), and times frames with the performance counter (`counter.cpp`). Before limiting by default: find out which game code misbehaves above 60 fps (physics, animation-driven movement, AI timing) -- under Wine with vsync the game rarely runs faster. Then either fix what misbehaves or default `MaxFPS` to 60 in the modern build (a console variable, so a player can lift it). | fix (verify) | `src/Engine/runtime/client/src/clientmgr.cpp` (`cm_HandleMaxFPS`) | todo |
| M-E5 | **The developer console.** Retail never draws the engine console (no `con_Draw`; `docs/engine/PLAN.md`, package 4), so console commands can only come from the command line or `autoexec.cfg`. Draw it (the Jupiter code was removed from the release build for retail's sake and can come back behind the define) and bind a key. | feature | `src/Engine/runtime/client/src/sys/win/winconsole_impl.cpp` | todo |
| M-E6 | **Internet play.** Sierra's WON directory servers, which the Internet server list and the version check ask, are gone (`ServerDir.dll`; without `sierraup.cfg` the list shows the directory-server error). LAN play and direct joins do not need them. A replacement directory (or a GameSpy-style master the community runs) is a project of its own. | feature | `src/Game/Libs/ServerDir/`, the game's multiplayer screens | todo |
| M-G3 | **The loading screen's 10 fps.** The loading-screen thread draws, then sleeps 100 ms. NOLF1's modern build shortened its equivalent sleep to load faster; in NOLF2 the level loads on the main thread while this one only draws, so a shorter sleep would only take time from the load. Kept. | decided | `src/Game/ClientShellDLL/ClientShellShared/LoadingScreen.cpp` | decided |
| M-G5 | **Names and chat as printf formats, and the chat buffer.** The server prints names and chat through `"%s"`, takes `%` out of player names and chat lines and cuts chat to 200 characters before printing or relaying them (so no client, retail or not, receives a `%` or a line that overruns its buffer); the dedicated server's console and log print text as text (`RETAIL_BUGS.md`). The engine's double format in `CLTServer::CPrint` (server package) and the client's own printing (`CShell.dll`) are left. Tested: `make modern` plays; a remote client needs two machines. | fix | `GameServerShell.cpp`, `PlayerObj.cpp`, `src/Game/ServerApp/ServerDlg.cpp`, `ScmdConsoleDriver_ServerApp.cpp` | done |
| M-G6 | **`HandleAddGoal`'s unbounded `strcat`** (`RETAIL_BUGS.md`). | fix | `GameServerShell.cpp` | done |
| M-G7 | **Debugging and single-player messages from remote clients.** In a multiplayer game the server ignores pause, teleport, console commands and triggers, stimuli, object alpha and AI goals from a non-local client; a trigger without a command no longer crashes it (`RETAIL_BUGS.md`). `CP_DAMAGE` left. | fix | `GameServerShell.cpp` | done |
| M-G8 | **Skill levels from the client bounded** to the skill tables (`RETAIL_BUGS.md`). | fix | `Skills.cpp` | done |
| M-G9 | **Unique player names unique** (`RETAIL_BUGS.md`). | fix | `PlayerObj.cpp` | done |
| M-G10 | **`FACEOBJECT`'s zero vector** (`RETAIL_BUGS.md`). | fix | `PlayerObj.cpp` | done |
| M-G11 | **`Body::FaceDir`/`FacePos`'s zero vector** (`RETAIL_BUGS.md`). | fix | `Body.cpp` | done |
| M-G12 | **An AI backing away faces away from its move**, not its own position (`RETAIL_BUGS.md`). | fix | `AIMovement.cpp` | done |
| M-G13 | **A keyframer that did not move keeps its rotation** (`RETAIL_BUGS.md`). | fix | `KeyFramer.cpp` | done |
| M-G14 | **`CMusicMgr::SetMood` refuses a mood with no levels** (`RETAIL_BUGS.md`). | fix | `MusicMgr.cpp` | done |
| M-G15 | **The client effects' colour step sets red** (`RETAIL_BUGS.md`). | fix | `src/Game/ClientFxDLL/BaseFx.cpp` | done |
| M-G16 | **`CString::Left` sets the length** (`RETAIL_BUGS.md`). | fix | `src/libs/MFCStub/mfcs_string.cpp` | done |
| M-L3 | **The launcher's path buffer and find handles** (`RETAIL_BUGS.md`). | fix | `src/Game/Launcher/Launcher.cpp`, `RezFind.cpp`, `DisplayMgr.cpp` | done |
| M-E7 | **`StopSecondary`/`StopMotif`'s endless loop**: one walk over the list (`RETAIL_BUGS.md`). | fix | `src/Engine/runtime/kernel/src/sys/win/ltdirectmusic_impl.cpp` | done |
| M-E8 | **Null checks in the client interface**: `ci_Get/SetLightRadius`, `cis_GetSurfaceDims` (`RETAIL_BUGS.md`). | fix | `client/src/clientde_impl.cpp`, `winclientde_impl.cpp` | done |
| M-E9 | **`InitLevel`'s trace typo** (`RETAIL_BUGS.md`). | fix | `ltdirectmusic_impl.cpp` | done |
| M-E10 | **The console print's one-past-the-end write** (`CLTClient::CPrint`, the client's `dsi_PrintToConsole`; `RETAIL_BUGS.md`). | fix | `clientde_impl.cpp`, `kernel/src/sys/win/dsys_interface.cpp` | done |
| M-E11 | **Error messages naming the wrong function**, the client's (`RETAIL_BUGS.md`). | fix | `clientde_impl.cpp`, `winclientde_impl.cpp`, `client_iltphysics.cpp`, `ltinfo_impl.cpp`, `sound/src/soundmgr.cpp` | done |
| M-E12 | **`streamsim_Open`'s leaked file** (`RETAIL_BUGS.md`). | fix | `kernel/src/sys/win/streamsim.cpp` | done |
| M-G4 | **A field-of-view option.** With M-E1 the default view is right at any shape; a menu slider for the vertical angle (`FovY`, now a console variable only) would be the next step. | feature | `ScreenDisplay`, `PlayerMgr` | todo |

## Not changed

| What | Why |
|---|---|
| The game's FOV console variables (`FovX`, `FovY`, `FovXInterface`, ...) | M-E1 widens the drawn view in the engine instead: the game reads its camera angles back (zoom, the underwater effect) and would compound a game-side widening every frame. |
| The `sierraup.cfg` crash in `ServerDir.dll` | not a modern item: retail checks for the missing file, and so does our build in both variants (`src/nolf2src/jupiter/serverdir2-sierraup.patch`). |
