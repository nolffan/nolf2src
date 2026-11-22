# Building

`make` is the whole build. This file describes what it does, how to run
parts of it by hand, and how the game is packaged.

## What you need

* **Linux with Docker.** The compilers are Win32 programs and run under Wine
  in a container; the host needs nothing else (no Wine, no Python).
* **The submodules**: `git submodule update --init`.
  * `ext/tools/`, the build's scripts, its tests (`playtest.sh`, `srvtest.sh`,
    `mptest.sh`) and the byte-matching and scoring tools: a repository of
    its own, shared with the reconstructions of *No One Lives Forever*
    (nolfsrc) and *Contract J.A.C.K.* (cjacksrc), so a tool one of them
    makes serves the others. A tool reads the project from its own files
    (`progress/targets.py`; `build/env.sh` names the variant macros and the
    header directory). See `ext/tools/README.md`.
  * `ext/toolchains/`, the compilers (Visual C++ 6.0 SP5 and the other
    revisions), the DirectX 8.1 SDK and Microsoft's DirectMusic. See
    `ext/toolchains/README.md`.
  * `ext/lithtools/`, the reconstruction of LithTech's development tools: the
    build uses its `lithrez` (`build/lithrez.sh` builds it, without its Qt
    GUI) to pack `assets/rez/`, the 1.3 update's data, into the game
    directory's `nolf2src.rez`, and the two official map packs,
    `assets/mappack001/` and `assets/mappack002/`, into `MapPack001.rez`
    and `MapPack002.rez` (`assets/README.md`). A shallow submodule.
  * `ext/ffmpeg`, FFmpeg, which the modern build's Bink player is built on
    (`build/ext.sh`). The release build does not need it.
* **Your own images** (bring your own: no part of the retail game, the
  update or the SDK is in this repository, and the build fetches nothing).
  Put them in `isos/` at the root of the checkout (it is ignored by git; a
  hard link is good: `ln <image> isos/`), or name their directory with
  `NOLF2_ISOS=<directory>`. Each file can have any name:

  | What | For | As |
  |---|---|---|
  | the two discs of *No One Lives Forever 2* (Europe): `No One Lives Forever 2 - A Spy in H.A.R.M.'s Way (Europe) (Disc 1)`, redump ID 35959, and `(Disc 2)`, redump ID 35960 | every build: the game's data (`make retail`) | a `.iso`, a `.bin` with its `.cue`, or a `.zip` that holds one of them |
  | Sierra's English 1.3 update, `nolf2-update_1x3.exe` (29,479,272 bytes) | every build: the retail binaries that `make progress` compares against, and the retail icon (`make retail`) | the `.exe` as it was published |
  | the CD of the LithTech Jupiter SDK, build 51 (volume label `LT_JUP_BIN_B51`) | every build: `ServerDir.dll`'s WONAPI source (`make sdk`) | as the discs |
  | the NOLF2 multiplayer demo, `nolf2_mpdemo_en.exe` (179,282,860 bytes) | `make progress` only: the pages of the retail `Lithtech.exe` that SecuROM encrypts (`make demo`) | the `.exe` as it was published |

  `build/discs.py` installs each from its list in `build/`: the retail game
  (`build/retail-files.txt`) into `out/retail/nolf2-eu-1.3/`, the SDK's
  WONAPI files (`build/sdk-files.txt`) into
  `out/retail/lithtech-jupiter-51/`, and the demo's engine
  (`build/demo-files.txt`) into `out/retail/nolf2-mpdemo/`. A list holds
  only metadata: each file's path, size and SHA-256, and where its bytes
  are in which image (InstallShield 6 cabinets, read and inflated in
  place: nothing of an image is run). A disc is recognised by its volume
  label and volume size, an installer by its size and SHA-256, and each
  file is checked against the list. So any correct copy of the discs
  works, not only the redump dumps. Without an image, `make` stops and says
  what to supply. `make retail`, `make sdk` and `make demo` do this once;
  each build checks the install again.

  `make NODISCS=1` builds without any of them (as CI does; below).
