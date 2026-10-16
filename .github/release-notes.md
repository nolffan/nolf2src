## Download

| File | What it is |
|---|---|
| `nolf2src-{{TAG}}.tar.gz` | **This is what you want**; the retail game (1.3) with bug fixes and new features. |
| `nolf2src-debug-{{TAG}}.tar.gz` | The same build with debug information. For bug reporting. |

**No game data is included.** A platform specific installer is included that copies the game's data from your own images
of the two discs of the European or the USA release, and from Sierra's English 1.3 update, `nolf2-update_1x3.exe` (read,
not run).

Supported images:

- Europe: <http://redump.org/disc/35959/>, <http://redump.org/disc/35960/>
- USA: <http://redump.org/disc/12883/>, and for disc 2 either <http://redump.org/disc/12882/> or
  <http://redump.org/disc/33578/>

## Install

**This is the whole game, not a patch.** Unpack it into a new, empty directory, not over an earlier release or another
installation: the installer checks the directory against `SHA256SUMS` and stops if it holds anything else. Copy your old
`Save` and `Profiles` folders across to keep your saved games and profiles.

The full guide is [here](https://github.com/{{REPO}}/blob/{{TAG}}/docs/INSTALL.md).

### Windows

Unpack the archive, drop both disc images and `nolf2-update_1x3.exe` onto `windows-install.bat`, then start `NOLF2.exe`.

### Linux

There's no native Linux build yet, but the game runs under Wine or Proton.

```sh
tar xzf nolf2src-{{TAG}}.tar.gz
cd nolf2src-{{TAG}}
./linux-install.sh /path/to/disc1.zip /path/to/disc2.zip /path/to/nolf2-update_1x3.exe
./linux-run.sh
```

#### Steam Deck

Add `NOLF2.exe` as a non-Steam game, enable compatibility mode, and pick a Proton runtime. (Untested so far.)

## What the modern build adds

- Wide screen support, with the menus and HUD keeping their shape; window and borderless modes, in the game and in the
  launcher.
- A field-of-view slider, antialiasing and anisotropic filtering.
- High frame rates at the right game speed.
- Xbox-style controllers.
- A developer console.
- Its own movie player: no proprietary libraries for the intro movies.
- A launcher that plays from its own folder, with no installer, registry or administrator needed.
- Fixes for many of the retail game's own bugs.

Every change since the retail game is in [`CHANGELOG.md`](https://github.com/{{REPO}}/blob/{{TAG}}/CHANGELOG.md).

## Testing

The game is a 32-bit Windows program. It is tested on Linux with Wine; Windows has had less testing. Please report
problems in the [issues](https://github.com/{{REPO}}/issues). With the debug build, attach `nolf2src.log` from the game
directory.
