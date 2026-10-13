#!/usr/bin/env bash
# tools/rendertest/run.sh [seconds-to-screenshot]: runs out/rendertest/rtest.exe
# under Wine and Xvfb (in the build container); prints its log (rtest.log)
# and leaves shot.png (the screen after a few seconds) and wine.log beside it.
cd "$(dirname "$0")/../../out/rendertest" || exit 1
rm -f rtest.log shot.png
export WINEDEBUG=${WINEDEBUG:--all,+seh,err+d3d}
cat > inner.sh <<IN
wine rtest.exe > wine.log 2>&1 &
PID=\$!
sleep ${1:-8}
xwd -root -silent | convert xwd:- shot.png
wait \$PID
echo "exit \$?" >> wine.log
IN
timeout 120 xvfb-run -a -s "-screen 0 1024x768x24" bash inner.sh
grep -v '^RunConsoleString' rtest.log 2>/dev/null
tail -1 wine.log