* About 10 GB of disk: 3.4 GB for the docker image, 1.9 GB for the
  installed retail game in `out/retail/`, 1.2 GB for each game directory in
  `out/` (the retail files the build does not change are hard links to
  `out/retail/`), 1 to 2 GB for each variant's build tree and Wine prefix,
  and 0.9 GB for a `-private` archive; and your images (2.4 GB with the
  SDK's and the demo).

## What `make` does

1. Checks the compilers are in `ext/toolchains/` and that `ext/lithtools/`
   is there.
2. Builds the docker image `nolf2src-build` from `docker/Dockerfile` if
   needed (a few minutes, once).
3. `make retail` and `make sdk`, in a container: the first time, install
   the retail game and the SDK's source from your images
   (`build/retail.sh`, `build/jupiter.sh`, `build/discs.py`); every time,
   check the installed files.
4. Runs `build/all.sh` in a throwaway container (`--rm --init`, named
   `nolf2src-build`), as your user, with the checkout mounted at `/repo`
   (and `NOLF2_ISOS`, read-only, at `/isos`).

`build/all.sh` then:

| Step | What | Output |
|---|---|---|
| 1. resources | the game data from the retail discs: the `.rez` archives (the retail game DLLs inside them zeroed) and the movies | `out/nolf2-legacy-release/` |
| 1b. assets | the 1.3 update's data, from `assets/`: `assets/rez/` packed into `nolf2src.rez` by lithtools' `lithrez` (`build/lithrez.sh`; a fixed time, so the same bytes every build), and 1.3's `autoexec.cfg` and default profile; the official map packs, `assets/mappack001/` and `assets/mappack002/`, packed into `MapPack001.rez` and `MapPack002.rez` (`assets/README.md`) | `out/nolf2-legacy-release/` |
| 2. third-party runtime | Bink (`binkw32.dll`) and the Microsoft C++ and MFC runtime DLLs from the retail game: licensed binaries with no source. The modern build takes only the Microsoft runtime, and builds its own `binkw32.dll` | `out/nolf2-legacy-release/` |
| 2b. Jupiter SDK source | WONAPI, the library `ServerDir.dll` is built with, from the installed SDK (`ext/tools/jupitersrc.py`; never committed). Without the SDK (`NODISCS=1`), the committed `assets/serverdir/ServerDir.dll` and its link map go where the compile puts its own, and the compile leaves `ServerDir.dll` out (`build/serverdir.py install`) | `src/Game/Libs/` |
| 2c. engine art | the icon `lithtech.rc` compiles into `Lithtech.exe` (`IDR_MAINFRAME`, five images): the retail icon, committed in `assets/art/lithtech/` (`assets/README.md`), copied into the directory `lithtech.rc` includes it from (`build/retailextract.py art install`). With the retail game, the build first checks it against the retail `Lithtech.exe`'s resources (`art check`, as `make art-check` does); `make art` writes it again from them. The engine's text resources (dialog, version block, string table) are `.rc` source in the repository (`lithtech.rc`, `server.rc`, `ltmsg.rc`); its other binary resources, MFC's help cursor and four bitmaps, come from the toolchain's `afxres.rc`, as the original's did | `src/Engine/runtime/winbuild/lithtech/res/` |
| 3. compile | `build/compile.sh`: every compile and link, by `build/build.mk` -- the libraries, the game DLLs, the launcher and the dedicated server from Monolith's workspace, `ServerDir.dll`, `snddrv.dll`, the engine (`Lithtech.exe`, `server.dll`) and `ltmsg.dll`. The release build's `ServerDir.dll` must then be `assets/serverdir/`'s, but for its link time (`build/serverdir.py check`; `make serverdir` writes it again) | `src/Game/built/`, `src/Engine/built/` |
| 4. assemble | the built binaries into the game directory; the game DLLs go in `custom/`, last in the rez stack | `out/nolf2-legacy-release/` |
| 5. audit | every PE file in the game directory listed with its origin (`MANIFEST.txt`); the build fails if one is unaccounted for, or if a `.rez` archive still holds one | |
| 6. package | the game directory as a compressed tar, whole (`-private`), and without the retail game's files plus the scripts that install them from the player's own disc images (`-public`; below) | `out/nolf2-legacy-release-private.tar.gz`, `-public.tar.gz` |

Every binary in the game directory is built from this repository except the
third-party runtime of step 2; the audit prints them all.

## Other targets

```sh
make test         # ext/tools/playtest.sh under Xvfb: the main menu, a new game,
                  #   the first level (ext/tools/playtest-newgame.txt; out/play/test/)
make progress     # score the build against the retail binaries, function by
                  #   function; fails if a function recorded as byte-identical
                  #   in progress/identical.txt no longer is
make progress-update   # record the score in progress/ (and its README.md table),
                  #   and the hashes make progress-ci checks against (progress/hashes/)
make progress-ci  # the same check without the retail game, against progress/hashes/
make ci           # what CI runs: make NODISCS=1, then make progress-ci
make retail-ranges   # build/retail-ranges.txt again, from the retail game
make art          # assets/art/ again, from the retail binaries; make art-check checks it
make serverdir    # assets/serverdir/ again, from the last make (with the SDK)
make shell        # a shell in the build container, at /repo
make clean        # remove out/ and every build output in the source tree
make distclean    # clean, and remove the docker image
```

The dedicated server has tests of its own, run in `make shell`:
`ext/tools/srvtest.sh` starts a game directory's `NOLF2Srv.exe` unattended under
Xvfb on a co-operative profile of its own, checks that it is still running
and then that Stop Server stops it, and prints the end of its log
(`nolf2srv.log`); `ext/tools/mptest.sh` has the game join such a server over
the LAN. Their runs are in `out/srvtest/<name>/` and `out/mptest/<name>/`:

```sh
G=out/nolf2-modern-release
SRVTEST_NAME=modern ext/tools/srvtest.sh $G/server.dll 60 $G
MPTEST_NAME=modern MPTEST_KEYS='Down Down Return Return w2 Down Return w2 F5 w4 Down Down Return w20 space w15' \
    ext/tools/mptest.sh $G/server.dll $G/Lithtech.exe 30 $G
# (in the modern game the found server is one Down further than mptest.sh's
# default keys go)
```

`make progress` scores what the last `make` built (it compiles nothing); the
retail images it compares against are extracted into `out/reference/` the
first time, and the multiplayer demo's engine is installed (`make demo`).
`progress/README.md` describes the scoring.

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

## Without the retail game: NODISCS=1

`make NODISCS=1` (and `make NODISCS=1 debug|modern|modern-debug`) builds
without any of your images: CI builds so. Every binary is compiled as
always, and is the same as with the images but for its link time: the
retail icon is the committed `assets/art/`, and `ServerDir.dll`, whose
source needs the SDK, is the committed release build's,
`assets/serverdir/`. Steps 1 and 2 copy no game data and no Bink or
Microsoft runtime; they write only those files' rows in `MANIFEST.txt`,
from `build/retail-files.txt` and `build/retail-ranges.txt` (the PE files
of the install, and the retail game DLLs zeroed inside the archives, with
each archive's SHA-256 after that; `make retail-ranges` writes it from the
retail game, and every build with it checks it). The checks against the
retail game do not occur. The game directory is `out/<name>-nodiscs/`,
with `NOT-PLAYABLE.txt` in it: it does not play, and `linux-run.sh`,
`linux-server.sh` and `make test` refuse it. Step 6 makes only its public
archive, `out/<name>-public.tar.gz`, which is the same as the one a build
with the images makes (but the link time of each binary).

`make progress-ci` then checks the build without the retail binaries:
`build/progress.sh ci` compares every function, resource, float constant,
string, vtable and call that `progress/hashes/` records with the build
(`ext/tools/hashcheck.py`, `datacheck.py ci`, `fpconst.py --ci`,
`vtabcheck.py --ci`). `make progress-update`, with the retail game, writes
`progress/hashes/` from the full check. It holds no retail bytes: only
addresses, lengths, our symbols and SHA-256 hashes. The check finds no new
match; only `make progress-update` does.

## Archives: private and public

Every game directory is packaged twice by `build/package.sh`:

* `out/<directory>-private.tar.gz` (about 0.9 GB): the whole directory,
  the retail game's data included. For your own machines, and for others
  developing on the build.
* `out/<directory>-public.tar.gz` (about 100 MB, most of it the 1.3
  update's data in `nolf2src.rez` and the map packs; 15 MB more for a debug build, with its
  `.pdb` files): the same without anything that came from the retail
  discs -- every file `MANIFEST.txt` lists as `data` or `THIRD-PARTY` --
  and with two scripts that install those files from the player's own disc
  images of *No One Lives Forever 2* (the European or the USA release):
  `linux-install.sh` and `windows-install.bat` (`build/mkinstall.py`). The
  data of Sierra's free English 1.3 update is in the archive itself
  (`asset` in `MANIFEST.txt`: `nolf2src.rez` and the shipped settings and
  default profile, `autoexec.cfg.retail` and `Default.prf.retail`, from
  `assets/`), and so are the official map packs (`MapPack001.rez`,
  `MapPack002.rez`), so the player needs only the discs. The scripts check
  every file they write against its SHA-256, so the result is the private
  archive's directory, byte for byte. Its last file, `SHA256SUMS`, lists
  every file of the archive and every file the scripts write (but
  `autoexec.cfg` and `Profiles/Default.prf`, which they write only once and
  the game rewrites); the scripts check the directory against it first and
  stop if a file of the archive is missing or changed, or a file is there
  that is neither the archive's nor one they or the game write (a release
  unpacked over another installation, before its first install). The
  one to give to other people.

