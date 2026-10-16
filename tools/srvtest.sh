#!/usr/bin/env bash
# srvtest.sh -- the dedicated server's runtime test: does NOLF2Srv.exe, with a
# given server.dll, host a level under Wine?
#
#   tools/srvtest.sh [server.dll] [seconds] [gamedir]
#
# server.dll: the engine to host with (default: ours,
#             src/Engine/built/Final/server/server.dll; out/reference/server.dll
#             is the retail control)
# seconds:    how long to let it run before judging (default 90)
# gamedir:    a game directory, as build/all.sh assembles it (default
#             out/nolf2-legacy-release); its NOLF2Srv.exe is the one run
#
# Runs inside the build container under Xvfb (`make shell`), in
# out/srvtest/<name>/ (<name>: the server.dll's directory name, or
# $SRVTEST_NAME): binaries copied, data linked, server.dll replaced. The server
# is started on a profile of its own (Profiles/srvtest.txt: co-operative,
# LAN only, port 27888) whose default campaign is the first two co-op
# missions, so it loads Worlds\RetailMultiplayer\CP_c01s01 at once. Writes
#   wine.log     what Wine printed (message boxes traced: an error the server
#                shows in one is in here)
#   shot.png     the virtual display at the end (the server's window: its
#                console shows the world it loaded)
#   windows.txt  the visible windows' titles
#   result.txt   ALIVE / EXITED; then, once the server has been stopped as
#                its operator would (Stop Server, Escape, and Yes in the
#                box that asks), STOPPED / NOT STOPPED
#   nolf2srv.log the server's console (the modern build writes it unasked)
# and prints result.txt, the end of the log and the message boxes. Exit
# status 0 only for ALIVE, then not NOT STOPPED, with no message box but
# the stop's question.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for t in wine xvfb-run xdotool convert; do
    command -v $t >/dev/null 2>&1 || { echo "srvtest.sh: no $t here -- run it in the build container (make shell)"; exit 2; }
done
abs() { case "$1" in /*) echo "$1" ;; *) echo "$REPO/$1" ;; esac; }
DLL="$(abs "${1:-src/Engine/built/Final/server/server.dll}")"
SECS="${2:-90}"
GAME="$(abs "${3:-out/nolf2-legacy-release}")"
[ -f "$DLL" ] || { echo "srvtest.sh: no $DLL"; exit 2; }
[ -f "$GAME/NOLF2Srv.exe" ] || { echo "srvtest.sh: $GAME has no NOLF2Srv.exe (build/all.sh makes the game directory)"; exit 2; }
NAME="${SRVTEST_NAME:-$(basename "$(dirname "$DLL")")}"
RUN="$REPO/out/srvtest/$NAME"
rm -rf "$RUN"; mkdir -p "$RUN/Profiles/srvtest/Campaigns" "$RUN/Save"
cd "$RUN" || exit 2
for f in "$GAME"/*; do
    b=$(basename "$f")
    case "$b" in Profiles|Save|autoexec.cfg|linux-run.sh|MANIFEST.txt) continue ;; esac
    if [ -f "$f" ] && [ "$(head -c 2 "$f" | tr -d '\0')" = MZ ]; then cp "$f" .; else ln -s "$f" .; fi
done
cp "$DLL" server.dll
cp "$GAME/autoexec.cfg.retail" autoexec.cfg
printf '[Multiplayer]\r\nGameType = 1\r\nPort = 27888\r\nLANOnly = TRUE\r\nDedicated = TRUE\r\n' > Profiles/srvtest.txt
printf '[MissionList]\r\nMission0=0\r\nMission1=1\r\nLoopMissions=1\r\n' > Profiles/srvtest/Campaigns/default_campaign.txt

# Everything Wine runs under the virtual display: a wineserver started
# without it leaves the server no window driver.
export WINEPREFIX="${WINEPREFIX:-/tmp/home/srvtest-wine}" WINEDEBUG="err+all,fixme-all,trace+msgbox"
xvfb-run -a -s '-screen 0 1024x768x24' bash -c "
    wineboot -i >/dev/null 2>&1
    wine reg add 'HKLM\\Software\\Monolith Productions\\No One Lives Forever 2\\1.0' /f >/dev/null 2>&1
    wine NOLF2Srv.exe -profile srvtest -name srvtest > wine.log 2>&1 & P=\$!
    sleep $SECS
    xwd -root -silent | convert xwd:- shot.png 2>/dev/null
    for w in \$(xdotool search --onlyvisible --name . 2>/dev/null); do xdotool getwindowname \$w; done > windows.txt 2>&1
    if kill -0 \$P 2>/dev/null; then echo ALIVE > result.txt; else echo EXITED > result.txt; fi
    # stopped as its operator would: Stop Server (Escape) and Yes (Return)
    W=\$(xdotool search --onlyvisible --name '^No One Lives Forever 2\$' 2>/dev/null | head -1)
    if [ -n \"\$W\" ] && kill -0 \$P 2>/dev/null; then
        xdotool windowactivate --sync \$W 2>/dev/null; xdotool windowfocus --sync \$W 2>/dev/null
        xdotool key Escape; sleep 2
        B=\$(xdotool search --onlyvisible --name '^NOLF2Svr\$' 2>/dev/null | head -1)
        [ -n \"\$B\" ] && { xdotool windowfocus --sync \$B 2>/dev/null; xdotool key Return; }
        for i in \$(seq 1 30); do kill -0 \$P 2>/dev/null || break; sleep 0.5; done
        if kill -0 \$P 2>/dev/null; then echo 'NOT STOPPED' >> result.txt; else echo STOPPED >> result.txt; fi
    fi
    wineserver -k 2>/dev/null
"
cat result.txt
if [ -f nolf2srv.log ]; then echo '-- nolf2srv.log (end):'; tail -n 15 nolf2srv.log; fi
grep -h 'msgbox' wine.log | grep -v 'want to stop the server' && exit 1
grep -q ALIVE result.txt &&! grep -q 'NOT STOPPED' result.txt
