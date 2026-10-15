# Console commands

This file lists every console command in NOLF2: the engine's client and
server commands, the game's commands, the multiplayer server's SCMD
commands, and the cheat codes. Variables (`Name value`) are listed in
[`VARIABLES.md`](VARIABLES.md). The modern build's other changes are
described in [`MODERN.md`](MODERN.md).

Commands and variable names are not case-sensitive. Arguments are separated
by spaces; quote an argument that contains spaces. Cheat codes are the
exception: type them in lower case.

## Opening the console

| Build | How |
|---|---|
| Retail | There is no console to open. The engine keeps one, but never draws it and never gives it keys. |
| Modern | The same. A drop-down console is planned ([`MODERN.md`](MODERN.md), M-E5, still to do). |

So commands can only come from these places, in both builds:

- **The command line.** `+Name value` on `Lithtech.exe`'s command line (or
  in the file given with `-cmdfile`). Each `+Name` takes exactly one
  argument, the word after it. You can add these in the launcher
  (`NOLF2.exe`, Options, the command-line box) or give them to
  `linux-run.sh`, which passes any argument it does not know to the engine
  unchanged, e.g. `./linux-run.sh +Exec mycmds.cfg`.
- **`autoexec.cfg`**, then **`display.cfg`** (other names with `-config
  <file>` and `-display <file>`). One line per command or variable.
- **A file run with `Exec`**, e.g. `+Exec mycmds.cfg` on the command line.

All three run once, as the engine starts: first every variable, then every
command. That is before the game DLL is loaded, so only the engine's own
client commands (section 1) exist at that point; the game's commands
(section 3) and `Cheat` are not registered yet and are ignored. The engine
rewrites `autoexec.cfg` when the game exits, keeping only variables, key
bindings and `ModelAdd`, so commands written into it are lost. Keep them in
a file of your own and run it with `+Exec`.

**During play**, the only way to run a console line is the `ActivateOverride`
variable: when its value does not start with a space, pressing Activate at
something in range (or Space during a cut-scene) runs the value as a console
line instead of activating the object, e.g.
`+ActivateOverride "ChaseToggle"`. Set it back to `" "` (one space) to
activate things again.

**Output.** Commands print to the engine console, which is never shown.
`+ErrorLog 1` copies everything printed there to `error.log` (another name
with the `ErrorLogFile` variable).

**Cheat codes** are typed in the chat line: `T` (SendMessage), or `Y`
(TeamMessage, team games only), in the shipped controls. The chat line
opens only while you are playing.

nolfsrc's modern-console commands (`GetPos`, `SetPos`) and its Shift+Esc key
wait for M-E5 here.

## 1. Engine client commands

| Command | Arguments | What it does |
|---|---|---|
| `quit` | | Quit the game. |
| `World` | `<name>` | Start a game on a world. Give the path from the game's root, e.g. `worlds\...`; `.dat` is added if missing. (The game's own way to start in a level is the `RunWorld` variable: `linux-run.sh --world`.) |
| `serv` | `<command ...>` | Run the rest of the line on the server's console. The server takes it only from its local client (single player, or the host). |
| `Exec` | `<file>` | Run a file of console commands and variables. |
| `Set` | | Print every client console variable and its value. |
| `ListCommands` | | Print the engine's built-in commands. |
| `Bind` | `<device> <trigger> <action> [...]` | Bind a key or button to one or more actions. Clears the trigger's old bindings first. |
| `RangeBind` | `<device> <trigger> <low> <high> <action> [...]` | Bind ranges of an axis to actions (`<low> <high> <action>` repeated). |
| `Scale` | `<device> <trigger> <scale>` | Set an axis' scale. |
| `RangeScale` | `<device> <trigger> <scale> <min> <max> <precenter>` | Set an axis' scale and range. (Retail bug: it checks for 5 arguments but reads 6.) |
| `AddAction` | `<name> <number>` | Create an input action. |
| `EnableDevice` | `<device>` | Turn on an input device, e.g. `"##gamepad"`. |
| `ListInputDevices` | | List the input devices. |
| `SSFile` | `<name>` | Base name for screenshots. |
| `UpdateServer` | `0\|1` | `0` stops updating the local server each frame, which freezes the game world. |
| `RenderCommand`, `RCom` | `<args ...>` | Pass a command to the renderer DLL. |
| `RestartRender` | `[dll]` | Restart the renderer, optionally with another `.ren` file. |
| `ResizeScreen` | `<width> <height>` | Change the resolution. Goes back to the old one if the new one fails. |
| `RestartConsole` | | Reset the console. |
| `MoveConsole` | `[Top\|Bottom\|Middle\|Full\|l t r b]` | Print or set the console's rectangle (the `ConsoleLeft`/`Top`/`Right`/`Bottom` variables). |
| `RebindTextures` | | Free the loaded textures, so they are loaded again. |
| `LogTextureInfo` | `<file.csv>` | Write the loaded textures to a CSV file: name, loaded, memory, size, mipmaps. |
| `ModelAdd` | `<r> <g> <b>` | Light added to every model, each 0-250. Saved in `autoexec.cfg`. |
| `ShowTicks` | `ALL\|NONE\|SUMMARY\|RENDER\|GAME\|ENGINE\|GRAPH ...` | Turn timing counters on or off. Alone, it lists the sections. |
| `ShowVersionInfo` | | Print the engine's version, build number and date. |
| `ConsoleHistory` | | Print the command history. |
| `ClearHistory` | | Clear the command history. |
| `WriteHistory` | `<file>` | Save the command history to a file. |
| `ReadHistory` | `<file>` | Load the command history from a file. |
| `HeapCompact` | | Compact the memory heap. |
| `Mem` | | Prints that the memory commands are not available in this build. |
| `BlastServer` | | Does nothing (debug builds only). |

