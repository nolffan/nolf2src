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
# Needs: the toolchain (toolchains/, see toolchains/README.md), Wine (the
# build container has it), and the retail game, NOLF2 (Europe) with the
# English 1.3 update, as the rez/ submodule installs it
# (rez/games/nolf2-eu-1.3/, build/retail.sh). It only reads that directory.
#
# The steps, in order:
#   1. resources          the game's data from the retail game: the .rez
#                         archives (with the retail game DLLs inside them
#                         zeroed), the movies, the shipped autoexec.cfg and
#                         default profile. No binary.
#   2. third-party runtime  Bink (binkw32.dll) and the Microsoft C++ and MFC
#                         runtime DLLs, from the retail game: licensed
#                         binaries with no source. The modern build
#                         (NOLF2_MIDDLEWARE=open, set by build/variant.sh)
#                         takes only the Microsoft runtime from the retail
#                         game, and our own binkw32.dll -- a Bink player on
#                         FFmpeg, built from src/modern/binkw32/ and the
#                         ext/ffmpeg submodule by build/ext.sh.
#   2b. Jupiter SDK source  WONAPI and CServerDir_Titan, which ServerDir.dll
#                         is built from and Monolith's release lacks: from
#                         the LithTech Jupiter SDK, as rez/ fetches it
#                         (build/jupiter.sh; `make` fetches it once), into
#                         src/Game/Libs/ (tools/jupitersrc.py; not committed).
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
#                         ltmsg.dsw), the engine's message strings.
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
#                         (tools/playtest.sh: the menus, a new game, play,
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
#                         player's own disc images and 1.3 update
#                         (build/package.sh).
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
RETAIL="$(retail_dir)"
retail_verify
jupiter_verify
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

step "1. resources: game data from $RETAIL -> $OUT"
python3 tools/retailextract.py resources "$RETAIL" "$OUT"
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
    step "2. open runtime: our Bink player on FFmpeg (build/ext.sh); the Microsoft runtime from $RETAIL"
    bash build/ext.sh
    python3 tools/retailextract.py thirdparty "$RETAIL" "$OUT" open
    python3 tools/retailextract.py openruntime "${NOLF2_EXT_OUT:-out/ext}" "$OUT"
else
    step "2. THIRD-PARTY RUNTIME: Bink and the Microsoft runtime from $RETAIL"
    python3 tools/retailextract.py thirdparty "$RETAIL" "$OUT"
fi

step "2b. Jupiter SDK source: WONAPI, CServerDir_Titan -> src/Game/Libs/"
python3 tools/jupitersrc.py "$(jupiter_source)" src

step "3. compile: Monolith's workspace (build/compile.sh: build/build.mk, ${NOLF2SRC_JOBS:-$(nproc)} jobs)"
bash build/compile.sh all
for ((i = 0; i < ${#BUILT[@]}; i += 2)); do
    [ -f "${BUILT[i]}" ] || { echo "error: ${BUILT[i]} was not built" >&2; exit 1; }
done

step "4. assemble: the built binaries -> $OUT"
for ((i = 0; i < ${#BUILT[@]}; i += 2)); do
    cp "${BUILT[i]}" "$OUT/${BUILT[i+1]}"
    printf 'built %s\t%s\n' "${BUILT[i]}" "${BUILT[i+1]}" >> "$OUT/MANIFEST.txt"
    echo "   ${BUILT[i+1]}  <-  ${BUILT[i]}"
done
# one row per file: the manifest is rewritten by the next step's tool
python3 - "$OUT/MANIFEST.txt" <<'PY'
import sys
p = sys.argv[1]
rows = {}
for line in open(p).read().splitlines():
    if "\t" in line and not line.startswith("#"):
        origin, path = line.split("\t", 1)
        rows[path] = origin
with open(p, "w") as f:
    f.write("# origin<TAB>path, one row per file build/all.sh put here\n")
    for path in sorted(rows, key=str.lower):
        f.write(f"{rows[path]}\t{path}\n")
PY

step "5. audit: every PE file in $OUT"
python3 tools/retailextract.py audit "$OUT"

# (NOLF2_PACKAGE=0 skips it: build/variant.sh packages its game directory
# itself)
if [ "${NOLF2_PACKAGE:-1}" = 1 ]; then
    step "6. package: $OUT -> $OUT-private.tar.gz, -public.tar.gz"
    bash "$REPO/build/package.sh" "$OUT"
fi

step "done: $OUT ($(( $(date +%s) - T0 ))s) -- play it with $OUT/linux-run.sh"
