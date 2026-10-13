#!/usr/bin/env bash
# mptest.sh -- the multiplayer runtime test: does a client join a dedicated
# server over UDP and get into its game?
#
#   tools/mptest.sh [server.dll] [Lithtech.exe] [seconds] [gamedir]
#
# server.dll:   the dedicated server's engine (default: ours,
#               src/Engine/built/Final/server/server.dll;
#               out/reference/server.dll is retail's, the protocol's control)
# Lithtech.exe: the client's engine (default: ours,
#               src/Engine/built/Final/Lithtech/Lithtech.exe; retail's does
#               not start under Wine: SecuROM)
# seconds:      how long both keep running after the client is in (default 30)
# gamedir:      a game directory, as build/all.sh assembles it (default
#               out/nolf2-legacy-release)
#
# Runs inside the build container (`make shell`), both processes under one
# Xvfb screen (640x480, the client's window size) and one Wine prefix, in
# out/mptest/<name>/ ($MPTEST_NAME, default "ours"):
#   server/  NOLF2Srv.exe with the server.dll, on the profile srvtest.sh uses
#            (co-operative, LAN only, port 27888, the first co-op mission),
#            +errorlog: server/nolf2srv.log is its console
#   client/  Lithtech.exe, started once the server has loaded its world
#            ($MPTEST_SRVWAIT, default 40 s), +errorlog and UDPDebug 1:
#            client/error.log is its console (the UDP driver's traces)
# The client is driven through the menus with xdotool, as a player would:
# Multiplayer (LAN) -> Cooperative -> Join -> F5 (find servers: the LAN
# broadcast query) -> the first server -> join; then Space at the briefing.
# (The command line's `+join <ip>` is no good here: away from the LAN menu the
# game validates the CD key on WON's servers first, which are long gone.)
# $MPTEST_KEYS replaces the key sequence (keysyms; wN waits N seconds).
# Writes wine-server.log, wine-client.log, shots/ and shots.png (the screen
# after each key), shot.png (at the end), result.txt:
#   JOINED   the server took the client in and kept it; the client entered
#            the world and its player connected; both still running
#   KICKED   the client got in and was disconnected
#   NOJOIN   both ran, the client never got in
#   EXITED   one of them stopped (which)
# Exit status 0 only for JOINED.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for t in wine xvfb-run xdotool convert montage; do
    command -v $t >/dev/null 2>&1 || { echo "mptest.sh: no $t here -- run it in the build container (make shell)"; exit 2; }
