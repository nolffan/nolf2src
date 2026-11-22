#!/usr/bin/env bash
# THE build: a runnable No One Lives Forever 2 in out/nolf2-legacy-release/,
# with the game compiled from Monolith's source release and the data taken
# from the retail game.
#
#   make                    (on the host: builds the docker image, installs
#                            and checks the retail game, runs this in a
#                            container)
#   build/all.sh            (inside the build container, e.g. `make shell`)
#
# Needs: the toolchain (ext/toolchains/, see ext/toolchains/README.md), Wine (the
# build container has it), the retail game, NOLF2 (Europe) with the English
# 1.3 update, as build/discs.py installs it from your two disc images and
# the update's installer (out/retail/nolf2-eu-1.3/, build/retail.sh), and
# the LithTech Jupiter SDK's WONAPI source, from your image of its CD the
# same way (out/retail/lithtech-jupiter-51/, build/jupiter.sh). It only
# reads those directories.
#
# NOLF2_NODISCS=1 builds without the retail game and without the SDK (the
# CI build, `make NODISCS=1`, for any variant). Every binary is the same as
# with them: the art they are compiled with is committed (assets/art/), and
# so is the release build's ServerDir.dll (assets/serverdir/), which is used
# in place of one compiled from the SDK's source. But step 1 copies no game
# data and step 2 no Bink or Microsoft runtime: both write only the
# manifest's rows of those files (from build/retail-files.txt and
# build/retail-ranges.txt). The game directory is out/<name>-nodiscs/, with
# NOT-PLAYABLE.txt in it: without the discs' .rez archives it does not
# play. Step 6 makes only its public archive, out/<name>-public.tar.gz,
# which is the playable form: unpacked, its install scripts copy the game
# data from the player's discs into it (build/mkinstall.py). It is the same
# archive as a build with the retail game makes (but the link time in each
# binary).
#
# The steps, in order:
#   1. resources          the game's data from the retail game: the .rez
#                         archives of the discs (with the retail game DLLs
#                         inside them zeroed) and the movies. No binary.
#   1b. assets            the 1.3 update's data and the two map packs, from
#                         assets/: nolf2src.rez, MapPack001.rez and
#                         MapPack002.rez (packed by lithrez), the shipped
#                         autoexec.cfg and default profile.
#   2. third-party runtime  Bink (binkw32.dll) and the Microsoft C++ and MFC
#                         runtime DLLs, from the retail game: licensed
#                         binaries with no source. The modern build
#                         (NOLF2_MIDDLEWARE=open, set by build/variant.sh)
#                         takes only the Microsoft runtime from the retail
#                         game, and our own binkw32.dll -- a Bink player on
#                         FFmpeg, built from src/modern/binkw32/ and the
#                         ext/ffmpeg submodule by build/ext.sh.
#   2b. Jupiter SDK source  WONAPI, the library ServerDir.dll is built with
#                         and Monolith's release lacks: from the LithTech
#                         Jupiter SDK, as build/discs.py installs it from
#                         your image of its CD (build/jupiter.sh; `make sdk`,
#                         which every build runs), into src/Game/Libs/
#                         (ext/tools/jupitersrc.py; not committed). Without
#                         the SDK (NODISCS=1), the committed
#                         assets/serverdir/ServerDir.dll goes where the
#                         compile puts its own, and the compile leaves
#                         ServerDir.dll out.
#   2c. engine art        the icon lithtech.rc compiles into Lithtech.exe
#                         (IDR_MAINFRAME, five images): the retail icon,
#                         committed in assets/art/lithtech/ (made from the
#                         retail Lithtech.exe's resources by `make art`, and
#                         checked against them in every build with the
#                         retail game), copied into
#                         src/Engine/runtime/winbuild/lithtech/res/. Its
#                         other binary resources, the help cursor and four
#                         bitmaps, are MFC's, from the toolchain's afxres.rc.
#   3. compile            every project of Monolith's workspace the game
#                         needs, by build/build.mk, all at once (one job per
#                         CPU; NOLF2SRC_JOBS=<n> to change it) and only what
#                         changed since the last build (`make clean` starts
#                         from nothing): the libraries, CShell.dll,
#                         Object.lto, ClientFx.fxd, CRes.dll, SRes.dll and
#                         the dedicated server NOLF2Srv.exe, Final
#                         configuration; ServerDir.dll
#                         (src/Game/Libs/ServerDir/ServerDir.dsw), the
#                         sound driver SndDrv.dll (src/Engine/snddrv/
#                         snddrv.dsw), the engine, Lithtech.exe and
#                         server.dll (src/Engine/runtime/winbuild/
#                         Engine.dsw), and ltmsg.dll (src/Engine/ltmsg/
#                         ltmsg.dsw), the engine's message strings. The
#                         release build's ServerDir.dll is then checked
#                         against assets/serverdir/ (build/serverdir.py;
#                         make serverdir writes it again).
#   4. assemble           the built binaries into out/nolf2-legacy-release/: the
#                         game DLLs in the custom/ rez directory, last in the
#                         rez stack (nolf2cmds.txt); the engine (Lithtech.exe,
#                         server.dll, snddrv.dll, ServerDir.dll, ltmsg.dll),
#                         the dedicated server and the launcher NOLF2.exe
#                         (linux-run.sh plays through it) in the game's
#                         root. Every
#                         binary of the game is then built here but the
#                         third-party runtime of step 2. Each built engine
#                         binary was shown to work in the game under Wine
#                         (ext/tools/playtest.sh: the menus, a new game, play,
#                         quicksave and quickload; Internet multiplayer
#                         reaching the directory-server request, which fails
#                         as retail's does without sierraup.cfg).
#   5. audit              every PE file in out/nolf2-legacy-release/ listed with
#                         its origin; the build fails if any is unaccounted
#                         for or if a .rez archive still holds one.
#   6. package            out/nolf2-legacy-release-private.tar.gz: the game
#                         directory as one file (unpack, then ./linux-run.sh
#                         -- see its header; Wine needed there), and
#                         -public.tar.gz: the same without the retail game's
#                         files, which its install scripts copy out of the
#                         player's own disc images (build/package.sh).
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Wine and the toolchain live in the build container: on the host, use make.
if ! command -v wine >/dev/null 2>&1; then
    echo "error: no wine here -- run \`make\` from the repository root (it runs this" >&2
    echo "       script in the build container), or run it inside \`make shell\`." >&2
    exit 1
