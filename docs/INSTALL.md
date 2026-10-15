# Installing and playing

This guide is for players. It explains how to get from a release download to
a running game. To build the game from source instead, see
[`BUILDING.md`](BUILDING.md).

## What to download

Each release has these archives:

| Archive | What it is |
|---|---|
| `nolf2-modern-release-public.tar.gz` | **The one you want.** The game built from source with the modern build's fixes and features ([`CHANGELOG.md`](../CHANGELOG.md)). |
| `nolf2-legacy-release-public.tar.gz` | The game built as it shipped (version 1.3), bugs included. Kept for archive purposes. |

No game files are included. Each archive has two installer scripts that copy
the game's data from your own disc images and the 1.3 update, and check every
file they write.

## What you need

- **The two discs of _No One Lives Forever 2: A Spy in H.A.R.M.'s Way_**,
  the European or the USA release, as disc images. The installer knows
  redump's dumps of them:
  - No One Lives Forever 2 - A Spy in H.A.R.M.'s Way (Europe) (Disc 1),
    (Disc 2)
  - No One Lives Forever 2 - A Spy in H.A.R.M.'s Way (USA) (Disc 1),
    (Disc 2), or redump's other dump of disc 2, "(Disc 2) (Alt)"

  An image can be a plain `.iso` (your own rip), redump's `.bin` (or its
  `.cue`), or redump's `.zip` download. A `.bin` or `.zip` is first
  converted to a temporary `.iso`, which needs about 0.6 GB of free space per
  disc; it is removed at the end. Other editions and dumps are not
  supported: the installer checks each image's checksum.
- **Sierra's English 1.3 update**, `nolf2-update_1x3.exe`. It is read, not
  run.
- **On Linux:** Wine with 32-bit support, or Proton (Steam), and `python3`.
- **On Windows:** nothing else. The installer uses the PowerShell that
  Windows 10 and 11 have, and the game is a 32-bit Windows program.

## Linux

1. Unpack the archive:

   ```sh
   tar xzf nolf2-modern-release-public.tar.gz
   cd nolf2-modern-release
   ```

2. Install the game data from your disc images and the update, in any
   order:

   ```sh
   ./linux-install.sh /path/to/disc1.zip /path/to/disc2.zip /path/to/nolf2-update_1x3.exe
   ```

   With no arguments it looks for them in the game directory and the
   directory above it. You can run it again safely: files already in place
   are checked and kept.

3. Play:

   ```sh
   ./linux-run.sh                           # as last left; at first a 640x480 window
   ./linux-run.sh --res 1920x1080 --fullscreen
   ./linux-run.sh --borderless              # a borderless window at the desktop's resolution
   ```

   `./linux-run.sh --help` lists the options. The game uses its own Wine
   prefix, `~/.wine-nolf2`, which is created on the first run, so your own
   prefix is left alone. `./linux-run-launcher.sh` starts the game through
   the original launcher (`NOLF2.exe`) instead.

Sound needs Wine's audio to work on your machine (`winecfg`, Audio tab). The
music is DirectMusic, which Wine only partly implements; `linux-run.sh
--help` shows how to install Microsoft's DirectMusic into the game's prefix.

## Steam Deck and Proton

1. In Desktop Mode, unpack the archive and run `linux-install.sh` as above.
2. In Steam, use Games > Add a Non-Steam Game and pick the game directory's
   `NOLF2.exe`.
3. In the shortcut's Properties > Compatibility, force a Proton version.

