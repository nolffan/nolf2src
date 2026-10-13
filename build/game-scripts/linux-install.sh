#!/usr/bin/env bash
# linux-install.sh -- install the game data from your own NOLF2.
#
#   ./linux-install.sh <NOLF2 directory>
#   ./linux-install.sh                 (finds it in your Wine prefix)
#
# <NOLF2 directory> is No One Lives Forever 2 as its setup installed it from
# your two discs, updated to 1.3 (English) -- the European or the USA
# release; the update is Sierra's nolf2-update_1x3.exe. Installed with Wine,
# it is in the prefix's drive_c (with no argument the script looks it up in
# the registry of $WINEPREFIX, then of ~/.wine); installed on Windows, copy
# the folder over or mount the drive. rez/ (github.com/nolffan/rez) also
# installs it from disc images, without Windows or Wine:
# `install-games.sh nolf2-eu-1.3`.
#
# The script copies the game's data out of that directory into this one --
# the .rez archives (with the retail game DLLs inside them zeroed: the game
# DLLs here are built from source), the movies, the shipped settings, and
# Bink and the Microsoft runtime where this build uses them -- and checks
# every file it writes against its SHA-256. Your NOLF2 is only read, and
# nothing else here is changed. It can be run again: a file already in
# place is checked and kept. Then play with ./run.sh (or ./run-launcher.sh).
#
# It needs bash, dd, sha256sum, base64, head, stat and find (GNU coreutils
# and findutils; a Steam Deck has them). The list of files, at the end of
# this script, says for each one which bytes of which installed file it is
# made of (tools/mkinstall.py).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$HERE/$(basename "${BASH_SOURCE[0]}")"
ME=linux-install.sh

for t in dd sha256sum base64 head stat sed find; do
    command -v "$t" >/dev/null || { echo "$ME: needs $t" >&2; exit 1; }
done

data() { sed -n '/^__NOLF2_INSTALL_DATA__$/,$p' "$SELF" | tail -n +2; }

# winepath <prefix> <C:\path>: a Windows path of a Wine prefix, as a Linux one
winepath() {
    local drive="${2:0:1}" rest="${2:2}"
    rest="${rest//\\//}"
    printf '%s/dosdevices/%s:%s' "$1" "${drive,,}" "$rest"
}

# installdir <prefix>: where the prefix's registry says NOLF2 is
installdir() {
    local reg="$1/system.reg" dir
    [ -f "$reg" ] || return 1
    dir=$(sed -n '/^\[Software\\\\\(Wow6432Node\\\\\)\{0,1\}Monolith Productions\\\\No One Lives Forever 2\\\\1\.0\]/I,/^$/{
        s/^"InstallDir"="\(.*\)"[[:space:]]*$/\1/p
    }' "$reg" | head -1)
    [ -n "$dir" ] || return 1
    dir="${dir//\\\\/\\}"
    winepath "$1" "$dir"
}

SRC="${1:-}"
if [ -z "$SRC" ]; then
    for prefix in "${WINEPREFIX:-}" "$HOME/.wine"; do
        [ -n "$prefix" ] || continue
        if d=$(installdir "$prefix") && [ -d "$d" ]; then SRC=$d; break; fi
    done
    if [ -z "$SRC" ]; then
        echo "$ME: no NOLF2 in the registry of ${WINEPREFIX:+$WINEPREFIX or }$HOME/.wine" >&2
        echo "  give the directory you installed it in: $ME <NOLF2 directory>" >&2
        exit 1
    fi
fi
[ -d "$SRC" ] || { echo "$ME: $SRC: no such directory" >&2; exit 1; }
SRC="$(cd "$SRC" && pwd)"
[ "$SRC" != "$HERE" ] || { echo "$ME: $SRC is this directory; give your installed NOLF2" >&2; exit 1; }
echo "installing from $SRC"

