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
#   both    then tools/datacheck.py: the text in our images' data against the
#           retail images'; fails on a difference progress/data-known.txt
#           does not list (update also drops the entries no longer needed);
#           and tools/fpconst.py --targets: the float constants our placed
#           functions load through a (masked) relocation against retail's;
#           fails on any that differs; and tools/vtabcheck.py --targets: our
#           vtables slot by slot, and the callees and globals our uniquely
#           placed functions reach, against retail's; fails on a
#           contradiction progress/vtab-known.txt does not list
#
# Before anything is scored, the cached retail images in out/reference/ are
# checked against progress/reference.sha256 (extracted again once if they
# differ, or if the tables' stamp does): a stale or altered cache would be
# scored as if it were retail.
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
        need=1
        break
    fi
done

# The cached retail images in out/reference/ are what is scored: they have
# to be the retail images progress/reference.sha256 names, every run, not
# merely present. The tables derived from them are stamped with what made
# them (that list and tools/enumfuncs.py, by content): a different stamp
# extracts everything again.
refcheck() { (cd out/reference && sha256sum --quiet -c ../../progress/reference.sha256); }
stamp=$(cat progress/reference.sha256 tools/enumfuncs.py | sha256sum | cut -d' ' -f1)
if [ -n "${need:-}" ] || ! refcheck 2>/dev/null || [ "$(cat out/reference/.stamp 2>/dev/null)" != "$stamp" ]; then
    echo "== retail images -> out/reference/ (for scoring only; missing, stale, or not the ones progress/reference.sha256 names)"
    bash build/reference.sh
    refcheck || { echo "error: out/reference/ still differs from progress/reference.sha256" >&2; exit 1; }
    echo "$stamp" > out/reference/.stamp
fi

# Lithtech.exe's encrypted pages as the multiplayer demo has them, for
# placing our functions there (progress/targets.py `readable`): the demo out
# of rez/'s artifact chunks, its engine unpacked, retail's image with the
# pages filled in (tools/demoimports.py; out/ only, never committed)
if [ ! -f out/mpdemo/Lithtech-readable.exe ]; then
    echo "== Lithtech.exe's encrypted pages from the multiplayer demo (for placement only)"
    [ -f rez/demos/nolf2_mpdemo_en.exe ] || bash rez/assemble-artifacts.sh demos/nolf2_mpdemo_en.exe
    python3 tools/demoimports.py extract
    python3 tools/demoimports.py plain
fi

python3 tools/progress.py
echo
rc=0
if [ "$mode" = check ]; then
    python3 tools/ratchet.py check ${COMPLETE:+--complete} ${COVERED:+--covered} || rc=$?
else
    python3 tools/ratchet.py update ${ACCEPT_LOSSES:+--accept-losses} || rc=$?
fi
# ... the text in the images' data against the retail text, held to the
# differences progress/data-known.txt lists (update: drops the ones that are
# gone)
echo
python3 tools/datacheck.py "$mode" || rc=1
# ... and the float constants behind the masked relocations
echo
echo "float constants (tools/fpconst.py):"
python3 tools/fpconst.py --targets || rc=1
# ... and every vtable slot and every call and global our identically placed
# functions reach, against the shipped ones (progress/vtab-known.txt)
echo
echo "vtables and wiring (tools/vtabcheck.py):"
python3 tools/vtabcheck.py --targets || rc=1
# ... and what all of it rested on (the toolchains' digests checked), kept
# with the baseline when one is recorded
echo
python3 tools/evidence.py || rc=1
[ "$mode" = update ] && cp out/progress/evidence.json progress/evidence.json
exit $rc
