#!/usr/bin/env bash
# Batch-decompile one shipped binary's app region to a single .c file.
#
#   tools/ghidra/decomp.sh out/reference/NOLF.exe 0x401000 0x409ed2 out/nolf-app.c
#
# The output is a READING AID, not source. Ghidra normalizes away exactly the
# things byte-matching depends on — loop form, declaration order, copy-ctor vs
# default-ctor-plus-assign, which local shares a register. Use it to get the
# control flow and the struct field offsets for free, then derive the actual
# source from tools/exedump.py as usual (guides/03).
#
# Needs ghidra.analyzeHeadless on PATH (the snap provides /snap/bin/) and
# roughly 2 GB of free RAM — the JVM is OOM-killed without it.
set -e
BIN="${1:?usage: decomp.sh <binary> <lo> <hi> <out.c>}"
LO="${2:?}"; HI="${3:?}"; OUT="$(realpath -m "${4:?}")"
# optional 5th arg: a file of function starts (one 0x-prefixed address per
# line, as `tools/enumfuncs.py <bin> --csv` produces). Ghidra's analysis
# cannot see functions reached only through `push imm32` and folds them into
# their neighbour, so seed them.
STARTS="${5:+$(realpath -m "$5")}"
HEADLESS="$(command -v ghidra.analyzeHeadless || echo /snap/bin/ghidra.analyzeHeadless)"
# The snap runs in a private mount namespace where /tmp is NOT the host /tmp,
# so a project directory under /tmp is invisible to it. Keep it under $HOME.
PROJ="$(mktemp -d -p "$HOME" ghidra-decomp.XXXXXX)"
cp "$BIN" "$PROJ/"
[ -n "$STARTS" ] && cp "$STARTS" "$PROJ/starts.txt"
mkdir -p "$(dirname "$OUT")"
"$HEADLESS" "$PROJ" decomp \
    -import "$PROJ/$(basename "$BIN")" \
    -scriptPath "$(cd "$(dirname "$0")" && pwd)" \
    -postScript DumpDecomp.java "$PROJ/out.c" "$LO" "$HI" ${STARTS:+"$PROJ/starts.txt"} \
    -deleteProject
# The script runs inside the snap's private mount namespace, where neither
# /tmp nor an arbitrary path is the one we see. Stage both ends under $PROJ.
cp "$PROJ/out.c" "$OUT"
rm -rf "$PROJ"
echo "wrote $OUT"
