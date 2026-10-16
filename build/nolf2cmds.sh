#!/usr/bin/env bash
# The game directory's nolf2cmds.txt, as a fresh build writes it:
#
#   build/nolf2cmds.sh
#
# windows-run.bat (the legacy build's) and tools/playtest.sh start the engine
# with this rez stack, as the retail NOLF2.exe launcher does with its own
# launchcmds.txt ("Lithtech.exe -cmdfile ..."). The order is the launcher's
# (later archives override earlier ones; the engine opens Engine.REZ
# itself), with the 1.3 update's archive (its UpdateCommandLine1) and then
# custom/ -- our game DLLs -- last, so that nothing overrides them (the
# retail launcher put custom/ before the update). build/all.sh writes it
# into the game directory, build/package.sh into the private archive and
# the legacy build's public one (the modern build has no windows-run.bat).
printf -- '-rez GAME.REZ -rez GAME2.REZ -rez GAMEDLL.REZ -rez SOUND.REZ -rez Update_v1x3.rez -rez custom\r\n'
