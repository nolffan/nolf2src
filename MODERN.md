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

The modern build's first source of fixes and features is the **NOLF 2
Modernizer** by HeyThereCoffeee (haekb) --
<https://github.com/haekb/nolf2-modernizer>,
<https://haekb.itch.io/nolf2-modernizer> -- read at its last commit,
`76cc9cd` (February 2026: Beta 2C and the openspy.net master server). Its
every change is inventoried below ("The Modernizer, change by change"), with
the commits it came in, and so are the known issues its pages list. Credit
for finding those problems, and for the design of the features, belongs to
the Modernizer; each item names the Modernizer commits it comes from.

## Rules for this work

* **Reimplement, never copy.** Fan fixes and patches for NOLF2 (the
  Modernizer, widescreen patches, the community's FOV and resolution tweaks)
  are a fine source for *what* is wrong and *why*; their code is not copied
  here. The Modernizer's repository has no licence of its own: its readme
  says the code stays bound to the NOLF 2 Tools EULA (its `EULA.htm`), and
  part of it is third-party (`gsmsalg.h`, GPL). So nothing of it is copied,
  not even where a fix is one line: write the change in this project's
  style, from the source we have. Commit hashes are for traceability and
  credit only. The same goes for nolfsrc's NOLF1 fixes: NOLF2's engine and
  game code are a different generation, so the idea carries over, the code
  rarely does.
* **The 2002 compilers.** The modern build uses the release build's
  toolchain (VC6 SP5, the DirectX 8.1 SDK). Nothing newer than VC6 accepts
  -- no C++11, no SDL, no Detours: the engine is ours, so an engine change is
  a change to `src/Engine/`. The Modernizer was built with Visual Studio 2019
  on SDL2 and C++11 (`std::thread`, `std::atomic`, `std::regex`), and, having
  no engine source, worked around the engine from the game DLL: it replaced
  the engine's input-manager function table at fixed addresses of the retail
  `Lithtech.exe` (`0x59ABC8`, `0x597A30`) and shipped a hex-edited
  `Lithtech.exe` (two edits, M-E13 and M-E14). Here each of those is a change
  to our engine source, behind the define. SDL's window, mouse and timer
  calls become Win32 (`SetWindowPos`, `WM_INPUT` declared by hand,
  `QueryPerformanceCounter`); threads become `CreateThread` and critical
  sections. Only the replacements for third-party binaries (`src/modern/`)
  are built with `zig cc` (`build/ext.sh`).
* **Release unchanged.** The release build compiles `src/` with every
  variant block taken out (`tools/releasesrc.py`, `out/release-tree/`), so a
  block cannot move a byte of the release binaries -- provided nothing is
  added *outside* a block, not even a blank line: `tools/releasesrc.py diff`
  must stay empty. After every change `make` and `make test` pass and
  `make progress` loses no recorded function; `make modern` builds and
  plays (`tools/playtest.sh out/nolf2-modern-release ...`).
* **Each block names its item**, by the id below (`// MODERN.md M-E1: ...`).
* **Game code is byte-matched by others.** `src/Game/` is matched against
  retail function by function; a modern change there is only ever inside
  a block, and new members of a class go in a block of their own.
* **Game data comes from the retail game.** No game data is committed. The
  Modernizer's own art (its HD menu background, console backdrop, Fira Code
  font) and data (`Jukebox.txt`, its `Layout.txt`) are not taken.

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

## Copy protection and the disc

Retail 1.3's `Lithtech.exe` is wrapped in SecuROM 4 (`docs/engine/anatomy.md`);
ours is built from source and has none, in both builds. Everything else that
touches copy protection or the disc, in every binary we build, and what the
modern build does about it:

