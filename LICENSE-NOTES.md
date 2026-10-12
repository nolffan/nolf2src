# What is whose

| Path | Whose | Terms |
|---|---|---|
| `src/Game/`, `src/Engine/sdk/`, `src/libs/`, `src/Build*.bat` | **Monolith Productions**: the *No One Lives Forever 2* source code release (version 1.3) -- the game code, the LithTech Jupiter SDK headers and Monolith's shared libraries -- unmodified apart from line endings (LF; `credits.txt` and `intro.txt`, which the game embeds byte for byte, keep CRLF) and changes inside `#ifdef NOLF2SRC_MODERN` / `NOLF2SRC_DEBUG` blocks (none yet). `src/libs/STLPort-4.0/` is STLport, `src/libs/zlib/` zlib, as the release carried them. | Monolith's terms for the source release; `src/Engine/sdk/Legal.txt` is its legal notice. Work out those terms before distributing anything built from it. |
| `src/nolf2src/`, `build/`, `tools/`, `docker/`, `Makefile`, the documentation | written for this project (much of it adapted from nolfsrc) | no licence is declared |
| `rez/` (submodule) | the disc images' installer; the images themselves are fetched from archive.org | see `rez/README.md` |
| `toolchains/` (submodule) | the compilers, assembled from public copies of the original media | see `toolchains/README.md` |

What a build puts in a game directory, by origin (`MANIFEST.txt` in the
directory lists every file; `tools/retailextract.py audit` every binary):

| | Whose | From |
|---|---|---|
| the game DLLs, the dedicated server | built here from Monolith's source | `src/` |
| the game data: `.rez` archives, movies, configs | Monolith Productions / Fox Interactive / Sierra | the retail game (the retail game DLLs inside the archives are zeroed) |
| the engine: `Lithtech.exe`, `server.dll`, `ServerDir.dll`, `snddrv.dll`, `ltmsg.dll` | Monolith Productions | the retail game, until it is built here |
| `binkw32.dll` (Bink), the Microsoft C++ and MFC runtime DLLs | RAD Game Tools, Microsoft | the retail game |
