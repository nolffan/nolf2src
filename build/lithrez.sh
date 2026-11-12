#!/usr/bin/env bash
# lithrez, the command line tool for LithTech .rez archives, built from the
# lithtools submodule (ext/lithtools/tools/lithrez; C++17, CMake) into
# out/lithrez/lithrez, without its Qt GUI and tests: build/all.sh packs
# assets/rez/ into the game directory's nolf2src.rez with it. Built again
# only when its sources are newer than the binary.
#
#   build/lithrez.sh
set -e
SRC=ext/lithtools/tools/lithrez
OUT=out/lithrez
[ -f "$SRC/CMakeLists.txt" ] || {
    echo "error: ext/lithtools/ is empty -- it is a submodule: run git submodule update --init lithtools" >&2
    exit 1
}
if [ -x "$OUT/lithrez" ] &&
   [ -z "$(find "$SRC/CMakeLists.txt" "$SRC/cli" "$SRC/core" -newer "$OUT/lithrez" -print -quit)" ]; then
    exit 0
fi
cmake -S "$SRC" -B "$OUT" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DLITHREZ_BUILD_GUI=OFF -DLITHREZ_BUILD_TESTS=OFF >/dev/null
cmake --build "$OUT" >/dev/null
