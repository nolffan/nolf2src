# What is whose

| Path | Whose | Terms |
|---|---|---|
| `src/Game/`, `src/Engine/sdk/`, `src/libs/`, `src/Build*.bat` | **Monolith Productions**: the *No One Lives Forever 2* source code release (version 1.3) -- the game code, the LithTech Jupiter SDK headers and Monolith's shared libraries -- unmodified apart from line endings (LF; `credits.txt` and `intro.txt`, which the game embeds byte for byte, keep CRLF) and changes inside `#ifdef NOLF2SRC_MODERN` / `NOLF2SRC_DEBUG` blocks (none yet). `src/libs/STLPort-4.0/` is STLport, `src/libs/zlib/` zlib, as the release carried them. | Monolith's terms for the source release; `src/Engine/sdk/Legal.txt` is its legal notice. Work out those terms before distributing anything built from it. |
| `src/Game/Libs/WONAPI/`; in `src/Game/Libs/ServerDir/`, `CServerDir_Titan.*`, `TitanTest.*`, `WinSync.h`, `stdafx.*` -- **not in the repository**: copied in at build time | **Monolith Productions / LithTech, Inc.**: the *LithTech Jupiter* SDK (build 51, March 2002), the engine's licensee SDK -- its "Source Code" file group, which has what the public release lacks for `ServerDir.dll`. `WONAPI` is WON's (Sierra's) Titan client library, as Monolith shipped it to licensees; `WONAPI/WONMisc/` includes GameSpy's query-reporting code (copyright GameSpy Industries). rez/ fetches the SDK's CD image from archive.org and installs its source (`rez/fetch-isos.sh`, `rez/install-games.sh`, pinned by SHA-256); `tools/jupitersrc.py` copies these files from it with LF line endings and applies `src/nolf2src/jupiter/*.patch` (the 2002 `CServerDir_Titan` brought to the 1.3 interface). | The SDK was licensed to engine licensees, not released. archive.org labels the item public domain; nothing in the SDK says so. So it is fetched, never committed (`.gitignore`), and the caution above applies more strongly still to anything built from it (`ServerDir.dll`): work out the terms before distributing it. |
| `src/nolf2src/`, `src/Game/Libs/ServerDir/ServerDir.dsp` and `ServerDir.dsw`, `src/Engine/ltmsg/`, `build/`, `tools/`, `docker/`, `Makefile`, the documentation | written for this project (much of it adapted from nolfsrc). The patches in `src/nolf2src/jupiter/` carry lines of the SDK's code as diff context. `src/Engine/ltmsg/ltmsg.rc` is a reconstruction of the retail `ltmsg.dll`'s resources: its strings are Monolith's engine messages, as that DLL has them. | no licence is declared |
| `rez/` (submodule) | the disc images' installer; the images themselves are fetched from archive.org | see `rez/README.md` |
| `toolchains/` (submodule) | the compilers, assembled from public copies of the original media | see `toolchains/README.md` |

What a build puts in a game directory, by origin (`MANIFEST.txt` in the
directory lists every file; `tools/retailextract.py audit` every binary):

| | Whose | From |
|---|---|---|
| the game DLLs, the dedicated server | built here from Monolith's source | `src/` |
| the game data: `.rez` archives, movies, configs | Monolith Productions / Fox Interactive / Sierra | the retail game (the retail game DLLs inside the archives are zeroed) |
| the engine: `Lithtech.exe`, `server.dll`, `ServerDir.dll`, `snddrv.dll`, `ltmsg.dll` | Monolith Productions | the retail game, until it is built here (`ServerDir.dll` is built, from the Jupiter SDK's source, but not yet put in the game) |
| `binkw32.dll` (Bink), the Microsoft C++ and MFC runtime DLLs | RAD Game Tools, Microsoft | the retail game |
