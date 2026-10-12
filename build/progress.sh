#!/usr/bin/env bash
# The scoreboard: how much of the build is byte-identical to the retail game.
#
#   make progress | make progress-update   (build/progress.sh check|update)
#
# Not adapted to NOLF2 yet. tools/progress.py and tools/ratchet.py are
# nolfsrc's, which know NOLF's binaries: each image's application and CRT
# regions, its libraries, d3d.ren. What is here already is the reference
# side -- build/reference.sh extracts the retail 1.3 binaries into
# out/reference/ with their function and vtable tables -- and the build's
# outputs, in src/Game/built/Final/ and src/libs/built/Final/.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo "build/progress.sh: the scoreboard is not adapted to NOLF2 yet (see its header)." >&2
echo "                   build/reference.sh extracts the retail binaries and their tables." >&2
exit 1