`nolf2cmds.txt`, the engine's command file as the build writes it (the rez
stack, `custom/` last), is in the game directory and the private archive,
for `ext/tools/playtest.sh`. The launcher never reads it: it writes its own
`launchcmds.txt` on every Play. So the public archive has none.

`LICENSE_NOTES.md` says what each holds and under whose terms.

Nothing is installed or run from the discs. NOLF2's setup stores its files
compressed in InstallShield 6 cabinets that span both discs (`data1.hdr`,
`data1.cab` to `data3.cab`; only `Data/GAME.REZ` is a plain file).
`build/mkinstall.py` writes the scripts from the lists in `build/` only, and
needs no disc image and no retail game: `build/retail-files.txt` gives, for
each retail file, the ranges of the images that hold it as it is or as
InstallShield's compressed chunks (each a 16-bit length and a raw deflate
stream; a file split across two cabinets has a range on each disc), one
way per release (the cabinets lie at other offsets on the USA discs);
`build/retail-ranges.txt` gives the retail game DLLs that the build zeroes
inside the archives. A game directory built with the retail game is
checked against them: each file that the scripts write must be in it as
they write it. A script then needs no InstallShield or ISO 9660 code, only
an inflater: it recognises each image by its size and SHA-256, and writes
each of our files from its retail file, with the retail game DLLs inside
the archives as zeros. On Linux `python3`'s zlib inflates (bash and
coreutils do the rest); on Windows, PowerShell 5.1's .NET `DeflateStream`
(an MSZIP block's 32 KB of history goes in front of it as a stored deflate
block, as it takes no dictionary). An image is a plain `.iso`, a raw `.bin`
(or its `.cue`) or a `.zip` of one, converted to a temporary `.iso` first.
Redump has two dumps of the USA disc 2; the other, `(Alt)`, has the
cabinet at the same offset, and is recorded by its size and SHA-256
(`us2alt` in `build/retail-files.txt`).

