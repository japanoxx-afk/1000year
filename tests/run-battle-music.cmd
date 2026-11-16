@echo off
setlocal
call "%~dp0..\native\vcvars.cmd"
if errorlevel 1 exit /b 1
cd /d "%~dp0.."
cl /nologo /utf-8 /std:c++17 /EHsc /W4 /O2 /MT tests\battle_music_tests.cpp /Fo:.tools\battle_music_tests.obj /Fe:.tools\battle_music_tests.exe /link user32.lib gdi32.lib ole32.lib strmiids.lib /DYNAMICBASE:NO /FIXED
if errorlevel 1 exit /b 1
.tools\battle_music_tests.exe "%~1" %2
exit /b %errorlevel%