done
abs() { case "$1" in /*) echo "$1" ;; *) echo "$REPO/$1" ;; esac; }
DLL="$(abs "${1:-src/Engine/built/Final/server/server.dll}")"
EXE="$(abs "${2:-src/Engine/built/Final/Lithtech/Lithtech.exe}")"
SECS="${3:-30}"
GAME="$(abs "${4:-out/nolf2-legacy-release}")"
SRVWAIT="${MPTEST_SRVWAIT:-40}"
KEYS="${MPTEST_KEYS:-Down Down Return Return w2 Down Return w2 F5 w4 Down Return w20 space w15}"
for f in "$DLL" "$EXE" "$GAME/NOLF2Srv.exe" "$GAME/nolf2cmds.txt" "$GAME/autoexec.cfg.retail"; do
    [ -f "$f" ] || { echo "mptest.sh: no $f"; exit 2; }
done
NAME="${MPTEST_NAME:-ours}"
RUN="$REPO/out/mptest/$NAME"
rm -rf "$RUN"; mkdir -p "$RUN"
setup() {   # setup <dir>: binaries copied, data linked
    mkdir -p "$1/Save"
    for f in "$GAME"/*; do
        b=$(basename "$f")
        case "$b" in Profiles|Save|autoexec.cfg|linux-run.sh|MANIFEST.txt|nolf2cmds.txt|run-cmds.txt) continue ;; esac
        if [ -f "$f" ] && [ "$(head -c 2 "$f" | tr -d '\0')" = MZ ]; then cp "$f" "$1/"; else ln -s "$f" "$1/"; fi
    done
    cp "$GAME/autoexec.cfg.retail" "$1/autoexec.cfg"
}
setup "$RUN/server"
cp "$DLL" "$RUN/server/server.dll"
mkdir -p "$RUN/server/Profiles/srvtest/Campaigns"
printf '[Multiplayer]\r\nGameType = 1\r\nPort = 27888\r\nLANOnly = 1\r\nDedicated = 1\r\n' > "$RUN/server/Profiles/srvtest.txt"
printf '[MissionList]\r\nMission0=0\r\nMission1=1\r\nLoopMissions=1\r\n' > "$RUN/server/Profiles/srvtest/Campaigns/default_campaign.txt"
setup "$RUN/client"
cp "$EXE" "$RUN/client/Lithtech.exe"
mkdir -p "$RUN/client/Profiles"
[ -f "$GAME/Default.prf.retail" ] && cp "$GAME/Default.prf.retail" "$RUN/client/Profiles/Default.prf"
printf '%s ++screenwidth 640 ++screenheight 480 ++bitdepth 32 ++windowed 1 +DisableMovies 1 +DisableSound 1 +errorlog 1 +alwaysflushlog 1 +UDPDebug 1\n' \
    "$(tr -d '\r\n' < "$GAME/nolf2cmds.txt")" > "$RUN/client/nolf2cmds.txt"

cat > "$RUN/runner.sh" <<'RUNNER'
SRVWAIT=$1 SECS=$2 KEYS=$3
wineboot -i >/dev/null 2>&1
K='HKLM\Software\Monolith Productions\No One Lives Forever 2\1.0'
# The 1.3 update as its installer registers it: NOLF2Srv.exe takes the
# update's rez from here (the client from nolf2cmds.txt). Without it the
# server's attribute files are 1.0's and the game's handshake kicks the client
# (the weapons/modelbutes/surface CRCs differ).
wine reg add "$K" /f >/dev/null 2>&1
wine reg add "$K" /v UpdateNum /t REG_DWORD /d 1 /f >/dev/null 2>&1
wine reg add "$K" /v UpdateCommandLine0 /t REG_SZ /d '-rez Update_v1x3.rez' /f >/dev/null 2>&1
(cd server && exec wine NOLF2Srv.exe -profile srvtest +errorlog 1 +alwaysflushlog 1) > wine-server.log 2>&1 & S=$!
sleep $SRVWAIT
(cd client && exec wine Lithtech.exe -cmdfile nolf2cmds.txt) > wine-client.log 2>&1 & C=$!
mkdir -p shots; N=0; WIN=""
for i in $(seq 1 120); do
    WIN=$(xdotool search --onlyvisible --name '^LithTech$' 2>/dev/null | head -1)
    [ -n "$WIN" ] && break; sleep 1
done
sleep 20   # the main menu
for k in $KEYS; do
    kill -0 $C 2>/dev/null || break
    case $k in
        w*) sleep ${k#w} ;;
        *)  [ -n "$WIN" ] && xdotool windowfocus $WIN 2>/dev/null
            xdotool keydown $k; sleep 0.08; xdotool keyup $k; sleep 1.5 ;;
    esac
    N=$((N+1)); xwd -root -silent | convert xwd:- $(printf 'shots/%02d-%s.png' $N $k) 2>/dev/null
done
for i in $(seq 1 $SECS); do
    sleep 1
    kill -0 $S 2>/dev/null || break
    kill -0 $C 2>/dev/null || break
done
xwd -root -silent | convert xwd:- shot.png 2>/dev/null
ST=""; kill -0 $S 2>/dev/null || ST="server"
kill -0 $C 2>/dev/null || ST="$ST client"
echo "$ST" > stopped.txt
wineserver -k 2>/dev/null
RUNNER
cd "$RUN" || exit 2
export WINEPREFIX="${WINEPREFIX:-/tmp/home/mptest-wine}" WINEDEBUG="${MPTEST_WINEDEBUG:-err+all,fixme-all,trace+msgbox,+seh}" \
    WINEDLLOVERRIDES="${MPTEST_DLLOVERRIDES-winedbg.exe=d}"
xvfb-run -a -s '-screen 0 640x480x24' bash runner.sh "$SRVWAIT" "$SECS" "$KEYS"
ls shots/*.png >/dev/null 2>&1 && montage -label '%f' -pointsize 10 shots/*.png shot.png -tile 4x -geometry 320x240+2+2 shots.png 2>/dev/null

SLOG=server/nolf2srv.log CLOG=client/error.log
touch "$SLOG" "$CLOG"
STOPPED="$(cat stopped.txt 2>/dev/null)"
if [ -n "$(echo $STOPPED)" ]; then
    echo "EXITED:$STOPPED" > result.txt
elif ! grep -q "New client" "$SLOG" || ! grep -q "Entering world" "$CLOG"; then
    echo NOJOIN > result.txt
elif grep -q "Removing client" "$SLOG" || grep -q "Disconnected from server" "$CLOG" || ! grep -q "MID_PLAYER_CONNECTED" "$CLOG"; then
    echo KICKED > result.txt
else
    echo JOINED > result.txt
fi
cat result.txt
echo "-- server console:"; grep -E "client|world|kick|Boot" "$SLOG" | tail -n 8
echo "-- client console:"; grep -E "^UDP|world|MID_PLAYER|Disconnect|ID packet" "$CLOG" | tail -n 12
grep -h 'msgbox' wine-server.log wine-client.log
grep -q '^JOINED' result.txt
