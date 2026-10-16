#!/bin/sh
# linux-server.sh -- run a No One Lives Forever 2 dedicated server
# (NOLF2Srv.exe, built from source) with Wine.
#
#   ./linux-server.sh [options] [NOLF2Srv.exe args...]
#
# Options:
#   --profile <name>   host with the server settings of the player profile
#                      <name> (Profiles/<name>.txt and its folder): what the
#                      game's Multiplayer > Host screens saved for it -- game
#                      type, missions, players, port, LAN only, password.
#                      Without it the server takes the only profile there
#                      is, or asks which one (on a display).
#   --headless         run without a display: under xvfb-run, a virtual X
#                      server (the default when $DISPLAY is not set)
#   --help             this text
# Anything else is handed to NOLF2Srv.exe: `-port <port>` and `-name
# <session name>` override the profile's, e.g.
#   ./linux-server.sh --profile Player -name "My server" -port 27888
#
# Environment:
#   WINEPREFIX   the Wine prefix to use (default: $HOME/.wine-nolf2, the one
#                linux-run.sh uses)
#   WINE         the wine binary (default: wine)
#   WINEDEBUG    Wine's log channels (default: -all)
#
# The server runs in this directory and writes its console to nolf2srv.log
# (emptied each start; this script passes +errorlog 1 +alwaysflushlog 1,
# which the modern build does by itself). The release build's NOLF2Srv.exe
# needs the registry key the retail installer left; this script writes it
# into the prefix, as linux-run.sh does. The server answers on UDP
# port 27888 (or the profile's, or -port) -- open it in a firewall for
# players on other machines. It runs until Stop Server is clicked, or the
# process is ended (Ctrl+C here).
set -e
cd "$(dirname "$0")"

PROFILE=
HEADLESS=
case "${DISPLAY:-}" in "") HEADLESS=1 ;; esac
while [ $# -gt 0 ]; do
    case "$1" in
        --profile)  PROFILE="${2:?--profile needs a profile name}"; shift ;;
        --headless) HEADLESS=1 ;;
        --help|-h)  sed -n '2,/^set -e$/{/^set -e$/d;p}' "./${0##*/}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)          break ;;
    esac
    shift
done

WINEPREFIX="${WINEPREFIX:-$HOME/.wine-nolf2}"
WINEDEBUG="${WINEDEBUG:--all}"
export WINEPREFIX WINEDEBUG
WINE="${WINE:-wine}"
command -v "$WINE" >/dev/null 2>&1 || { echo "linux-server.sh: '$WINE' not found -- install Wine (32-bit support needed)" >&2; exit 1; }

# The profile: named, or the only one there is. Without a display nobody can
# answer NOLF2Srv.exe's question which one, or its message that there is none.
NPROF=$(ls Profiles/*.txt 2>/dev/null | wc -l)
if [ -n "$PROFILE" ]; then
    [ -f "Profiles/$PROFILE.txt" ] || { echo "linux-server.sh: no profile Profiles/$PROFILE.txt" >&2; exit 1; }
elif [ "$NPROF" = 0 ]; then
    echo "linux-server.sh: no profile in Profiles/ -- set up a server in the game (Multiplayer > Host)," >&2
    echo "                 which saves it in your profile, or copy one here (docs/INSTALL.md)" >&2
    exit 1
elif [ "$NPROF" != 1 ] && [ -n "$HEADLESS" ]; then
    echo "linux-server.sh: several profiles -- name one with --profile:" >&2
    ls Profiles/*.txt | sed 's|^Profiles/||; s|\.txt$||; s|^|    |' >&2
    exit 1
fi
[ -n "$PROFILE" ] && set -- -profile "$PROFILE" "$@"

# a prefix to set up: make it now if it does not exist yet
[ -d "$WINEPREFIX/dosdevices" ] || "$WINE" wineboot -i >/dev/null 2>&1 || true
# The release build's server stops without the installer's key, and takes
# the 1.3 update's archive (and custom/ again after it) from its values; the
# modern build's needs none (docs/MODERN.md, M-G50).
if ! grep -q '^EXT .*	binkw32\.dll$' MANIFEST.txt 2>/dev/null; then
    DIR="$("$WINE" winepath -w "$(pwd)" 2>/dev/null)"
    KEY='HKLM\Software\Monolith Productions\No One Lives Forever 2\1.0'
    reg() { "$WINE" reg add "$@" /reg:32 /f >/dev/null 2>&1
            "$WINE" reg add "$@" /reg:64 /f >/dev/null 2>&1 || true; }
    reg "$KEY" /v InstallDir         /t REG_SZ    /d "$DIR"
    reg "$KEY" /v UpdateNum          /t REG_DWORD /d 2
    reg "$KEY" /v UpdateCommandLine1 /t REG_SZ    /d '-rez Update_v1x3.rez -rez custom'
fi

if [ -n "$HEADLESS" ]; then
    command -v xvfb-run >/dev/null 2>&1 || { echo "linux-server.sh: no display, and no xvfb-run (install xvfb) to make one" >&2; exit 1; }
    # The wineserver the setup above started has no display, and a program
    # started under it would get no window driver: let it end first, so the
    # server's own starts on the virtual display.
    "${WINESERVER:-wineserver}" -w 2>/dev/null || true
    exec xvfb-run -a "$WINE" NOLF2Srv.exe +errorlog 1 +alwaysflushlog 1 "$@"
fi
exec "$WINE" NOLF2Srv.exe +errorlog 1 +alwaysflushlog 1 "$@"
