#!/usr/bin/env bash
# The game directory as one file, to copy to the machine that plays it:
#
#   build/package.sh out/nolf2-<legacy|modern>-<release|debug> [<name>]
#
# writes two archives, each unpacking to <name>/ (by default the game
# directory's own name; then <name>/linux-run.sh -- see its header; Wine
# needed there -- or, on Windows, NOLF2.exe):
#
#   out/<name>-private.tar.gz   the whole directory, the retail game's data
#                               included: for your own machines, and anyone
#                               developing on the build
#   out/<name>-public.tar.gz    the same without anything that came from the
#                               retail game (MANIFEST.txt's `data` and
#                               `THIRD-PARTY` files), which its
#                               linux-install.sh / windows-install.bat copy
#                               out of the player's own disc images
#                               (build/mkinstall.py, from the lists in build/
#                               only: no disc image is needed here): the one
#                               to give to other people. Its SHA256SUMS lists
#                               every file of the archive and every file the
#                               scripts write; they refuse a directory that
#                               is not the archive unpacked.
#
# NOLF2_ARCHIVES (default "private public") says which to write; with
# "public" alone (the CI build, .github/workflows/ci.yml) the private one is
# not made.
#
# A game directory built without the retail game (NODISCS=1: it has
# NOT-PLAYABLE.txt, and it is out/<name>-nodiscs/) has no private archive:
# it is skipped, or an error if NOLF2_ARCHIVES asks for it. Its public
# archive is the same as one built with the retail game (NOT-PLAYABLE.txt is
# left out of it).
#
# build/all.sh runs it for the release build (step 6) and build/variant.sh
# for each variant, once its data and symbols are in place.
#
# Links are stored as the files they point to (-h). Each archive is a fresh
# install, whatever has been played in the directory: no saves (an empty
# Save/), no logs, no player profiles but the shipped default one,
# autoexec.cfg as the shipped one (autoexec.cfg.retail), none of what the
# launcher and the game write as they run (launchcmds.txt, display.cfg,
# BanList.txt) nor the per-machine state linux-run.sh creates; the public
# one has them too when their shipped copies ship with it (assets/game/),
# else its install scripts write them. nolf2cmds.txt, the engine's command file as the build
# writes it (build/nolf2cmds.sh), is in the private archive (for
# ext/tools/playtest.sh) but not the public one: the launcher never reads it
# (it writes launchcmds.txt).
# Each is written beside and renamed into place, so a failed run never
# leaves a truncated one; the <name>.tar.gz and plain .tar older builds made
# are removed.
set -e
OUT="${1:?usage: build/package.sh <game directory> [<name>]}"
OUT="${OUT%/}"
DIR="$(basename "$OUT")"
NAME="${2:-$DIR}"
PARENT="$(dirname "$OUT")"
PKG="$PARENT/$NAME-private.tar.gz"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVES=" ${NOLF2_ARCHIVES:-private public} "
NODISCS=
[ -f "$OUT/NOT-PLAYABLE.txt" ] && NODISCS=1

# The fresh files, staged beside the directory and renamed into it.
STAGE=".pkg-$NAME"
rm -rf "$PARENT/$STAGE"
mkdir -p "$PARENT/$STAGE"
trap 'rm -rf "$PARENT/$STAGE"' EXIT
cp "$OUT/autoexec.cfg.retail" "$PARENT/$STAGE/autoexec.cfg"
mkdir -p "$PARENT/$STAGE/Profiles"
cp "$OUT/Default.prf.retail" "$PARENT/$STAGE/Profiles/Default.prf"
bash "$HERE/nolf2cmds.sh" > "$PARENT/$STAGE/nolf2cmds.txt"
# <DIR>/... is <NAME>/... in the archives, and so is the stage
NAMES=(--transform="s|^$STAGE/|$NAME/|")
[ "$DIR" = "$NAME" ] || NAMES+=(--transform="s|^$DIR/|$NAME/|" --transform="s|^$DIR\$|$NAME|")

# what neither archive holds
EXCLUDE=(--exclude="$DIR/Save/*" --exclude="$DIR/Profiles/*" --exclude="$DIR/autoexec.cfg"
         --exclude="$DIR/nolf2cmds.txt" --exclude="$DIR/display.cfg" --exclude="$DIR/BanList.txt"
         --exclude='*.log' --exclude=run-cmds.txt
         --exclude=launchcmds.txt --exclude=cd --exclude='*.part')

