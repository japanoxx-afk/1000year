@echo off
if /I "%VSCMD_ARG_TGT_ARCH%"=="x86" exit /b 0
set "mythVS="
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "mythVS=%%i"
if not defined mythVS exit /b 1
call "%mythVS%\VC\Auxiliary\Build\vcvars32.bat" >nul
exit /b %errorlevel%
