#!/usr/bin/env bash
# The game directory as one file, to copy to the machine that plays it:
#
#   build/package.sh out/nolf2-<legacy|modern>-<release|debug>
#
# writes out/<name>.tar.gz, which unpacks to <name>/ (then <name>/run.sh --
# see its header; Wine needed there). build/all.sh runs it for the release
# build (step 6) and build/variant.sh for each variant, once its data and
# symbols are in place.
#
# Links are stored as the files they point to (-h). The archive is a fresh
# install, whatever has been played in the directory: no saves (an empty
# Save/), no logs, no player profiles but the shipped default one,
# autoexec.cfg as the shipped one (autoexec.cfg.retail),
# nolf2cmds.txt as the build writes it (build/nolf2cmds.sh), and none of
# the per-machine state run.sh creates. The archive is written beside and renamed into
# place, so a failed run never leaves a truncated one, and a plain .tar an
# older build made is removed with it.
set -e
OUT="${1:?usage: build/package.sh <game directory>}"
OUT="${OUT%/}"
NAME="$(basename "$OUT")"
PARENT="$(dirname "$OUT")"
PKG="$PARENT/$NAME.tar.gz"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The fresh files, staged beside the directory and renamed into it.
STAGE=".pkg-$NAME"
rm -rf "$PARENT/$STAGE"
mkdir -p "$PARENT/$STAGE"
trap 'rm -rf "$PARENT/$STAGE"' EXIT
cp "$OUT/autoexec.cfg.retail" "$PARENT/$STAGE/autoexec.cfg"
mkdir -p "$PARENT/$STAGE/Profiles"
cp "$OUT/Default.prf.retail" "$PARENT/$STAGE/Profiles/Default.prf"
bash "$HERE/nolf2cmds.sh" > "$PARENT/$STAGE/nolf2cmds.txt"

tar -C "$PARENT" -h -cf - \
    --exclude="$NAME/Save/*" --exclude="$NAME/Profiles/*" --exclude="$NAME/autoexec.cfg" --exclude="$NAME/nolf2cmds.txt" \
    --exclude='*.log' --exclude=run-cmds.txt --exclude=cd --exclude='*.part' \
    --transform="s|^$STAGE/|$NAME/|" \
    "$NAME" "$STAGE/autoexec.cfg" "$STAGE/Profiles/Default.prf" "$STAGE/nolf2cmds.txt" |
    gzip -6 > "$PKG.part"
mv "$PKG.part" "$PKG"
rm -f "$(dirname "$OUT")/$NAME.tar"
echo "   $PKG: $(du -h "$PKG" | cut -f1) (unpacks to $NAME/)"
