# Building

`make` is the whole build. This file describes what it does, how to run
parts of it by hand, and how the game is packaged.

## What you need

* **Linux with Docker.** The compilers are Win32 programs and run under Wine
  in a container; the host needs nothing else (no Wine, no Python).
* **The submodules**: `git submodule update --init`.
  * `toolchains/`, the compilers (Visual C++ 6.0 SP5 and the other
    revisions), the DirectX 8.1 SDK and Microsoft's DirectMusic. See
    `toolchains/README.md`.
  * `rez/`, the retail game the build takes its data from. It fetches the
    redump images of the two European discs of *No One Lives Forever 2*
    from archive.org, checks them, and installs the game from them as its
    own setup would, then the English 1.3 update it carries, into
    `rez/games/nolf2-eu-1.3/`, checked file by file against
    `rez/games.sha256`, and the USA release's two discs, which the public
    archive's install scripts are made against too (below). It also
    fetches the LithTech Jupiter SDK's CD image and installs its source into `rez/sdk/lithtech-jupiter-51/`, for
    `ServerDir.dll` (`LICENSE-NOTES.md`). `make` does both the first time
    (`make retail`, `make sdk`); see `rez/README.md`.
  * `ext/ffmpeg`, FFmpeg, which the modern build's Bink player is built on
    (`build/ext.sh`). The release build does not need it.
* About 14 GB of disk: 3.4 GB for the docker image, 5.9 GB in `rez/` (the
  disc images of both releases, zipped and unzipped, the SDK's image, the
  installed game),
  1.2 GB for each game directory in `out/` (the retail files the build does
  not change are hard links to `rez/games/`), 1 to 2 GB for each variant's
  build tree and Wine prefix, and 0.9 GB for a `-private` archive.

## What `make` does

1. Checks the compilers are in `toolchains/` and that `rez/` is there.
2. Builds the docker image `nolf2src-build` from `docker/Dockerfile` if
   needed (a few minutes, once).
3. `make retail` and `make sdk`, in a container: the first time, fetch the
   disc images and the SDK's image and install them (`build/retail.sh`,
   `build/jupiter.sh`); every time, check the installed files.
4. Runs `build/all.sh` in a throwaway container (`--rm --init`, named
   `nolf2src-build`), as your user, with the checkout (and so `rez/`)
   mounted at `/repo`.

`build/all.sh` then:

| Step | What | Output |
|---|---|---|
| 1. resources | the game data from the retail game: the `.rez` archives (the retail game DLLs inside them zeroed), the movies, the shipped `autoexec.cfg` and default profile | `out/nolf2-legacy-release/` |
| 2. third-party runtime | Bink (`binkw32.dll`) and the Microsoft C++ and MFC runtime DLLs from the retail game: licensed binaries with no source. The modern build takes only the Microsoft runtime, and builds its own `binkw32.dll` | `out/nolf2-legacy-release/` |
| 2b. Jupiter SDK source | WONAPI and `CServerDir_Titan`, which `ServerDir.dll` is built from, from the installed SDK (`tools/jupitersrc.py`; never committed) | `src/Game/Libs/` |
| 3. compile | `build/compile.sh`: every compile and link, by `build/build.mk` -- the libraries, the game DLLs, the launcher and the dedicated server from Monolith's workspace, `ServerDir.dll`, `snddrv.dll`, the engine (`Lithtech.exe`, `server.dll`) and `ltmsg.dll` | `src/Game/built/`, `src/Engine/built/` |
| 4. assemble | the built binaries into the game directory; the game DLLs go in `custom/`, last in the rez stack | `out/nolf2-legacy-release/` |
| 5. audit | every PE file in the game directory listed with its origin (`MANIFEST.txt`); the build fails if one is unaccounted for, or if a `.rez` archive still holds one | |
| 6. package | the game directory as a compressed tar, whole (`-private`), and without the retail game's files plus the scripts that install them from the player's own disc images and 1.3 update (`-public`; below) | `out/nolf2-legacy-release-private.tar.gz`, `-public.tar.gz` |

Every binary in the game directory is built from this repository except the
third-party runtime of step 2; the audit prints them all.

## Other targets

```sh
make test         # tools/playtest.sh under Xvfb: the main menu, a new game,
                  #   the first level (tools/playtest-newgame.txt; out/play/test/)
make progress     # score the build against the retail binaries, function by
                  #   function; fails if a function recorded as byte-identical
                  #   in progress/identical.txt no longer is
make progress-update   # record the score in progress/ and README.md
make shell        # a shell in the build container, at /repo
make clean        # remove out/ and every build output in the source tree
make distclean    # clean, and remove the docker image
```

`make progress` scores what the last `make` built (it compiles nothing); the
retail images it compares against are extracted into `out/reference/` the
first time. `progress/README.md` describes the scoring.

## Variant builds: debug and modern

