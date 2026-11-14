param([string]$GameExe="")
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
New-Item -ItemType Directory -Force .tools | Out-Null
& "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe" /nologo /target:exe /out:.tools\CoreTests.exe /reference:System.Net.Http.dll /reference:System.Web.Extensions.dll tests\CoreTests.cs src\Core.cs src\Updates.cs
if($LASTEXITCODE -ne 0){throw 'Test compilation failed'}
& .tools\CoreTests.exe $GameExe
if($LASTEXITCODE -ne 0){throw 'Core tests failed'}
& "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe" /nologo /platform:x86 /codepage:65001 /reference:System.Web.Extensions.dll /out:.tools\ReplayArchiveTests.exe tests\ReplayArchiveTests.cs src\ReplayArchive.cs src\Core.cs
if($LASTEXITCODE -ne 0){throw 'Replay test compilation failed'}
& .tools\ReplayArchiveTests.exe
if($LASTEXITCODE -ne 0){throw 'Replay archive tests failed'}
& tests\run-replay-native.cmd
if($LASTEXITCODE -ne 0){throw 'Native replay tests failed'}
& scripts\build.ps1
& tests\Test-Installer.ps1
} finally {Pop-Location}

