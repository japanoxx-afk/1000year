@echo off
setlocal
call "%~dp0..\native\vcvars.cmd"
if errorlevel 1 exit /b 1
cd /d "%~dp0.."
cl /nologo /utf-8 /std:c++17 /EHsc /W4 /O2 /MT tests\replay_native_tests.cpp /Fo:.tools\replay_native_tests.obj /Fe:.tools\replay_native_tests.exe /link /DYNAMICBASE:NO /FIXED
if errorlevel 1 exit /b 1
.tools\replay_native_tests.exe
exit /b %errorlevel%
