# Installing and playing

This guide is for players. It explains how to get from a release download to
a running game. To build the game from source instead, see
[`BUILDING.md`](BUILDING.md).

## What to download

Each release has these archives, named for its version (`v0.1.0-alpha`, for
example):

| Archive | What it is |
|---|---|
| `nolf2src-<version>.tar.gz` | **The one you want.** The game built from source with the modern build's fixes and features ([`CHANGELOG.md`](../CHANGELOG.md)). |
| `nolf2src-debug-<version>.tar.gz` | The same with debug information. If the game crashes, it writes a backtrace to `nolf2src.log`. |

To try changes before the next release, there is the
[nightly](https://github.com/nolffan/nolf2src/releases/tag/nightly): the
latest `master`, rebuilt each time a change is merged and its builds pass.
Its archives are named for the commit they were built from,
`nolf2src-nightly-<commit>.tar.gz` and
`nolf2src-debug-nightly-<commit>.tar.gz` (the first seven digits of its
hash), and each unpacks to a directory of that name. It has had no testing
beyond the builds, so expect the occasional new bug; say in a bug report
that you are on a nightly, and which commit. It installs like any release.

The legacy build, the game built as it shipped (version 1.3), bugs
included, is kept for archive purposes and is not attached to releases. To
get it, build it ([`BUILDING.md`](BUILDING.md)); each build on GitHub
Actions also keeps it as an artifact for a while.

No game files are included. Each archive has two installer scripts that copy
the game's data from your own disc images and the 1.3 update, and check every
file they write.

**Each release is the whole game, not a patch.** Unpack it into a new, empty
directory, never over an earlier release or another installation of the
game. The installer checks this first and stops if the directory holds
anything the release does not: it lists every file of the release, and every
file the installer writes, in `SHA256SUMS`. To keep your saved games and
profiles, copy the old directory's `Save` and `Profiles` folders into the
new one.

Once the game is installed, `sha256sum -c SHA256SUMS` in its directory checks
every file of it (all but your settings, `autoexec.cfg` and
`Profiles/Default.prf`, which the game rewrites).

## What you need

- **The two discs of _No One Lives Forever 2: A Spy in H.A.R.M.'s Way_**,
  the European or the USA release, as disc images. These are the images the
  installer expects:
  - Europe: <http://redump.org/disc/35959/> (Disc 1),
    <http://redump.org/disc/35960/> (Disc 2)
  - USA: <http://redump.org/disc/12883/> (Disc 1), and for Disc 2 either
    of redump's two dumps of it: <http://redump.org/disc/12882/> ("(Disc 2)
    (Alt)", the one redump marks verified) or
    <http://redump.org/disc/33578/> ("(Disc 2)")

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

1. Unpack the archive into a new, empty directory:

   ```sh
   tar xzf nolf2src-v0.1.0-alpha.tar.gz    # the version you downloaded
   cd nolf2src-v0.1.0-alpha
   ```

   Each archive unpacks to a directory of its own name
   (`nolf2src-debug-v0.1.0-alpha` for the debug one).

2. Install the game data from your disc images and the update, in any
   order:

   ```sh
   ./linux-install.sh /path/to/disc1.zip /path/to/disc2.zip /path/to/nolf2-update_1x3.exe
   ```

   With no arguments it looks for them in the game directory and the
   directory above it. You can run it again safely: files already in place
   are checked and kept, and your saves, profiles, settings, logs and
   screenshots are left alone.

3. Play:

   ```sh
   ./linux-run.sh
   ```

   This opens the game's launcher, `NOLF2.exe`: click Play. The first time,
   it asks for a detail setting first. The launcher's Display button sets
   the resolution and the window mode.

   The game uses its own Wine prefix, `~/.wine-nolf2`, which is created on
   the first run, so your own prefix is left alone. Arguments go to the
   game: `./linux-run.sh ++windowed 1` starts it in a window whatever
   Options > Display says, and `./linux-run.sh -gogame` skips the
   launcher's window. `./linux-run.sh --help` says more.

Sound needs Wine's audio to work on your machine (`winecfg`, Audio tab). The
music is DirectMusic, which Wine only partly implements; `linux-run.sh
--help` shows how to install Microsoft's DirectMusic into the game's prefix.

## Steam Deck and Proton

1. In Desktop Mode, unpack the archive and run `linux-install.sh` as above.
2. In Steam, use Games > Add a Non-Steam Game and pick the game directory's
   `NOLF2.exe`.
3. In the shortcut's Properties > Compatibility, force a Proton version.

The controller works as an Xbox-style pad (see [Controller](#controller)).
On the Steam Deck the modern build starts full screen at the Deck's own
1280x800 (Steam tells the game it runs on a Deck); Options > Display
changes it. These steps are untested so far.

## Windows

1. Unpack the archive into a new, empty folder (7-Zip and Windows 11's
   Explorer both open `.tar.gz`).
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
  line wins. To start the engine by hand in the legacy build, use the
  game's command file:

  ```bat
  Lithtech.exe -cmdfile nolf2cmds.txt
  ```

  or (either build) list the archives with `custom` last:

  ```bat
  Lithtech.exe -rez GAME.REZ -rez GAME2.REZ -rez GAMEDLL.REZ -rez SOUND.REZ -rez Update_v1x3.rez -rez custom +ScreenWidth 2560 +ScreenHeight 1440
  ```

  (`Engine.REZ` is opened by the engine itself.) Settings can follow the
  command file, e.g. `Lithtech.exe -cmdfile nolf2cmds.txt +ScreenWidth 2560
  +ScreenHeight 1440`. The launcher, `NOLF2.exe`, does this for you (it
  writes its command line to `launchcmds.txt`).

## First start

- **Screen.** The modern build starts the first time in a window, the
  largest that fits your desktop (16:9 sizes on a 16:9 desktop, e.g.
  1600x900 on a 1920x1080 one); on a Steam Deck, full screen at 1280x800.
  Choose the resolution and window mode in Options > Display (or the
  launcher's Display button). Window mode can be Full screen, Window or
  Borderless window, and the game starts as you last left it. Wide screens
  are supported: the view widens, and the menus and HUD keep their shape.
  The legacy build starts the first time at the resolution of the detail
  setting the launcher asks for (640x480 to 1024x768); full screen on
  Windows, a window with `linux-run.sh`.
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
| `launchcmds.txt` | The command line the launcher last started the game with. |
| `nolf2srv.log`, `BanList.txt` | The dedicated server's log (below), and the players banned from a server, written when one stops. |
| `SHA256SUMS` | The checksum of every file of the release (`sha256sum -c SHA256SUMS`). |

## Multiplayer

Sierra's servers for the Internet server list are gone, so the list is
empty. LAN games and joining a server by its address work. The modern build
does not play with retail 1.3 players and servers: the game code differs,
which the handshake checks.

## A dedicated server

The game directory also has the game's stand-alone server, `NOLF2Srv.exe`:
a server with no player of its own, which keeps hosting a game for others
to join over the LAN or by its address.

Its settings are a player profile's: the game type, missions, number of
players, port, password and options that the game's Multiplayer > Host
screens save in `Profiles/<name>.txt` (and the mission lists in the
`Profiles/<name>/` folder). Set them up there first.

- **From the game:** Multiplayer > Host, turn on "Dedicated server", and
  start: the game closes and the server starts with your profile.
- **Windows:** start `NOLF2Srv.exe`. With one profile it uses it; with
  several it asks which. `NOLF2Srv.exe -profile <name>` names it.
- **Linux:**

  ```sh
  ./linux-server.sh                      # the only profile, or it asks which
  ./linux-server.sh --profile Player -name "My server" -port 27888
  ```

  Without a display (a server machine, a container) it runs under
  `xvfb-run`, a virtual display, which then needs to be installed (`xvfb`),
  and the profile must be named when there are several.
  `./linux-server.sh --help` lists the options.

On the command line `-profile <name>` picks the profile, and `-name
<session name>` and `-port <port>` override its own. To set up a server on a
machine where the game is never played, copy a profile (`Profiles/<name>.txt`
and its folder) from one where it is.

The server's console is written to `nolf2srv.log` in the game directory,
emptied at each start. The modern build always writes it, with the time of
each line, and adds where it is hosted (address, UDP port, players, LAN
only or not) and any error that stops it; `+errorlog 0` turns it off. The
legacy build writes it only with `+errorlog 1` (`linux-server.sh` passes
that).

The server answers on UDP port 27888 (or the profile's port, or `-port`):
let it through the firewall for players on other machines. It runs until
Stop Server is clicked, or the process is ended (Ctrl+C for
`linux-server.sh`). The Internet server list is gone (above), so players
outside the LAN join it by its address.
