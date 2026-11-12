# Sourced by build/env.sh and build/variant.sh.
#
# nolf2src_tree_layout <tree>: build/ and the tools copied into one of the
# build's own trees (out/release-tree/, out/build-<variant>/), the tools at
# <tree>/ext/tools/ so that they take <tree> for the project (as their
# layout.py works it out), and every other submodule of ext/ (the compilers,
# the retail game where build/retail.sh looks for it, lithrez's source, the
# modern build's FFmpeg) a link to this checkout's. A tree made before the
# submodules moved to ext/ had a link for ext/ itself, and tools/ and links
# for toolchains, rez and lithtools at its top: those go first.
nolf2src_tree_layout() {
    local repo tree="$1" d n
    repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    if [ -L "$tree/ext" ]; then rm "$tree/ext"; fi
    rm -rf "$tree/tools"
    rm -f "$tree/toolchains" "$tree/rez" "$tree/lithtools"
    mkdir -p "$tree/ext"
    [ -d "$tree/ext" ] && [ ! -L "$tree/ext" ] || {
        echo "error: $tree/ext is not a directory" >&2; return 1; }
    rm -rf "$tree/build" "$tree/ext/tools"
    tar -C "$repo" -cf - --exclude='__pycache__' --exclude='.git' build ext/tools |
        tar -C "$tree" -xf - || return 1
    for d in "$repo"/ext/*; do
        n="$(basename "$d")"
        [ "$n" = tools ] || [ -L "$tree/ext/$n" ] ||
            ln -s "../../../ext/$n" "$tree/ext/$n" || return 1
    done
}