| Where | What | Retail | Modern |
|---|---|---|---|
| `Lithtech.exe` | SecuROM (encrypted pages, redirected imports, disc check at start) | not in the source at all: Monolith's code has no trace of it, so neither build has it | -- |
| `server.dll`, `ServerDir.dll`, `snddrv.dll`, `ltmsg.dll`, `CShell.dll`, `Object.lto`, `NOLF2Srv.exe` | -- | never protected; no disc access | -- |
| Launcher `CLauncherApp::CD_GetDriveLetterWithGame` (`Launcher.cpp`) | at every start, twice: reads `CdRom Drive` from the registry (nothing writes it), then probes every optical drive (`GetDriveType`, `OpenFile` on `X:\NOLF2.EXE`, `X:\DATA\GAME2.REZ`) for the game disc | kept | M-L4: no drive is probed; there is no game disc |
| Launcher `FindRezFiles` (`RezFind.cpp`) | finds `GAME.REZ` in the game directory, and only if it is missing there, on the disc (`<drive>:\data\GAME.rez`) | kept | M-L4: never the disc (the drive letter is always "none") |
| Launcher `CD_VerifyGame` / `CD_ExistGame` (`OnPlay`) | "Please insert Disc 1" loop -- unreachable even in retail: `CD_ExistGame` always answers yes | kept | unchanged (still unreachable) |
| Launcher `CD_GetDriveLetter` | a second drive scan | dead code in both | -- |
| `CWinUtil::GetMoviesPath` (`Shared/WinUtil.cpp`) | scans the optical drives for `Movies\` | dead code in both: the movies play from `Movies\*.bik` in the game directory | -- |
| `Autorun`, `AutoRun2` | the disc's autorun programs | not built | -- |
| `CScreenPreload::UpdateCDKeyValidation` (CShell) | before every TCP join not started from the LAN screen, validates the CD key with Sierra's WON authentication servers -- gone, so an Internet join, and a `+join <ip>` from the command line even to a LAN server, fail with "Invalid CD Key" | kept | M-G17: no check |
| `CScreenMulti` (CShell) | Internet multiplayer: the CD-key field, the "no CD key" refusal, the WON key validation before Join/Host | kept | M-G17: no CD-key field, no check |
| `ServerDir.dll` (`CServerDir_Titan`: `SetCDKey`, `IsCDKeyValid`, the `Validate_CDKey` request; the `WON` console program) | the key's local checksum, the registry key `Sierra\CDKeys`, the WON certificate | kept | unchanged; nothing asks it any more |
| Servers (`Object.lto`, `NOLF2Srv.exe`) | -- | never check a key | -- |

Not copy protection, though often taken for it: the multiplayer handshake's
checksums of `CShell.dll` and four attribute files (anti-cheat; a client
whose game code differs from the server's is turned away -- so modern and
release builds cannot play together), the registry values the installer
writes (`InstallDir`, which the launcher and `NOLF2Srv.exe` need;
`run-launcher.sh` writes them), and the online updater `SierraUp.exe`.

## Status legend

| Status | Meaning |
|---|---|
| todo | not started |
| done | implemented behind `NOLF2SRC_MODERN` (or, for tooling, in both builds), release verified unchanged, modern build tested |
| decided | a question settled rather than code to write; the decision is given |
| not ported | deliberately left out; the reason is given |

"retail bug" in the Kind column: the retail game is wrong there (the
evidence is in the item, and in `docs/engine/PLAN.md`, notes "modernizer:
retail bugs", for `RETAIL_BUGS.md`).

## New console / config variables

Console variables, saved in `autoexec.cfg` once set (from the console, the
command line or a menu). The modern build's strings are IDs 31000 and up
(`ClientResShared.h`, the English `ClientResShared.rc`).

| Variable | Type | Default | Meaning | Item |
|---|---|---|---|---|
| `MaxFPS` | float | 60 (retail: 0, and ignored in the final build) | the most frames a second; 0 is no limit; at most 1000; Display's "Frame rate limit" | M-E4 |
| `RunInBackground` | int | 0 | windowed: play on when the window loses the focus; Display's "Run in background" | M-G41 |
| `ShowFramerate` | int | 0 | show the frame rate at the top of the screen in play | M-G44 |
| `Windowed` | int | (engine) | existing; now on the Display screen ("Windowed"), applied at once | M-G40 |
| `FovY`, `FovX` | float | 78, 90 | existing; now set from the Display screen ("Field of view", the vertical angle) | M-G4 |

## Items

Ids: M-X middleware, M-L launcher, M-E engine (`src/Engine/`), M-G game
code (`src/Game/`). Credit: the Modernizer's commits an item comes from, or
"ours". The order is the order of value: crash fixes and what makes the game
run well today first. M-G5 to M-G16, M-E7 to M-E12 and M-L3 are the retail-bug
fixes of the bugs package (`RETAIL_BUGS.md`), which has rows of its own; the
Modernizer's items take the ids after them.

| Id | Item | Kind | Credit | Where | Status |
|---|---|---|---|---|---|
| M-X1 | **Bink on FFmpeg.** The modern build's `binkw32.dll` is ours (above). Retail's movies stall under some Wine setups, so `run.sh` turns them off for the release build; the modern build plays them (the four logo movies at start). | middleware | ours | `src/modern/binkw32/`, `build/ext.sh`, `tools/retailextract.py openruntime` | done |
| M-X2 | **No OpenMiles.** NOLF2 has no Miles (above). | middleware | -- | -- | decided |
| M-X3 | **The Microsoft runtime DLLs.** Wine has its own `msvcrt`, `msvcp60` and `mfc42`, so a Wine-only modern build could leave them out; Windows needs them beside the game. Kept in both builds. | middleware | -- | `tools/retailextract.py` | decided |
| M-L1 | **The launcher in the game directory.** `NOLF2.exe` (built from `src/Game/Launcher`) is installed in both builds, with `run-launcher.sh`, which writes the registry values the retail installer left (install directory; the 1.3 update's archive, then `custom/` again so the update's zeroed DLLs cannot override ours) and starts it in a window. NOLF2's launcher has no disc check for play (above). Tested under Wine: the first-run detail dialog, then `Lithtech.exe -cmdfile launchcmds.txt` to the main menu. This is tooling, so not behind the define. | feature | ours | `build/all.sh`, `build/game-scripts/run-launcher.sh` | done |
| M-L2 | **Launcher's dedicated-server name.** The launcher starts the dedicated server (`-goserver`) as `NOLF2Svr.EXE`; the game ships `NOLF2Srv.exe`, so it never started. Tested: `NOLF2.exe -goserver` starts the dedicated server in the modern build, and stays at the launcher in the release build. | fix (retail bug) | ours | `src/Game/Launcher/TO2/RES/Lang/EN/Launcher.rc` | done |
| M-L4 | **No disc.** The launcher looks for the game disc at every start: it reads a `CdRom Drive` registry value nothing writes, then probes every optical drive for `NOLF2.EXE` and `DATA\GAME2.REZ` -- on a machine of today an empty or slow drive stalls the launcher, and the answer is only ever used as a fallback place for `GAME.REZ`, which an install has in its own directory. In the modern build no drive is "the game disc": no probing, and the archives come from the game directory only. | fix | ours | `src/Game/Launcher/Launcher.cpp` (`CD_GetDriveLetterWithGame`) | done |
| M-E1 | **Widescreen field of view (Hor+).** The game sets one pair of view angles for every screen (`FovX` 90, `FovY` 78, a 4:3 view), so on a wider screen the same view was stretched sideways. A full-screen view of the world (`RenderCamera`) wider than 4:3 now keeps the vertical angle and widens the horizontal one to the screen's shape (`tan(x/2)` scaled by the width over 4:3): more is seen at the sides, nothing is stretched. The camera's own angles, which the game reads back for zoom, the underwater wobble and damage effects, are not changed -- only the scene the renderer is given -- so every game-side FOV effect works on top of it. At 4:3 nothing changes. Tested at 1280x720 against the release build (C01S01: the same briefing, a wider view in play). With M-G2 the interface's 3D objects (`RenderObjects`: the menus' and briefings' art) widen the same way, to stay beside the centred 2D page. The Modernizer does the same in the game DLL (`FovX` from `FovY` for the screen's shape). | fix | a357a2c, 4158560, a88b29b, 4d73a99 | `src/Engine/runtime/client/src/clientmgr.cpp` (`CClientMgr::Render`) | done |
| M-G1 | **Widescreen resolutions.** The game's Display screen and the launcher's Display dialog list only exact 4:3 modes. Both now list every mode at least as wide as 4:3 (narrower ones, 5:4, stay out: M-E1 only widens). Tested at 1280x720: the release build's Display screen shows no resolution at all, the modern one 1280x720x32. | fix | 02dcc42 | `src/Game/ClientShellDLL/TO2/ScreenDisplay.cpp`, `src/Game/Launcher/DisplayMgr.cpp` | done |
| M-G17 | **No CD key.** Joining a server not picked on the LAN screen (an Internet join, or `+join <ip>` from the command line, even to a LAN server) first validates the CD key with Sierra's WON authentication servers, which are gone, so it fails with "Invalid CD Key"; the Internet screen asks for a key and keeps Join and Host off without one. No server ever checks a key. The modern build skips the validation and hides the key field. | fix | 08c2766, 51b12f6, 410ba8f | `ScreenPreload.cpp` (`FirstUpdate`), `TO2/ScreenMulti.cpp` (`OnFocus`, `RequestValidate`) | done |
| M-G18 | **Activate-type list: a freed node read.** `CActivateTypeHandler::OnLinkBroken` erases the broken link from its `std::list` and then reads the object through the erased iterator, twice (the early-out test and the message it sends). Take the object first, then erase. | fix (retail bug) | f3e9ab8 (the Modernizer moved only the test) | `src/Game/Shared/ActivateTypeMgr.cpp` | done |
| M-G19 | **Snow: erasing from a set while walking it.** `CSnowFX::UpdateAirspaces` deactivates every active airspace by walking `activeAirspaces`, but `CSnowFXAirspace::Deactivate` erases itself from that set, so the loop steps on from a freed tree node (with snow turned off, or the camera beyond the volume's draw distance). Take the first one until none is left. | fix (retail bug) | f3e9ab8 | `ClientShellShared/SnowFX.cpp` | done |
| M-G20 | **Scatter (grass): the same.** `CScatterFX::UpdateSubVolumes`, `activeSubVolumes`. The Modernizer's first fix (return early when the set is empty) stopped grass from ever being drawn ("the missing foliage", Beta 2); its second walks a copy. | fix (retail bug) | f20889f, 3c85c5e | `ClientShellShared/ScatterFX.cpp` | done |
| M-G22 | **A forced dodge that drew a block.** `CAIBrain::GetDodgeStatus`: a forced dodge whose roll lands in the block range picks no action (forced dodges must move), and the checks that follow read `fCheckDistance` unset. Shuffle instead. | fix (retail bug) | c83e9ea | `ObjectShared/AIBrain.cpp` | done |
| M-G23 | **Checking a body that is gone.** `CAIHumanStateCheckBody::Update` sets `pChecker` only when the body is still a body or an AI; when it has been removed or faded, the rest of the update ran on an unset pointer. Fail the state then. | fix (retail bug) | c828105 | `ObjectShared/AIHumanState.cpp` | done |
| M-G25 | **Head and aim tracking: NaN.** `FindConstrainedVector` takes the square root of `1 - (y/h)^2`, which rounding can make slightly negative; the NaN went into the tracked node's rotation. Clamp at 0, as the root just above it already does. (The Modernizer's `floor` version flattens the ellipse; not taken.) | fix (retail bug) | 20bb266, fa809b8 | `src/Game/Shared/TrackedNodeControlFn.cpp` | done |
| M-G26 | **Server list.** `CScreenJoin::DisplayCurServerList` assigns where it compares (`if (nServerIndex = m_nSelectedServer)`), so the list re-selects its last server instead of the one selected before; and it passes a `std::string` object to `sprintf("%s")` (it worked only because STLport's string begins with its buffer pointer). | fix (retail bug) | 8cc73ac (the `%s`); the `=` is ours | `TO2/ScreenJoin.cpp` | done |
| M-G27 | **Radar object without a type.** `RadarObject::ReadProps` reads the radar type through `pType`, which is never set when the object has no `Type`. | fix (retail bug) | 57f7ef0 | `ObjectShared/RadarObject.cpp` | done |
| M-G30 | **Music above 100 frames a second.** `CMusicMgr::Update` takes one server frame's time off every mood each frame; the AIs put one frame's time back on the mood they want, but from their own update, which runs at most every `c_fUpdateDelta` (0.01 s). Above 100 frames a second the moods drain faster than they are kept up, so the warning and combat music drop out at once (the Modernizer: "music transitions are broken on high fps"). An AI's update now keeps its mood up for the time it covers, at least 0.01 s. (The Modernizer instead runs the decay at most every 10 ms of wall time, which slows it below real time at high rates.) | fix (retail bug) | 4512257, 98a3d0c | `ObjectShared/MusicMgr.cpp`/`.h` (`DoMoodFor`), `AIState.cpp` (`UpdateMusic`) | done |
| M-G2 | **Menus and HUD at wide resolutions.** The interface is laid out on a 640x480 page scaled by `width/640` and `height/480` (`CInterfaceResMgr`); most controls scale both ways by the width's ratio, so at 16:9 the menus are stretched and run off the bottom of the screen (no "Quit" at 1280x720), and the HUD is stretched. On a screen wider than 4:3 the page is now scaled by the height alone (x ratio = y ratio) and centred: the side margin is one offset (`CInterfaceResMgr::GetXOffset`), which every control takes in `CLTGUICtrl::SetScale` (and the list's, the button's image, the HUD message's icon), `ConvertScreenPos`/`ConvertScreenRect` add, and the few places that place text from the ratios themselves add (help text, loading and post-load screens, credits, chat prompt, scope, the dead player's dot). The interface camera widens to match (M-E1), so the menus' 3D art stays beside its text. The HUD keeps to the screen's edges: an item in the left third of the page stays at the left edge, one in the right third moves with the right edge, one in the middle stays centred (`GetHUDXOffset`, read again in every item's `UpdateLayout`, which now also runs when the screen changes). The in-game menu bar, which starts at the page's left edge, reaches on to the screen's. At 4:3 and narrower nothing changes. `tools/playtest.sh` maps menu clicks for this layout in a modern game directory (`PLAYTEST_MAP=modern`), and `tools/playtest-menus.txt` tours the menus. Tested at 1280x720 (the main menu, Options, Display, Profile, multiplayer, a new game to play, the in-game menu) and at 640x480 (unchanged). The Modernizer gave every control an `ApplyPosition(scale, offset)` and placed each HUD item by hand; the scope, the overlays and the 2D-only screens are M-G34 to M-G38. | feature | 12322a4, 2c91bab, 67f67df, 0adfdb9, 98135e5, 9d22f0a, 72a1f17, df653a0, 56a41b3, 1e37c88, 9785ceb, 654d91f, 67fdced, 0c18a31 .. 9f69d27 (the `ApplyPosition` series), 092c59b, da07ebb, 533d06c, 5a7355a, b79f23e, fca0803, df4e143, bcb1766, 8b82696, 6f55d65, 3f3362f, 913a8e4, ee3b387, f18ee3a, fe13e3a, eeb9ba6, 3753f2d, a1875be, 2729186, 550d065, 3eb9f39 | `InterfaceResMgr`, `LTGUIMgr/ltguictrl`, `BaseScreen`, the HUD items, the menus | done |
| M-G34 | **Scope and camera overlays at wide resolutions.** The scope's mask sprite (`g_vOverlaySpriteScale`) and the scope's posts are sized for 4:3 and stretch; keep them round and centred, and fill the sides black. | feature | 4bc13df, e5f47c3, 78d38b5, 1b8e183 | `InterfaceMgr.cpp` (`UpdateOverlays`), `TO2/HUDCrosshair.cpp` (`RenderScope`) | todo |
| M-E15 | **Player-view effects at wide resolutions.** The player-view models themselves are projected with the screen's shape (`d3d_SetReallyClose`), so the weapon does not stretch; but the player-view draw primitives (`d3ddrawprim.cpp`, really-close transform: effects drawn in the weapon's space) take their aspect from `PVModelAspect`, which `autoexec.cfg` sets to 1.2 for a 4:3 screen, and would stretch sideways on a wider one. The Modernizer sets `PVModelAspect` to the screen's width over height; here the configured aspect is kept and widened by the screen's shape over 4:3, so 4:3 is unchanged. | feature | 1b8e183 | `src/Engine/runtime/render_b/src/sys/d3d/d3ddrawprim.cpp` | done |
| M-G35 | **Zoom's shape.** `CPlayerMgr::UpdateCameraZoom` scales the vertical angle with the horizontal one (`fovY = fovX * FovY / FovX`), but a view's shape is the ratio of the angles' tangents, not of the angles: zoomed in, the view came out about 7% flatter than the normal one (90/78 degrees). The zoomed view now keeps the normal view's tangent ratio (M-E1 then widens it for the screen as it does the normal view). The Modernizer computes the vertical angle for the screen's shape instead. Not seen zoomed in a test: the first level's crossbow has no scope. | fix (retail bug) | b04c3c6 | `PlayerMgr.cpp` | done |
| M-G36 | **Cinematics in 4:3.** An option to keep the cutscenes' letterbox 4:3 (black side bars) on a wide screen, as they were framed. | feature | abe34f8 | `InterfaceMgr.cpp` (`UpdateLetterBox`), `ScreenDisplay` | todo |
| M-G37 | **Side bars on 2D-only screens.** The loading, briefing and mission-end screens are 4:3 art; on a wide screen fill the margins (the Modernizer slides black bars in over 500 ms). | feature | c141b38, bb537ff, 5e75f60, 3d388ca, a6e7b1b | `InterfaceMgr.cpp`, `LoadingScreen.cpp` | todo |
| M-G38 | **Damage flash at wide resolutions.** The "taking health" screen effect is a sprite cut off at the sides of a wide screen; the Modernizer redraws it as a full-screen HUD item. | feature | 6f40ce8, 6d1cb68 | `PlayerMgr.cpp`, a HUD item | todo |
| M-E2 | **Windowed mode at any size.** The renderer wanted a display mode of the window's size in the adapter's list even when windowed (`PickDefaultMode`, "Can't find an appropriate display mode!"), so a window could only be a size the desktop could switch to. Windowed, any size is now taken: the first mode in the desktop's format, at the window's size. Tested: a 1000x560 window on a 1280x720 desktop. | fix | ours (the Modernizer resizes the window with SDL: 02dcc42) | `src/Engine/runtime/render_a/src/sys/d3d/d3d_shell.cpp` (`PickDefaultMode`) | done |
| M-G40 | **Windowed mode on the Display screen.** A "Windowed" toggle for the engine's `Windowed`; leaving the screen with a change restarts the renderer (`RestartRender`), so the mode changes at once. Tested at 1280x720: on, the game goes on in a borderless window (M-G42) and the screen shows it on again. | feature | 6d8c6bd | `TO2/ScreenDisplay.cpp`/`.h`, `ClientResShared` strings (31000 and up) | done |
| M-G42 | **The window.** Retail sized a window for a framed window's borders without giving it that frame (the engine creates it captioned only), and the game then resized it whole to the mode (`SetWindowSize`), so the picture lost the frame's width; a full-screen window kept whatever style it had, so going from full screen to a window could leave it without a frame (the Modernizer's known issue K9). Now the engine sets the style with every mode: windowed at the desktop's size or larger, a borderless window over the whole screen; smaller, a framed window whose inside is the mode's size, centred; full screen, a bare window on top. The game no longer resizes a window. | fix (retail bug) | f558e02 | `render_a/src/sys/d3d/common_init.cpp`, `GameClientShell.cpp` (`SetWindowSize`) | done |
| M-G41 | **Losing the focus in a window; running in the background.** On losing the focus the engine shut its renderer down and brought it back on regaining it (every texture reloaded, a black window meanwhile), which only a full-screen device needs. In a window it now keeps the renderer and the sound; the game is told (and pauses) as before, unless `RunInBackground` is set (a Display-screen toggle), and then it plays on behind other windows. Full screen is as retail. (The Modernizer passes the focus messages around the engine instead, d092f25: in full screen that blacked the screen out.) | feature | 66687f0, bfcdc0b, d092f25, dd1f5a5 | `src/Engine/runtime/kernel/src/sys/win/client.cpp` (`WM_ACTIVATEAPP`), `TO2/ScreenDisplay.cpp` | done |
| M-E3 | **Mouse look.** Mouse look reads DirectInput's mouse one event at a time (`nEvents = 1` for the system mouse, "fixes the USB mouse lockups") and runs every trigger after each, smoothing each axis over its last three samples (`InputRate`); an axis's last value is used again by every later pass of the frame and by the next frames until it ages out (after `InputRate`/10 ms, checked once a frame). So one mouse event turned the view by about three times its motion at 60 frames a second, smeared over three frames, and more at higher frame rates or with fewer events (a slow or low-rate mouse) -- the "wavy", frame-rate-dependent mouse the Modernizer replaced with SDL. Now the mouse's whole buffer is read, each look axis (x, y) adds up the frame's motion and hands on exactly that, once; the wheel and the buttons are as before. The device buffer is 1024 events instead of 64, which a 1000 Hz mouse overflowed ("Input buffer overflow") at low frame rates. In the engine, so the game's `GetAxisOffsets` is unchanged. A mouse reporting at a high rate felt about the same in retail (each event then counted nearly once); a slow one turns slower now than it did. Tested: xdotool's 30-pixel steps turned the view about a fifth as far as in the release build. Raw input (`WM_INPUT`) as the source is not needed for this; left for later if Wine's DirectInput mouse proves coarse. | fix (retail bug) | 825f644, f588f3f, 0783a0a, 2d451a9, 2ab51a3, 3a833fb, 00b54e8, b19011f, 1b19d5d, ad1cd56 | `src/Engine/runtime/kernel/src/sys/win/input.cpp` (`input_ReadInput`, the buffer size) | done |
| M-G43 | **Mouse wheel in menus.** In the menus and the in-game menus the wheel moves the selection up and down as the arrow keys do (and so scrolls a list that has the selection); in play the wheel stays the engine's, for its bindings. The Modernizer scrolls lists by pages. | feature | b01f7eb, e1e2216, b8998d7 | `GameClientShell.cpp` (`HookedWindowProc`) | done |
| M-G32 | **Fire held after loading.** The Modernizer's fire flag stuck on after loading or the menus. That was its own input layer's list of pressed buttons; retail clears the engine's input on every way back into play (`CInterfaceMgr::PrePlayingState`, `ClearInput`). Nothing to do. | decided | c367388, a2371c5 | -- | decided |
| M-E4 | **High frame rates.** The engine's frame limiter, `MaxFPS`, only ever worked outside the final build (`cm_HandleMaxFPS` is under `#ifndef _FINAL`), so the game ran as fast as it could. Parts of it go wrong fast: the music above 100 frames a second (M-G30), and the Modernizer saw cutscene timing and multiplayer animations go wrong and limits the client to 60. The modern build limits the frame rate to `MaxFPS` in every build -- 60 unless set; 0 is no limit; at most 1000 -- sleeping while more than 2 ms are left and spinning for the rest; the Display screen offers 30 to 240 and none. Tested: `MaxFPS 20` holds the game at 20. | fix | 6ae6b9f, 21291d4, 0aefc93 | `src/Engine/runtime/client/src/clientmgr.cpp` (`cm_ModernFrameLimit`), `src/Engine/runtime/shared/src/engine_vars.cpp` (the default), `TO2/ScreenDisplay.cpp` | done |
| M-G49 | **Dedicated server's frame rate.** A dedicated server runs as fast as it can; the Modernizer caps it at 60 in multiplayer (a busy wait; a listen server's host turns it off with a message). With the engine's own limiter a sleep does it. | fix | 2759902 | `TO2GameServerShell.cpp` | todo |
| M-G44 | **Frame-rate counter.** `ShowFramerate 1` shows the frame rate, averaged over 30 frames, at the top of the screen in play. | feature | 21291d4, 23c22b8, dfc0eba, 83cdef5 | `ClientShellShared/HUDMgr.cpp` | done |
| M-E13 | **Antialiasing.** The engine has `AntiAliasFSOverSample` but uses it only full screen: a window always gets `D3DSWAPEFFECT_COPY` and one back buffer, and Direct3D 8 multisamples only with `DISCARD`. The Modernizer's first edit to `Lithtech.exe` (file offsets `0xC1E58`, `0xC1E61`) makes it always `DISCARD`; then a Display-screen cycle (off, 2x, 4x, 8x, 16x) with a fallback to no antialiasing when the mode cannot be set. Its known issue K1 (a one-pixel shift of 2D items) comes with it. | feature | 6671730, fa71070, 6d8c6bd | `render_a/src/sys/d3d/d3d_device.cpp`, `ScreenDisplay`, `ProfileMgr` | todo |
| M-G45 | **Anisotropic filtering levels.** The Performance screen's anisotropic setting becomes off, 2x, 4x, 8x, 16x (needs the renderer to take a level). | feature | 37313ba, 389d5c7 | `TO2/ScreenPerformance.cpp`, the renderer | todo |
| M-G4 | **A field-of-view option.** A Display-screen slider for the vertical angle, 50 to 100 degrees (`FovY`; 78 in retail): the horizontal one (`FovX`) follows with retail's shape (90 by 78), and M-E1 widens it for a wide screen. Applied to the camera at once. The Modernizer's slider is the horizontal angle (70-150), with its 4:3 equivalent in the help text. | feature | a357a2c, ed64756, 4158560, 66687f0 | `TO2/ScreenDisplay.cpp` | done |
| M-E5 | **The developer console.** Retail never draws the engine console (no `con_Draw`; `docs/engine/PLAN.md`, package 4), so console commands can only come from the command line or `autoexec.cfg`. Draw it (the Jupiter code was removed from the release build for retail's sake and can come back behind the define) and bind a key. The Modernizer wrote its own in the game DLL (backquote, half the screen, history, `help`; paused in single player, usable in multiplayer; `NumConsoleLines` as a HUD item). | feature | fad2677, af980a1, ace76d3, e29690b, b91a8c0, ef432db, d8839f0, b6f44bc, 88edf42, 5aacb97, c204123, b07fb43, a868f53, 91a1710, 34deaf8, 63f2795, c28e182 | `src/Engine/runtime/client/src/sys/win/winconsole_impl.cpp` | todo |
| M-E6 | **Internet play.** Sierra's WON directory servers, which the Internet server list and the version check ask, are gone (`ServerDir.dll`; without `sierraup.cfg` the list shows the directory-server error). LAN play and direct joins (M-G17) do not need them. The Modernizer replaced `ServerDir.dll` with its own (`JServerDir`): a GameSpy master-server client and server reporter, now against `master.openspy.net` (list over TCP 28900 with the `gamename nolf2` handshake; `\status\` queries and heartbeats over UDP 27900). A VC6 reimplementation behind the same `IServerDirectory` interface is a project of its own (and the GameSpy validation algorithm must be written anew, not taken from `gsmsalg.h`). | feature | 93b6d92 .. 66bd8ae (2019), 192d33f .. 58ee967 (2020), 9027a94, 75b2e71, 36c384e, 0db89df, fc399e1, 9735698, e3423b3, b3ad8dc, 76cc9cd | `src/Game/Libs/ServerDir/`, the game's multiplayer screens | todo |
| M-G50 | **Dedicated server without the installer's registry.** `NOLF2Srv.exe` reads its archives from the registry the installer wrote; the Modernizer takes them from `-rez` arguments and a config file. | feature | 0389129, 69fb03d | `src/Game/ServerApp/ServerDlg.cpp` | todo |
| M-G47 | **Game controllers.** The Modernizer rewrote all input on SDL2's game-controller interface (rebindable XInput-style buttons and axes, dead zones, sensitivity; a "Gamepad" screen). Here: XInput (loaded at run time) beside the engine's DirectInput joystick, feeding the same actions. | feature | ad1cd56, 26f33e3, 54c9c81, de195cc | `src/Engine/runtime/kernel/src/sys/win/input.cpp`, `ScreenJoystick` | todo |
| M-G46 | **Jukebox.** A screen that plays the game's music themes and their intensities (and, later, the soundtrack's singles). Needs its own song list: the Modernizer's `Jukebox.txt` and its song names are its own data, not taken. | feature | 802ccd2, a8514b6, c2edc87, 755e002, 3bf358b, 0020c2a, 01c200a | a new screen | todo |
| M-G3 | **The loading screen's 10 fps.** The loading-screen thread draws, then sleeps 100 ms. NOLF1's modern build shortened its equivalent sleep to load faster, and the Modernizer sleeps 10 ms (7a0d77f, 51b12f6); in NOLF2 the level loads on the main thread while this one only draws, so a shorter sleep would only take time from the load. Kept. | decided | 7a0d77f, 51b12f6 | `src/Game/ClientShellDLL/ClientShellShared/LoadingScreen.cpp` | decided |
| M-G21 | **Goal removal in `CAIGoalMgr::UpdateGoals`.** The Modernizer saw the loop use its iterator after `RemoveGoal` erased that element. The list is a `std::vector`, so with VC6's STLport the iterator then points at the next goal, which the loop means to look at -- not a bug here (only a checked-iterator library objects). | decided | 333dd70, 262e1b7 | `ObjectShared/AIGoalMgr.cpp` | decided |
| M-G24 | **`AIVolumeJunction`'s action list.** A static vector is `reserve`d and written with `operator[]` past its size. With STLport the storage is there and nothing reads its size; harmless here. | decided | c2457c2 | `ObjectShared/AIVolume.cpp` | decided |
| M-G28 | **AI information volumes' sense masks.** The current information volume is stored as an `AIVolume*` (a C cast from `AIInformationVolume*`; the two are siblings, both `AISpatialRepresentation`s) and read back with `dynamic_cast<AIInformationVolume*>`, which in the Modernizer's build failed, so the masks never applied. VC6's run time finds the target class in the object's own class list, from its virtual table, without checking the cast's source type, so the cast succeeds here and the masks apply. Not a retail bug; nothing to do. | decided | b788856 | `ObjectShared/AIStimulusMgr.cpp`/`.h` | decided |
| M-G29 | **Damage-type flags above bit 31.** `CDTButeMgr::Init` builds each type's flag as `1 << (uint64)i`; a conforming compiler shifts an `int`, so types 31 and up (there are 37) got wrong flags in the Modernizer's build ("bananas becoming incredibly deadly"). VC6 shifts in 64 bits: the code it makes (our release `Object.lto`) loads 1:0 into edx:eax and calls the run time's 64-bit shift (`__allshl`). Not a retail bug; nothing to do. | decided | 197cd30 | `src/Game/Shared/DamageTypes.cpp` | decided |
| M-G33 | **Popup text corruption (Intel).** On Intel graphics the intel-item popup text came out garbled; the Modernizer recreates the text item before each popup. The cause is unknown and the renderer here is not the retail one; not ported until it is seen. | not ported | 3fd5228 | -- | not ported |
| M-G31 | **Music stopped before loading screens.** The Modernizer brings back a stop of the music that Monolith had commented out in `PreLoadingLevelState`, against an intermittent DirectMusic crash on loading screens. Not seen here; Monolith took it out on purpose (the music plays on through the load). Not ported until the crash is seen. | not ported | bfd1586 | `InterfaceMgr.cpp` | not ported |

