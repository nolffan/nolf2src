# Source this to get the VC6-under-Wine build environment. It runs inside the
# build container (docker/Dockerfile; `make shell` gives you one), where Wine
# is on PATH and the toolchain is toolchains/ in this checkout
# (toolchains/README.md). The compile and link command lines themselves are
# build/build.mk's.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for f in msvc-6.00-8966/BIN/cl.exe msvc-6.00-9782/Common/MSDev98/Bin/RC.EXE dxsdk-8.1/include/d3d8.h; do
    if [ ! -f "$REPO/toolchains/$f" ]; then
        echo "error: toolchains/$f not found -- the toolchain is missing (toolchains/README.md)" >&2
        return 1 2>/dev/null || exit 1
    fi
done
if ! command -v wine >/dev/null 2>&1; then
    echo "error: wine is not on PATH -- run this inside the build container (make shell)" >&2
    return 1 2>/dev/null || exit 1
fi
export WINEDEBUG=-all
export WINEDLLOVERRIDES="mscoree,mshtml="

# Extra flags for every compile and every link, for the debug and modern
# builds (build/variant.sh sets them). Empty otherwise -- and the release
# build's command lines are then exactly what the project files say.
export NOLF2SRC_CFLAGS="${NOLF2SRC_CFLAGS:-}"
export NOLF2SRC_LDFLAGS="${NOLF2SRC_LDFLAGS:-}"
export NOLF2SRC_RCFLAGS="${NOLF2SRC_RCFLAGS:-}"    # resource scripts: /d NAME
# They are only allowed in the trees build/variant.sh makes (out/build-*/):
# anywhere else they would put NOLF2SRC_DEBUG or NOLF2SRC_MODERN code into the
# objects `make progress` scores, which must only ever be the release build.
if [ -n "$NOLF2SRC_CFLAGS$NOLF2SRC_LDFLAGS$NOLF2SRC_RCFLAGS" ]; then
    case "$REPO" in
        */out/build-*) ;;
        *) echo "error: NOLF2SRC_CFLAGS / LDFLAGS / RCFLAGS are set, but this is not a" >&2
           echo "       build/variant.sh tree ($REPO). Unset them; use make debug/modern." >&2
           return 1 2>/dev/null || exit 1 ;;
    esac
fi

# The release build compiles src/ WITHOUT its NOLF2SRC_MODERN /
# NOLF2SRC_DEBUG blocks, not merely with them switched off: a block the
# compiler skips still moves everything below it, and VC6 lets the file's
# layout decide where some out-of-line inline functions go, so enough
# skipped blocks can change the release binary (tools/releasesrc.py).
# build/compile.sh calls this first, with its own arguments: in a checkout it
# brings out/release-tree/ up to date -- src/ with those blocks resolved as
# the release build sees them, the same build/ and tools/, this checkout's
# build outputs -- runs the script there, copies the build outputs back into
# this checkout's src/ (where `make progress` and the checks read them) and
# exits with the script's status. In a build/variant.sh tree (out/build-*/,
# which must see the blocks), or inside the release tree, it does nothing.
nolf2src_release_tree() {
    [ -n "${NOLF2SRC_IN_RELEASE_TREE:-}" ] && return 0
    case "$REPO" in */out/build-*) return 0 ;; esac
    local tree="$REPO/out/release-tree" script rc=0
    script="$(basename "${BASH_SOURCE[1]}")"
    mkdir -p "$tree"
    python3 "$REPO/tools/releasesrc.py" sync "$REPO/src" "$tree/src" || exit 1
    python3 "$REPO/tools/releasesrc.py" outputs "$REPO/src" "$tree/src" || exit 1
    rm -rf "$tree/build" "$tree/tools"
    tar -C "$REPO" -cf - --exclude='__pycache__' build tools | tar -C "$tree" -xf -
    [ -L "$tree/toolchains" ] || ln -s ../../toolchains "$tree/toolchains"
    ( cd "$tree" && NOLF2SRC_IN_RELEASE_TREE=1 bash "build/$script" "$@" ) || rc=$?
    python3 "$REPO/tools/releasesrc.py" outputs "$tree/src" "$REPO/src" || exit 1
    exit $rc
}

# Compile and link through build/build.mk, in this tree (run it after
# nolf2src_release_tree): every listed target, NOLF2SRC_JOBS at a time
# (default: one per CPU), each job's output kept together.
nolf2src_make() {
    make -C "$REPO" -f build/build.mk --no-print-directory -Otarget \
        -j"${NOLF2SRC_JOBS:-$(nproc)}" "$@"
}