fi
export WINEDEBUG=-all

cd "$REPO"
source build/retail.sh
source build/jupiter.sh
OUT="${NOLF2_GAME_OUT:-out/nolf2-legacy-release}"
NODISCS=
if [ "${NOLF2_NODISCS:-0}" = 1 ]; then
    NODISCS=1
    RETAIL=-
    # not the game directory of a real build: this one does not play
    # (build/variant.sh gives its own, out/<name>-nodiscs)
    OUT="${NOLF2_GAME_OUT:-out/nolf2-legacy-release-nodiscs}"
else
    RETAIL="$(retail_dir)"
    retail_verify
    jupiter_verify
fi
T0=$(date +%s)
step() { echo; echo "######## $* ($(( $(date +%s) - T0 ))s)"; }
B=src/Game/built/Final
BUILT=(
    "$B/ClientShellDLL/TO2/CShell.dll"  custom/cshell.dll
    "$B/ObjectDll/TO2/Object.lto"       custom/object.lto
    "$B/ClientFxDll/ClientFx.fxd"       custom/clientfx.fxd
    "$B/ClientRes/TO2/CRes.dll"         custom/cres.dll
    "$B/ServerRes/TO2/SRes.dll"         custom/sres.dll
    "$B/ServerApp/NOLF2Srv.exe"         NOLF2Srv.exe
    "$B/Launcher/NOLF2.exe"             NOLF2.exe
    src/Engine/built/Final/Lithtech/Lithtech.exe  Lithtech.exe
    src/Engine/built/Final/server/server.dll      server.dll
    src/Engine/built/Final/snddrv/SndDrv.dll      snddrv.dll
    src/Game/built/Final/libs/ServerDir/ServerDir.dll  ServerDir.dll
    src/Engine/built/Final/ltmsg/ltmsg.dll        ltmsg.dll
)
case "${NOLF2SRC_CFLAGS:-}" in
    *NOLF2SRC_MODERN*) BUILT+=("$B/Launcher/NOLF2Launcher.exe" NOLF2Launcher.exe) ;;
esac

if [ -n "$NODISCS" ]; then
    step "1. resources: without the retail game, only the manifest rows of its data -> $OUT"
    mkdir -p "$OUT"
    cat > "$OUT/NOT-PLAYABLE.txt" <<EOF
This directory was built without the retail game (NODISCS=1). It has no
game data from the discs (no .rez archives of the discs, no movies, no Bink
and no Microsoft runtime): it does not play. The playable form is its
public archive, $(basename "$OUT" -nodiscs)-public.tar.gz beside it: unpack it
into an empty directory, then run its install script with your two disc
images (docs/INSTALL.md).
EOF
else
    step "1. resources: game data from $RETAIL -> $OUT"
    rm -f "$OUT/NOT-PLAYABLE.txt"
fi
python3 build/retailextract.py resources "$RETAIL" "$OUT"

