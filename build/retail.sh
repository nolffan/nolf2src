# Sourced by build/all.sh, build/reference.sh and the Makefile: the retail
# game the build takes its data from -- No One Lives Forever 2 (Europe) with
# the English 1.3 update, the version Monolith's source release is, installed
# by the rez/ submodule from the redump images of its two discs and the
# update (rez/README.md) -- and whether it is the right one.
#
# RETAIL_RELEASE  rez/'s name for it
# retail_dir      prints rez/games/nolf2-eu-1.3, if it is installed
# retail_install  fetches the two disc images from archive.org and installs
#                 the release from them and the update (rez/patches/),
#                 unless it is installed already
#                 (rez/fetch-isos.sh, rez/install-games.sh; `make` runs it)
# retail_verify   checks every installed file against rez/games.sha256 (the
#                 Makefile runs it before every build; NOLF2_SKIP_RETAIL_CHECK=1
#                 skips it)
RETAIL_RELEASE=nolf2-eu-1.3

retail_rez() {
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    if [ ! -f "$here/rez/install-games.sh" ]; then
        echo "error: rez/ is empty -- the disc images and their installer are the rez/" >&2
        echo "       submodule: run git submodule update --init (see rez/README.md)" >&2
        return 1
    fi
    echo "$here/rez"
}

retail_dir() {
    local rez d
    rez="$(retail_rez)" || return 1
    d="$rez/games/$RETAIL_RELEASE"
    if [ -f "$d/MANIFEST.txt" ] && [ -f "$d/Lithtech.exe" ] && [ -f "$d/Update_v1x3.rez" ]; then
        echo "$d"; return 0
    fi
    echo "error: the retail game is not installed in $d" >&2
    echo "       run make (or, in make shell, build/retail.sh's retail_install)" >&2
    return 1
}

retail_install() {
    local rez
    rez="$(retail_rez)" || return 1
    [ -f "$rez/games/$RETAIL_RELEASE/MANIFEST.txt" ] && return 0
    echo "== fetching and installing $RETAIL_RELEASE (rez/: about 1.1 GB from archive.org, once)"
    "$rez/fetch-isos.sh" "$RETAIL_RELEASE" && "$rez/install-games.sh" "$RETAIL_RELEASE"
}

retail_verify() {
    local rez d
    rez="$(retail_rez)" || return 1
    d="$(retail_dir)" || return 1
    [ "${NOLF2_SKIP_RETAIL_CHECK:-0}" = 1 ] && return 0
    # a stamp skips re-hashing 1.8 GB on every build while the files are unchanged
    local stamp key
    stamp="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/out/.retail-verified"
    key="$(cd "$d" && find . -type f -printf '%p %s %T@\n' | sort | sha256sum | cut -d' ' -f1)"
    if [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$key" ]; then
        return 0
    fi
    echo "== checking $d against rez/games.sha256"
    if ! python3 -I "$rez/tools/install.py" --verify "$rez/games" "$RETAIL_RELEASE"; then
        echo "error: the installed $RETAIL_RELEASE does not match rez/games.sha256." >&2
        echo "       Reinstall it: rez/install-games.sh --force $RETAIL_RELEASE" >&2
        return 1
    fi
    mkdir -p "$(dirname "$stamp")" && echo "$key" > "$stamp"
}
