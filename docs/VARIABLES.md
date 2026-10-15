# Console variables

This file lists the game's console variables: what each one does, its
default, and whether it is new in the modern build. Commands are listed in
[`CONSOLE.md`](CONSOLE.md); the modern build's changes are in
[`MODERN.md`](MODERN.md).

It is not every variable the engine knows. It leaves out internal tuning
values with no visible effect, and most renderer debug switches.

Retail NOLF2 never draws its console, so a variable is set from the command
line, from `autoexec.cfg`, or by the menus, which write the variables behind
their settings. The modern build has a drop-down console (backquote or
Shift+Esc; [`CONSOLE.md`](CONSOLE.md), [`MODERN.md`](MODERN.md) M-E5) where
`Name value` sets one and `Name` shows it.

## How variables work

- **Setting one.** Put `Name value` (or `"Name" "value"`, the form the game
  writes) on a line of `autoexec.cfg`. On the command line, use
  `+Name value`; the launcher starts the engine this way, with its command
  line in `launchcmds.txt` (`-cmdfile launchcmds.txt`).
- **Names are not case-sensitive.** `ScreenWidth` and `screenwidth` are the
  same variable, and so are the modern `ShowFramerate` and the engine's
  `ShowFrameRate`.
- **Toggling.** A value of `!` toggles a variable between 0 and 1.
- **What is saved.** The engine writes `autoexec.cfg` when the game quits,
  and only then: the menus do not write it, so a crash loses what changed
  since the game started. It saves only variables marked for saving:
  - those a menu has set (the game sets them as `+Name value`);
  - those that came from a config file (`autoexec.cfg`, `display.cfg`, or a
    file run with `Exec`);
  - those set as `++Name value` on the command line.

  A plain `+Name value` on the command line is not marked: it lasts until the
  game quits, unless the variable was already marked (it came from
  `autoexec.cfg`, for instance). `-Name value` sets a variable and removes
  the mark. Variables the engine, the renderer or the game create with their
  default value are not marked either, so they are not written until
  something sets them.
- **Config files.** The engine reads `autoexec.cfg` (or the file named by
  `-config <file>`), then `display.cfg` (or `-display <file>`), then the
  command line, each over the one before. The game writes `display.cfg`
  itself, at start-up and whenever it applies the display settings:
  `ScreenWidth`, `ScreenHeight`, `BitDepth`, `HardwareCursor`, `VSyncOnFlip`,
  `GammaR`, `GammaG`, `GammaB` and, in the modern build, `Windowed` and
  `WindowMode`. So a resolution given on the command line is kept for the
  next run. The launcher's Display dialog reads `display.cfg` (and, in the
  modern build, `autoexec.cfg` for the window mode). A server, the local one
  of a single-player game included, reads `s_autoexec.cfg` when it starts.
- **The profile.** NOLF2 keeps many settings in the player profile,
  `Profiles/<name>.txt`; the current profile's name is in the registry
  (`ProfileName`), and a new profile starts as a copy of
  `Profiles/Default.prf`. The profile holds the key bindings, the mouse and
  keyboard settings, the game options and the crosshair, the sound settings,
  the Performance screen's settings and the multiplayer player set-up. When
  the profile loads, after `autoexec.cfg`, `display.cfg` and the command line,
  it writes its values into their variables, so a value for one of these in
  `autoexec.cfg` or on the command line is overwritten: change them in the
  menus (or in the profile, while the game is not running). The game saves
  the profile when a menu changes it and when it quits. The tables say
  "profile" for these, with `Default.prf`'s value.
- **Restoring defaults.** The launcher's Options, "Restore Defaults", starts
  the game with `+RestoreDefaults 1`: the profile is reloaded from
  `Default.prf`, the hardware cursor, V Sync and gamma are reset, and the
  launcher asks for a detail level, which it passes as
  `+SetPerformanceLevel` (with a resolution, unless one was chosen).
- **Server variables.** The game server's variables live on the server's
  own console. Set them in `s_autoexec.cfg`, which is read but never
  written, or (the modern build, single player or the host) with
  `serv Name value` in the console.
- **Per-level values.** Each level sets `FarZ`, the fog variables
  (`FogEnable`, `FogNearZ`, `FogFarZ`, `SkyFogEnable` and the others) and the
  volumetric fog when it loads, so a value set for them only lasts until the
  next level.
