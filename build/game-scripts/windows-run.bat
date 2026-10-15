@echo off
rem windows-run.bat -- start No One Lives Forever 2 (built from source) on
rem Windows, without the launcher.
rem
rem   windows-run.bat [engine args...]
rem
rem Double-click it, or give it engine arguments, e.g.
rem   windows-run.bat +ScreenWidth 2560 +ScreenHeight 1440
rem Later arguments override earlier ones, and these come last.
rem
rem It does what the launcher (NOLF2.exe) does, without the launcher or the
rem registry: it starts `Lithtech.exe -cmdfile run-cmds.txt` in this folder.
rem The command file, rewritten every run, is nolf2cmds.txt's rez stack --
rem the game's archives, then custom\, the game DLLs built from source, last,
rem so that the 1.3 update's (zeroed) DLLs cannot override them -- and then
rem the arguments. On the first run autoexec.cfg -- the game's settings,
rem rewritten on every exit -- starts as a copy of the shipped one
rem (autoexec.cfg.retail). The intro movies are off (+DisableMovies 1) with
rem RAD's binkw32.dll, as linux-run.sh has them; on in the modern build,
rem whose own Bink player (MANIFEST.txt lists it as EXT) plays them.
rem
rem build/all.sh installs it with CRLF line endings, which cmd needs.
setlocal
cd /d "%~dp0"
if not exist Lithtech.exe goto notgame
if not exist nolf2cmds.txt goto notgame
if not exist GAME.REZ goto notinstalled
if not exist autoexec.cfg copy /y autoexec.cfg.retail autoexec.cfg >nul
if not exist Save mkdir Save

set "NOLF2_REZ="
set /p NOLF2_REZ=<nolf2cmds.txt
set "NOLF2_MOVIES=1"
for /f "delims=" %%L in ('findstr /b /c:"EXT " MANIFEST.txt 2^>nul') do set "NOLF2_MOVIES=0"
rem (the redirection first: "... 1 >file" would be read as "1>file")
>run-cmds.txt echo %NOLF2_REZ% +DisableMovies %NOLF2_MOVIES% %*
Lithtech.exe -cmdfile run-cmds.txt
exit /b %errorlevel%

:notgame
echo windows-run.bat: put it in the game folder (beside Lithtech.exe and nolf2cmds.txt).
pause
exit /b 1

:notinstalled
echo windows-run.bat: the game's data is not here yet -- run windows-install.bat first.
pause
exit /b 1
