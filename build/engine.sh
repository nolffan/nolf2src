#!/usr/bin/env bash
# The engine's reconstruction loop (guides/02-the-loop.md): build one engine
# project, or recompile ONE of its files, and match what was compiled
# against the retail image, function by function (tools/exematch.py).
#
#   build/engine.sh <project> [link]       compile and link it (build.mk)
#   build/engine.sh <project> objs         compile its objects, no link
#   build/engine.sh <project> verify       compile its objects, then match
#                                          every one in the retail image
#   build/engine.sh <project>-one <file.cpp> [symbol-filter]
#                                          recompile one file, match only it
#   build/engine.sh server test            link server.dll, then load it
#                                          under Wine with its base occupied
#                                          and call CreateServer/DeleteServer
#                                          (tools/loadtest.c)
#
# <project> is a project of build/build.mk, as tools/dsp2mk.py names it from
# Monolith's workspace: `Lithtech` (Lithtech.exe) and `server` (server.dll)
# once src/Engine/runtime/winbuild/Engine.dsw is in the build (the skeleton
# package of docs/engine/PLAN.md); also snddrv, ServerDir, or any game
# project. The retail image a project is matched against is the one named
# like the project's output (out/reference/, build/reference.sh).
#
# The compiles are build/compile.sh's: in out/release-tree/ (src/ without its
# variant blocks), with the objects copied back here. The objects of a
# project and the source each compiles are read from the rules dsp2mk.py
# wrote (.build/*.mk of the tree that was built). A file compiled into both
# engine binaries -- most of server/, shared/, world/, model/, kernel/net --
# is two objects: `server-one x.cpp` rebuilds only server.dll's; run
# `Lithtech-one x.cpp` as well, or the exe's object goes stale.
#
# Runs in the build container (`make shell`).
set -e
source "$(dirname "$0")/env.sh"
cd "$REPO"

usage() {
    echo "usage: $0 <project> [link|objs|verify] | server test"
    echo "       $0 <project>-one <file.cpp> [symbol-filter]"
    exit 2
}
[ $# -ge 1 ] || usage

# The retail images: this checkout's out/reference/, or, in a tree under
# out/, the checkout's.
REF="${NOLF2_REFERENCE:-}"
if [ -z "$REF" ]; then
    for r in "$REPO/out/reference" "$REPO/../reference"; do
        [ -d "$r" ] && { REF="$r"; break; }
    done
fi
[ -n "$REF" ] || { echo "error: no out/reference/ -- run build/reference.sh" >&2; exit 1; }

# Where the build ran, and so where dsp2mk.py's rules are
BUILT_TREE="$REPO/out/release-tree"
case "$REPO" in */out/build-*|*/out/release-tree) BUILT_TREE="$REPO" ;; esac
[ -n "${NOLF2SRC_IN_RELEASE_TREE:-}" ] && BUILT_TREE="$REPO"

# rules: make sure the project's rules exist (a dry run of build.mk writes
# them), or fail saying the project is not in the build yet
rules() {
    local p="$1"
    if ! grep -qs "^P_${p}_OUT :=" "$BUILT_TREE"/.build/*.mk; then
        bash build/compile.sh -n "$p" >/dev/null 2>&1 || true
    fi
    if ! grep -qs "^P_${p}_OUT :=" "$BUILT_TREE"/.build/*.mk; then
        echo "error: build/build.mk has no project '$p'." >&2
        case "$p" in
            Lithtech|server)
                echo "       The engine's projects come from src/Engine/runtime/winbuild/Engine.dsw," >&2
                echo "       which build/build.mk does not read yet (the skeleton package," >&2
                echo "       docs/engine/PLAN.md)." >&2 ;;
        esac
        echo "       Projects it has: $(grep -ho '^P_[A-Za-z0-9_]*_OUT' "$BUILT_TREE"/.build/*.mk 2>/dev/null \
            | sed 's/^P_//; s/_OUT$//' | sort -u | tr '\n' ' ')" >&2
        exit 1
    fi
}
var() {   # var <make variable> -> its value in the generated rules
    grep -h "^$1 :=" "$BUILT_TREE"/.build/*.mk | head -1 | sed "s/^$1 := *//"
}
# the retail image a project's output is matched against
image() {
    local out f
    out="$(basename "$(var "P_$1_OUT")")"
    f="$(find "$REF" -maxdepth 1 -iname "$out" | head -1)"
    [ -n "$f" ] || { echo "error: no retail $out in $REF (build/reference.sh)" >&2; exit 1; }
    echo "$f"
}

# match <image> <obj>... [-- symbol-filter]
match() {
    local img="$1"; shift
    local args=() filter=""
    while [ $# -gt 0 ]; do
        if [ "$1" = "--" ]; then filter="${2:-}"; break; fi
        args+=("$1"); shift
    done
    if [ -n "$filter" ]; then
        python3 tools/exematch.py "$img" "${args[@]}" | grep -Ei "${filter}|^matched" || true
    else
        python3 tools/exematch.py "$img" "${args[@]}"
    fi
}

case "$1" in
    *-one)
        p="${1%-one}"
        tu="${2:-}"; [ -n "$tu" ] || usage
        rules "$p"
        want="$(basename "${tu%.*}").obj"
        obj=""
        for o in $(var "P_${p}_OBJS"); do
            [ "$(basename "${o,,}")" = "${want,,}" ] && obj="$o"
        done
        if [ -z "$obj" ]; then
            echo "error: project $p compiles no $want" >&2; exit 1
        fi
        bash build/compile.sh "$obj"
        match "$(image "$p")" "$obj" -- "${3:-}" ;;
    server)
        if [ "${2:-}" = test ]; then
            rules server
            bash build/compile.sh server ltmsg
            dll="$(var P_server_OUT)"
            msg="$(var P_ltmsg_OUT)"
            d="out/linktest"
            mkdir -p "$d"
            cp tools/loadtest.c "$dll" "$msg" "$d/"
            ( cd "$d" && run_cl /nologo /O1 loadtest.c /link /out:loadtest.exe \
                  kernel32.lib user32.lib ole32.lib >/dev/null &&
              nolf2src_tools_env && wine loadtest.exe "$(basename "$dll")" rebase )
            exit $?
        fi ;&
    *)
        p="$1"
        rules "$p"
        case "${2:-link}" in
            link)   bash build/compile.sh "$p" ;;
            objs)   bash build/compile.sh $(var "P_${p}_OBJS") ;;
            verify) bash build/compile.sh $(var "P_${p}_OBJS")
                    match "$(image "$p")" $(var "P_${p}_OBJS") ;;
            *)      usage ;;
        esac ;;
esac
