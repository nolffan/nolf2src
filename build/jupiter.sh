# Sourced by build/all.sh and the Makefile: the LithTech Jupiter SDK (build
# 51, March 2002), the engine licensees' SDK, whose source has what
# Monolith's release lacks for ServerDir.dll -- WONAPI, its WON/Titan
# library (ext/tools/jupitersrc.py). build/discs.py installs its WONAPI
# files from your own image of the SDK's CD (build/sdk-files.txt); nothing
# of it is committed here (docs/LICENSE_NOTES.md).
#
# JUPITER_SDK      the name of the install directory
# NOLF2_SDK        where it is installed: out/retail/lithtech-jupiter-51 by
#                  default (build/variant.sh sets it to the checkout's)
# jupiter_source   prints out/retail/lithtech-jupiter-51, if it is installed
# jupiter_install  installs the WONAPI source from the SDK's image in isos/
#                  (or $NOLF2_ISOS), unless it is installed already from
#                  the same build/sdk-files.txt (`make sdk`; every build with
#                  the retail game runs it)
# jupiter_verify   checks every installed file against build/sdk-files.txt
#                  (build/all.sh runs it before every build that compiles
#                  ServerDir.dll)
JUPITER_SDK=lithtech-jupiter-51

jupiter_repo() { (cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); }

jupiter_root() { echo "${NOLF2_SDK:-$(jupiter_repo)/out/retail/$JUPITER_SDK}"; }

jupiter_source() {
    local d
    d="$(jupiter_root)"
    if [ -f "$d/.retail-files" ] && [ -f "$d/Game/Libs/WONAPI/WONAPI.dsp" ]; then
        echo "$d"; return 0
    fi
    echo "error: the Jupiter SDK's source is not installed in $d" >&2
    echo "       run make sdk (it needs your image of the SDK's CD in isos/: see docs/BUILDING.md)" >&2
    return 1
}

jupiter_install() {
    local d list
    d="$(jupiter_root)"
    list="$(jupiter_repo)/build/sdk-files.txt"
    if [ -f "$d/.retail-files" ] && cmp -s "$d/.retail-files" "$list"; then
        return 0
    fi
    echo "== installing the WONAPI source of $JUPITER_SDK from your image of its CD (build/discs.py, once)"
    python3 "$(jupiter_repo)/build/discs.py" install sdk "$d"
}

jupiter_verify() {
    local d
    d="$(jupiter_source)" || return 1
    if ! python3 "$(jupiter_repo)/build/discs.py" verify sdk "$d" >/dev/null; then
        echo "error: the installed $JUPITER_SDK does not match build/sdk-files.txt." >&2
        echo "       Install it again: rm -rf $d && make sdk" >&2
        return 1
    fi
}
