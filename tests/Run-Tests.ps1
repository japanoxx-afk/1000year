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
& scripts\build.ps1
& tests\Test-Installer.ps1
} finally {Pop-Location}

