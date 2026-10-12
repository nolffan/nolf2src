#!/usr/bin/env bash
# Compile and link: build/build.mk, in parallel, in the tree that is built.
#
#   build/compile.sh [target...]     (inside the build container)
#
# Targets are build/build.mk's: all (the default), a project by its workspace
# name (ClientShellDLL, Object, ClientFxDLL, ClientRes, ServerRes, Launcher,
# ServerApp, or a library), or any output file. Started in a checkout it
# builds in out/release-tree/ (src/ without its variant blocks: build/env.sh,
# nolf2src_release_tree) and copies the outputs back into this checkout's
# src/; in a build/variant.sh tree, there. NOLF2SRC_JOBS sets the number of
# parallel jobs (default: the CPU count).
set -e
source "$(dirname "$0")/env.sh"
nolf2src_release_tree "$@"
cd "$REPO"
nolf2src_make "${@:-all}"