The controller works as an Xbox-style pad (see [Controller](#controller)).
These steps are untested so far.

## Windows

1. Unpack the archive (7-Zip and Windows 11's Explorer both open
   `.tar.gz`).
2. Drop both disc images and `nolf2-update_1x3.exe` onto
   `windows-install.bat`, or put them in the game folder and double-click
   it.
3. Start `NOLF2.exe`, the launcher, and click Play.

The modern build's launcher plays the game in its own folder, with no
registry and no administrator needed.

The legacy build's launcher is the original one, which looks for the game
in the registry. In the legacy build `windows-install.bat` therefore also
registers the game the way the original installer did: for all users when
it runs as an administrator (right-click > Run as administrator), otherwise
for your Windows user only, which is enough for the launcher. If you move
the game folder, run `windows-install.bat` again (it checks the files and
keeps them). The legacy build also has `windows-run.bat`, which starts the
game directly, without the launcher or the registry. It hands its arguments
to the game, e.g. `windows-run.bat +ScreenWidth 2560 +ScreenHeight 1440`.

Windows support has had less testing than Linux. The programs are not
signed, so SmartScreen may warn before the first start. If something goes
wrong, please report it.

### Troubleshooting on Windows

- **The launcher shows "Install" instead of "Play"**, and clicking it says
  it is "Unable to launch the setup program": the launcher did not find the
  game in the registry. Releases before this fix did not register it. Use a
  newer release: the modern build's launcher finds the game in its own
  folder and needs no registry; for the legacy build, run
  `windows-install.bat` again (with your images, as before; nothing is
  copied twice), or play with `windows-run.bat`.
- **"Bad Image ... csh*.tmp is either not designed to run on Windows or it
  contains an error" (0xc000012f), then "Missing shell DLL cshell.dll"**:
  `Lithtech.exe` was started without `-rez custom` last. The game's own
  DLLs, built from source, are in the `custom` folder; the copies inside
  `Update_v1x3.rez` are blanked out, and an archive later on the command
  line wins. To start the engine by hand, use the game's command file:

  ```bat
  Lithtech.exe -cmdfile nolf2cmds.txt
  ```

  or list the archives with `custom` last:

  ```bat
  Lithtech.exe -rez GAME.REZ -rez GAME2.REZ -rez GAMEDLL.REZ -rez SOUND.REZ -rez Update_v1x3.rez -rez custom +ScreenWidth 2560 +ScreenHeight 1440
  ```

  (`Engine.REZ` is opened by the engine itself.) Settings can follow the
  command file, e.g. `Lithtech.exe -cmdfile nolf2cmds.txt +ScreenWidth 2560
  +ScreenHeight 1440`. The launcher, `NOLF2.exe`, does this for you.

## First start

- **Screen.** The game starts in a 640x480 window. Choose the resolution and
  window mode in Options > Display. Window mode can be Full screen, Window or
  Borderless window. Wide screens are supported: the view widens, and the
  menus and HUD keep their shape.
- **Frame rate.** The game is limited to 240 frames a second by default.
  Options > Display > "Frame rate limit" offers 30 to 300 or none.
  Multiplayer always runs at 60 at most.
- **Field of view, antialiasing.** Also in Options > Display.
- **Crouch.** Retail's "Crouch toggle" control (Options > Controls >
  Configure controls) makes a press crouch and the next stand.

## Controller

An Xbox-style (XInput) controller works in the menus and in the game. That
is also what Steam Input makes of the Steam Deck's controls and of most other
pads.

- In the game, the left stick moves and the right stick looks; the triggers
  fire and zoom.
- In the menus, use the d-pad or a stick to move, A to choose and B to go
  back.
- Start opens the menu; A skips a cutscene.
- Options > Controls > Controller sets the look speed, inverted look and dead
  zones. Configure controls binds the buttons like keys.

So far the controller has been tested with a simulated pad only.

## Console and cheats

The game has no console you can open (the modern build's is still to come).
Variables and the engine's commands can be given on the command line
(`./linux-run.sh +ShowFramerate 1`) or in `autoexec.cfg`. Cheat codes are
typed in the chat line (`T`) during play, e.g. `god`.

- [`CONSOLE.md`](CONSOLE.md) lists the commands and cheat codes.
- [`VARIABLES.md`](VARIABLES.md) lists the settings.

## Where things are

| File | What |
|---|---|
| `autoexec.cfg` | Your settings and key bindings, rewritten when the game exits. `autoexec.cfg.retail` is the shipped one: copy it over yours to start from the defaults. |
| `display.cfg` | The display settings the launcher reads. |
| `Profiles/` | Your player profiles: key bindings and most options. |
| `Save/` | Saved games. |

## Multiplayer

Sierra's servers for the Internet server list are gone, so the list is
empty. LAN games and joining a server by its address work. The modern build
does not play with retail 1.3 players and servers: the game code differs,
which the handshake checks.
