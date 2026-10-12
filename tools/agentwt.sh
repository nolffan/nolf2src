#!/usr/bin/env bash
# Create (or remove) an isolated git worktree that can BUILD and VERIFY, for
# working on several things at once -- typically several agents in parallel,
# each in its own tree, so that one's half-finished edit never changes what
# another measures, and every edit comes back already verified.
#
# A plain `git worktree add` is not enough, because what the build needs is
# not tracked:
#
#   toolchains/       the compilers (a submodule, not checked out in a
#                     worktree)
#   out/reference/    the retail images the checks compare against
#                     (build/reference.sh)
#   rez/              the installed retail game the build takes its data
#                     from (a submodule too; build/retail.sh)
#
# so they are symlinked in, RELATIVELY: the worktree lives inside the
# checkout (.worktrees/<name>, gitignored), and the build container mounts
# the checkout at /repo, so a relative link resolves both on the host and in
# the container. An absolute host path would not resolve in the container.
# toolchains/ and rez/ stay real directories (the submodules', uninitialised
# in a worktree); each compiler tree, and each entry of rez/, is linked.
#
# The worktree is a new branch, wt/<name>, started at HEAD (or at the given
# start point -- another branch, e.g. a wt/ branch to build on): uncommitted
# changes in the main checkout are not in it. Commit verified work there and
# merge or cherry-pick it from the main checkout; `rm` removes the tree but
# keeps the branch (delete it with `git branch -D wt/<name>` once merged).
# Each worktree gets its own src/*/Release and src/lithshared/out, so trees
# cannot corrupt each other's objects. A new worktree has none: build what
# you work on first (in the container):
#
#   make shell                                 # from the MAIN checkout
#   cd /repo/.worktrees/<name>
#   build/libs.sh all && build/engine.sh server   # then the *-one loops
#
# Usage:  tools/agentwt.sh add <name> [start]   # prints the host and container paths
#         tools/agentwt.sh rm  <name>
#         tools/agentwt.sh list
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WTROOT="$REPO/.worktrees"

case "${1:-list}" in
add)
    name="${2:?usage: agentwt.sh add <name>}"
    dir="$WTROOT/$name"
    mkdir -p "$WTROOT"
    if [ ! -d "$dir" ]; then
        if git -C "$REPO" show-ref -q --verify "refs/heads/wt/$name"; then
            git -C "$REPO" worktree add -q "$dir" "wt/$name"
        else
            git -C "$REPO" worktree add -q -b "wt/$name" "$dir" "${3:-HEAD}"
        fi
    fi
    # the compiler trees, one link each, inside the worktree's toolchains/
    mkdir -p "$dir/toolchains"
    for t in "$REPO"/toolchains/*/; do
        t="$(basename "$t")"
        [ -e "$dir/toolchains/$t" ] || ln -s "../../../toolchains/$t" "$dir/toolchains/$t"
    done
    mkdir -p "$dir/out"
    [ -L "$dir/out/reference" ] || ln -s ../../../out/reference "$dir/out/reference"
    # rez/: its scripts and checksums, and the installed game in games/
    mkdir -p "$dir/rez"
    for t in "$REPO"/rez/*; do
        t="$(basename "$t")"
        [ -e "$dir/rez/$t" ] || ln -s "../../../rez/$t" "$dir/rez/$t"
    done
    [ -f "$REPO/out/reference/server.dll" ] \
        || echo "note: no out/reference/ yet -- run build/reference.sh in the main checkout"
    echo "host:      $dir"
    echo "container: /repo/.worktrees/$name   (make shell, from the main checkout)"
    echo "branch:    wt/$name"
    ;;
rm)
    name="${2:?usage: agentwt.sh rm <name>}"
    # the links first, so nothing can reach through them to the real trees
    find "$WTROOT/$name/toolchains" "$WTROOT/$name/rez" "$WTROOT/$name/out" -maxdepth 1 -type l -delete 2>/dev/null || true
    git -C "$REPO" worktree remove --force "$WTROOT/$name" 2>/dev/null || rm -rf "$WTROOT/$name"
    git -C "$REPO" worktree prune
    echo "removed $name (branch wt/$name kept)"
    ;;
list)
    git -C "$REPO" worktree list
    ;;
*)  echo "usage: $0 {add|rm|list} [name]"; exit 1 ;;
esac