## 2. Engine server commands

These run on the server. Ways to reach them: the command box of the
dedicated server (`NOLF2Srv.exe`), which runs each line on the server's
console; or `serv <command>` from the local client. `s_autoexec.cfg` is read
by the server for variables only.

| Command | Arguments | What it does |
|---|---|---|
| `world` | `<name> [0]` | Start a world on the server. `0` loads it without its objects. |
| `SpawnObject` | `<class> ["props"]` | Create an object 200 units from the first player (along the world's Z axis), e.g. `SpawnObject PlayerVehicle (VehicleType Snowmobile)`, which is what `rosebud` runs. |
| `objectinfo` | | Count the objects by class: total, active, and memory. |
| `ShowGameVars` | | Print every server console variable. |
| `ShowUsedFiles` | | List every file the server has opened. |
| `DisableWMPhysics` | | Give every object box physics. |
| `Mem` | | Prints that the memory commands are not available in this build. |
| `ExhaustMemory` | | Does nothing (debug builds only). |

## 3. Game commands

The client game registers these when it loads. Until M-E5 they can only be
run through `ActivateOverride` (see above). Commands marked *server* are sent
to the game server.

| Command | Arguments | What it does |
|---|---|---|
| `Cheat` | `<code> [args]` | Run a cheat code (section 5). |
| `ChaseToggle` | | Switch between first and third person, when alive and not zoomed. Works in single player too, unlike `budonkadonk`. |
| `FragSelf` | | Kill yourself. *server* |
| `ExitLevel` | | Finish the current level, as `maphole`: single player only. |
| `Teleport` | `<x> <y> <z>` | Does nothing: the final build leaves out the player teleport. |
| `Cmd` | `<command> <arg> [...]` | Send a command to the server's command manager, as a level's trigger would. At least one argument is needed after the command name. *server* |
| `Trigger` | `<object> <message>` | Send a one-word message to the named objects. *server* |
| `List` | `<class>` | Print the objects of a class (case-sensitive) and their positions on the server's console. *server* |
| `Stimulus` | `<type> [multiplier]` | Create an AI stimulus at the player's position. *server* |
| `RenderStimulus` | `[0\|1]` | Show AI stimuli as spheres (default `1`). *server* |
| `Alpha` | `<object> <alpha>` | Set a named object's alpha. *server* |
| `AddGoal` | `<AI> <goal> [name=value ...]` | Give a named AI a goal. *server* |
| `RemoveGoal` | `<AI> <goal>` | Remove a goal from a named AI. *server* |
| `ClientFX` | `<fx> <object>` or `<fx> <x> <y> <z>` | Does nothing: the server has no handler for its message. |
| `Music` | `I\|PS\|PM\|V\|SS\|SM\|S\|P ...` | Control the DirectMusic score: intensity, play a secondary segment or motif, volume, stop a segment, motif or the music, play. Needs at least two words; fewer prints the help. |
| `InitSound` | | Restart the sound. |
| `ReloadWeapons` | | Reload the weapon attributes. |
| `ReloadSurfaces` | | Reload the surface attributes. |
| `ReloadFX` | | Reload the FX attributes, then the weapons and surfaces. |
| `Health`, `MaxHealth`, `Armor`, `MaxArmor` | `<number>` | Set the number the HUD shows, not the real value. |
| `Air` | `<percent>` | Set the air meter the HUD shows. |
| `TestSubtitle` | `<string id>` | Show a subtitle from the string table. |
| `SimulateChat` | | Add 25 numbered test lines to the chat messages. |
| `EditFX` | `<scalefx>` | In a menu, move and scale a menu ScaleFX: arrows move, A/D/W/S scale, PgUp/PgDn change the step, Enter ends and prints the position and scale. |

**Modern:** in a multiplayer game the server ignores `Cmd`, `Trigger`,
`List`, `Stimulus`, `RenderStimulus`, `Alpha`, `AddGoal` and `RemoveGoal`
(and pause and teleport) from any client but the host's own; retail obeyed
them from anyone (M-G7). `AddGoal` stops at the first `name=value` pair that
does not fit in its 128-character message; retail wrote past it (M-G6).

## 4. SCMD: multiplayer server administration

In a multiplayer game, a line starting with `scmd` in the chat line, or in the
dedicated server's command box, is an administration command. The host must
turn on "Allow SCMD" and set a password; one administrator at a time logs in
with it. `scmd` alone lists the commands.

| Command | What it does |
|---|---|
| `scmd help` | List the SCMD commands. |
| `scmd login <password>` | Log in as the administrator. |
| `scmd logout` | Log out. |
| `scmd listclients` | List the players: id, name, ping, IP. |
| `scmd bootname <name>` | Kick a player by name. |
| `scmd bootid <id>` | Kick a player by id. |
| `scmd banclient <id>` | Ban a player's IP by id. |
| `scmd addban <IP>` | Ban an IP, e.g. `123.45.*`. |
| `scmd removeban <banid>` | Remove a ban. |
| `scmd listbans` | List the banned IPs. |
| `scmd listmissions` | List the missions of the campaign. |
| `scmd setmission <index>` | Go to a mission of the campaign. |
| `scmd nextmission` | Go to the next mission. |
| `scmd nextround` | Go to the next round of this level. |
| `scmd listgameoptions` | List the game options. |
| `scmd setgameoption <id> <value>` | Set a game option. |

## 5. Cheat codes

Type a cheat code in the chat line (`T`), or use `Cheat <code>`. The codes
are lower case, with no `mp` prefix (the development build's names had one:
`mpgod`, `mppos`, ...). The retail and modern builds have the same cheats.

In multiplayer only `budonkadonk`, `nextmission` and `boot` do anything.
Any other code typed in the chat line in multiplayer is sent to everyone as
an ordinary chat message.

| Code | Effect | Single player | Multiplayer |
|---|---|---|---|
| `god` | God mode on/off | yes | no |
| `health` | Full health | yes | no |
| `armor` | Full armor | yes | no |
| `ammo` | Full ammunition | yes | no |
| `guns` | Every weapon, with ammunition | yes | no |
| `kfa` | Every weapon and ammunition, full health and armor | yes | no |
| `tears` | Ammunition never runs out, on/off; turning it on also gives every weapon | yes | no |
| `mods` | Every modification for the weapons you carry | yes | no |
| `gear` | Every gear item | yes | no |
| `gimmegun <weapon>` | One weapon, by name or number | yes | no |
| `gimmeammo <ammo>` | One ammunition type, by name or number | yes | no |
| `gimmemod <gear>` | One **gear item**, by name or number (see below) | yes | no |
| `skillz` | Skill points: what the missions before this one award | yes | no |
| `poltergeist` | AI cannot see you (they can still hear you), on/off | yes | no |
| `pos` | Show your position on screen, on/off | yes | no |
| `rosebud` | Spawn a snowmobile | yes | no |
| `baddaboom` | Bodies fly far from explosions, on/off | yes | no |
| `maphole` | Finish the current level | yes | no |
| `nextmission` | Go to the next mission | yes | host only |
| `boot <name>` | Kick a player | no | host only |
| `budonkadonk` | First/third person view | no | yes |
| `endgame` | Mark the game as finished, on/off: the single-player menu then lists the chapters | yes | no |
| `build` | Show the build's version | yes | no |
| `secretsquirrel` | Show the build's GUID | yes | no |
| `obtuse` | Sets `ConsoleEnable`; nothing to see, since the console is never drawn | yes | no |

A retail mistake in the obfuscated table: the code meant for `gimmemod` is
garbage, and the one meant for `gimmegear` is the string `gimmemod`. So
`gimmemod <gear>` gives a gear item, `gimmegear` is not a code, and no code
gives a single modification.

The development cheats are still recognized, but the final build does
nothing with them: `mpclip`, `mpteleport`, `mpwpos`, `mpwmpos`,
`mpbreachoffset`, `mplightscale`, `mplightadd`, `mpfov`, `mpboyisuck`,
`mptriggers`, `mpcamera`, `mpcampos`.

Cheats can also be applied automatically: list them in
`Attributes\ClientButes.txt` under `[Cheats]`, as `Cheat0 = "god"`,
`Cheat1 = ...`. They run each time you enter a level.
