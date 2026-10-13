#!/usr/bin/env bash
# tools/rendertest/build.sh: builds rtest.exe, a test harness for the
# renderer (render_a, render_b), into out/rendertest/. Run it in the build
# container after `build/engine.sh Lithtech link`: it compiles rtest.cpp with
# Lithtech.exe's flags and links it with every object and library of
# Lithtech.exe's link (out of its .rsp), /FORCE:MULTIPLE so that rtest's
# WinMain wins over client.cpp's. Never part of the game or the score.
set -e
source "$(dirname "$0")/../../build/env.sh"
cd "$REPO"
OUT="$REPO/out/rendertest"
mkdir -p "$OUT"
rsp="$REPO/src/Engine/built/Final/Lithtech/Lithtech.exe.rsp"
[ -f "$rsp" ] || { echo "error: no $rsp -- run build/engine.sh Lithtech link" >&2; exit 1; }
# Lithtech.exe's compile of a render_b file: its directory and flags
r=$(grep "call compile,[^,]*/d3dtexinterface.obj," out/release-tree/.build/engine.mk | head -1 | python3 -c '
import sys
a=sys.stdin.read().split("call compile,",1)[1].split(",")
print(a[1]+"|"+a[6])')
dir=${r%%|*}; fl=${r#*|}; fl=$(echo "$fl" | sed 's#/Fo[^ ]*##')
cd "$REPO/$dir"
run_cl $fl /Fo$(nolf2src_wpath "$OUT/rtest.obj") /c $(nolf2src_wpath "$REPO/tools/rendertest/rtest.cpp") > "$OUT/cl.log" 2>&1 < /dev/null || true
tr -d '\r' < "$OUT/cl.log" | grep -v '^rtest.cpp$' || true
{ echo "$(nolf2src_wpath "$OUT/rtest.obj")"; echo "/FORCE:MULTIPLE"; echo "/out:$(nolf2src_wpath "$OUT/rtest.exe")"
  tr ' ' '\n' < "$rsp" | grep -v '^/out:\|^/map:\|^$'; } > "$OUT/link.rsp"
run_link @$(nolf2src_wpath "$OUT/link.rsp") > "$OUT/link.log" 2>&1 < /dev/null || true
tr -d '\r' < "$OUT/link.log" | grep -v 'LNK4006\|LNK4088\|LNK4098\|previous definition\|Creating library' || true
ls -la "$OUT/rtest.exe"
