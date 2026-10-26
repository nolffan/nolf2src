#!/usr/bin/env bash
# The scoreboard: how much of the build is byte-identical to the retail game,
# held to what has already been recorded. See progress/README.md.
#
#   make progress           (on the host: runs `build/progress.sh check` in a
#                            container)
#   make progress-update    (`build/progress.sh update`: record the run)
#   build/progress.sh check|update   (inside the build container, or on a
#                                     host with Python 3)
#
# Scores what the last `make` left in the tree (each binary progress/targets.py
# names, and the objects and libraries its link read); it compiles nothing.
# Needs the installed retail game (build/retail.sh): its binaries are
# extracted into out/reference/ the first time.
#
#   check   tools/progress.py, then tools/ratchet.py check: fails if a
#           function recorded in progress/identical.txt no longer matches
#           (COMPLETE=1: also unless every function matches; COVERED=1:
#           unless nothing is unwritten or unplaced)
#   update  tools/progress.py, then tools/ratchet.py update: records the run
#           in progress/ and rewrites README.md's table (ACCEPT_LOSSES=1 to
#           record a run that lost functions)
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

mode="${1:-check}"
case "$mode" in
    check|update) ;;
    *) echo "usage: build/progress.sh check|update" >&2; exit 2 ;;
esac

# the images, and the function tables build/reference.sh derives from them
for f in Lithtech.exe server.dll ServerDir.dll snddrv.dll ltmsg.dll \
         NOLF2.exe NOLF2Srv.exe CShell.dll Object.lto ClientFx.fxd \
         CRes.dll SRes.dll \
         Lithtech-functions.csv server-functions.csv ServerDir-functions.csv \
         snddrv-functions.csv NOLF2-functions.csv NOLF2Srv-functions.csv \
         CShell-functions.csv Object-functions.csv ClientFx-functions.csv; do
    if [ ! -f "out/reference/$f" ]; then
        echo "== retail binaries -> out/reference/ (for scoring only)"
        bash build/reference.sh
        break
    fi
done

# the function tables are derived by tools/enumfuncs.py: a newer
# enumerator (a rule that finds more starts) means new tables
for f in out/reference/*-functions.csv; do
    if [ tools/enumfuncs.py -nt "$f" ]; then
        echo "== tools/enumfuncs.py changed: the function tables again"
        bash build/reference.sh tables
        break
    fi
done

python3 tools/progress.py
echo
if [ "$mode" = check ]; then
    python3 tools/ratchet.py check ${COMPLETE:+--complete} ${COVERED:+--covered}
else
    python3 tools/ratchet.py update ${ACCEPT_LOSSES:+--accept-losses}
fi
