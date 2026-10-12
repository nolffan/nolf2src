# nolf2src

*No One Lives Forever 2: A Spy in H.A.R.M.'s Way*, built from source.

The game code is Monolith's own public source release (version 1.3, the
game's last update), compiled with the compiler Monolith used, Visual C++ 6,
under Wine. The aim, as for [nolfsrc](https://github.com/nolffan/nolfsrc)
(the first game), is two builds:

- **legacy**: the 1.3 game as it shipped, rebuilt so that it compiles back
  to the retail binaries byte for byte, as far as that can be done;
- **modern**: the same source with fixes and new features (`NOLF2SRC_MODERN`),
  and eventually our own renderers.

## Where it stands

| | |
|---|---|
| Game DLLs | `CShell.dll`, `Object.lto`, `ClientFx.fxd`, `CRes.dll`, `SRes.dll` compile from Monolith's workspace (`src/Game/TO2.dsw`, Final configuration) and run in the game. Each is the retail binary's exact size, compiled with VC6 SP5 (build 8966) as retail was. `ClientFx.fxd`, `CRes.dll` and `SRes.dll` are byte for byte the retail ones apart from link time stamps; `CShell.dll` and `Object.lto` are close but not yet identical. |
| Dedicated server | `NOLF2Srv.exe` compiles; its code is the retail one's but for two `CButeMgr` functions (`libs/ButeMgr`), where SP5 orders two loads the other way round. |
| Launcher | `NOLF2.exe` compiles against the DirectX 8.1 SDK; every code segment matches the retail one's. Not yet put in the game directory. |
| Engine | `Lithtech.exe`, `server.dll`, `ServerDir.dll`, `snddrv.dll`, `ltmsg.dll`: no source (Monolith released the game, not the engine). The build takes them from the retail game, marked RETAIL, until they are reconstructed. The retail `Lithtech.exe` is copy-protected (SecuROM), so the game does not start under Wine yet: it asks for the disc. |
| Scoring | `build/reference.sh` extracts the retail 1.3 binaries and their function tables; `make progress` is not adapted from nolfsrc yet. |

## Building

Needs docker and the two submodules (`git submodule update --init`):
`toolchains/` (the compilers) and `rez/` (which fetches the European discs
from archive.org and installs the game with its 1.3 update).

```sh
make            # out/nolf2-legacy-release/ and out/nolf2-legacy-release.tar.gz
make debug      # out/nolf2-legacy-debug/: symbols, NOLF2SRC_DEBUG
make modern     # out/nolf2-modern-release/: NOLF2SRC_MODERN
make help       # everything else
```

`build/build.mk` builds Monolith's workspace as Developer Studio would:
`tools/dsp2mk.py` reads `TO2.dsw` and the project files and writes the
rules, compile for compile.

See `LICENSE-NOTES.md` for what is whose.