step "1b. assets: the 1.3 update's data and the two map packs (assets/) -> $OUT/nolf2src.rez, MapPack001.rez, MapPack002.rez and the shipped settings"
# The 1.3 update's data ships with the release (assets/README.md): what its
# Update_v1x3.rez carries besides the game DLLs, packed into nolf2src.rez by
# lithtools' lithrez (build/lithrez.sh) with a fixed time, so the archive is
# the same bytes on every build; and the settings and default profile it
# installs. build/retailextract.py keeps the retail Update_v1x3.rez out.
# The official map packs (assets/README.md) are packed into the archives
# their installers installed, MapPack001.rez and MapPack002.rez, as NOLF2's
# LithRez wrote them (--compat 1.10: no resource IDs) and with each
# original's time: the same files as the originals, every time.
bash build/lithrez.sh
rm -f "$OUT/Update_v1x3.rez"                 # the retail archive, before assets/
out/lithrez/lithrez c "$OUT/nolf2src.rez.part" assets/rez --time 1044489600 >/dev/null
mv "$OUT/nolf2src.rez.part" "$OUT/nolf2src.rez"
for mp in 001:1037757884 002:1044088336; do
    out/lithrez/lithrez c "$OUT/MapPack${mp%%:*}.rez.part" "assets/mappack${mp%%:*}" \
        --compat 1.10 --time "${mp#*:}" >/dev/null
    mv "$OUT/MapPack${mp%%:*}.rez.part" "$OUT/MapPack${mp%%:*}.rez"
done
cp assets/game/autoexec.cfg "$OUT/autoexec.cfg.retail"
cp assets/game/Profiles/Default.prf "$OUT/Default.prf.retail"
printf 'asset assets/rez (lithrez)\tnolf2src.rez\n' >> "$OUT/MANIFEST.txt"
printf 'asset assets/mappack001 (lithrez)\tMapPack001.rez\n' >> "$OUT/MANIFEST.txt"
printf 'asset assets/mappack002 (lithrez)\tMapPack002.rez\n' >> "$OUT/MANIFEST.txt"
printf 'asset assets/game/autoexec.cfg\tautoexec.cfg.retail\n' >> "$OUT/MANIFEST.txt"
printf 'asset assets/game/Profiles/Default.prf\tDefault.prf.retail\n' >> "$OUT/MANIFEST.txt"
echo "   nolf2src.rez  <-  assets/rez/ ($(find assets/rez -type f | wc -l) files)"
echo "   MapPack001.rez  <-  assets/mappack001/ ($(find assets/mappack001 -type f | wc -l) files)"
echo "   MapPack002.rez  <-  assets/mappack002/ ($(find assets/mappack002 -type f | wc -l) files)"

# autoexec.cfg and the default profile start as the shipped ones (the game
# rewrites them); a rebuild keeps the player's.
[ -f "$OUT/autoexec.cfg" ] || cp "$OUT/autoexec.cfg.retail" "$OUT/autoexec.cfg"
mkdir -p "$OUT/Save" "$OUT/custom" "$OUT/Profiles"
[ -f "$OUT/Profiles/Default.prf" ] || cp "$OUT/Default.prf.retail" "$OUT/Profiles/Default.prf"
bash build/nolf2cmds.sh > "$OUT/nolf2cmds.txt"
# linux-run.sh: start the game with the host's Wine, through our NOLF2.exe
# (build/game-scripts/; usage in its header). On Windows the launcher,
# NOLF2.exe, is the way in.
rm -f "$OUT/run.sh" "$OUT/run-launcher.sh"   # their names before the linux- prefix
rm -f "$OUT/windows-run.bat"                 # the legacy build's, no longer made
rm -f "$OUT/linux-run-launcher.sh"           # linux-run.sh's name before it replaced
                                             # the launcher-less script
cp build/game-scripts/linux-run.sh "$OUT/"
chmod +x "$OUT/linux-run.sh"
# linux-server.sh: a dedicated server, NOLF2Srv.exe, with the host's Wine
# (headless under xvfb-run; usage in its header)
cp build/game-scripts/linux-server.sh "$OUT/" && chmod +x "$OUT/linux-server.sh"

if [ "${NOLF2_MIDDLEWARE:-retail}" = open ]; then
    if [ -n "$NODISCS" ]; then
        step "2. open runtime: our Bink player on FFmpeg (build/ext.sh); without the retail game, only the manifest rows of the Microsoft runtime"
    else
        step "2. open runtime: our Bink player on FFmpeg (build/ext.sh); the Microsoft runtime from $RETAIL"
    fi
    bash build/ext.sh
    python3 build/retailextract.py thirdparty "$RETAIL" "$OUT" open
    python3 build/retailextract.py openruntime "${NOLF2_EXT_OUT:-out/ext}" "$OUT"
