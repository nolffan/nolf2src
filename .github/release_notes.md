## Download

| File | What it is |
|---|---|
| `nolf2src-{{ARCHIVE}}.tar.gz` | **This is what you want**; the retail game (1.3) with bug fixes and new features. |
| `nolf2src-debug-{{ARCHIVE}}.tar.gz` | The same build with debug information. For bug reporting. |

**No game data is included beyond Sierra's free 1.3 update**, whose data comes with the release, so you don't need it. A platform specific installer is included that copies the game's data from your own images of the two discs of the European or the USA release.

Supported images (the redump dumps of the discs):

- Europe: `No One Lives Forever 2 - A Spy in H.A.R.M.'s Way (Europe) (Disc 1)`, redump ID 35959, and `(Disc 2)`, redump ID 35960
- USA: `No One Lives Forever 2 - A Spy in H.A.R.M.'s Way (USA) (Disc 1)`, redump ID 12883, and for disc 2 either `(Disc 2) (Alt)`, redump ID 12882, or `(Disc 2)`, redump ID 33578

## Install

**This is the whole game, not a patch.** For a first installation, unpack it into a new, empty directory and run the installer. **To upgrade, unpack it over your installed game** (the same build, legacy or modern): put the files of its directory into your game's directory, e.g. `tar xzf <archive> --strip-components=1 -C <game directory>`. Do not run the installer again: the files from your discs, your saved games, your profiles and your settings stay.

The full guide is [here](https://github.com/{{REPO}}/blob/{{TAG}}/docs/INSTALL.md).

### Windows

Unpack the archive, drop both disc images onto `windows-install.bat`, then start `NOLF2.exe`.

### Linux

There's no native Linux build yet, but the game runs under Wine or Proton.

```sh
tar xzf nolf2src-{{ARCHIVE}}.tar.gz
cd nolf2src-{{ARCHIVE}}
./linux-install.sh /path/to/disc1.zip /path/to/disc2.zip
./linux-run.sh
```

#### Steam Deck

Add `NOLF2.exe` as a non-Steam game, enable compatibility mode, and pick a Proton runtime. (Untested so far.)

## What the modern build adds

- Wide screen support, with the menus and HUD keeping their shape; window and borderless modes, in the game and in the launcher.
- A field-of-view slider, antialiasing and anisotropic filtering.
- High frame rates at the right game speed.
- Xbox-style controllers.
- A developer console.
- Its own movie player: no proprietary libraries for the intro movies.
- A launcher that plays from its own folder, with no installer, registry or administrator needed.
- Fixes for many of the retail game's own bugs.

Every change since the retail game is in [`CHANGELOG.md`](https://github.com/{{REPO}}/blob/{{TAG}}/CHANGELOG.md).

## Testing

The game is a 32-bit Windows program. It is tested on Linux with Wine; Windows has had less testing. Please report problems in the [issues](https://github.com/{{REPO}}/issues). With the debug build, attach `nolf2src.log` from the game directory.
