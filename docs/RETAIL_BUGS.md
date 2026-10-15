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

Where the bug is in the engine (`Lithtech.exe`, `server.dll`), the entry
names the retail address it was read from. The engine's source here is a
reconstruction (`docs/engine/PLAN.md`), so an engine entry is listed only
where our function is byte-identical to the retail one at that address
(`tools/exematch.py`; for a string, the string is in the retail image too):
it describes what the retail code does, not a guess. Addresses are as in the
retail images (`build/reference.sh` extracts them into `out/reference/`).
The game binaries (`CShell.dll`, `Object.lto`, `ClientFx.fxd`, `NOLF2.exe`,
`NOLF2Srv.exe`) are built from Monolith's own source as it shipped, so their
entries name the function and the source file instead.

Many of NOLF1's bugs (nolfsrc's `RETAIL_BUGS.md`) were looked for here. Those
NOLF2 no longer has are listed at the end, so nobody looks again.

**Fixed so far** (in the modern build):

* [The launcher starts a dedicated server that does not exist](#the-launcher-starts-a-dedicated-server-that-does-not-exist)
* [A step in a client effect's colour keys sets alpha from red, and red not at all](#a-step-in-a-client-effects-colour-keys-sets-alpha-from-red-and-red-not-at-all)
* [Unique player names are not unique](#unique-player-names-are-not-unique)
* [`CString::Left` leaves the length of the whole string](#cstringleft-leaves-the-length-of-the-whole-string)
* [Level particle systems stop emitting at high frame rates](#level-particle-systems-stop-emitting-at-high-frame-rates)
* [Above 100 frames a second the AIs slow down](#above-100-frames-a-second-the-ais-slow-down)
* [The player walks slower, and crouches slower still, at high frame rates](#the-player-walks-slower-and-crouches-slower-still-at-high-frame-rates)
* [Aim, fire sparks and debris change with the frame rate](#aim-fire-sparks-and-debris-change-with-the-frame-rate)
* [Out of the water, the player floats lower and jumps lower at high frame rates](#out-of-the-water-the-player-floats-lower-and-jumps-lower-at-high-frame-rates)
* [`CLTTransform::Inverse` returns its input](#clttransforminverse-returns-its-input)
* [`StopSecondary` and `StopMotif` can loop for ever](#stopsecondary-and-stopmotif-can-loop-for-ever)
* [`FACEOBJECT` normalises a zero vector](#faceobject-normalises-a-zero-vector)
* [`Body::FaceDir` and `FacePos` test for zero before flattening](#bodyfacedir-and-facepos-test-for-zero-before-flattening)
* [An AI backing away from an obstacle faces its own position](#an-ai-backing-away-from-an-obstacle-faces-its-own-position)
* [A keyframer aligned to its path normalises a zero move](#a-keyframer-aligned-to-its-path-normalises-a-zero-move)
* [`CMusicMgr::SetMood` reads before its level table](#cmusicmgrsetmood-reads-before-its-level-table)
* [`ci_GetLightRadius` and `ci_SetLightRadius` do not check the handle](#ci_getlightradius-and-ci_setlightradius-do-not-check-the-handle)
* [`cis_GetSurfaceDims` writes through unchecked pointers](#cis_getsurfacedims-writes-through-unchecked-pointers)
* [The console print writes one past its buffer](#the-console-print-writes-one-past-its-buffer)
* [The launcher's own path can overrun a buffer](#the-launchers-own-path-can-overrun-a-buffer)
* [Player names and chat are used as printf format strings](#player-names-and-chat-are-used-as-printf-format-strings) (on the server; see the entry)
* [A chat line overruns a stack buffer](#a-chat-line-overruns-a-stack-buffer) (on the server; see the entry)
* [`HandleAddGoal` appends without a bound](#handleaddgoal-appends-without-a-bound)
* [The server obeys debugging and single-player messages from any client](#the-server-obeys-debugging-and-single-player-messages-from-any-client)
* [A client's skill levels index past the skill tables](#a-clients-skill-levels-index-past-the-skill-tables)
* [`streamsim_Open` leaks the file when the stream cannot be allocated](#streamsim_open-leaks-the-file-when-the-stream-cannot-be-allocated)
* [The launcher never closes its find handles](#the-launcher-never-closes-its-find-handles)
* [Error messages that name the wrong function](#error-messages-that-name-the-wrong-function) (the client's)
* [`InitLevel`'s trace misspells a parameter](#initlevels-trace-misspells-a-parameter)
* [A gamepad's buttons are bound by their instance number](#a-gamepads-buttons-are-bound-by-their-instance-number)
* [The console's keys test Ctrl whatever key they ask about](#the-consoles-keys-test-ctrl-whatever-key-they-ask-about)

Not fixed yet because the code is in a part of the tree another piece of
work owns: the engine's `server/`, `shared/`, `world/`, `model/`,
`kernel/net` and `kernel/io` (the server package) and the client game
`CShell.dll` (`src/Game/ClientShellDLL`, being byte-matched). Those entries
say so.

---

## Wrong results

### The launcher starts a dedicated server that does not exist
`NOLF2.exe`, string table `IDS_SERVEREXE`, used by `CLauncherDlg::LaunchGame` ·
`src/Game/Launcher/TO2/RES/Lang/EN/Launcher.rc`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-L2): the
> string names `NOLF2Srv.exe`. The release build keeps the retail name.

The launcher's dedicated-server choice (and `NOLF2.exe -goserver`)
`WinExec`s the program named by `IDS_SERVEREXE`, `NOLF2Svr.EXE`; the game
installs the dedicated server as `NOLF2Srv.exe` (`Svr` for `Srv`), so it
never starts and the launcher says it cannot launch the server.

### A step in a client effect's colour keys sets alpha from red, and red not at all
`CBaseFX::CalcColour` (ClientFx.fxd) · `src/Game/ClientFxDLL/BaseFx.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G15): the
> red key goes to red. The release build keeps the retail line.

Between two colour keys at the same time (a step, `tmDist <= 0`) the
function writes `*pAlpha = endKey.m_red / 255.0f` where it means `*pRed`;
alpha is overwritten from the alpha key two lines later, and red is never
written. The caller's red is whatever it held: an uninitialised local in
`CSpriteSystem` (`spritesystemfx.cpp`), so an effect with a step in its
colour gets a garbage red channel at that key.

### Unique player names are not unique
`CPlayerObj::GenerateUniqueName` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/PlayerObj.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G9): the
> candidate is cut to the buffer before it is checked, and the number goes
> on a base cut short enough to keep it. The release build keeps the retail
> code.

A taken name gets a number appended (`"%s%d"`), and the candidate is checked
against the other players' names before it is cut to the 16-byte buffer.
For a name of the full 15 characters, `name0` is free, and is then cut back
to `name`: two players share the "unique" name the game uses for the
scoreboard, kill messages and chat.

### `CString::Left` leaves the length of the whole string
`0x10141c10` (CShell.dll; `MFCStub`, also in the other game binaries that
call it) · `src/libs/MFCStub/mfcs_string.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G16): the
> length is set from the cut string. The release build keeps the retail
> code.

`Left(n)` copies the whole string and writes a terminator at `n`, without
setting the length, so `GetLength()` reports the original length and a
`Concat` afterwards appends behind the terminator, where nothing reads it.
NOLF1's `MFCStub` had the same fault in `Concat` (nolfsrc); NOLF2's
`Concat` is right, `Left` is not. The host screens cut the session name and
passwords with it (`ScreenHost.cpp`). (`Mid` has the same omission, and
builds from past the end when `nFirst` is beyond it, but no shipped binary
links it.)

### Level particle systems stop emitting at high frame rates
`CParticleSystemFX::Update`, `CLineSystemFX::Update` (CShell.dll) ·
`src/Game/ClientShellDLL/ClientShellShared/ParticleSystemFX.cpp`, `LineSystemFX.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E4): an
> update that owes less than one particle (or line) leaves the clock
> alone, so the time adds up until one is owed (nolfsrc's fix). The
> release build keeps the retail code.

NOLF1's bug, unchanged: each update adds `floor(fParticlesPerSecond * dt)`
particles and restarts the clock, so the fraction is lost every frame. When
a frame is shorter than one particle's worth of time the count is always 0:
at 100 frames a second, every emitter slower than 100 particles a second
goes dark. The weather volumes' snow is such a system and their rain a line
system (`WeatherFX.cpp`), which does the same; no retail single-player world
places a `ParticleSystem` object itself. And the other way round for a
system that thins out with the camera's distance (`bRelToCameraPos`):
`GetNumParticles` turns any count, 0 too, into at least one once the camera
is past the inner radius, so such a system adds one particle every frame,
more the faster the frame rate.

### Above 100 frames a second the AIs slow down
`CAI::EngineMessageFn` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/AI.cpp`,
`AIUtils.cpp` (`c_fUpdateDelta`); the engine's server tick,
`src/Engine/runtime/server/src/servermgr.cpp` (`CServerMgr::Update`)

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E4): a
> game tick runs only once 10 ms have passed since the last one. The
> release build keeps the retail code.

In single player the client runs the server once a frame, and each tick
advances the game by the real time since the last (in whole
milliseconds; no time is lost, unlike NOLF1's 10 ms minimum). An AI asks
to be updated every `c_fUpdateDelta`, 10 ms, and its update moves, turns
and counts down by the server's frame time (`GetFrameTime`): the time since
the last *tick*, not since its own last update. Up to 100 frames a second
each tick covers at least 10 ms and the AI is updated every tick; above
that it is updated on one tick in two, three or more but still steps by one
tick's time, so whatever it does by the frame time runs slow: at 300 frames
a second a third of its speed, at 700 a sixth. Measured (a temporary log of
one AI's updates in the Performance world's tornado cinematic): the AI's
frame times added up to 0.71 of the game time at 60 frames a second and
0.12 at 719; with the fix, 0.71 at 748. Any other object updated less often than every
frame does the same. The game time itself, and so the cut-scenes (their
cameras and keyframers update every frame) and the timers, run at real
speed at any rate: the camera cuts of that cinematic came within 0.05 s of
each other at 59 and 719 frames a second.

### The player walks slower, and crouches slower still, at high frame rates
`CMoveMgr::UpdateNormalMotion`, `MoveLocalSolidObject`, `UpdateMotion`,
`UpdatePushers` (CShell.dll) ·
`src/Game/ClientShellDLL/ClientShellShared/CMoveMgr.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E4): the
> speed cap is applied once a 60th of a second, and the per-frame amounts
> below are per 60th of a second. The release build keeps the retail code.

The player's speed is cut back to the cap (`GetMaxVelMag`) at the start of
each frame, and the frame's push then takes it past the cap until the next
frame (the engine's physics, `motion.cpp`, is exact for a constant push):
the longer the frame, the faster the walk. Measured (a temporary per-frame
log of the player's position, C01S01): 197 units a second at 60 frames a
second, 183 at 300 and at 700 -- 7% slower. And a frame's move shorter than
0.1 is dropped (`MoveLocalSolidObject`): 6 units a second at 60 frames a
second, 30 at 300, 100 at 1000, where a crouching walk (92 units a second)
is below it and barely moves -- measured 29 units in a second's walk
backwards at 636 frames a second, 92 at 60. Three more amounts are per
frame: the "can't move" damping halves the speed every frame, the
spectator's takes 0.9 of it every frame, and a pusher (an explosion's
push) adds its whole push every frame it lasts.

Left as it is: a jump's arc. The engine integrates gravity with a quarter
of a·dt² instead of half, which raises a jump by about g·t·dt/4: 51.5
units at 60 frames a second, 50.0 at 300, 49.8 at 700 (its exact height),
the air time 0.47 s and 0.45 s. Retail's own range was wider (at 30 frames
a second, higher still).

### Aim, fire sparks and debris change with the frame rate
`CClientWeapon::UpdateMovementPerturb`, `CFireFX::Update`,
`BounceMovingObject` (CShell.dll) ·
`src/Game/ClientShellDLL/ClientShellShared/ClientWeapon.cpp`, `FireFX.cpp`,
`client_physics.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E4): each
> is measured per 60th of a second. The release build keeps the retail
> code.

Three amounts are per frame where they mean per time:
- the weapon's inaccuracy from turning takes the turn since the last frame,
  so the same turn spreads the aim less the higher the frame rate (a fifth
  as much at 300 frames a second as at 60);
- a fire makes a spark with one chance in ten every frame, five times as
  many sparks at 300 as at 60;
- a bouncing piece of debris (shell casings, gibs) comes to rest below a
  speed of 15/√dt (116 units a second at 60, 260 at 300), so at high frame
  rates it stops sooner.

### Out of the water, the player floats lower and jumps lower at high frame rates
`CMoveMgr::UpdateInLiquid`, `UpdateNormalMotion` (CShell.dll) ·
`src/Game/ClientShellDLL/ClientShellShared/CMoveMgr.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E4): the
> rise lasts two 60ths of a second, and the jump gets a 60th of a second's
> swim-up push, at any frame rate (nolfsrc's fix). The release build keeps
> the retail code.

NOLF1's bug, unchanged. Swimming up, the rise stops the frame after the
head (the camera, which lags a frame) breaks the surface, so the faster the
frame rate the lower the player floats. And a jump out of the water also
gets that frame's swim-up acceleration on top of the jump's speed, so its
height depends on the frame's length. Measured (a temporary per-frame log,
C13S03's pool): floating 3 units lower at 120 frames a second than at 60;
the upward speed after the jump frame 472 units a second at 120, 496 at
60; the jump's top 61 units above where it started at 120, 71.5 at 60. With
the fix: the float height as at 60, 495 units a second, 67 units. In NOLF1
the lower float let the head bob dip the camera back under, and the jumps
to climb out were lost; NOLF2's swimming did not dip it in the test.

### Snow ignores the size of its weather volume
`CWeatherFX::CreateSnow` (CShell.dll) · `src/Game/ClientShellDLL/ClientShellShared/WeatherFX.cpp`

Not fixed, as in nolfsrc: the levels were tuned with it.

NOLF1's bug, unchanged: the flake rate is scaled by the volume's area into
`fFlakesPerSec`, and the particle system is then given the unscaled rate
read from the attributes again. Every snow volume snows at the same rate.

### The server list reselects the wrong row
`CScreenJoin::DisplayCurServerList` (CShell.dll) · `src/Game/ClientShellDLL/TO2/ScreenJoin.cpp`

Not fixed yet: `CShell.dll`.

Rebuilding the list, `if (nServerIndex = m_nSelectedServer)` assigns where
it means to compare. With any server but the first selected, every row
matches, and the selection ends on the last row.

### A gamepad's buttons are bound by their instance number
`CScreenConfigure::Bind` (CShell.dll) · `src/Game/ClientShellDLL/TO2/ScreenConfigure.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`): a joystick's and a
> gamepad's controls are both bound by name (MODERN.md M-G63).

Configure controls binds the control just pressed. A key is named by its
scan code (`"##%d"`, e.g. `##57`); a joystick's control is meant to be named
by its name, but the test is
`nControlCode && (deviceType != DEVICETYPE_JOYSTICK || deviceType == DEVICETYPE_GAMEPAD)`,
whose second half adds nothing: for a gamepad it is true, so a gamepad's
button is bound as `##<its instance number>` (button 0 alone, whose number
is 0, by name). The engine resolves `##n` to the first of the device's
objects whose instance number is n (`input_AddTrigger`,
`DeviceObjectEnumCallback`), and DirectInput numbers a HID gamepad's axes
and buttons each from 0, axes first: the second button binds the Y axis.
The button then does nothing, and the binding's range (0 to 0), held
against the axis's value, turns the command on while the stick is at one
end of its travel (an axis that reads 0 there). Meant,
by all appearances: `!= DEVICETYPE_JOYSTICK && != DEVICETYPE_GAMEPAD`.

### A particle system's colour range ignores the start colour
`CBaseParticleSystemFX::GetRandomColorInRange` (CShell.dll) ·
`src/Game/ClientShellDLL/ClientShellShared/BaseParticleSystemFX.cpp`

Not fixed yet: `CShell.dll`; the fix also changes how smoke, trails and
explosions look.

The red component is picked between the two colours, and green and blue are
scaled from it as `m_vColorRange.y * fColorR / m_vColorRange.x`, without
`m_vColor1` and with `fColorR` where `fColorR - m_vColor1.x` belongs: colour
1 (100, 200, 50) to colour 2 (200, 250, 100) gives green 25 to 50, not 200
to 250. When only green or blue varies, the colour is always colour 1. NOLF1
has the same code.

### Sprite systems take an animation length in the wrong unit, and one mode applies `AnimSpeed` the wrong way
`CSpriteSystem::Init`, `CSpriteSystem::Update` (ClientFx.fxd) · `src/Game/ClientFxDLL/spritesystemfx.cpp`

Not fixed: every sprite-system effect was tuned as it is.

The default animation length (`SS_ANIMLEN_SPRITEDEFAULT`) takes the sprite's
length in milliseconds as frames a second, then divides the frame count by
it, giving frames squared over milliseconds: an 8-frame sprite at 10 frames
a second lasts 0.08 s, not 0.8 s (the two agree only at about 31.6 frames a
second). And `AnimSpeed` divides the length in two modes and multiplies it
in the particle-lifespan one, so speed 2 doubles the rate in two modes and
halves it in the third.

### The attached-camera animation clamp skips ten frames
`CPlayerMgr` (CShell.dll) · `src/Game/ClientShellDLL/ClientShellShared/PlayerMgr.cpp`

Not fixed yet: `CShell.dll`.

When the player's attached-camera animation would run backwards, it is set
to the previous time plus `10000.0f * GetFrameTime()`: animation times are
milliseconds, so that is ten frame times ahead, not one.

### `CGenLTStream::WriteStream` ignores the source offset
`0x1000edec` (server.dll) · `src/Engine/runtime/shared/src/genltstream.cpp`

Not fixed yet: the engine's `shared/`.

NOLF1's `CBaseStream::WriteStream`, unchanged in its successor: `dwMin` is
used to work out how much to copy and for nothing else; the source is never
sought there, so the bytes come from wherever it was.

### The compressed-vector codec does not round-trip
`0x10006c22` encoder, `0x10006d75` decoder (server.dll) ·
`src/Engine/runtime/shared/src/compress.cpp`

Not fixed yet: the engine's `shared/`.

NOLF1's bug, unchanged: the minor axes are encoded scaled by 2^18 - 1 and
decoded divided by 2^18, so every vector comes back short by one part in
262144 on both.

### The property-type guard normalises to a value that is also out of range
`cb_VerifyClassDefProperties`, `0x10001db5` (server.dll) · `src/Engine/runtime/shared/src/classbind.cpp`

Not fixed yet: the engine's `shared/`.

NOLF1's bug, unchanged: a `PropDef` type outside `PT_STRING`..`PT_ROTATION`
in a loaded object DLL is rewritten to `NUM_PROPERTYTYPES` (8), one past the
last type, and the DLL is accepted.

### `ReadHStringAsString` seeks backwards, in the wrong unit
`CLTMessage_Read::ReadHStringAsString`, `0x10012b11` (server.dll) ·
`src/Engine/runtime/shared/src/ltmessage.cpp`

Not fixed yet: the engine's `shared/`.

After reading `min(nMaxLen, nLength)` characters it should skip the rest of
a string too long for the buffer. The test is the wrong way round
(`if (nMaxLen > nLength)`), so the common case, a buffer bigger than the
string, seeks *back* by the difference, and a string that was cut leaves its
tail unread; and `Seek` counts bits where it is given bytes. Either way the
next field of the message is read from the wrong place. The null-string
length `0xFFFF` is also read as 65535 characters.

### `WriteMessage` stores a nested message's size in 16 bits
`CLTMessage_Write::WriteMessage`, `0x100126dc` (server.dll) ·
`src/Engine/runtime/shared/src/ltmessage.cpp`

Not fixed yet: the engine's `shared/`.

The size of a message written into another is in bits and written with
`Writeuint16`: a sub-message over 65535 bits (8 KB) gets a wrong size, and
the reader (`ReadMessage`, `0x1001296a`, which only `ASSERT`s) reads the
rest of the outer message out of step.

### `CD3DDrawPrim::SetCamera` hands `SetViewport` an unset width and height
`0x41d760` (lithtech.exe) · `src/Engine/runtime/render_b/src/sys/d3d/d3ddrawprim.cpp`

Not fixed yet (the renderer; see below for what our source already does).

Retail fills the local viewport's position and depth range but not its width
and height, and writes the camera's size into the *saved* viewport instead;
`SetViewport` then gets whatever was on the stack, and `PopRenderStates`
later restores a viewport with the camera's size at the old position. The
no-camera branch also compares the saved member `m_PrevViewport.X` where the
local `PrevViewport.X` is meant. Our source already deviates from retail at
the first point (it fills the local's width and height: the renderer would
not run otherwise, `docs/engine/PLAN.md` package 6), so the release build
does not reproduce that half; the other two are retail's in both builds.

### `CLTDirectMusicMgr::Stop` discards the queue it was asked to wait for
`0x43d800` (lithtech.exe) · `src/Engine/runtime/kernel/src/sys/win/ltdirectmusic_impl.cpp`

Not fixed, as in nolfsrc: the game only ever calls it with the default enact
type.

`Stop(LTDMEnactNextSegment)` leaves the primary segment to run out but
empties the command queues at once.

### The engine's version reads 4294967295.4294967295
`GetLTExeVersion`, `0x491200`; `RunClientApp`, `0x4054c0` (lithtech.exe) ·
`src/Engine/runtime/kernel/src/sys/win/version_resource.cpp`, `client.cpp`

Not fixed: cosmetic.

The version comes from an `RCDATA` resource 12346 that the retail exe does
not have. `GetLTExeVersion` fails, the failure is ignored
(`CClientMgr::Init`), and the `LTVersionInfo` keeps the `0xFFFFFFFF` its
constructor set: the console's `version` and the log line "LithTech build
4294967295.4294967295 initialized" print that.

### Mouse look overshoots, unevenly, and more at high frame rates
`input_ReadInput`, `0x4319b0` (lithtech.exe) · `src/Engine/runtime/kernel/src/sys/win/input.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`): the mouse's whole
> buffer is read and each look axis hands on the sum of the frame's
> motion, once (MODERN.md M-E3); the frame rate is limited to 240 by
> default (M-E4). The sensitivity's scale is kept, so a setting turns as
> it did in 2002 (about 1.2x then, 1x now); the Mouse screen's "Input
> rate", the smoothing, is gone.

The system mouse is read one DirectInput event at a time (`nEvents = 1`,
"fixes the USB mouse lockups"; x and y are separate events), and after each
event, and once more after the empty read that ends the loop, every trigger
is run and adds its current value to the frame's axis offsets. A relative
axis's value is its *last* event (not the sum of the frame's), blended 12%
(`InputRate` / 100) toward the mean of its last three, and it is only
replaced by a zero once `GetTickCount` has moved more than `InputRate` / 10
ms past that event, a test made once a frame. So:
- an x event is added again on every y event's pass of the same frame:
  moving diagonally roughly doubles the horizontal turn;
- a value is added again on every frame until a tick goes by: the faster
  the frame rate, the more times;
- slow motion (few events a frame) is amplified more than fast motion.

A model of the function (byte-identical to retail), fed an even sweep,
turns the view by these multiples of the mouse's motion: 1.06 at 60 frames
a second with a 1000 Hz mouse moving fast, 1.6 moving slowly, 2.1
diagonally; at 144 frames, 1.15, 2.4 and 2.2; at 300 frames with a 125 Hz
mouse, 2.9 and 3.8 diagonally. Measured in the release build (a temporary
log of each frame's mouse counts and look offsets, under Xvfb at about 57
frames a second, xdotool moving the pointer every 30 ms): 2.8 horizontally;
diagonally 3.8 in x and 2.8 in y (y's event comes second, so x is added
again on its pass); one event of 2 counts turned the view by 3.68, 1.84 and
0.08 counts' worth over three frames. In 2002, at 30 frames a second and a 125 Hz
mouse, it was a steady 1.2. Today's frame rates (the release build has no
frame limit: `MaxFPS` works only outside the final build) make the look
speed change with speed, direction and frame time, which reads as a mouse
that jumps about. The fix is to add up each look axis's events over the
frame and use that once.

### `CLTTransform::Inverse` returns its input
`0x10047c91` (server.dll) · `src/Engine/runtime/shared/src/transformlt_impl.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`): the inverse matrix is
> converted back. The release build keeps the retail call. No `MODERN.md`
> entry: nothing in the game calls it.

It turns the transform into a matrix, inverts that into `mInverse`, and then
converts the *original* matrix back into `inverse` (`lea -0x40(%ebp)` at
`0x10047cb3` is `mTransform`, not `mInverse`), so `inverse` comes back
equal to `transform`.

### The multiplayer timer runs on while paused
`CInterfaceTimer::Draw`, `0x100eb260` (CShell.dll) ·
`src/Game/ClientShellDLL/ClientShellShared/InterfaceTimer.cpp`, `InterfaceTimer.h`

Not fixed yet: `CShell.dll`.

The timer works out the time left from the game time on every draw and
never reads the pause flag the server sends with it
(`CInterfaceMgr::HandleDisplayTimerMsg`; `SetTime` stores the flag, at
`0x1005c484` and `0x10063f4e`, and nothing reads it), so a paused round's
timer keeps counting down on screen. The source release fixes it: it keeps
the time left (`m_fTimeLeft`) while paused. Retail's class has no such
member, which is how the reconstruction matches.

### Possibly: an armed bomb deactivates after a stopped defuse
`Bombable::HandleStoppedMsg`, `0x101d45b0` (Object.lto) ·
`src/Game/ObjectDLL/ObjectShared/Bombable.cpp`

Not fixed: not seen in the game yet.

When a defuse is interrupted and the bomb is still armed, retail sets
`m_bCanDeactivate` (the store at `0x101d4640`); planting cleared it so that
`Prop::Update` keeps the object updating for the countdown. The source
release does not set it there. If it matters, an armed bomb whose defuse
was stopped may stop updating, and its countdown with it.

### The console's keys test Ctrl whatever key they ask about
`CConsole::OnKeyPress`, `0x497c00`, and `CConCommandBox::OnKeyPress`,
`0x4963d0` (lithtech.exe) ·
`src/Engine/runtime/client/src/sys/win/winconsole_impl.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, `MODERN.md` M-E5):
> `IsKeyDown` tests the key it is given.

The console's `IsKeyDown(vkKey)`, inlined into both, ignores its argument
and tests `VK_CONTROL`, so Shift+Tab (complete backwards) did what Ctrl+Tab
does (list the matches). Retail never opens its console, so nobody met it
there; the modern build's console does.

### The console's name completion runs past the engine variables
`CClientConIterator::NextItem`, `0x41b130` (lithtech.exe) ·
`src/Engine/runtime/client/src/consolecommands.cpp`

Not fixed: the modern build's console completes names its own way
(`MODERN.md` M-E5), and retail's never runs.

Walking the engine variables, it ends the list when the *command* index
(`m_iCommandIndex`) reaches the number of engine variables instead of the
engine variable index, so the walk only stops when `Get` finds nothing past
the end of the table. It also has no `End` or `PrevItem`, so completing
backwards (Shift+Tab, once the entry above is fixed) finds nothing.

---

## Crashes and corruption: checks that are missing

### `StopSecondary` and `StopMotif` can loop for ever
`0x43e3a0`, `0x43e710` (lithtech.exe) · `src/Engine/runtime/kernel/src/sys/win/ltdirectmusic_impl.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E7): one walk
> over the list serves the by-name and the stop-everything case; each node is
> visited once, its next link read first. The release build keeps the
> retail loops.

Stopping by name re-runs `Find(name)` until nothing is found, and only
`CleanupSegmentState` takes a node out of the list. It is skipped for a node
whose enact type is "play to the end" (`LTDMEnactNextSegment`, the
`Segment` keyword of the game's `music stopsecondary` and `stopmotif`
commands, or a segment whose default is that) and, as in NOLF1, for one
whose segment has no DirectMusic segment (the wrong member is tested). Such a
node is found again for ever: the game hangs, holding the music command
queue's lock. The stop-everything walk moves on only past nodes with a
segment state, so a node without one would hang it too.

### `FACEOBJECT` normalises a zero vector
`CPlayerObj::ProcessCommand` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/PlayerObj.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G10): with
> no horizontal direction the player's rotation is left alone.

NOLF1's bug, unchanged: turning the player to face an object, the direction
is flattened and normalised with `VEC_NORM`; an object straight above or
below the player leaves a zero vector, and the rotation is set from NaNs.

### `Body::FaceDir` and `FacePos` test for zero before flattening
`Body::FaceDir`, `Body::FacePos` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/Body.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G11): the
> test is made on the flattened direction.

Both guard the normalisation against a zero direction, then set `y` to 0 and
normalise: a straight up or down direction passes the test and normalises a
zero vector. `CBodyStateExplode::Init` passes the death direction, so a body
thrown straight up gets a NaN rotation.

### An AI backing away from an obstacle faces its own position
`CAIMovement` obstacle avoidance (Object.lto) · `src/Game/ObjectDLL/ObjectShared/AIMovement.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G12): it
> faces away from its move, as the path code in the same file does.

Moving backwards (`kAM_Encode_GB`) around an obstacle, the AI is told to
`FacePosMoving(m_pAI->GetPosition())`: the direction to its own position is
zero, `Normalize` makes it NaN, and `CAI::FacePos` (whose "too close" test a
NaN passes) stores NaN as the target rotation, which is saved with the game.

### A keyframer aligned to its path normalises a zero move
`KeyFramer::UpdateObjects` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/KeyFramer.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G13): an
> object that did not move, or whose target is where it is, keeps its
> rotation.

`AlignToPath` takes the object's direction from its last move and
normalises it: an update that does not move it (`GOTOKEY` to the key it is
at, two keys at the same place) gives it a NaN rotation. A target object at
the object's own position does the same.

### `CMusicMgr::SetMood` reads before its level table
`CMusicMgr::SetMood` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/MusicMgr.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G14): a mood
> out of range, or one with no levels, is refused.

It picks `GetRandom(0, m_acMoods[eMood] - 1)`; for a mood the theme gives
no levels that is `GetRandom(0, -1)`, which returns 0 or -1, and indexes the
level table at `0xFFFFFFFF` or at a slot never set. The player's `SetMood`
message checks the mood only against the top of the range, so a negative
one indexes before the table.

### `ci_GetLightRadius` and `ci_SetLightRadius` do not check the handle
`0x475380`, `0x40b870` (lithtech.exe) · `src/Engine/runtime/client/src/clientde_impl.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E8): a null
> handle returns. The release build keeps the retail reads.

NOLF1's `ci_SetLightRadius` bug, and now its getter too: both read the
object type straight off the handle, so a null one faults.

### `cis_GetSurfaceDims` writes through unchecked pointers
`0x4932f0` (lithtech.exe) · `src/Engine/runtime/client/src/sys/win/winclientde_impl.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E8): only
> the outputs given are zeroed.

NOLF1's bug, unchanged: given a surface it fills whichever outputs were
asked for; given a null surface it zeroes both without checking either.

### The console print writes one past its buffer
`CLTClient::CPrint`, `0x408db0`; `dsi_PrintToConsole`, `0x4293f0` (lithtech.exe) ·
`src/Engine/runtime/client/src/clientde_impl.cpp`,
`src/Engine/runtime/kernel/src/sys/win/dsys_interface.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E10): the
> line is formatted one short of the buffer, and an empty one is not read
> before its start.

Both format into a stack buffer (512 and 500 bytes) and then, if the line
does not end in a newline, write `'\n'` at `len` and the terminator at
`len + 1`. A line that filled the buffer has `len` one short of its end, so
the terminator goes one byte past it. An empty line reads `msg[-1]`.

### The launcher's own path can overrun a buffer
`CLauncherApp::InitInstance` (NOLF2.exe) · `src/Game/Launcher/Launcher.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-L3): the
> path is written with a bound.

Checking whether the game is already running, the launcher reads the
current directory into 125 bytes, appends `\`, and `sprintf`s it with
`LITHTECH.EXE` into `sExe[128]`: an install directory of 116 to 124
characters overruns `sExe` at start-up.

### Lip-sync keyframes go out of step when a bone is skipped
`HandleNodeControlLipSync` (CShell.dll) · `src/Game/ClientShellDLL/ClientShellShared/NodeController.cpp`

Not fixed yet: `CShell.dll`.

A `.lip` file names its bones, then gives each one's keyframes. A bone the
model does not have, or one no node control is free for, is skipped in the
second loop without reading its keyframe block, so every later bone reads
the previous one's data. The bone count from the file also indexes a
32-entry array, and the bone name length fills a 256-byte buffer, unchecked.

### `ILTModel::GetNodeName` reads one past the node list
`0x4a7a90` (lithtech.exe; the same code in server.dll) · `src/Engine/runtime/shared/src/modellt_impl.cpp`

Not fixed yet: the engine's `shared/`.

The node is checked with `hNode > NumNodes()`, where `>=` is meant: node
`NumNodes()` reads one past `m_FlatNodeList` and calls `GetName()` through
what is there. (NOLF1's `ci_GetModelNodeName` refused node 0 and did not
terminate; NOLF2's accepts node 0 and uses `LTStrCpy`, but has this.)

### `trk_ScanToKeyFrame` divides by the last keyframe's time
`0x100011d6` (server.dll) · `src/Engine/runtime/model/src/animtracker.cpp`

Not fixed yet: the engine's `model/`.

NOLF1's `at_Advance` bug in its successor: a looping animation wraps with
`%= endTime`, guarded only against one keyframe, so several keyframes all at
time 0 divide by zero.

### `LTObject::Clear` leaves the standing-on link untied
`0x10021fa2` (server.dll) · `src/Engine/runtime/shared/src/objectmgr.cpp`

Not fixed yet: the engine's `shared/`.

NOLF1's `m_StandingLink` bug, unchanged: of the object's links only this
one gets its data pointer and no `prev`/`next`, so they are whatever the
object bank's memory held. Latent: it is unlinked only when `m_pStandingOn`
is set.

### An object DLL of the wrong version is freed twice
`cb_LoadModule`, `0x10001d42` (server.dll) · `src/Engine/runtime/shared/src/classbind.cpp`

Not fixed yet: the engine's `shared/`.

On a version mismatch it unbinds the module (deleting the binding and
`FreeLibrary`) but leaves the pointer in the `ClassBindModule`, and
`CClassMgr::Term` unbinds it again (`0x1000201a`): a second `FreeLibrary`
and a delete of freed memory.

### The world loader trusts a polygon's vertex count
`WorldBsp::Load`, `0x100092c1`; `w_NodeForIndex`, `0x10008e34` (server.dll) ·
`src/Engine/runtime/world/src/de_mainworld.cpp`

Not fixed yet: the engine's `world/`.

A polygon is read into a stack `SDiskPoly` with room for 40 vertices,
sized by the vertex count from the file (a `uint8`): up to 1,028 bytes go
into 168. The texture-name loop writes past its length the same way, and
`w_NodeForIndex` lets an index below -2 through to `&pList[index]`. Only a
malformed world file triggers them.

---

## Multiplayer: what one machine can do to another

### Player names and chat are used as printf format strings
`CGameServerShell::HandlePlayerMessage`, `HandlePlayerGhostMessage`,
`HandlePlayerTaunt` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/GameServerShell.cpp`;
`CServerDlg` (NOLF2Srv.exe) · `src/Game/ServerApp/ServerDlg.cpp`,
`ScmdConsoleDriver_ServerApp.cpp`;
`CLTServer::CPrint`, `0x1002c875` (server.dll) · `src/Engine/runtime/server/src/serverde_impl.cpp`;
`CInterfaceMgr::OnMessage` (CShell.dll) · `src/Game/ClientShellDLL/ClientShellShared/InterfaceMgr.cpp`

> **FIXED in the modern build, on the server** (`NOLF2SRC_MODERN`,
> MODERN.md M-G5): the game server prints names and chat through `"%s"`,
> takes `%` out of player names (`GenerateUniqueName`) and chat lines before
> it prints or relays them, and the dedicated server's console and log
> print their lines as text (`WriteConsoleString("%s", ...)`, `fputs`).
> A client connected to a modern server, retail or not, so never receives a
> `%`. Not fixed yet: the engine's `CLTServer::CPrint` (the server package)
> and the client's own printing (`CShell.dll`).

NOLF1's LithTech format-string hole, wider in NOLF2. On the server, a taunt
line goes straight to `CPrint(szString)`, and a chat line is `sprintf`ed
with the name and then printed with `CPrint(szMsg)`. The engine's
`CLTServer::CPrint` formats its arguments and passes the result to
`dsi_PrintToConsole` (`0x1000ac2d`) *as a format* a second time; on a
dedicated server the line reaches `CServerDlg::WriteConsoleString`, which
formats it a third time, and the server log, `fprintf(file, line)`, a
fourth. On every client the kill and tag messages are built with the
player's name and printed with `CPrint(szTmp)`. A `%n` in a name or a chat
line writes through the stack on the server and on everyone who sees it.

### A chat line overruns a stack buffer
`CGameServerShell::HandlePlayerMessage` (Object.lto);
`CInterfaceMgr::OnMessage`, `MID_PLAYER_MESSAGE` (CShell.dll)

> **FIXED in the modern build, on the server** (`NOLF2SRC_MODERN`,
> MODERN.md M-G5): the server prints without the buffer and cuts the line to
> 200 characters before relaying it, which a client's buffer holds with any
> name. Not fixed yet in the client's own code (`CShell.dll`).

New in NOLF2: a chat line of up to 255 characters is `sprintf`ed as
`"%s: %s"` with the player's name into `char szMsg[256]` on the server, and
relayed unchanged to every client, which `sprintf`s it as `"%s : %s"` with
the name into another `char szTemp[256]`. The game's chat box stops at 63
characters; a modified client does not, and overruns the stack of the
server and of every other player at once.

### `HandleAddGoal` appends without a bound
`CGameServerShell::HandleAddGoal` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/GameServerShell.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G6): it
> stops at the first pair that does not fit (and, M-G7, ignores the message
> from remote clients).

The AI debugging message `MID_ADD_GOAL` names an AI and a count of
name/value pairs, each up to 63 characters, which are `strcat`ed into a
128-byte stack buffer. Two long pairs overrun it, from any client that names
an existing object.

### The server obeys debugging and single-player messages from any client
`CGameServerShell::OnMessage`, `HandleConsoleTrigger` (Object.lto) ·
`src/Game/ObjectDLL/ObjectShared/GameServerShell.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G7): in a
> multiplayer game the server ignores those messages from remote clients,
> and a trigger without a command is no longer compared. `CP_DAMAGE` is not
> changed (see below).

The client sends pause and unpause only in single player, and teleport,
console commands and triggers, stimuli, object alpha and AI goals only from
its developer console (teleport only in a non-final build); the server
obeys all of them from any client in any game. Any player can pause the
server, teleport, send any message to any object (`trigger`) or run any
command-manager command. A trigger whose command is a null string
(`ReadHString` of the null marker) is passed to `_strnicmp` and crashes the
server. Also `CPlayerObj::HandleClientMsg`'s `CP_DAMAGE` applies damage of a
client's choosing to any object it names; the game sends it for falls and
vehicles, so refusing it needs more than a guard, and it is left as it is.

### A client's skill levels index past the skill tables
`CSkills::MultiplayerInit` (Object.lto) · `src/Game/ObjectDLL/ObjectShared/Skills.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-G8): no
> level past the table.

With skills on (co-op), a client's requested levels (up to 255) are bought
while the pool lasts, each level's cost read from
`m_nCosts[skill][level]` unchecked: past level 4 it reads the next skill's
row (whose level-0 cost is 0, so it is free), and later the modifier tables
(`m_Stealth[level]`, ...) are indexed past their end too.

### The join password and the handshake are not enforced
`CGameServerShell::ProcessHandshake`, `OnMessage` (Object.lto) ·
`src/Game/ObjectDLL/ObjectShared/GameServerShell.cpp`

Not fixed yet: it needs a test with a client and a server on two machines.

NOLF1 sent the password to anyone who asked; NOLF2 checks a hash of it on
the server. But on a wrong password the server only tells the client
(`KickClient` is commented out, "so that it can handle an incorrect password
a little more smoothly"), and nothing waits for the handshake: a client is
put in the world before it, and no message is refused until it is done. A
client that ignores the answer, or skips the handshake, plays on a locked
server and skips the handshake's checks of the game files' checksums.

### The server keeps a client's first hello and trusts the client pointer
`OnHelloPacket`, `0x10027c31`; `OnConnectStagePacket`, `0x10027c0b`;
`OnCommandStringPacket`, `0x10027b3a` (server.dll) ·
`src/Engine/runtime/server/src/s_net.cpp`

Not fixed yet: the engine's `server/`.

A second hello replaces the client's data buffer (up to 64 KB, the size the
client gives) without freeing the first, as often as the client likes; and
these three handlers use the client pointer without the null check the
others make.

### `ReadHString` assumes the string is terminated
`CLTMessage_Read::ReadHString`, `0x100129bb`; `PeekHString`, `0x10012d2a`
(server.dll) · `src/Engine/runtime/shared/src/ltmessage.cpp`

Not fixed yet: the engine's `shared/`.

The characters are read into an `alloca` buffer of the given length and
passed to `str_CreateString`, which reads to a terminator: a string sent
without one is read past the buffer.

---

## Leaks

### `streamsim_Open` leaks the file when the stream cannot be allocated
`0x10033f49` (server.dll) · `src/Engine/runtime/kernel/src/sys/win/streamsim.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E12): the
> file is closed.

NOLF1's bug, unchanged: `fopen` succeeds, the stream object fails to
allocate, and the function returns null with the file open.

### The launcher never closes its find handles
`ExistRezFile`, `ExistRezDir`, `CDisplayMgr::EnumerateRenderers` (NOLF2.exe) ·
`src/Game/Launcher/RezFind.cpp`, `DisplayMgr.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-L3).

Each `_findfirst` handle is left open on every path.

### `_findclose` on a handle that was never opened
`df_GetFileInfo`, `0x1000832b` (server.dll) · `src/Engine/runtime/kernel/io/src/sys/win/de_file.cpp`;
`CProfileMgr`, `CPerformanceMgr`, `CScreenHostMission` (CShell.dll);
`CWinUtil::CopyDir`, `EmptyDir` · `src/Game/Shared/WinUtil.cpp`

Not fixed: harmless (the C runtime refuses the -1 handle).

NOLF1's `ar_FindFile` slip in several places: the `_findclose` follows the
`if (handle != -1)` block instead of being in it.

---

## Wrong diagnostics

Minor: these change what the engine reports, not what it does.

### Error messages that name the wrong function

> **FIXED in the modern build, in the client** (`NOLF2SRC_MODERN`,
> MODERN.md M-E11): the rows marked fixed report their own names. The server
> ones wait for the server package.

The engine's parameter checks report through a macro taking the function's
name; these were copied from a neighbour and the name never changed. Every
function is byte-identical to retail's, and every wrong name is in the
retail image.

| function | address | reports itself as | |
|---|---|---|---|
| `ci_FreeServiceList` | `0x40bc10` (lithtech.exe) | `CLTClient::GetServiceList` | fixed |
| `cis_UnoptimizeSurface` | `0x492ee0` (lithtech.exe) | `OptimizeSurface` | fixed |
| `cis_RenderObjects` | `0x495260` (lithtech.exe) | `RenderCamera`, at three of its four checks | fixed |
| `CLTPhysicsClient::SetObjectDims` | `0x4ac200` (lithtech.exe) | `SPhysicsLT::SetObjectDims` | fixed |
| `ci_GetSoundTimer` | `0x409d50` (lithtech.exe) | `GetSoundDuration` | fixed |
| `ci_SortParticles` | `0x40b320` (lithtech.exe) | `CLTClient::OptimizeParticles` | fixed |
| `CLTClient::SetCanvasRadius` | `0x4088e0` (lithtech.exe) | `CLTClient::GetCanvasRadius` | fixed |
| `CLTClient::GetMaxRadiusInPoly` | `0x408950` (lithtech.exe) | `CLTServer::GetMaxRadiusInPoly` | fixed |
| `in_GetPerformanceInfo` | `0x442900` (lithtech.exe) | `ClientDE::GetVersionInfoExt`, at its second check | fixed |
| `CSoundMgr::SetSoundFilter` | `0x4b1980` (lithtech.exe) | `CSoundMgr::SetSoundFilterParam` | fixed |
| `ILTModel::GetNextNode` | (lithtech.exe, server.dll) `shared/src/modellt_impl.cpp` | `GetNextModelNode` | |
| `dsi_LoadServerObjects` | server.dll, `kernel/src/sys/win/dsys_interface.cpp` | `LoadObjectsInDirectory` | |
| `se_ChangeSpriteFile`, `se_ChangeModelFile` | server.dll, `server/src/server_extradata.cpp` | `se_InitSprite`, `se_InitModelObject` | |
| `CLTServer::GetClientPing`, `UnloadTexture`, `si_DoObjectRotation` | server.dll, `server/src/serverde_impl.cpp` | `ILTPhysics::GetPing`, `ThreadLoadTexture`, `SetObjectRotation` (and "`TreadLoadFile`") | |
| `sm_RestoreConsoleVars` | server.dll, `server/src/game_serialize.cpp` | `RestoreObjects` | |

And `sm_SetupError(LT_MISSINGCLASS, "%s", "BaseClass")` in
`server/src/classmgr.cpp` passes the format as the argument: the message
`ltmsg.dll` builds from it reads "Missing class: %s.".

### Checks reported at the wrong debug level

Not fixed: the level 15 ones may be deliberate (a render call made every
frame), the others print a real failure.

A check's message prints only when the debug level is at least the one it
names, and in the client interface that is almost always 1:
`cis_RenderCamera` (`0x495080`) and `cis_MakeCubicEnvMap` (`0x495170`)
report at 15, which nothing sets; `cis_ScaleSurfaceToSurface` (`0x4939f0`)
at 4; `ci_GetPolyGridInfo` (`0x40b750`), `ci_SetPolyGridEnvMap`
(`0x40b4d0`), `ci_GetPolyGridTextureInfo` (`0x40b5c0`) and
`dsi_SetRenderMode` (`0x428c50`) at 0, so they always print.

### `InitLevel`'s trace misspells a parameter
`CLTDirectMusicMgr::InitLevel` (lithtech.exe; the string is in the retail image) ·
`src/Engine/runtime/kernel/src/sys/win/ltdirectmusic_impl.cpp`

> **FIXED in the modern build** (`NOLF2SRC_MODERN`, MODERN.md M-E9).

NOLF1's typo, unchanged: `... sDefine2=%s sDeine3=%s`.

---

## NOLF1 bugs NOLF2 does not have

Looked for and not found, so nobody looks again:

* `CSoundMgr::GetFilterIndex`'s inverted comparison: no such function; the
  reverb getter's damping slip is in a block Monolith commented out.
* `ci_GetRenderModes`'s find handle: `dsi_GetRenderModes` searches no files.
* `CLTDirectMusicMgr::InitLevel`'s leaked path: retail frees it on the
  success path only (`0x43cfed` jumps past the `delete`), but our
  `InitLevel` is not byte-identical yet and frees it on both.
* The value-returning readers quoting the shutdown message: no `csbase`.
* The object-DLL temp name, the tree-path builder, `CBaseStream`,
  `CMemStream`, `ServerMessage`'s size checks, `LTMatrix::TransformPlane`,
  `wm_ResetGeometry`, the box-intersect planes, `w_IsPolyBlocking`,
  `ws_AddClippedContact`, `Model::LoadChildModels`, `sm_WriteObjectFiles`,
  `se_ModelHashCleanup`, the fragment-record allocator, and `CString::Concat`:
  rewritten or fixed in NOLF2's engine and libraries.
* Doors and switches with no move direction: `ActiveWorldModel::ReadProps`
  replaces a zero `MoveDir` with up.
* Model shadows switched off by cinematics: `CPlayerMgr` keeps a flag.
* The ammo HUD surface, the hit-sphere debug model, `GetMovementData`, the
  style table in `CCharacterFX`, the player setup's 32-byte buffer, the
  server browser's option table: rewritten or checked in NOLF2.
* The join password sent to anyone who asks: NOLF2 sends only whether there
  is one (but see the handshake above).