else
    if [ -n "$NODISCS" ]; then
        step "2. third-party runtime: without the retail game, only the manifest rows of Bink and the Microsoft runtime"
    else
        step "2. THIRD-PARTY RUNTIME: Bink and the Microsoft runtime from $RETAIL"
    fi
    python3 build/retailextract.py thirdparty "$RETAIL" "$OUT"
fi

SERVERDIR_BUILT=src/Game/built/Final/libs/ServerDir/ServerDir.dll
if [ -n "$NODISCS" ]; then
    step "2b. no Jupiter SDK: the committed ServerDir.dll, assets/serverdir/ -> $(dirname "$SERVERDIR_BUILT")/"
    # where the compile puts its own (build/build.mk then leaves it out), so
    # that make progress-ci finds it there with its link map; without the
    # compile's command file beside it, a later build with the SDK makes it
    # again
    export NOLF2SRC_SERVERDIR=prebuilt
    python3 build/serverdir.py install "$SERVERDIR_BUILT"
else
    step "2b. Jupiter SDK source: WONAPI -> src/Game/Libs/"
    python3 ext/tools/jupitersrc.py "$(jupiter_source)" src
fi

step "2c. engine art: the retail icon, assets/art/lithtech/ -> src/Engine/runtime/winbuild/lithtech/res/"
# (with the retail game: first checked against the retail Lithtech.exe's
# resources, as make art-check does)
[ -n "$NODISCS" ] || python3 build/retailextract.py art check "$RETAIL"
python3 build/retailextract.py art install

step "3. compile: Monolith's workspace (build/compile.sh: build/build.mk, ${NOLF2SRC_JOBS:-$(nproc)} jobs)"
bash build/compile.sh all
for ((i = 0; i < ${#BUILT[@]}; i += 2)); do
    [ -f "${BUILT[i]}" ] || { echo "error: ${BUILT[i]} was not built" >&2; exit 1; }
done
# The release build's ServerDir.dll, compiled from the SDK's source, must be
# the committed one that a build without the SDK uses (but its link time).
if [ -z "$NODISCS" ] && [ -z "${NOLF2SRC_CFLAGS:-}" ]; then
    python3 build/serverdir.py check "$SERVERDIR_BUILT"
fi

step "4. assemble: the built binaries -> $OUT"
for ((i = 0; i < ${#BUILT[@]}; i += 2)); do
    cp "${BUILT[i]}" "$OUT/${BUILT[i+1]}"
    printf 'built %s\t%s\n' "${BUILT[i]}" "${BUILT[i+1]}" >> "$OUT/MANIFEST.txt"
    echo "   ${BUILT[i+1]}  <-  ${BUILT[i]}"
done
# one row per file: the manifest is rewritten by the next step's tool
python3 - "$OUT/MANIFEST.txt" <<'PY'
import os, sys
p = sys.argv[1]
d = os.path.dirname(p)
# (a directory built without the retail game has the rows of the discs'
# files, but not the files: build/mkinstall.py reads them)
nodiscs = os.path.exists(os.path.join(d, "NOT-PLAYABLE.txt"))
rows = {}
for line in open(p).read().splitlines():
    if "\t" in line and not line.startswith("#"):
        origin, path = line.split("\t", 1)
        retail = origin.startswith(("data nolf2-eu-1.3:", "THIRD-PARTY nolf2-eu-1.3:"))
        # a file an older build put here and this one removed
        if os.path.exists(os.path.join(d, path)) or nodiscs and retail:
            rows[path] = origin
with open(p, "w") as f:
    f.write("# origin<TAB>path, one row per file build/all.sh put here\n")
    for path in sorted(rows, key=str.lower):
        f.write(f"{rows[path]}\t{path}\n")
PY

step "5. audit: every PE file in $OUT"
python3 build/retailextract.py audit "$OUT"

# (NOLF2_PACKAGE=0 skips it: build/variant.sh packages its game directory
# itself)
if [ "${NOLF2_PACKAGE:-1}" = 1 ] && [ -n "$NODISCS" ]; then
    step "6. package: $OUT -> $(dirname "$OUT")/$(basename "$OUT" -nodiscs)-public.tar.gz (no private archive without the retail game)"
    bash "$REPO/build/package.sh" "$OUT" "$(basename "$OUT" -nodiscs)"
elif [ "${NOLF2_PACKAGE:-1}" = 1 ]; then
    step "6. package: $OUT -> $OUT-private.tar.gz, -public.tar.gz"
    bash "$REPO/build/package.sh" "$OUT"
fi

if [ -n "$NODISCS" ]; then
    step "done: $OUT ($(( $(date +%s) - T0 ))s) -- built without the retail game: it does not play (NOT-PLAYABLE.txt); its public archive, installed from the discs, does; check the build with make progress-ci"
else
    step "done: $OUT ($(( $(date +%s) - T0 ))s) -- play it with $OUT/linux-run.sh"
fi
