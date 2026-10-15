#!/usr/bin/env bash
# playtest.sh -- the runtime test: does the game load a level and keep running
# (and, with an input script, does it PLAY)?
#
#   tools/playtest.sh [gamedir] [world] [seconds]
#   PLAYTEST_SCRIPT=tools/playtest-basic.txt tools/playtest.sh [gamedir] [world]
#
# gamedir:    a complete game directory, as build/all.sh assembles it
#             (default out/nolf2-legacy-release). It is tested exactly as it is: every
#             binary in it runs, nothing is substituted or filled in.
# world:      a world path inside the .rez stack (default Worlds\RetailSinglePlayer\C01S01);
#             "-" starts without one (the game opens on its main menu)
# seconds:    how long to let it run before judging (default 60; in script
#             mode, extra idle seconds after the script, default 0)
#
# Runs inside the build container under Xvfb, in its own directory
# out/play/<name>/ (<name> is the game directory's basename, or
# $PLAYTEST_NAME): the data is symlinked from the game directory and its
# binaries copied in, so the game directory itself is never modified --
# autoexec.cfg and Save/ are private copies (the engine rewrites
# autoexec.cfg on exit and the game writes saves). Writes, in that directory:
#   wine.log   everything Wine and the game printed
#   shot.png   a screenshot of the virtual display at the end
#   result.txt ALIVE / EXITED / CRASHED / NO HUD, plus the reason
# and prints result.txt. Exit status 0 only for ALIVE.
#
# Scripted input (PLAYTEST_SCRIPT=<file>): instead of idling, the runner
# drives the game window with xdotool from a script, one command per line
# ('#' starts a comment). The run's autoexec.cfg is then the shipped one (autoexec.cfg.retail)
# (the shipped default controls: the game directory's autoexec.cfg can have
# lost its key bindings) and Save/ starts empty, so every run starts from the same
# state. Commands:
#   window [timeout]      wait (default 120s) for the LithTech window, focus
#                         it, park the pointer at its centre; the clock for
#                         every later step starts here (put it first)
#   wait <secs>           sleep (fractions allowed)
#   key <keysym>...       tap keys (X keysyms: w a s d space c f Escape F6
#                         F9 1 2 Shift_L Left Right Return ...)
#   type <text>           type the text (the rest of the line, its spaces
#                         as single spaces; no '#'), a key every 0.1s
#   hold <keysym> <secs>  hold a key down for <secs>
#   down <keysym> / up <keysym>   press / release (combine with turn etc.)
#   turn <dx> <dy> [steps]   relative mouse motion, split into <steps>
#                         (default 10) moves 30 ms apart (mouse look)
#   click [button] [secs] mouse button (1 = fire), held <secs> (default 0.1)
#   skipcine [timeout]    until the HUD is up (the health bar is drawn: the
#                         player is in control), press Space (skips a
#                         cinematic) and Return (takes the first answer of a
#                         dialogue decision) in turn, every 3s; returns once
#                         the HUD has been up for 4s, or after <timeout>
#                         (default 90s); if the HUD never comes up, the
#                         run is judged NO HUD, a failure
#   shot <name>           screenshot the game window -> shots/NN-<name>.png
#   screen <name>         screenshot the whole display (the window on it)
#   focus                 re-focus the game window
#   minimize / restore    iconify the game window (it loses the focus) /
#                         map and activate it again (a window manager's
#                         job: PLAYTEST_WM)
#   mmove <x> <y>         move the pointer to a point of the menus' 640x480
#                         page, mapped to the window as PLAYTEST_MAP says:
#                         "retail" (the page centred, unscaled; the default
#                         for a release build) or "modern" (the centred 4:3
#                         area, scaled by the height: docs/MODERN.md M-G2; the
#                         default for a game directory named *modern*)
#   mclick <x> <y>        the same, then a click of button 1
#   pad [button...] [axis=value...]
#                         the test controller (the modern build's ##gamepad,
#                         docs/MODERN.md M-E20, which in a scripted run reads its
#                         state from the file NOLF2SRC_PADTEST names, not
#                         from XInput): the buttons held from now on -- a b
#                         x y lb rb back start ls rs up down left right (the
#                         d-pad) -- and the axes, lx ly rx ry -100..100 (y up
#                         positive) and lt rt 0..100; what is not named is
#                         released / centred. `pad` alone: all released;
#                         `pad off`: no controller connected (the start)
#   tap <button>...       press and release pad buttons in turn (0.1s each)
#   wfocus <regex> [timeout]   wait (default 60s) for a visible window whose
#                         name matches, and focus it (the launcher's
#                         dialogs: PLAYTEST_LAUNCH)
#   wclick <regex> <x> <y>    click at a point of that window (its own
#                         coordinates)
#   sclick <x> <y>        click at a point of the display
# After every command the runner checks the game process; if it has died the
# script stops and the run is judged (EXITED / CRASHED, naming the line).
# Everything that happened goes to script.log; shots.png is a contact sheet
# of all shots. Steps are timed from the 'window' command, so the same script
# replays the same inputs at the same moments on every run -- compare two
# runs with `playtest.sh compare` (game-side timing, AI and physics still
# vary, so expect near, not pixel-identical, frames).
# The game runs full screen on a virtual display of exactly its screen mode
# (the engine, like retail's, wants a display mode of the window's size
# even when windowed, and Xvfb offers only its own size), with sound: where
# there is no sound card (a container), ALSA's default device is its null
# plugin (an asound.conf in the run directory, through ALSA_CONFIG_PATH),
# so Wine's DirectSound has an output device and the engine's sound driver
# initialises and plays, into nothing.
# Optional settings, from the environment:
#   PLAYTEST_RES=WxH      the screen mode (32-bit) instead of 640x480x32;
#                         the virtual display is that size
#                         (e.g. 1280x720, 1920x1080)
#   PLAYTEST_WINDOWED=1   a window instead of full screen (Wine's frame
#                         makes it smaller than the display)
#   PLAYTEST_SCREEN=WxH   the virtual display's size, when it should not be
#                         the screen mode's (a window on a larger desktop)
#   PLAYTEST_WM=<command> a window manager to run on the display first
#                         (e.g. openbox; it must be in the image: Xvfb
#                         alone has none, so no frame, focus or placement)
#   PLAYTEST_ARGS="..."   more engine arguments (e.g. +DisableSound 1)
#   PLAYTEST_CFG=<file>   console variables appended to the run's
#                         autoexec.cfg (lines like "UIScale" "1.000000")
#   PLAYTEST_SAVES=<dir>  start a scripted run with a copy of these saved
#                         games as its Save/ (instead of none)
#   PLAYTEST_LAUNCH="..." start the game with `wine <this>` in the run
#                         directory instead of `wine Lithtech.exe -cmdfile
#                         nolf2cmds.txt`: e.g. "NOLF2.exe" (the launcher),
#                         "Lithtech.exe" (no arguments), "cmd /c
#                         windows-run.bat". The game counts as running while
#                         that program or a Lithtech.exe is (the launcher
#                         exits once it has started the engine).
#   PLAYTEST_PREFIX=<dir> the Wine prefix (default: the container's; a
#                         relative path is from the repository); a new
#                         directory is a fresh prefix, no registry values
# The default keys (defctrls.cfg): WASD move, arrows turn, Space jump,
# C duck, F / mouse 1 fire, R reload, Shift_L next weapon, 1-0 weapons,
# E activate, F6 quicksave, F9 quickload, Escape menu.
#
# Run it inside the build container: `make test` does (the main menu), and
# `make shell` gives a shell to run it by hand.
#
#   tools/playtest.sh compare <runA> <runB>
# compares two scripted runs (directory names under out/play/, e.g. two
# PLAYTEST_NAMEs): per shot, the normalised RMSE between the two frames (0 = same,
# roughly < 0.1 = the same view, > 0.2 = a different screen), and writes
# out/play/compare-<runA>-<runB>.png (A left, B right, one row per shot).
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for t in wine xvfb-run xdotool convert; do
    command -v $t >/dev/null 2>&1 || { echo "playtest.sh: no $t here -- run it in the build container (make test / make shell)"; exit 2; }