rm -f "$PARENT/$NAME.tar" "$PARENT/$NAME.tar.gz"
if [[ $ARCHIVES == *" private "* ]] && [ -n "$NODISCS" ]; then
    if [ -n "${NOLF2_ARCHIVES:-}" ]; then
        echo "   $PKG: $OUT was built without the retail game, but NOLF2_ARCHIVES asks for it" >&2
        exit 1
    fi
    echo "   $PKG: skipped (built without the retail game)"
elif [[ $ARCHIVES == *" private "* ]]; then
    tar -C "$PARENT" -h -cf - "${EXCLUDE[@]}" \
        "${NAMES[@]}" \
        "$DIR" "$STAGE/autoexec.cfg" "$STAGE/Profiles/Default.prf" "$STAGE/nolf2cmds.txt" |
        gzip -6 > "$PKG.part"
    mv "$PKG.part" "$PKG"
    echo "   $PKG: $(du -h "$PKG" | cut -f1) (unpacks to $NAME/)"
fi
[[ $ARCHIVES == *" public "* ]] || exit 0

# The public archive: the install scripts beside the rest, the retail files
# left out.
PUB="$PARENT/$NAME-public.tar.gz"
python3 "$HERE/mkinstall.py" "$OUT" "$PARENT/$STAGE"
sed "s|^|$DIR/|" "$PARENT/$STAGE/disc-files.txt" > "$PARENT/$STAGE/exclude.txt"
echo "$DIR/NOT-PLAYABLE.txt" >> "$PARENT/$STAGE/exclude.txt"
# autoexec.cfg and the default profile: the install scripts write them when
# their shipped copies come from the discs; when those ship with the release
# (assets/game/, the 1.3 update's), the archive carries them too
SETTINGS=()
for s in autoexec.cfg Profiles/Default.prf; do
    grep -qxF "$s" "$PARENT/$STAGE/disc-files.txt" || SETTINGS+=("$STAGE/$s")
done
tar -C "$PARENT" -h -cf "$PARENT/$STAGE/public.tar" "${EXCLUDE[@]}" \
    --anchored --no-wildcards --exclude-from="$PARENT/$STAGE/exclude.txt" \
    "${NAMES[@]}" \
    "$DIR" "${SETTINGS[@]}" "$STAGE/linux-install.sh" "$STAGE/windows-install.bat"
# Last, SHA256SUMS: every file of the archive and every file the install
# scripts write, but the two they write only once, which the game rewrites
# (autoexec.cfg and Profiles/Default.prf). The scripts check the directory
# against it before they install, and `sha256sum -c SHA256SUMS` checks an
# install.
python3 - "$PARENT/$STAGE/public.tar" "$PARENT/$STAGE/disc-sums.txt" \
    > "$PARENT/$STAGE/SHA256SUMS" <<'PY'
import hashlib, sys, tarfile
lines = []
with tarfile.open(sys.argv[1]) as t:
    for m in t:
        rel = m.name.split("/", 1)[1] if "/" in m.name else ""
        # the two the game rewrites, when the archive carries them
        if m.isfile() and rel and rel not in ("autoexec.cfg", "Profiles/Default.prf"):
            lines.append(f"{hashlib.sha256(t.extractfile(m).read()).hexdigest()}  {rel}")
lines += open(sys.argv[2]).read().splitlines()
names = [l[66:] for l in lines]
if len(set(n.lower() for n in names)) != len(names):
    sys.exit("package.sh: a file twice in SHA256SUMS")
for l in sorted(lines, key=lambda l: l[66:].lower()):
    sys.stdout.write(l + "\n")
PY
tar -C "$PARENT" -rf "$PARENT/$STAGE/public.tar" --transform="s|^$STAGE/|$NAME/|" "$STAGE/SHA256SUMS"
gzip -6 < "$PARENT/$STAGE/public.tar" > "$PUB.part"
mv "$PUB.part" "$PUB"
echo "   $PUB: $(du -h "$PUB" | cut -f1) (unpacks to $NAME/; its data from the discs)"
