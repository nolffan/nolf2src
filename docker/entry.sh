#!/bin/bash
# Entry point of the build container (docker/Dockerfile).
#
# The container runs as the invoking user's uid, which has no home in the
# image: HOME is a scratch directory, and the Wine prefix lives in the
# checkout (out/wineprefix, created on first use, removed by `make clean`) so
# it belongs to that user and survives between runs.
export HOME="${HOME:-/tmp/home}"
[ -w "$HOME" ] || export HOME=/tmp/home
mkdir -p "$HOME"
export WINEPREFIX="${WINEPREFIX:-/repo/out/wineprefix}"
export WINEDEBUG="${WINEDEBUG:--all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=}"
if [ ! -f "$WINEPREFIX/system.reg" ]; then
    echo "== initialising the Wine prefix ($WINEPREFIX)"
    mkdir -p "$WINEPREFIX"
    wine wineboot -u >/dev/null 2>&1
    wineserver -w
fi
cd /repo 2>/dev/null || true
exec "$@"