- **Console output.** The variables that print something print to the
  console, which retail never draws (the modern build's does). `ErrorLog 1`
  (in `autoexec.cfg` or on the command line) writes everything printed to
  the console to `error.log`.

"Shipped" in a table is the value in the `autoexec.cfg` or `Default.prf`
the game ships with, where it differs from the code's default. "Modern" means
the variable exists, or does something, only in the modern build.

## Modern build

| Variable | Default | What it does |
|---|---|---|
| `MaxFPS` | 240 (retail: 0, and ignored in the final build) | The most frames a second; 0 is no limit; at most 1000. In multiplayer (hosting or joining) 60 at most, also when it is 0. Display screen: "Frame rate limit" (30, 60, 75, 100, 120, 144, 165, 200, 240, 300, none). |
| `ShowFramerate` | 0 | 1 shows the frame rate, averaged over 30 frames, at the top of the screen in play. No menu. |
| `Windowed` | 0 (unset) | 0 full screen, 1 a window (retail variable; the Display screen's and the launcher's "Window mode" now set it, and a change applies at once). Saved in `display.cfg` too. |
| `WindowMode` | 0 (unset) | With `Windowed` 1: 1 a framed window, 2 a borderless window over the whole primary monitor at the desktop's resolution. 0 (a config from before the setting) is a framed window unless the mode is as large as the desktop, which is borderless. Display: "Window mode" (Full screen, Window, Borderless window). Saved in `display.cfg` too. |
| `RunInBackground` | 0 | In a window: 1 lets the game play on when its window loses the focus, instead of pausing. Display: "Run in background". |
| `FovY`, `FovX` | 78, 90 | The camera's vertical and horizontal angles, in degrees (retail variables). Display: "Field of view" sets `FovY` (50 to 100) and `FovX` with retail's shape (90 by 78); the modern build widens the horizontal angle further for a screen wider than 4:3. |
| `AntiAliasFSOverSample` | 0 | Multisample antialiasing, samples per pixel (retail renderer variable, now in a window too); fewer if the card has not that many. Read when the renderer starts. Display: "Anti-aliasing" (off, 2x, 4x, 8x; a change restarts the renderer). |
| `Cinematics43` | 0 | On a wide screen, 1 covers the sides beyond the centred 4:3 area while the cutscene letterbox is up. Display: "4:3 cinematics". |
| `Anisotropic` | 0 | Anisotropic filtering, now as a degree: 0, 2, 4, 8 or 16 (held to the card's most). Performance screen: "Anisotropic filtering" (Off, 2x, 4x, 8x, 16x). Retail's "On" wrote 1, no better than bilinear. |
| `PadLookSpeed` | 1 | Controller: the right stick's turn rate, times 180 degrees a second across and 120 up and down. Controller screen: "Look speed" (0.25 to 3). |
| `PadInvertY` | 0 | Controller: 1 makes the right stick's up look down. Controller screen: "Invert look". |
| `PadLookCurve` | 2 | Controller: the right stick's response; its deflection past the dead zone is raised to this power (1 = linear). No menu. |
| `PadLookDeadZone` | 0.15 | Controller: the right stick's radial dead zone (0 to 0.9 of its travel). Controller screen: "Look dead zone" (0 to 0.5). |
| `PadMoveDeadZone` | 0.2 | Controller: the left stick's radial dead zone. Past three quarters of its travel the player runs. Controller screen: "Move dead zone" (0 to 0.5). |
| `PadHoldButtons` | 0 | Set by the game, not a setting: the controller buttons the game reads itself for the moment (a dialogue decision), which the bindings do not see. |
| `MouseScaleBase` | 0.0005 (modern), 0.00125 (retail) | The mouse's turn per count at sensitivity 0; each step of `MouseSensitivity` adds `MouseScaleIncrement` (0.001125). Lower in the modern build because each mouse count is now counted once. |

## Display and window

| Variable | Default | What it does |
|---|---|---|
| `ScreenWidth`, `ScreenHeight` | 640, 480 (shipped 800, 600) | The screen mode. Display: "Resolution"; the launcher's Display dialog passes it. Saved in `display.cfg`. |
| `BitDepth` | 32 | The screen's colour depth. Saved in `display.cfg`. |
| `CardDesc` | (none) | The Direct3D device to use; the launcher passes it as `++CardDesc`. |
| `HardwareCursor` | 0 (shipped 1) | 1 uses the hardware cursor in the menus. `DisableHardwareCursor 1` (the launcher's "Disable Hardware Cursor") forbids it. Display: "Hardware cursor". |
| `VSyncOnFlip` | 1 | 1 waits for the display's refresh. Display: "V Sync". |
| `GammaR`, `GammaG`, `GammaB` | 1, 1, 1 | Gamma. Display: "Gamma" sets all three. |
| `BackBufferCount` | 2 | Back buffers: 2 is triple buffering. Performance: "Triple buffering"; the launcher's "Disable Triplebuffering" greys it out. |
| `ForceClear` | 0 (shipped 1) | 1 clears the whole screen every frame. |
| `LetterBox` | 0 | 1 forces the cinematic letterbox bars on. |
| `ScreenFadeAtLevelStart` | 1 | 0 skips the fade-in when a level starts. |
| `DynamicLoadScreen` | 1 | 0 shows a still loading screen instead of the animated one (the launcher's "Disable Animated Load Screens"). |
| `LoadScreenWait` | 1 | 0 goes straight into play after loading, without stopping at the briefing (single player) or the waiting screen (multiplayer). |

## Performance and rendering

The Performance screen's settings are kept in the profile (its `[Settings]`
and `[Details]`) and written to these variables when the profile loads.

| Variable | Default | What it does |
|---|---|---|
| `PerformanceConfig` | (profile) | The Performance screen's preset: `.DefaultLow`, `.DefaultMid`, `.DefaultHigh` or `.CustomConfig`. The names count performance, not detail: `.DefaultLow` is the most detail. |
| `DetailLevel` | (profile) | Texture resolution, 0 low to 2 high; sets the texture groups' `GroupOffset1` to `GroupOffset3`. Performance: "Texture resolution". |
| `MipMapOffset`, `GroupOffset0` to `GroupOffset3` | 0 | Skip the most detailed mip levels of all textures, or of one group; higher is blurrier. |
| `DynamicLightWorld` | 0 | Dynamic lights on the world. Performance: "Dynamic lights". |
| `ShadowDetail` | (profile) | Model shadows: 0 off, 1 low to 3 high. Sets `ModelShadow_Proj_Enable` and the projected shadows' blending, texture size and count. Performance: "Shadows". |
| `BumpMapPolyGrids`, `FresnelPolyGrids` | 1, 1 | Bump mapping and the fresnel effect on water. Performance: "PolyGrid bumpmapping", "PolyGrid fresnel". |
| `Trilinear`, `Bilinear` | 0 (shipped 1), 1 | Texture filtering. Performance: "Trilinear filtering". |
| `EnvMapEnable` | 1 | Environment maps (chrome). Performance: "Environment map". |
| `DetailTextures` | 1 | Detail textures. Performance: "Detail textures". |
| `EnvironmentalDetail` | (profile) | 0 off to 3 high: grass (`ScatterEnable`) and snow (`SnowEnable`, `SnowDensityScale`). Performance: "Environmental". |
| `FXDetail` | (profile) | 0 low to 2 high: sets `ClientFXDetailLevel` and `DebrisFXLevel`. Performance: "Effects". |
| `Tracers`, `ShellCasings` | 1, 1 | Tracers and shell casings. Performance: "Tracers", "Shell casings". |
| `PreCacheAssets` | (profile) | 1 has the server precache a level's assets as it loads. Performance: "Precache Assets". |
| `PerformanceLevel` | 1 (shipped 3) | Detail of some effects (particle trails, water). |
| `32BitTextures`, `32BitLightMaps` | 0 (shipped 1), 1 | Keep textures and lightmaps at 32 bits instead of 16. |
| `MipMapBias` | 0 (shipped -1) | Mipmap selection bias; lower is sharper. |
| `Saturate` | 0 (shipped 1) | 1 doubles the brightness ramps ("saturated" lighting). |
| `LightMap`, `DynamicLight` | 1, 1 | Lightmaps; dynamic lights. |
| `MaxModelLights` | 4 | Dynamic lights per model. |
| `MaxModelShadows` | 1 | Model shadows on or off. |
| `ModelLODOffset` | 0 | Model level-of-detail bias. |
| `FarZ` | 10000 (shipped 100000) | The far clip distance. Each level sets its own. |
| `FogEnable` | 0 (shipped 1) | Distance fog. Each level sets it, with `FogNearZ`, `FogFarZ`, `FogR`, `FogG`, `FogB`. |
| `DrawSky` | 1 | 0 hides the sky. |
| `DrawWorld`, `DrawModels`, `DrawGuns`, `DrawSprites`, `DrawParticles`, `DrawPolyGrids`, `DrawLineSystems`, `DrawCanvases`, `DrawWorldModels`, `DrawVolumeEffects` | 1 | 0 hides each kind of object (`DrawGuns`: the weapon in your hands). |
| `Wireframe` | 0 | 1 draws everything as wireframe. |
| `LightmapsOnly`, `DrawFlat` | 0 | Debug views: lightmaps only; flat shading. |

## Sound and music

| Variable | Default | What it does |
|---|---|---|
| `SoundEnable`, `MusicEnable` | 1, 1 | Sound and music on or off. `DisableSound 1`, `DisableMusic 1` (the launcher's "Disable Sound", "Disable Music") turn them off for a run. |
| `SoundVolume` | profile: 75 | Effects volume, 0-100. Sound: "Sound effects volume". |
| `SpeechSoundMultiplier` | profile: 1 | Speech volume. Sound: "Speech volume". |
| `WeaponsSoundMultiplier`, `DefaultSoundMultiplier` | profile: 1, 0.75 | Weapon and other sounds' volume. No menu. |
| `MusicVolume` | profile: 1250 | Music volume, -2500 (off) to 5000. Sound: "Music volume". |
| `MusicActive` | 1 | Music playing; the game clears it when the music volume is at its lowest. |
| `Sound16Bit` | profile: 1 | Sound effects quality. Sound: "Sound effects quality". |
| `MusicQuality` | profile: 0 | Music quality. Sound: "Music quality". |
| `SoundFilters` | 0 (shipped 1) | Reverb and filters by area. `DisableSoundFilters 1` (the launcher's "Disable Sound Filters") turns them off. |

## Mouse and keyboard

| Variable | Default | What it does |
|---|---|---|
| `MouseSensitivity` | profile: 2 | Mouse sensitivity, 0-10. Mouse: "Mouse sensitivity". |
| `MouseInvertY` | profile: 0 | 1 inverts the mouse's up and down. Mouse: "Invert y axis". |
| `MouseLook` | profile: 1 | Mouse look. Mouse: "Always mouse look". |
| `InputRate` | profile: 12 | Retail smoothing of the mouse (and a joystick's axes), 0-40. Mouse: "Mouse smoothing" (retail). The modern build's mouse look does not smooth, and the slider is gone. |
| `AutoCenter` | profile: 0 | 1 centres the view when you stop looking (only without mouse look). Keyboard: "Auto-center". |
| `NormalTurnRate`, `FastTurnRate`, `LookUpRate` | profile: 1.5, 2.3, 2.5 | Keyboard turning and looking speeds. Keyboard: "Normal turn speed", "Fast turn speed", "Up/down look speed". |
| `VehicleTurnRateScale` | profile: 1 | Snowmobile steering speed. Mouse and Keyboard: "Vehicle turn speed". |
| `JoystickDisable` | 0 | 1 leaves DirectInput joysticks out. The modern build has its own XInput controller and no DirectInput joysticks, so it does nothing there. |

Always run is a profile setting (`AlwaysRun`, Game: "Always run") with no
variable of its own.

## Game and HUD

| Variable | Default | What it does |
|---|---|---|
| `Difficulty` | profile: 1 | 0 easy to 3 very hard. Game: "Difficulty". |
| `Subtitles` | profile: 0 | Subtitles. Game: "Subtitles". |
| `Gore` | profile: 1 | Blood. Game: "Blood" (always 0 in the low-violence version). |
| `HUDLayout` | profile: 0 | HUD style. Game: "Heads-up display style". |
| `HeadBob`, `WeaponSway` | profile: 1, 1 | Head bob and weapon sway, 0-1. Game: "Head bob", "Weapon sway". |
| `MessageDuration` | profile: 1 | How long messages stay, as a multiple. Game: "Message duration". |
| `AutoWeaponSwitch` | profile: 1 | Switch to a better weapon when you pick it up. Game: "Auto-switch weapons". |
| `VehicleContour` | profile: 1 | The snowmobile tilts with the ground. Game: "Snowmobile Contouring". |
| `CrosshairRed`, `CrosshairGreen`, `CrosshairBlue`, `CrosshairAlpha` | profile: 31, 255, 255, 127 | The crosshair's colour, 0-255. Crosshair screen. |
| `CrosshairStyle`, `CrosshairDynamic` | profile: 0, 1 | The crosshair's style; 1 scales it with the weapon's accuracy. Crosshair: "Style", "Dynamic scaling". |
| `DrawInterface` | 1 | 0 hides the whole HUD (for screenshots). |
| `MuzzleLight`, `EnableWeatherFX` | 1, 1 | The light of a muzzle flash; weather effects. |
| `EnableDamageFX` | 1 | 0 turns the damage screen effects off (poison, stun, sleep, burn). |
| `LeanAngle`, `LeanOutTime`, `LeanCenterTime` | 3, 0.5, 0.5 (shipped 8, 0.15, 0.2) | How far the player leans, in degrees, and how fast (seconds). |
| `PlayerGravity` | -2000 | The player's gravity. |
| `FallDamageMinHeight`, `FallDamageMaxHeight` | 300, 500 | Falls higher than the first hurt; the damage grows up to the second. |
| `NoMovies` | 0 | 1 skips the intro movies (as does `DisableMovies 1`, the launcher's "Disable Movies"). |
| `SkipTitle` | 0 | 1 goes straight to the main menu. |

## Multiplayer

| Variable | Default | What it does |
|---|---|---|
| `UpdateRate` | 10; 60 from the first run | Server updates a second to ask for. The game sets 60 once (and `UpdateRateInitted 1`). |
| `BandwidthTargetClient` | 256000 | Your send bandwidth, bits a second. The profile's connection setting (player set-up) writes it; on a LAN the most. |
| `CSendRate` | 15 | Your position updates to the server a second. |
| `IgnoreTaunts` | 0 | 1 neither plays nor sends taunts. |

The player's name, model and the host's game settings are in the profile, not
in variables.

## Start-up

These are read once, from the command line (as `+Name value`).

| Variable | What it does |
|---|---|
| `runworld` | `+runworld <world>` starts a single-player game in that level. |
| `join`, `password`, `gametype` | `+join <address>` joins a server, with that password, as that game type (`Cooperative`, `Deathmatch`, `TeamDeathmatch` or `DoomsDay`; Deathmatch if none). |
| `host` | `+host 1` hosts a game with the current profile's host settings. |
| `multiplayer` | The launcher passes 0 or 1. |

## Debugging

| Variable | Default | What it does |
|---|---|---|
| `ErrorLog`, `ErrorLogFile`, `AlwaysFlushLog` | 0, `error.log`, 0 | 1 writes everything printed to the console to the file (set it before start-up: `autoexec.cfg` or the command line); flush after every line. |
| `TraceConsole` | 0 | 1 also sends console text to the debugger (`OutputDebugString`). |
| `DebugLevel` | 0 | How much debugging text the engine and game print. |
| `ShowConnStats`, `ShowFileAccess`, `InputDebug` | 0 | Print network statistics, every file opened, input device activity. |
| `HighPriority` | 0 | 1 runs the game at high process priority. |
| `alwaysfocused` | 0 | 1 keeps the local server's world running while the game is not the active window (single player). |
| `LatencySim`, `DropRate` | 0 | Simulate network lag and packet loss. |

## Server (`s_autoexec.cfg`)

| Variable | Default | What it does |
|---|---|---|
| `DamageScale`, `HealScale` | 1, 1 | Multiply all damage and healing. |
| `TimeScale` | 1 | Game speed. |
| `BodyLifetime` | 30 | Seconds a body stays. |
| `CanShowDims` + `ShowDims` | 0 | Both 1 draw every object's bounding box. |
| `ShowTriggers` | 0 | Print trigger messages (`FilterTriggerMsgs` narrows them). |
| `ShowGameTime` | 0 | Print the game time. |

## Variables that do nothing

The shipped `autoexec.cfg` still names variables of LithTech's earlier games
that nothing in NOLF2 reads, among them `RenderDll` (the renderer is built
into the engine), `TripleBuffer` (it is `BackBufferCount`), `RunLock` (always
run is the profile's), `LODScale`, `LodOffset`, `LightSaturate`, `FastLight`,
`DrawShadows`, `DrawPortals`, `EnvMapWorld`, `ModelShadowProj`,
`CrosshairColorR`/`G`/`B`, `FadeBodies`, `BulletHoles`, `ObjectiveMessages`,
`PickupMessageDuration`, `ImpactFXLevel`, `ProfileName` (the current
profile is the registry's) and `SendBandwidth`. The engine also creates
`MasterPaletteMode`, `ModelTransitionMS` and `Software`, which nothing reads,
and `ConsoleAlpha` and `NumConsoleLines`, which only matter to a console
drawn the development build's way (retail draws none; the modern build's
uses neither). `ConsoleEnable` 0 keeps the modern build's console shut;
`ConsoleFont`, `ConsoleFontSize` and `ConsoleLeft`/`Top`/`Right`/`Bottom`
set its face, letter size and rectangle (`CONSOLE.md`). The engine's own `ShowFrameRate` printout
is not in the final build; the modern `ShowFramerate` (the same variable)
draws its counter itself.
