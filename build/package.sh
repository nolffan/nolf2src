#!/usr/bin/env bash
# The game directory as one file, to copy to the machine that plays it:
#
#   build/package.sh out/nolf2-<legacy|modern>-<release|debug>
#
# writes two archives, each unpacking to <name>/ (then <name>/linux-run.sh --
# see its header; Wine needed there):
#
#   out/<name>-private.tar.gz   the whole directory, the retail game's data
#                               included: for your own machines, and anyone
#                               developing on the build
#   out/<name>-public.tar.gz    the same without anything that came from the
#                               retail game (MANIFEST.txt's `data` and
#                               `THIRD-PARTY` files), which its
#                               linux-install.sh / windows-install.bat copy
#                               out of the player's own disc images and 1.3
#                               update (tools/mkinstall.py): the one to give
#                               to other people. It needs the images of both
#                               releases' discs in rez/isos/ (rez/fetch-isos.sh
#                               nolf2-eu nolf2-usa); without them it is
#                               skipped.
#
# NOLF2_ARCHIVES (default "private public") says which to write; with
# "public" alone (the CI build, .github/workflows/public-archives.yml) the
# private one is not made, and no disc images is an error, not a skip.
#
# build/all.sh runs it for the release build (step 6) and build/variant.sh
# for each variant, once its data and symbols are in place.
#
# Links are stored as the files they point to (-h). Each archive is a fresh
# install, whatever has been played in the directory: no saves (an empty
# Save/), no logs, no player profiles but the shipped default one,
# autoexec.cfg as the shipped one (autoexec.cfg.retail), nolf2cmds.txt as
# the build writes it (build/nolf2cmds.sh), and none of the per-machine
# state linux-run.sh and linux-run-launcher.sh create; the public one has
# neither autoexec.cfg nor the default profile, which its install scripts
# write.
# Each is written beside and renamed into place, so a failed run never
# leaves a truncated one; the <name>.tar.gz and plain .tar older builds made
# are removed.
set -e
OUT="${1:?usage: build/package.sh <game directory>}"
OUT="${OUT%/}"
NAME="$(basename "$OUT")"
PARENT="$(dirname "$OUT")"
PKG="$PARENT/$NAME-private.tar.gz"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVES=" ${NOLF2_ARCHIVES:-private public} "

# The fresh files, staged beside the directory and renamed into it.
STAGE=".pkg-$NAME"
rm -rf "$PARENT/$STAGE"
mkdir -p "$PARENT/$STAGE"
trap 'rm -rf "$PARENT/$STAGE"' EXIT
cp "$OUT/autoexec.cfg.retail" "$PARENT/$STAGE/autoexec.cfg"
mkdir -p "$PARENT/$STAGE/Profiles"
cp "$OUT/Default.prf.retail" "$PARENT/$STAGE/Profiles/Default.prf"
bash "$HERE/nolf2cmds.sh" > "$PARENT/$STAGE/nolf2cmds.txt"

# what neither archive holds
EXCLUDE=(--exclude="$NAME/Save/*" --exclude="$NAME/Profiles/*" --exclude="$NAME/autoexec.cfg"
         --exclude="$NAME/nolf2cmds.txt" --exclude='*.log' --exclude=run-cmds.txt
         --exclude=launchcmds.txt --exclude=cd --exclude='*.part')

rm -f "$PARENT/$NAME.tar" "$PARENT/$NAME.tar.gz"
if [[ $ARCHIVES == *" private "* ]]; then
    tar -C "$PARENT" -h -cf - "${EXCLUDE[@]}" \
        --transform="s|^$STAGE/|$NAME/|" \
        "$NAME" "$STAGE/autoexec.cfg" "$STAGE/Profiles/Default.prf" "$STAGE/nolf2cmds.txt" |
        gzip -6 > "$PKG.part"
    mv "$PKG.part" "$PKG"
    echo "   $PKG: $(du -h "$PKG" | cut -f1) (unpacks to $NAME/)"
fi
[[ $ARCHIVES == *" public "* ]] || exit 0

# The public archive: the install scripts beside the rest, the retail files
# left out.
PUB="$PARENT/$NAME-public.tar.gz"
rc=0
python3 "$HERE/../tools/mkinstall.py" "$OUT" "$PARENT/$STAGE" || rc=$?
if [ $rc = 3 ] && [ -n "${NOLF2_ARCHIVES:-}" ]; then
    echo "   $PUB: no disc images, but NOLF2_ARCHIVES asks for it" >&2
    exit 1
elif [ $rc = 3 ]; then
    echo "   $PUB: skipped (no disc images)"
    rm -f "$PUB"
    exit 0
elif [ $rc != 0 ]; then
    exit $rc
fi
sed "s|^|$NAME/|" "$PARENT/$STAGE/disc-files.txt" > "$PARENT/$STAGE/exclude.txt"
tar -C "$PARENT" -h -cf - "${EXCLUDE[@]}" \
    --anchored --no-wildcards --exclude-from="$PARENT/$STAGE/exclude.txt" \
    --transform="s|^$STAGE/|$NAME/|" \
    "$NAME" "$STAGE/nolf2cmds.txt" "$STAGE/linux-install.sh" "$STAGE/windows-install.bat" |
    gzip -6 > "$PUB.part"
mv "$PUB.part" "$PUB"
echo "   $PUB: $(du -h "$PUB" | cut -f1) (unpacks to $NAME/; its data from the discs)"
