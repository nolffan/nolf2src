#!/bin/sh
# linux-run-launcher.sh -- start No One Lives Forever 2 through its launcher,
# NOLF2.exe (ours, built from src/Game/Launcher), the way the retail install
# does.
#
#   ./linux-run-launcher.sh [--fullscreen] [launcher args...]
#
# Click "Play" (the first time, the launcher asks for a detail setting
# first). The launcher writes launchcmds.txt and starts Lithtech.exe with it
# (`Lithtech.exe -cmdfile launchcmds.txt`). ./linux-run.sh skips the
# launcher and has more options; use it if this one gives you trouble. Arguments are the
# launcher's: it hands what it does not know to the engine (e.g.
# +DisableSound 1), and -gogame starts the game at once, without the
# launcher's window.
#
# The launcher reads what the retail installer left in the registry, and
# this script writes it into its Wine prefix, under
# HKLM\Software\Monolith Productions\No One Lives Forever 2\1.0 (same
# environment variables as linux-run.sh, plus WINESERVER, default wineserver;
# default prefix $HOME/.wine-nolf2):
#   * InstallDir: this directory (the launcher changes to it).
#   * UpdateNum, UpdateCommandLine1: the archives it adds after its own
#     (GAME.REZ, GAME2.REZ, GAMEDLL.REZ, SOUND.REZ, custom): the 1.3
#     update's, as its installer wrote -- and, after it, custom/ again,
#     holding the game DLLs built from source, so that the update's (zeroed)
#     retail DLLs cannot override them (later archives win; nolf2cmds.txt
#     has the same order).
#   * Disable Movies: on with RAD's binkw32.dll, whose movies stall under
#     some Wine setups; off in the modern build, whose own Bink player plays
#     them (MANIFEST.txt lists it as EXT).
# No disc is needed: NOLF2's launcher only looks for one to install from.
# The game starts in a window (++windowed 1; --fullscreen leaves it out),
# at the resolution the launcher's Display dialog or detail setting picks.
set -e
cd "$(dirname "$0")"
WINEPREFIX="${WINEPREFIX:-$HOME/.wine-nolf2}"
WINEDEBUG="${WINEDEBUG:-fixme-all}"
export WINEPREFIX WINEDEBUG
WINE="${WINE:-wine}"
command -v "$WINE" >/dev/null 2>&1 || { echo "linux-run-launcher.sh: '$WINE' not found -- install Wine (32-bit support needed)" >&2; exit 1; }

WINDOWED="++windowed 1"
if [ "${1:-}" = --fullscreen ]; then WINDOWED=""; shift; fi

[ -f autoexec.cfg ] || cp autoexec.cfg.retail autoexec.cfg
mkdir -p Save

MOVIES_OFF=1
grep -q '^EXT .*	binkw32\.dll$' MANIFEST.txt 2>/dev/null && MOVIES_OFF=0

# a prefix to set up: make it now if it does not exist yet
[ -d "$WINEPREFIX/dosdevices" ] || "$WINE" wineboot -i >/dev/null 2>&1 || true
DIR="$("$WINE" winepath -w "$(pwd)" 2>/dev/null)"
KEY='HKLM\Software\Monolith Productions\No One Lives Forever 2\1.0'
# Both registry views: in a 64-bit prefix `wine reg` writes the 64-bit one,
# while NOLF2.exe, a 32-bit program, reads HKLM\Software through the 32-bit
# one (Wow6432Node). (A 32-bit prefix has one view; the /reg:64 write then
# fails, harmlessly.)
reg() { "$WINE" reg add "$@" /reg:32 /f >/dev/null 2>&1
        "$WINE" reg add "$@" /reg:64 /f >/dev/null 2>&1 || true; }
reg "$KEY" /v InstallDir         /t REG_SZ    /d "$DIR"
reg "$KEY" /v NetRegionCode      /t REG_SZ    /d EN
reg "$KEY" /v UpdateNum          /t REG_DWORD /d 2
reg "$KEY" /v UpdateCommandLine1 /t REG_SZ    /d '-rez Update_v1x3.rez -rez custom'
reg "$KEY" /v 'Disable Movies'   /t REG_DWORD /d $MOVIES_OFF

exec "$WINE" NOLF2.exe $WINDOWED "$@"