## The Modernizer, change by change

What the Modernizer changes that has no item of its own above, and why it is
not taken. (Each of its other changes is credited in an item.)

| Change | Commits | Decision |
|---|---|---|
| SDL2, Visual Studio 2019 projects, STLport extracted, C++ conformance edits, Azure pipeline, Discord SDK | 0196942, fed0485, a2b1746, 0f9db47, bd2ebe1, 23d5968, 2e199c5, d232b37, 6637aa4, 5dc6d7d, 101a2ff, 410e476, 3d28617, 05edf75, e2ca053, d89da8f, d357a5f, d529a8e, 5a6fb09, 1be8355, a0f9210, db8a13e and the other build-only commits | build plumbing for another compiler; the behaviour they enable is reimplemented with Win32 and VC6 |
| Discord rich presence and lobbies | 173127a, 078e90a, 08c2766, 51b12f6, 38c61a8, 4043f89, 023ed40, 89ba326, 1b75967, 9ede046, 7378781 | a closed SDK, and compiled out in the Modernizer itself |
| A new version (`v1.4M`, net version `1.0.0.4M`, handshake minor 4) | c8e1554, 65424c4, 12f2dc8, 1c8140c, 3fb5610, d90cf40 | decided: the modern build keeps 1.3's version; the handshake's checksum of `CShell.dll` already keeps differing builds apart |
| The server list ignores the mod name | bec7731, 34deaf8 | not ported: the retail check is right |
| The game times its own frames (`CWinUtil::GetTime`, a server frame time of its own for ~30 objects) | 6160c0b, 7a44cac, 557ed1b, 8501e66, fa71070 | not ported: works around the engine's timer, which is ours (M-E4) |
| Ragdolls (`EnableRagdolls`, Monolith's unfinished `RagDoll.cpp`) and the "Experimental" options screen that turns them on | d94e971, 50ab29a, a9e6c65, a70d2a7, d85deb8, 5650744, ed68ff7, 121997f | not ported: an unfinished feature (bodies fall through the world); the screen's other option is M-E4's limiter |
| The main menu without Cate (`IntroFX0` `MainLoopFX`) | b92bc92 | not needed: with M-G2 and M-E1 the menu's 3D art stays in place at any shape |
| Paint the window black before the first frame | acd9b2e | todo with M-G42 (a white window flashes when the mode changes) |
| Vehicle `NaN` guard (`FixVectorIfZero`) | 0a0362d, fef8291, f45c5ba | not ported: the NaN is in an unused vector, and the guard adds a phantom (1,1,1) acceleration |
| `CLiteObjectMgr::CleanList` | 232cb48, 57f3e6a | not ported: the retail swap-and-pop is right with STLport; only a checked-iterator library objects |
| `ButeMgr::Save` with no file name; `delete` of an array; `alloca` in `HUDDamage`; `_getcwd` checks; `FXProp` union member; `Body::Init`'s and `CSearchable`'s pointer checks; `CBodyStateExplode`'s | f20889f, 57f7ef0 | not ported: compiler warnings, not reachable faults (the destructible is a member and never NULL; a `char` array's `delete` is the same as `delete[]` in VC6). `RadarObject` is the one real bug (M-G27) |
| Asserts made quiet (garbage name/value pair, keyframer without keys, animation parser's `yyval`) | 2e91aaa, dfafe9a, f20889f | not ported: debug-build asserts only |
| Strict floating-point exception macros, parser and flex debugging, logging to `Debug.log`, crash dialog | 7adb906, 0a0362d, 9dcae71, d89da8f, e1582f8, 77a424d, 1d1fc5f, 2d9377c, 9984ed2, 6b4b696, a37a4dd, c8ffa5d | not ported: `make debug` and `make modern-debug` have symbols and the project's own crash log (`nolf2src_crash.h`) |
| `SpriteFX` offset hack | c8781bd | not ported: self-described partial, unverified |
| Random menu music | abe5e2e, f4f2c23 | not ported: compiled out, then removed |
| The second hex edit of `Lithtech.exe`: no `autoexec.cfg` written at exit (file offset `0xED0D`) | ad1cd56 | not ported: needed only because its input layer kept the bindings in a `controls.cfg` of its own (its known issue K3); our engine keeps them where retail does |
| Its art and data: the HD menu background, the console backdrop and Fira Code font, `Layout.txt`, `Jukebox.txt`, `controls.cfg`, `Default.prf`, `JServerInfo.txt` | e2c38f1, 1fa25fa, 802ccd2, ad1cd56, 013b81d | not taken (game data comes from the retail game) |

## The Modernizer's known issues

Its readme (`Assets/ModernizerReadme.txt`, Beta 2) and itch.io page list
these; each against the modern build:

| | Known issue | Here |
|---|---|---|
| K1 | Antialiasing shifts 2D items by about a pixel at their edges | with M-E13, to check when it lands (a likely cause: the 2D quads' half-pixel alignment, which a multisampled target shows) |
| K2 | Jukebox singles take a second to load | not applicable: no MP3 singles (M-G46 plays the game's own music) |
| K3 | Controls are saved in a `controls.cfg` of its own, so no other mod works with it | not applicable: the input changes (M-E3, M-G47) are in the engine, and the bindings stay in `autoexec.cfg` |
| K4 | Cate is missing from the main menu | not applicable: M-G2 with the widened interface camera keeps her beside the menu |
| K5 | Jukebox can crash while switching songs | M-G46: stop the playing theme before the next starts (to do with it) |
| K6, K7 | Jukebox songs sorted alphabetically; duplicate singles | M-G46 (its own list, in game order) |
| K8 | The controller works only in play, not in the menus | M-G47: XInput feeds the engine's actions, which the menus read too |
| K9 | Going to a lower resolution from a full-screen window can leave a borderless window | M-G42: the window style is set again on every mode change |
| K10 | A multiplayer browser crash "somewhere" | M-G26 fixes the list's selection; the browser stays retail's until M-E6 |
| K11 | The music is a little jumpy (the base game too) | M-G30: above 100 frames a second the moods drained between AI updates; at lower rates the retail behaviour is kept |

## Not changed

| What | Why |
|---|---|
| The game's FOV console variables (`FovX`, `FovY`, `FovXInterface`, ...) | M-E1 widens the drawn view in the engine instead: the game reads its camera angles back (zoom, the underwater effect) and would compound a game-side widening every frame. |
| The `sierraup.cfg` crash in `ServerDir.dll` | not a modern item: retail checks for the missing file, and so does our build in both variants (`src/nolf2src/jupiter/serverdir2-sierraup.patch`). |
