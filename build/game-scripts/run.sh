#!/bin/sh
# run.sh -- start No One Lives Forever 2 (built from source) with Wine.
#
#   ./run.sh [options] [engine args...]
#
# Options:
#   --fullscreen          full screen (default: a window)
#   --windowed            a window (the default)
#   --res WxH             the window / screen mode to start in (default
#                         640x480); the menus may still draw at 640x480 inside
#                         it until a resolution is chosen in Options > Display
#   --world <path>        go straight into a level, e.g.
#                         --world 'Worlds\RetailSinglePlayer\C01S01'
#   --help                this text
# Anything else is handed to the engine unchanged (e.g. +DisableSound 1).
#
# Environment:
#   WINEPREFIX   the Wine prefix to use (default: $HOME/.wine-nolf2, created on
#                first run, so your own prefix is left alone)
#   WINE         the wine binary (default: wine)
#   WINEDEBUG    Wine's log channels (default: fixme-all, which silences
#                DirectMusic's chatter)
#
# This does what the retail NOLF2.exe launcher does: it starts
# `Lithtech.exe -cmdfile <command file>` from the game directory. The command
# file (run-cmds.txt, rewritten every run) is nolf2cmds.txt's rez stack plus
# the options above. On the first run autoexec.cfg -- the game's settings,
# rewritten on every exit -- starts as a copy of the shipped one
# (autoexec.cfg.retail).
#
# Sound: the engine's own snddrv.dll plays through DirectSound, so it needs
# Wine's audio working on this machine (winecfg > Audio); +DisableSound 1
# runs without it. The music is DirectMusic, which Wine only partly
# implements; Microsoft's DirectMusic can be installed in the prefix:
#   WINEPREFIX=~/.wine-nolf2 winetricks dmband dmcompos dmime dmloader \
#       dmscript dmstyle dmsynth dmusic dmusic32 dswave gmdls
# The intro movies are off (+DisableMovies 1) with RAD's binkw32.dll, whose
# movies stall under some Wine setups; on in the modern build, whose own
# Bink player (on FFmpeg; MANIFEST.txt lists it as EXT) plays them.
set -e
cd "$(dirname "$0")"

WINDOWED=1
RES=640x480
WORLD=
EXTRA=
while [ $# -gt 0 ]; do
    case "$1" in
        --fullscreen) WINDOWED=0 ;;
        --windowed)   WINDOWED=1 ;;
        --res)        RES="${2:?--res needs WxH}"; shift ;;
        --world)      WORLD="${2:?--world needs a world path}"; shift ;;
        --help|-h)    sed -n '2,40p' "./${0##*/}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)            EXTRA="$EXTRA $1" ;;
    esac
    shift
done
MOVIES=1
grep -q '^EXT .*	binkw32\.dll$' MANIFEST.txt 2>/dev/null && MOVIES=0
W="${RES%x*}"; H="${RES#*x}"
case "$W$H" in *[!0-9]*|"") echo "run.sh: --res wants WxH, e.g. 1024x768" >&2; exit 2 ;; esac

WINEPREFIX="${WINEPREFIX:-$HOME/.wine-nolf2}"
WINEDEBUG="${WINEDEBUG:-fixme-all}"
export WINEPREFIX WINEDEBUG
WINE="${WINE:-wine}"
command -v "$WINE" >/dev/null 2>&1 || { echo "run.sh: '$WINE' not found -- install Wine (32-bit support needed)" >&2; exit 1; }

[ -f autoexec.cfg ] || cp autoexec.cfg.retail autoexec.cfg
mkdir -p Save

# The rez stack from nolf2cmds.txt (its -rez arguments; build/all.sh wrote it),
# then our settings: later arguments override earlier ones.
REZ=$(tr -d '\r' < nolf2cmds.txt | tr ' ' '\n' | awk '$0=="-rez"{getline n; printf "-rez %s ", n}')
{
    printf '%s++screenwidth %s ++screenheight %s ++bitdepth 32 ++windowed %s +DisableMovies %s' \
        "$REZ" "$W" "$H" "$WINDOWED" "$MOVIES"
    [ -n "$WORLD" ] && printf ' +runworld %s' "$WORLD"
    printf '%s\r\n' "$EXTRA"
} > run-cmds.txt

exec "$WINE" Lithtech.exe -cmdfile run-cmds.txt