The scripts also write `autoexec.cfg` and `Profiles/Default.prf`, the 1.3
update's shipped settings and default profile, but only if there are none:
the archive does not carry them, so that a newer release unpacked over an
installed game keeps the player's own. Every other file of ours is in the
archive at its own path, with its SHA-256 in `SHA256SUMS`. So to upgrade,
the player unpacks the new release over the installed game and does not
run the installer again (`INSTALL.md`).

`NOLF2_ARCHIVES` says which archives to write (default `private public`):
`make NOLF2_ARCHIVES=public` (or any variant target) writes only the
public one. `IMAGE_BUILD=0` makes the targets use the docker image as it
is instead of building it.

### GitHub Actions

`.github/workflows/ci.yml` builds the release game and all three variants
without the retail game (`make NODISCS=1 <target>`, `NOLF2_ARCHIVES=public`)
on every push to `master`, every pull request and on demand, each in a job
of its own named for its variant (`nolf2-legacy-release`,
`nolf2-legacy-debug`, `nolf2-modern-release`, `nolf2-modern-debug`), all
four at the same time (one failing still lets the others finish). The
runner has no disc image, no update, no SDK and no retail data, and fetches
none. The release build's job also runs `make progress-ci` (a function
recorded as byte-identical that stops matching fails the run). Each job
keeps its public archive as the run's artifact, the `.tar.gz` itself
rather than a zip around it. The private archives are never made there. A
first job, "prepare", writes the docker image's layer cache, which the
builds only read. The submodules are fetched over HTTPS at depth 1.

Pushing a tag `v*` (e.g. `v0.1.0-alpha`) runs it on the tag too, and once
all four builds pass, the job "release" makes a GitHub release of the tag
(a pre-release when the tag has a hyphen) with the modern build's public
archives attached, named for the tag: `nolf2src-<tag>.tar.gz` and
`nolf2src-debug-<tag>.tar.gz`, each repacked to unpack to a directory of
that name. The legacy build is not attached. A new release's text is
`.github/release_notes.md` (`{{TAG}}` and `{{REPO}}` filled in), followed
by GitHub's generated list of changes; a release of the tag made by hand
beforehand keeps its own text, and gets the archives added. A push to
`master` whose four builds pass moves the pre-release "nightly" to the
commit in the same way, with `nolf2src-nightly-<commit>.tar.gz` and
`nolf2src-debug-nightly-<commit>.tar.gz` and `.github/nightly_notes.md`
before the release notes. Its steps are the make targets above, so a run
can be reproduced locally:

```sh
git submodule update --init                 # ext/tools/, ext/toolchains/, ext/lithtools/, ext/ffmpeg
export NOLF2_ARCHIVES=public                # (CI: the image from its layer cache, IMAGE_BUILD=0)
make NODISCS=1 && make progress-ci
make NODISCS=1 debug && make NODISCS=1 modern && make NODISCS=1 modern-debug
ls out/*-public.tar.gz
```
