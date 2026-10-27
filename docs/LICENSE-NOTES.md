# What is whose

| Path | Whose | Terms |
|---|---|---|
| `src/Game/`, `src/Engine/sdk/`, `src/libs/`, `src/Build*.bat` | **Monolith Productions**: the *No One Lives Forever 2* source code release (version 1.3) -- the game code, the LithTech Jupiter SDK headers and Monolith's shared libraries -- unmodified apart from line endings (LF; `credits.txt` and `intro.txt`, which the game embeds byte for byte, keep CRLF) changes inside `#ifdef NOLF2SRC_MODERN` / `NOLF2SRC_DEBUG` blocks (`MODERN.md`), and the places where the retail 1.3 game differs from the release, reconstructed for this project from the retail `CShell.dll` and `Object.lto`, made in place and marked with `RETAIL:` comments. `src/libs/STLPort-4.0/` is STLport, `src/libs/zlib/` zlib, as the release carried them. | Monolith's terms for the source release; `src/Engine/sdk/Legal.txt` is its legal notice. Work out those terms before distributing anything built from it. |
| `src/Game/Libs/WONAPI/` -- **not in the repository**: copied in at build time | **Monolith Productions / LithTech, Inc.**: the *LithTech Jupiter* SDK (build 51, March 2002), the engine's licensee SDK -- its "Source Code" file group, which has the library the public release lacks for `ServerDir.dll`. `WONAPI` is WON's (Sierra's) Titan client library, as Monolith shipped it to licensees; `WONAPI/WONMisc/` includes GameSpy's query-reporting code (copyright GameSpy Industries). rez/ fetches the SDK's CD image from archive.org and installs its source (`rez/fetch-isos.sh`, `rez/install-games.sh`, pinned by SHA-256); `tools/jupitersrc.py` copies these files from it with LF line endings. | The SDK was licensed to engine licensees, not released. archive.org labels the item public domain; nothing in the SDK says so. So it is fetched, never committed (`.gitignore`), and the caution above applies more strongly still to anything built from it (`ServerDir.dll`): work out the terms before distributing it. |
| in `src/Game/Libs/ServerDir/`, `CServerDir_Titan.*`, `TitanTest.*`, `WinSync.h`, `stdafx.*` | **Monolith Productions**: NOLF2's server directory (the WON/Titan implementation of `IServerDir.h`), as the F.E.A.R. source release carries it in `libs/ServerDir/` (its 1.3 code, matching the retail `ServerDir.dll`), with LF line endings; changes are marked `nolf2src`. | as Monolith's code above |
| `src/nolf2src/`, `src/Game/Libs/ServerDir/ServerDir.dsp` and `ServerDir.dsw`, `src/Engine/ltmsg/`, `build/`, `tools/`, `docker/`, `Makefile`, the documentation | written for this project (much of it adapted from nolfsrc). `src/Engine/ltmsg/ltmsg.rc` is a reconstruction of the retail `ltmsg.dll`'s resources: its strings are Monolith's engine messages, as that DLL has them. | no licence is declared |
| `src/Engine/snddrv/`, `src/libs/ltmem/` | written for this project: a reconstruction of the engine's sound driver `SndDrv.dll` (and of what it links of the `ltmem` library) from the retail 1.3 binary, so **Monolith Productions'** code in substance. Its classes, names and code follow Monolith's later revision of the same driver, as the F.E.A.R. (Jupiter EX) engine source carries it, corrected to the retail bytes; that revision's comments are not carried over. `eax.h` and `eaxguid/eaxguid.cpp` restate what the driver uses of **Creative Labs'** EAX 2.0 interface (its ids and property layouts, the values read off the retail image) in place of Creative's SDK header and `eaxguid.lib`. | as Monolith's code above; no licence is declared for what is this project's |
| `src/Engine/runtime/`, `src/Engine/libs/rezmgr/` | **Monolith Productions / LithTech, Inc.** (later Touchdown Entertainment): the *LithTech Jupiter* engine's own source -- its runtime (client, server, shared, kernel, world, model, sound, render_a, render_b, ui, controlfilemgr, lithtemplate, the `winbuild` resource scripts) and its RezMgr library -- as a 2006 distribution of the engine carries it, the same engine line as NOLF2's, three to four years later (`docs/engine/fear-mapping.md`). Only the files the retail `Lithtech.exe` and `server.dll` link, and the headers they include, were taken (`docs/engine/PLAN.md`, package 2); they were committed first as they were, with LF line endings, and every later change is a back-port to the 2002 engine (or, marked `nolf2src`, what it takes to build). `render_a/src/sys/d3d/FixedPoint.h` is Chris Hecker's fixed-point code, as Monolith carried it. | as Monolith's code above: Monolith's terms; no licence is declared for the engine source itself. Work out the terms before distributing anything built from it (`Lithtech.exe`, `server.dll`). |
| `src/modern/binkw32/` | written for this project: the modern build's Bink player (adapted from nolfsrc's, the same project's for NOLF1) | no licence is declared |
| `ext/ffmpeg` (submodule) | **FFmpeg**, upstream at github.com/FFmpeg/FFmpeg, pinned to n8.1.3 | LGPL-2.1-or-later as the modern build configures it (no GPL or non-free parts enabled); see its `LICENSE.md` |
| `rez/` (submodule) | the disc images' installer; the images themselves are fetched from archive.org | see `rez/README.md` |
| `tools/` (submodule) | the build's scripts, tests and byte-matching tools, shared with the NOLF and Contract J.A.C.K. projects | ours; see `tools/README.md` |
| `toolchains/` (submodule) | the compilers, assembled from public copies of the original media | see `toolchains/README.md` |

What a build puts in a game directory, by origin (`MANIFEST.txt` in the
directory lists every file; `tools/retailextract.py audit` every binary):

| | Whose | From |
|---|---|---|
| the game DLLs, the dedicated server | built here from Monolith's source | `src/` |
| the game data: `.rez` archives, movies, configs | Monolith Productions / Fox Interactive / Sierra | the retail game (the retail game DLLs inside the archives are zeroed) |
| the engine: `Lithtech.exe`, `server.dll` | built here from the LithTech Jupiter engine source, back-ported to 2002 (Monolith Productions / LithTech, Inc.); `Lithtech.exe`'s icon is the retail game's, read out of the retail `Lithtech.exe` at build time and never committed | `src/Engine/runtime/`, `src/Engine/libs/rezmgr/`; the icon from the retail game |
| `snddrv.dll`, the sound driver; `ltmsg.dll`, the engine's messages | built here from reconstructions (Monolith Productions' code in substance; ltmsg's strings are the retail DLL's) | `src/Engine/snddrv/`, `src/Engine/ltmsg/` |
| `ServerDir.dll`, the server directory | built here from Monolith's `CServerDir_Titan` (from the F.E.A.R. source release) and the LithTech Jupiter SDK's WONAPI, fetched at build time | `src/Game/Libs/ServerDir/`, `src/Game/Libs/WONAPI/` |
| `NOLF2.exe`, the launcher | built here from Monolith's source | `src/Game/Launcher/` |
| `binkw32.dll` (Bink), the Microsoft C++ and MFC runtime DLLs | RAD Game Tools, Microsoft | the retail game |
| `binkw32.dll` in the modern build | built here: our player (`src/modern/binkw32/`) statically linked with FFmpeg (LGPL-2.1-or-later) | `build/ext.sh`, from `ext/ffmpeg` |

