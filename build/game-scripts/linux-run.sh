#!/bin/sh
# linux-run.sh -- start No One Lives Forever 2 (built from source) with Wine,
# through NOLF2.exe: direct start in modern builds, the interactive launcher
# in legacy builds (built from src/Game/Launcher).
#
#   ./linux-run.sh [game args...]
#
# Modern builds start immediately using the same saved settings and wait
# until Lithtech.exe exits. Open NOLF2Launcher.exe in the same Wine
# prefix for the interactive launcher (Display and Options).
# Legacy builds: click "Play" and choose a detail setting on first run.
# The launcher writes launchcmds.txt and starts Lithtech.exe with it
# (`Lithtech.exe -cmdfile launchcmds.txt`); its Display and Options buttons
# set the renderer's resolution and the engine's options. Arguments are
# handed to the launcher, which passes them on to the engine after its own
# (later ones win), e.g.
#   ./linux-run.sh ++windowed 1                  a window, whatever Display says
#   ./linux-run.sh ++windowed 1 ++WindowMode 2   (modern build) a borderless
#                                                window over the whole desktop
#   ./linux-run.sh +DisableSound 1               no sound
#   ./linux-run.sh -gogame                       start the game at once,
#                                                without the launcher's window
#   ./linux-run.sh --help                        this text
#
# The modern build starts as it was last left (Options > Display, or the
# launcher's Display: full screen, a window or a borderless window, and the
# resolution). A fresh install, where the game has never run, starts in a
# window, the largest that fits the desktop (of the desktop's shape if one
# does); on a Steam Deck (SteamDeck=1, which Steam sets) full screen at
# 1280x800. The launcher chooses that, as it does on Windows. The legacy
# build always starts in a window (++windowed 1, before the arguments, so
# ./linux-run.sh ++windowed 0 still asks for full screen), as its Display
# has no window mode; the first time at the detail setting's resolution.
#
# Environment:
#   WINEPREFIX   the Wine prefix to use (default: $HOME/.wine-nolf2, created on
#                first run, so your own prefix is left alone)
#   WINE         the wine binary (default: wine)
#   WINEDEBUG    Wine's log channels (default: fixme-all, which silences
#                DirectMusic's chatter)
#
# The modern build's launcher needs nothing from the registry (it plays the
# game in its own directory, docs/MODERN.md M-L6, and keeps its settings
# under the user's key, M-L7). The legacy build's is the retail one, which
# reads what the retail installer left in the registry, and this script
# writes that into its Wine prefix, under HKLM\Software\Monolith
# Productions\No One Lives Forever 2\1.0:
#   * InstallDir: this directory (the launcher changes to it).
#   * UpdateNum, UpdateCommandLine1: the archives it adds after its own
#     (GAME.REZ, GAME2.REZ, GAMEDLL.REZ, SOUND.REZ, custom): the 1.3
#     update's, as its installer wrote -- and, after it, custom/ again,
#     holding the game DLLs built from source, so that the update's (zeroed)
#     retail DLLs cannot override them (later archives win).
#   * Disable Movies: on, with RAD's binkw32.dll, whose movies stall under
#     some Wine setups. (The modern build's own Bink player, on FFmpeg, plays
#     them.)
# No disc is needed: NOLF2's launcher only looks for one to install from.
# On the first run autoexec.cfg -- the game's settings, rewritten on every
# exit -- starts as a copy of the shipped one (autoexec.cfg.retail).
#
# Sound: the engine's own snddrv.dll plays through DirectSound, so it needs
# Wine's audio working on this machine (winecfg > Audio); +DisableSound 1
# runs without it. The music is DirectMusic, which Wine only partly
# implements; Microsoft's DirectMusic can be installed in the prefix:
#   WINEPREFIX=~/.wine-nolf2 winetricks dmband dmcompos dmime dmloader \
#       dmscript dmstyle dmsynth dmusic dmusic32 dswave gmdls
set -e
cd "$(dirname "$0")"
case "${1:-}" in
--help|-h) sed -n '2,/^set -e$/{/^set -e$/d;p}' "./${0##*/}" | sed 's/^# \{0,1\}//'; exit 0 ;;
esac
WINEPREFIX="${WINEPREFIX:-$HOME/.wine-nolf2}"
WINEDEBUG="${WINEDEBUG:-fixme-all}"
export WINEPREFIX WINEDEBUG
WINE="${WINE:-wine}"
command -v "$WINE" >/dev/null 2>&1 || { echo "linux-run.sh: '$WINE' not found -- install Wine (32-bit support needed)" >&2; exit 1; }
[ -f GAME.REZ ] || { echo "linux-run.sh: the game's data is not here yet -- run ./linux-install.sh first" >&2; exit 1; }

# The modern build: its own Bink player (MANIFEST.txt lists it as EXT).
MODERN=
grep -q '^EXT .*	binkw32\.dll$' MANIFEST.txt 2>/dev/null && MODERN=1

[ -f autoexec.cfg ] || cp autoexec.cfg.retail autoexec.cfg
mkdir -p Save
WINDOWED="++windowed 1"
[ -z "$MODERN" ] || WINDOWED=""

# a prefix to set up: make it now if it does not exist yet
[ -d "$WINEPREFIX/dosdevices" ] || "$WINE" wineboot -i >/dev/null 2>&1 || true
if [ -z "$MODERN" ]; then
    DIR="$("$WINE" winepath -w "$(pwd)" 2>/dev/null)"
    KEY='HKLM\Software\Monolith Productions\No One Lives Forever 2\1.0'
    # Both registry views: in a 64-bit prefix `wine reg` writes the 64-bit
    # one, while NOLF2.exe, a 32-bit program, reads HKLM\Software through the
    # 32-bit one (Wow6432Node). (A 32-bit prefix has one view; the /reg:64
    # write then fails, harmlessly.)
    reg() { "$WINE" reg add "$@" /reg:32 /f >/dev/null 2>&1
            "$WINE" reg add "$@" /reg:64 /f >/dev/null 2>&1 || true; }
    reg "$KEY" /v InstallDir         /t REG_SZ    /d "$DIR"
    reg "$KEY" /v NetRegionCode      /t REG_SZ    /d EN
    reg "$KEY" /v UpdateNum          /t REG_DWORD /d 2
    reg "$KEY" /v UpdateCommandLine1 /t REG_SZ    /d '-rez Update_v1x3.rez -rez custom'
    reg "$KEY" /v 'Disable Movies'   /t REG_DWORD /d 1
fi

exec "$WINE" NOLF2.exe $WINDOWED "$@"
