@echo off
setlocal
call "%~dp0vcvars.cmd"
if errorlevel 1 exit /b 1
cd /d "%~dp0.."
if not exist dist\native mkdir dist\native
set "extra="
set "output=MythReplay"
if /I "%~1"=="test" set "extra=/DMYTH_REPLAY_TEST"
if /I "%~1"=="test" set "output=MythReplayTest"
cl /nologo /utf-8 /std:c++17 /EHsc /W4 /O2 /MT /LD %extra% native\replay.cpp /Fo:dist\native\%output%.obj /Fe:dist\native\%output%.dll /link user32.lib
exit /b %errorlevel%
