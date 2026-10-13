#!/usr/bin/env bash
# Create (or remove) an isolated git worktree that can BUILD and VERIFY, for
# working on several things at once -- typically one agent per package of
# docs/engine/PLAN.md, each in its own tree, so that one's half-finished edit
# never changes what another measures.
#
# A plain `git worktree add` is not enough, because what the build needs is
# not tracked:
#
#   toolchains/       the compilers and SDKs (a submodule, not checked out
#                     in a worktree)
#   rez/              the installed retail game (build/retail.sh), the
#                     Jupiter SDK (rez/sdk/, build/jupiter.sh) and the demo
#                     and patch artifacts (a submodule too)
#   out/reference/    the retail images the checks compare against
#                     (build/reference.sh)
#   ext/ffmpeg/       FFmpeg, which the modern build's Bink player is built
#                     on (build/ext.sh; a submodule)
#
# so they are copied in as HARD LINKS (`cp -al`): no extra space, and unlike
# a symbolic link a hard link resolves inside the build container, which
# `make` runs with the worktree itself mounted at /repo (a link pointing
# above the worktree would dangle there). Never edit a file under those
# in a worktree: it is the main checkout's file too.
#
# The worktree is .worktrees/<name> (gitignored) on a new branch <name>,
# started at HEAD or at the given start point. Builds go to the tree's own
# src/*/built and out/, so trees cannot corrupt each other's objects; a new
# worktree has none, so build first. Give each tree's containers their own
# names, or two `make`s collide on the default name:
#
#   make -C .worktrees/<name> all CONTAINER=<name>-build
#   make -C .worktrees/<name> progress CONTAINER=<name>-progress
#
# Commit verified work on the branch; merging it is the coordinator's
# (PLAN.md). `rm` removes the tree but keeps the branch.
#
# Usage:  tools/agentwt.sh add <name> [start]
#         tools/agentwt.sh rm  <name>
#         tools/agentwt.sh list
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WTROOT="$REPO/.worktrees"

case "${1:-list}" in
add)
    name="${2:?usage: agentwt.sh add <name> [start]}"
    dir="$WTROOT/$name"
    mkdir -p "$WTROOT"
    if [ ! -d "$dir" ]; then
        if git -C "$REPO" show-ref -q --verify "refs/heads/$name"; then
            git -C "$REPO" worktree add -q "$dir" "$name"
        else
            git -C "$REPO" worktree add -q -b "$name" "$dir" "${3:-HEAD}"
        fi
    fi
    # the submodules' contents and the reference images, hard-linked
    for d in toolchains rez out/reference ext/ffmpeg; do
        [ -d "$REPO/$d" ] || continue
        mkdir -p "$dir/$d"
        for t in "$REPO/$d"/* "$REPO/$d"/.[!.]*; do
            [ -e "$t" ] || continue
            b="$(basename "$t")"
            [ "$b" = .git ] && continue
            [ -e "$dir/$d/$b" ] || cp -al "$t" "$dir/$d/$b"
        done
    done
    [ -f "$REPO/out/reference/server.dll" ] \
        || echo "note: no out/reference/ yet -- run build/reference.sh in the main checkout"
    echo "tree:   $dir"
    echo "branch: $name"
    echo "build:  make -C $dir all CONTAINER=$name-build"
    ;;
rm)
    name="${2:?usage: agentwt.sh rm <name>}"
    git -C "$REPO" worktree remove --force "$WTROOT/$name"
    git -C "$REPO" worktree prune
    echo "removed $name (branch $name kept)"
    ;;
list)
    git -C "$REPO" worktree list
    ;;
*)  echo "usage: $0 {add|rm|list} [name] [start]"; exit 1 ;;
esac