done
if [ "${1:-}" = compare ]; then
    A="${2:?usage: playtest.sh compare <runA> <runB>}"; B="${3:?usage: playtest.sh compare <runA> <runB>}"
    cd "$REPO/out/play" || exit 1; L=()
    for f in $A/shots/*.png; do
        b=$(basename $f); [ -f $B/shots/$b ] || { echo "$b  (missing in $B)"; continue; }
        r=$(compare -metric RMSE $f $B/shots/$b null: 2>&1 | sed 's/.*(\(.*\))/\1/')
        printf '%-24s %s\n' "$b" "$r"; L+=($f $B/shots/$b)
    done
    [ ${#L[@]} -gt 0 ] && montage -label '%d/%f' -pointsize 9 "${L[@]}" -tile 2x -geometry 320x240+2+2 compare-$A-$B.png
    exit
fi
GAMEDIR="${1:-out/nolf2-legacy-release}"
WORLD="${2:-Worlds\\RetailSinglePlayer\\C01S01}"
SCRIPT="${PLAYTEST_SCRIPT:-}"
if [ -n "$SCRIPT" ]; then SECS="${3:-0}"; else SECS="${3:-60}"; fi
abs() { case "$1" in /*) echo "$1" ;; *) echo "$REPO/$1" ;; esac; }
GAME="$(abs "$GAMEDIR")"
for f in Lithtech.exe server.dll nolf2cmds.txt autoexec.cfg.retail Default.prf.retail; do
    [ -f "$GAME/$f" ] || { echo "$GAME/$f missing -- not a game directory (build/all.sh makes one)"; exit 2; }
done
NAME="${PLAYTEST_NAME:-$(basename "$GAME")}"

RUN="$REPO/out/play/$NAME"
rm -rf "$RUN"; mkdir -p "$RUN"
# binaries copied, data linked (relative links)
REL="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$GAME" "$RUN")"
for f in "$GAME"/*; do
    b=$(basename "$f")
    # (MANIFEST.txt is linked: windows-run.bat reads it)
    case "$b" in autoexec.cfg|Save|Profiles|nolf2cmds.txt|linux-run.sh|linux-run-launcher.sh|run-cmds.txt|launchcmds.txt) continue ;; esac
    if [ -f "$f" ] && [ "$(head -c 2 "$f" | tr -d '\0')" = MZ ]; then cp "$f" "$RUN/$b"
    else ln -s "$REL/$b" "$RUN/$b"; fi
done
echo "game directory: $GAME" > "$RUN/binaries.txt"
if [ -n "$SCRIPT" ]; then
    cp "$(abs "$SCRIPT")" "$RUN/script.txt" || exit 2
    cp "$GAME/autoexec.cfg.retail" "$RUN/autoexec.cfg"
    mkdir "$RUN/Profiles" && cp "$GAME/Default.prf.retail" "$RUN/Profiles/Default.prf"
    if [ -n "${PLAYTEST_SAVES:-}" ]; then cp -r "$(abs "$PLAYTEST_SAVES")" "$RUN/Save" || exit 2
    else mkdir "$RUN/Save"; fi
else
    cp "$GAME/autoexec.cfg" "$RUN/autoexec.cfg" 2>/dev/null || cp "$GAME/autoexec.cfg.retail" "$RUN/autoexec.cfg"
    if [ -d "$GAME/Profiles" ]; then cp -r "$GAME/Profiles" "$RUN/Profiles"
    else mkdir "$RUN/Profiles" && cp "$GAME/Default.prf.retail" "$RUN/Profiles/Default.prf"; fi
    if [ -d "$GAME/Save" ]; then cp -r "$GAME/Save" "$RUN/Save"; else mkdir "$RUN/Save"; fi
fi
# The engine takes the world from the command file, not from arguments after
# -cmdfile: write a per-run copy with +runworld appended.
rm -f "$RUN/nolf2cmds.txt"
# (nolf2cmds.txt is the rez stack; the screen mode and the movies are the
# harness's, as linux-run.sh adds its own)
CMDS="$(tr -d '\r\n' < "$GAME/nolf2cmds.txt") ++screenwidth 640 ++screenheight 480 ++bitdepth 32 ++windowed ${PLAYTEST_WINDOWED:-0} +DisableMovies 1${PLAYTEST_ARGS:+ $PLAYTEST_ARGS}"
SCREEN=640x480   # the virtual display: the screen mode (see the header)
if [ -n "${PLAYTEST_RES:-}" ]; then
    RW=${PLAYTEST_RES%x*}; RH=${PLAYTEST_RES#*x}
    CMDS="$(echo "$CMDS" | sed -E "s/\+\+screenwidth [0-9]+/++screenwidth $RW/; s/\+\+screenheight [0-9]+/++screenheight $RH/; s/\+\+bitdepth [0-9]+/++bitdepth 32/")"
    SCREEN="${RW}x${RH}"
fi
# a desktop of another size than the mode (a window on a larger screen)
[ -n "${PLAYTEST_SCREEN:-}" ] && SCREEN="$PLAYTEST_SCREEN"
if [ "$WORLD" = - ]; then printf '%s\n' "$CMDS" > "$RUN/nolf2cmds.txt"
else printf '%s +runworld %s\n' "$CMDS" "$WORLD" > "$RUN/nolf2cmds.txt"; fi
[ -n "${PLAYTEST_CFG:-}" ] && { cat "$(abs "$PLAYTEST_CFG")" >> "$RUN/autoexec.cfg" || exit 2; }

# The runner, executed inside the container under xvfb-run.
cat > "$RUN/runner.sh" <<'RUNNER'
#!/bin/bash
# $1 = seconds (idle mode: total; script mode: extra after the script)
SECS=$1
# a window manager first, when asked for (PLAYTEST_WM): it frames, places
# and focuses the game's windows, as a desktop's does
if [ -n "${PLAYTEST_WM:-}" ]; then
    $PLAYTEST_WM > wm.log 2>&1 &
    sleep 2
fi
if [ -n "${PLAYTEST_LAUNCH:-}" ]; then
    wine $PLAYTEST_LAUNCH > wine.log 2>&1 &
    PID=$!
    alive() { kill -0 $PID 2>/dev/null || pgrep -fi 'lithtech\.exe' >/dev/null; }
else
    wine Lithtech.exe -cmdfile nolf2cmds.txt > wine.log 2>&1 &
    PID=$!
    alive() { kill -0 $PID 2>/dev/null; }
fi
STOPPED=""; NOHUD=""

if [ -f script.txt ]; then
    mkdir -p shots
    N=0; WIN=""; WX=0; WY=0; WW=1024; WH=768
    log() { awk -v a="$(date +%s.%N)" -v b="${T0:-0}" -v m="$*" 'BEGIN { printf "%7.2f %s\n", (b > 0 ? a - b : 0), m }' >> script.log; }
    # the game window (a smaller 'LithTech' startup window comes first)
    findwin() {
        local w
        for w in $(xdotool search --onlyvisible --name '^LithTech$' 2>/dev/null); do
            eval "$(xdotool getwindowgeometry --shell "$w" 2>/dev/null)"
            [ "${WIDTH:-0}" -ge 600 ] && { echo "$w"; return; }
        done
    }
    geom() {
        eval "$(xdotool getwindowgeometry --shell "$WIN" 2>/dev/null)"
        WX=${X:-0}; WY=${Y:-0}; WW=${WIDTH:-1024}; WH=${HEIGHT:-768}
    }
    focuswin() { [ -n "$WIN" ] && xdotool windowfocus "$WIN" 2>/dev/null; }
    # a point of the menus' 640x480 page -> the pointer (see mmove)
    pagemove() {
        local p
        p="$(awk -v lx=$1 -v ly=$2 -v W=$((WW-2)) -v H=$((WH-2)) -v m="${PLAYTEST_MAP:-retail}" 'BEGIN {
            if (m == "modern") { s = H/480; x = lx*s + (W - H*4/3)/2; y = ly*s }
            else { x = lx + (W-640)/2; y = ly + (H-480)/2 }
            printf "%d %d", x, y }')"
        set -- $p
        xdotool mousemove $((WX+1+$1)) $((WY+1+$2))
    }
    # the test controller's state -> $NOLF2SRC_PADTEST (see `pad`), written
    # whole and renamed, so the game never reads half a line
    padset() {
        local b=0 lx=0 ly=0 rx=0 ry=0 lt=0 rt=0 a v
        if [ "${1:-}" = off ]; then rm -f "$NOLF2SRC_PADTEST"; return; fi
        for a in "$@"; do
            case "$a" in
                up) b=$((b|0x1)) ;; down) b=$((b|0x2)) ;; left) b=$((b|0x4)) ;; right) b=$((b|0x8)) ;;
                start) b=$((b|0x10)) ;; back) b=$((b|0x20)) ;; ls) b=$((b|0x40)) ;; rs) b=$((b|0x80)) ;;
                lb) b=$((b|0x100)) ;; rb) b=$((b|0x200)) ;;
                a) b=$((b|0x1000)) ;; b) b=$((b|0x2000)) ;; x) b=$((b|0x4000)) ;; y) b=$((b|0x8000)) ;;
                l[xy]=*|r[xy]=*) v=$(( ${a#*=} * 32767 / 100 )); eval "${a%%=*}=$v" ;;
                l[t]=*|r[t]=*) v=$(( ${a#*=} * 255 / 100 )); eval "${a%%=*}=$v" ;;
                *) log "  pad: unknown $a" ;;
            esac
        done
        echo "$b $lx $ly $rx $ry $lt $rt" > "$NOLF2SRC_PADTEST.part" && mv -f "$NOLF2SRC_PADTEST.part" "$NOLF2SRC_PADTEST"
    }
    grab() { xwd -root -silent | convert xwd:- -crop "${WW}x${WH}+${WX}+${WY}" +repage "$@"; }
    # is the HUD up (= the player is in control)? The health bar: red, at
    # x 30..60, y 448..452 of the 640x480 view (scaled to the window size).
    hud() {
        local x=$((WX + 30*WW/642)) y=$((WY + 448*WH/482)) w=$((30*WW/642)) h=$((4*WH/482 + 1))
        xwd -root -silent | convert xwd:- -crop "${w}x${h}+${x}+${y}" -format '%[fx:mean.r] %[fx:mean.g]' info: 2>/dev/null |
            awk '{ exit !($1 > 0.3 && $1 > 2.5 * $2) }'
    }
    T0=$(date +%s.%N)
    LINE=0
    while IFS= read -r raw || [ -n "$raw" ]; do
        LINE=$((LINE+1))
        l="${raw%%#*}"; l="$(echo $l)"
        [ -z "$l" ] && continue
        set -- $l; cmd=$1; shift
        if ! alive; then STOPPED="line $LINE ($l)"; break; fi
        log "$LINE: $l"
        case "$cmd" in
            window)
                to=${1:-120}; s=0
                while [ -z "$(findwin)" ] && [ $s -lt $((to*2)) ] && alive; do sleep 0.5; s=$((s+1)); done
                WIN=$(findwin)
                if [ -z "$WIN" ]; then log "  no window"; continue; fi
                geom; focuswin
                xdotool mousemove $((WX+WW/2)) $((WY+WH/2))
                T0=$(date +%s.%N)
                log "  window $WIN ${WW}x${WH}+${WX}+${WY}" ;;
            wait)  sleep "$1" ;;
            key)   for k in "$@"; do xdotool keydown "$k"; sleep 0.08; xdotool keyup "$k"; sleep 0.12; done ;;
            type)  xdotool type --delay 100 -- "$*" ;;
            hold)  xdotool keydown "$1"; sleep "$2"; xdotool keyup "$1" ;;
            down)  xdotool keydown "$1" ;;
            up)    xdotool keyup "$1" ;;
            turn)  st=${3:-10}; dx=$(( $1 / st )); dy=$(( $2 / st ))
                   for i in $(seq $st); do xdotool mousemove_relative -- $dx $dy; sleep 0.03; done ;;
            click) xdotool mousedown "${1:-1}"; sleep "${2:-0.1}"; xdotool mouseup "${1:-1}" ;;
            skipcine)
                to=${1:-90}; st=$(date +%s); clear=0; k=space
                while [ $(( $(date +%s) - st )) -lt $to ] && alive; do
                    if hud; then clear=$((clear+1)); [ $clear -ge 4 ] && break; sleep 1; continue; fi
                    clear=0; log "  no HUD -> $k"
                    xdotool keydown $k; sleep 0.08; xdotool keyup $k; sleep 3
                    [ $k = space ] && k=Return || k=space
                done
                if [ $clear -ge 4 ]; then log "  skipcine done after $(( $(date +%s) - st ))s"
                else NOHUD="line $LINE"; log "  skipcine: no HUD after $(( $(date +%s) - st ))s"; fi ;;
            shot)  N=$((N+1)); f=$(printf 'shots/%02d-%s.png' $N "$1"); grab "$f"; log "  -> $f" ;;
            screen) N=$((N+1)); f=$(printf 'shots/%02d-%s.png' $N "$1"); xwd -root -silent | convert xwd:- "$f"; log "  -> $f (the display)" ;;
            focus) focuswin ;;
            minimize) [ -n "$WIN" ] && xdotool windowminimize "$WIN" 2>/dev/null ;;
            restore) [ -n "$WIN" ] && { xdotool windowmap "$WIN" 2>/dev/null; xdotool windowactivate "$WIN" 2>/dev/null || focuswin; } ;;
            mmove) pagemove "$1" "$2" ;;
            mclick) pagemove "$1" "$2"; sleep 0.4; xdotool mousedown 1; sleep 0.1; xdotool mouseup 1 ;;
            pad)   padset "$@" ;;
            tap)   for k in "$@"; do padset "$k"; sleep 0.1; padset; sleep 0.25; done ;;
            wfocus)
                to=${2:-60}; s=0; W=""
                while [ $s -lt $((to*2)) ] && alive; do
                    W=$(xdotool search --onlyvisible --name "$1" 2>/dev/null | tail -1)
                    [ -n "$W" ] && break; sleep 0.5; s=$((s+1))
                done
                if [ -n "$W" ]; then xdotool windowfocus "$W" 2>/dev/null; log "  window $W: $(xdotool getwindowname "$W" 2>/dev/null)"
                else log "  no window named $1"; fi ;;
            wclick)
                W=$(xdotool search --onlyvisible --name "$1" 2>/dev/null | tail -1)
                if [ -n "$W" ]; then
                    eval "$(xdotool getwindowgeometry --shell "$W" 2>/dev/null)"
                    xdotool mousemove $((X+$2)) $((Y+$3)); sleep 0.3; xdotool click 1
                    log "  clicked $W at $2,$3"
                else log "  no window named $1"; fi ;;
            sclick) xdotool mousemove "$1" "$2"; sleep 0.3; xdotool click 1 ;;
            *)     log "  unknown command: $cmd" ;;
        esac
    done < <(tr -d '\r' < script.txt)
    [ -z "$STOPPED" ] && ! alive && STOPPED="end of script"
    if [ -z "$STOPPED" ]; then
        for i in $(seq 1 $SECS); do sleep 1; alive || break; done
        alive || STOPPED="idle after the script"
    fi
    ls shots/*.png >/dev/null 2>&1 && montage -label '%t' -pointsize 10 shots/*.png -tile 4x -geometry 320x240+2+2 shots.png 2>/dev/null
    WHAT="the script ($LINE lines)"
else
    for i in $(seq 1 $SECS); do sleep 1; alive || break; done
    WHAT="${SECS}s"
fi
xwd -root -silent | convert xwd:- shot.png 2>/dev/null
if alive && [ -n "$NOHUD" ]; then
    echo "NO HUD: alive, but the player never got control (skipcine at $NOHUD)" > result.txt
    wineserver -k; sleep 2
elif alive; then
    echo "ALIVE after $WHAT" > result.txt
    wineserver -k; sleep 2
else
    wait $PID; RC=$?
    if grep -qiE "unhandled exception|page fault|EXCEPTION_ACCESS_VIOLATION|backtrace" wine.log; then
        echo "CRASHED (exit $RC)${STOPPED:+ at $STOPPED}" > result.txt
        grep -iE "unhandled exception|page fault|EXCEPTION_ACCESS_VIOLATION" wine.log | head -3 >> result.txt
    else
        echo "EXITED (exit $RC)${STOPPED:+ at $STOPPED} before $WHAT finished" > result.txt
    fi
fi
RUNNER

(
cd "$RUN" || exit 1
if [ ! -e /dev/snd ] && [ -f /usr/share/alsa/alsa.conf ]; then
    printf '</usr/share/alsa/alsa.conf>\npcm.!default { type null }\n' > asound.conf
    export ALSA_CONFIG_PATH="$RUN/asound.conf"
fi
export WINEDEBUG=${PLAYTEST_WINEDEBUG:--all,+seh} WINEDLLOVERRIDES=${PLAYTEST_DLLOVERRIDES-winedbg.exe=d}
# (Wine wants it absolute: a relative one is the repository's)
case "${PLAYTEST_PREFIX:-}" in
    "") ;;
    /*) export WINEPREFIX=$PLAYTEST_PREFIX ;;
    *)  export WINEPREFIX=$REPO/$PLAYTEST_PREFIX ;;
esac
# the modern build lays its menus out in the centred 4:3 area (docs/MODERN.md M-G2)
case "$(basename "$GAME")" in *modern*) DEFMAP=modern ;; *) DEFMAP=retail ;; esac
export PLAYTEST_MAP="${PLAYTEST_MAP:-$DEFMAP}"
# a scripted run's controller is the test pad, and starts unplugged (`pad`)
[ -n "$SCRIPT" ] && export NOLF2SRC_PADTEST=padtest.txt
xvfb-run -a -s "-screen 0 ${SCREEN}x24" bash runner.sh $SECS
)
cat "$RUN/result.txt" 2>/dev/null || echo "NO RESULT (the run failed)"
grep -q '^ALIVE' "$RUN/result.txt" 2>/dev/null
