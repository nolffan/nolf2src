# Sourced by build/all.sh and the Makefile: the LithTech Jupiter SDK (build
# 51, March 2002), the engine licensees' SDK, whose source has what
# Monolith's release lacks for ServerDir.dll -- WONAPI and CServerDir_Titan
# (tools/jupitersrc.py). The rez/ submodule fetches its CD image from
# archive.org and installs its "Source Code" file group (rez/README.md,
# "sdk/"); nothing of it is committed here (LICENSE-NOTES.md).
#
# JUPITER_SDK      rez/'s name for it
# jupiter_source   prints rez/sdk/lithtech-jupiter-51, if it is installed
# jupiter_install  fetches the SDK's image (about 637 MB, once) and installs
#                  its source, unless that is done already
#                  (rez/fetch-isos.sh, rez/install-games.sh; `make` runs it)
# jupiter_verify   checks every installed file against rez/sdk.sha256
#                  (build/all.sh runs it before every build)
JUPITER_SDK=lithtech-jupiter-51

jupiter_rez() {
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    if [ ! -f "$here/rez/install-games.sh" ]; then
        echo "error: rez/ is empty -- the Jupiter SDK and its installer are the rez/" >&2
        echo "       submodule: run git submodule update --init (see rez/README.md)" >&2
        return 1
    fi
    echo "$here/rez"
}

jupiter_source() {
    local rez d
    rez="$(jupiter_rez)" || return 1
    d="$rez/sdk/$JUPITER_SDK"
    if [ -f "$d/MANIFEST.txt" ] && [ -f "$d/Game/Libs/WONAPI/WONAPI.dsp" ]; then
        echo "$d"; return 0
    fi
    echo "error: the Jupiter SDK's source is not installed in $d" >&2
    echo "       run make (or, in make shell, build/jupiter.sh's jupiter_install)" >&2
    return 1
}

jupiter_install() {
    local rez
    rez="$(jupiter_rez)" || return 1
    [ -f "$rez/sdk/$JUPITER_SDK/MANIFEST.txt" ] && return 0
    echo "== fetching and installing $JUPITER_SDK (rez/: about 637 MB from archive.org, once)"
    "$rez/fetch-isos.sh" "$JUPITER_SDK" && "$rez/install-games.sh" "$JUPITER_SDK"
}

jupiter_verify() {
    local rez
    rez="$(jupiter_rez)" || return 1
    jupiter_source >/dev/null || return 1
    if ! python3 -I "$rez/tools/install.py" --verify "$rez/games" "$JUPITER_SDK" >/dev/null; then
        echo "error: the installed $JUPITER_SDK does not match rez/sdk.sha256." >&2
        echo "       Reinstall it: rez/install-games.sh --force $JUPITER_SDK" >&2
        return 1
    fi
}