`make` builds the release game, the only build `make progress` ever scores.
`make debug` (`NOLF2SRC_DEBUG`: symbols, logging), `make modern`
(`NOLF2SRC_MODERN`: `MODERN.md`; its Bink player on FFmpeg) and `make
modern-debug` (both) build the same source with those defines into
`out/nolf2-legacy-debug/`, `out/nolf2-modern-release/` and
`out/nolf2-modern-debug/`. Each is `build/variant.sh <variant>`: the source
is copied into `out/build-<variant>/` and built there by the same
`build/all.sh`, so the release build's outputs are never touched; its
header has the details.

## Archives: private and public

Every game directory is packaged twice by `build/package.sh`:

* `out/<directory>-private.tar.gz` (about 0.9 GB): the whole directory,
  the retail game's data included. For your own machines, and for others
  developing on the build.
* `out/<directory>-public.tar.gz` (5 MB; about 20 MB for a debug build,
  with its `.pdb` files): the same without anything
  that came from the retail game -- every file `MANIFEST.txt` lists as
  `data` or `THIRD-PARTY` -- and with two scripts that install those files
  from the player's own disc images of *No One Lives Forever 2* (the
  European or the USA release) and Sierra's English 1.3 update,
  `nolf2-update_1x3.exe`: `linux-install.sh` and `windows-install.bat`
  (`tools/mkinstall.py`). They check every file they write against its
  SHA-256, so the result is the private archive's directory, byte for byte.
  The one to give to other people.

`LICENSE-NOTES.md` says what each holds and under whose terms.

Nothing is installed or run from the discs or the update. NOLF2's setup
stores its files compressed in InstallShield 6 cabinets that span both
discs (`data1.hdr`, `data1.cab` to `data3.cab`; only `Data/GAME.REZ` is a
plain file), and the update packs its own InstallShield setup into a
Microsoft cabinet (MSZIP) inside a self-extractor. `tools/mkinstall.py`
works out, against the images in `rez/isos/` and the update rez/ carries,
where every byte the game needs is: for each retail file, the ranges of an
image that hold it as it is or as InstallShield's compressed chunks (each a
16-bit length and a raw deflate stream; a file split across two cabinets
has a range on each disc), one way per release (the cabinets lie at other
offsets on the USA discs), and for the update, the cabinet's offset. It
reads every way back and checks it against the retail file before it
writes the list. A script then needs no InstallShield or ISO 9660 code,
only an inflater: it recognises each image by its size and SHA-256, unpacks
the update's cabinet in memory (checked by its SHA-256 too), and writes
each of our files from its retail file, with the retail game DLLs inside
the archives as zeros. On Linux `python3`'s zlib inflates (bash and
coreutils do the rest); on Windows, PowerShell 5.1's .NET `DeflateStream`
(an MSZIP block's 32 KB of history goes in front of it as a stored deflate
block, as it takes no dictionary). An image is a plain `.iso`, redump's
`.bin` (or its `.cue`) or redump's `.zip`, converted to a temporary `.iso`
first. Redump has two dumps of the USA disc 2; the other, `(Alt)`, which
rez/ does not fetch, has the cabinet at the same offset, and is recorded by
its size and SHA-256 (`mkinstall.py`'s `ALIASES`; checked whenever it is in
`rez/isos/`).

The public archive is made only if `rez/isos/` has the `.iso` of both
discs of both releases: `make retail` fetches the USA ones too
(`build/retail.sh`'s `retail_discs`, 1.1 GB more, once).
`NOLF2_ARCHIVES` says which archives to write (default `private public`):
`make NOLF2_ARCHIVES=public` (or any variant target) writes only the
public one, and fails rather than skip it without the disc images.
`IMAGE_BUILD=0` makes the targets use the docker image as it is instead of
building it.

### GitHub Actions

`.github/workflows/public-archives.yml` builds the release game and all
three variants with `NOLF2_ARCHIVES=public` on every push to `master`, every
pull request and on demand, each in a job of its own and all four at the
same time (one failing still lets the others finish), runs `make progress`
on the release build (a function recorded as byte-identical that stops
matching fails the run), and keeps the four public archives as the run's
artifacts, each the `.tar.gz` itself rather than a zip around it. The
private archives are never made there. Its steps are the make targets
above, so a run can be reproduced locally:

```sh
git submodule update --init                 # toolchains/, rez/, ext/ffmpeg
make image && make retail sdk               # (CI: the image from its layer cache, IMAGE_BUILD=0)
export NOLF2_ARCHIVES=public
make && make progress && make debug && make modern && make modern-debug
ls out/*-public.tar.gz
```

A first job, "prepare", fetches the redump zips of the European and the
USA discs and the Jupiter SDK's image (2.9 GB from archive.org) only if the
cache (keyed on `rez/isos/SHA256SUMS`, against which `rez/fetch-isos.sh`
checks them either way) does not have them, so the builds never all
download them at once, and it writes the docker image's layer cache, which
the builds only read. The submodules are fetched over HTTPS at depth 1.