The modern build's `binkw32.dll` is FFmpeg (LGPL-2.1-or-later), statically
linked with our player. The LGPL asks that whoever receives it can rebuild
it against a modified FFmpeg, which `build/ext.sh` and the source here
allow.

## The archives

Each game directory is packaged twice (`build/package.sh`; `BUILDING.md`).
This says what each holds; it is not legal advice and grants nothing.

**`<directory>-private.tar.gz`** is the whole game directory: everything in
the table above, the retail game's data and the third-party runtime
included. Those are Monolith Productions', Fox Interactive's and Sierra's,
RAD Game Tools' and Microsoft's, under the terms the retail game came with:
the private archive is for your own machines, and for others developing on
the build who have the game, not for handing out.

**`<directory>-public.tar.gz`** holds only what the build made and the
project's own files, none of the retail game's:

| In it | Whose | Terms |
|---|---|---|
| `Lithtech.exe`, `server.dll` | built here from the LithTech Jupiter engine source (Monolith Productions / LithTech, Inc.); `Lithtech.exe` carries the retail game's icon, as the retail `Lithtech.exe` does | as the engine source above: no licence is declared for it |
| `custom/` (`cshell.dll`, `object.lto`, `clientfx.fxd`, `cres.dll`, `sres.dll`), `NOLF2.exe`, `NOLF2Srv.exe` | built here from Monolith's *No One Lives Forever 2* source release | Monolith's terms for that release (`src/Engine/sdk/Legal.txt`) |
| `ServerDir.dll` | built here from Monolith's `CServerDir_Titan` and the LithTech Jupiter SDK's WONAPI (with GameSpy's query reporting) | as the SDK above for WONAPI: licensed to engine licensees, not released |
| `snddrv.dll`, `ltmsg.dll` | built here from this project's reconstructions (Monolith's code in substance; `ltmsg.dll`'s strings are the retail DLL's) | as above |
| `binkw32.dll` (modern builds only) | our Bink player statically linked with FFmpeg | LGPL-2.1-or-later (FFmpeg); the source is `src/modern/binkw32/` and `ext/ffmpeg`, rebuilt by `build/ext.sh` |
| `.pdb`, `.map` (debug builds only) | the linker's, for the binaries above | as those binaries |
| `linux-run.sh`, `linux-install.sh`, `windows-install.bat`, `nolf2cmds.txt`, `MANIFEST.txt`, `SHA256SUMS` | written for this project (the install scripts by `tools/mkinstall.py`, with the sizes and SHA-256 of the disc images, the update and the retail files they read, and where on the images each file's bytes are) | no licence is declared |

It has no `.rez` archive, movie, setting or profile of the retail game, no
RAD Bink and no Microsoft runtime DLL. The install scripts copy those from
the player's own disc images of NOLF2 (the European or the USA release)
and Sierra's 1.3 update into the directory, on the player's machine;
nothing of them is in the archive, and the scripts carry no InstallShield
or Microsoft code (they inflate with python3's zlib or .NET's
DeflateStream). So
the public archive is the one meant for other people -- but its binaries
are still built from Monolith's source, the LithTech engine source and the
Jupiter SDK, whose terms no licence here overrides: work them out before
distributing it, as the tables above say. The GitHub Actions workflow
(`.github/workflows/public-archives.yml`) makes only public archives.