# The installed game's files, by lower-cased path (Windows does not care
# about case, and setup and the update do not agree on it), and the Wine
# prefix's system folders, where setup puts the Microsoft runtime.
declare -A FILES SYSFILES
while IFS= read -r p; do FILES[${p,,}]=$p; done < <(find -L "$SRC" -maxdepth 3 -type f -printf '%P\n')
case "$SRC" in */drive_c/*)
    win="${SRC%%/drive_c/*}/drive_c/windows"
    for sys in "$win/syswow64" "$win/system32"; do
        [ -d "$sys" ] || continue
        while IFS= read -r p; do
            [ -n "${SYSFILES[${p,,}]:-}" ] || SYSFILES[${p,,}]="$sys/$p"
        done < <(find -L "$sys" -maxdepth 1 -type f -iname '*.dll' -printf '%P\n')
    done ;;
esac

# The sources: each file of the install the list uses, found and of the
# right size (a wrong version of the game fails here, before anything is
# written). Only the Microsoft runtime (opt) may be missing or another
# version, and the settings (own) another size.
declare -A SPATH SSIZE SNAME
bad=0
while read -r tag n size sha kind name; do
    [ "$tag" = S ] || continue
    SSIZE[$n]=$size; SNAME[$n]=$name
    p=${FILES[${name,,}]:-}
    if [ -n "$p" ]; then p="$SRC/$p"; else p=${SYSFILES[${name,,}]:-}; fi
    if [ -z "$p" ]; then
        [ "$kind" = opt ] || { echo "$ME: no $name in $SRC" >&2; bad=1; }
        continue
    fi
    SPATH[$n]=$p
    if [ "$kind" = - ] && [ "$(stat -L -c %s "$p")" != "$size" ]; then
        echo "$ME: $p is not the 1.3 one ($(stat -L -c %s "$p") bytes, not $size)" >&2
        bad=1
    fi
done < <(data)
if [ $bad = 1 ]; then
    echo "$ME: that is not NOLF2 updated to 1.3 (English); see the top of this script" >&2
    exit 1
fi

# The files.
ok() {  # ok <path> <size> <sha>: is the file there, and right?
    [ -f "$1" ] && [ "$(stat -c %s "$1")" = "$2" ] &&
        [ "$(sha256sum < "$1" | cut -d' ' -f1)" = "$3" ]
}
OPTNOTE="Windows has its own; under Wine only run-launcher.sh needs MFC42.DLL"
written=0 kept=0 skipped=0 skip=1 whole=
while read -r tag a b c d; do
    case "$tag" in
    F)  name=$a; dest="$HERE/$a"; size=$b; sha=$c; flag=$d; part="$dest.part"; skip=0; whole=
        if [ "$flag" = once ] && [ -e "$dest" ]; then skip=1; kept=$((kept + 1))
        elif ok "$dest" "$size" "$sha"; then skip=1; kept=$((kept + 1))
        else
            echo "$a"
            mkdir -p "$(dirname "$dest")"
            : > "$part"
        fi ;;
    C)  [ $skip = 0 ] && [ -z "$whole" ] || continue
        src=${SPATH[$a]:-}
        if [ -z "$src" ] || [ "$(stat -L -c %s "$src")" != "${SSIZE[$a]}" ]; then
            case "$flag" in
            opt)  echo "  skipped: not in $SRC, or another version ($OPTNOTE)"
                  rm -f "$part"; skip=1; skipped=$((skipped + 1)); continue ;;
            own|once) whole=$src; continue ;;   # the player's own settings
            esac
            echo "$ME: ${SNAME[$a]}: missing or the wrong size" >&2; exit 1
        fi
        dd if="$src" of="$part" bs=1M iflag=skip_bytes,count_bytes \
            skip="$b" count="$c" oflag=append conv=notrunc status=none ;;
    Z)  [ $skip = 0 ] && [ -z "$whole" ] || continue
        head -c "$a" /dev/zero >> "$part" ;;
    L)  [ $skip = 0 ] && [ -z "$whole" ] || continue
        printf '%s' "$a" | base64 -d >> "$part" ;;
    E)  [ $skip = 1 ] && continue
        [ -z "$whole" ] || cp "$whole" "$part"
        if ! ok "$part" "$size" "$sha"; then
            case "$flag" in
            opt)  echo "  skipped: another version in $SRC ($OPTNOTE)"
                  rm -f "$part"; skipped=$((skipped + 1)); continue ;;
            own|once) echo "  not the shipped one: your own settings, taken as they are" ;;
            *)    rm -f "$part"
                  echo "$ME: $name came out wrong (not the 1.3 file, or a disk error?); the files before it are in place" >&2
                  exit 1 ;;
            esac
        fi
        mv -f "$part" "$dest"
        written=$((written + 1)) ;;
    esac
done < <(data | sed -n '/^F /,$p')
mkdir -p "$HERE/Save"
note=
[ $skipped = 0 ] || note=", $skipped skipped"
echo "done: $written files written, $kept already in place$note. Play with ./run.sh"
exit 0
