$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$target=Join-Path $root ('.tools\update-fixture-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $target | Out-Null
Set-Content (Join-Path $target 'settings.json') 'preserve settings'
Set-Content (Join-Path $target 'game-save.dat') 'preserve game'
Set-Content (Join-Path $target 'MythLauncher.exe') 'old launcher'
& "$root\scripts\apply-update.ps1" -Package "$root\dist\MythLauncher.zip" -Target $target -LauncherPid 0 -NoRestart
if((Get-FileHash "$target\MythLauncher.exe").Hash -ne (Get-FileHash "$root\dist\MythLauncher.exe").Hash){throw 'Updated launcher mismatch'}
if((Get-Content "$target\settings.json") -ne 'preserve settings' -or (Get-Content "$target\game-save.dat") -ne 'preserve game'){throw 'User files changed'}
$backup=Get-ChildItem $target -Directory -Filter 'update-backup-*'|Select-Object -First 1
if((Get-Content (Join-Path $backup.FullName 'MythLauncher.exe')) -ne 'old launcher'){throw 'Backup missing'}
Write-Output 'PASS installer upgrades launcher, backs up old version and preserves user/game files'
$bad=Join-Path $target 'bad'
Expand-Archive "$root\dist\MythLauncher.zip" $bad
Set-Content "$bad\MythLauncher.exe" 'tampered'
Compress-Archive "$bad\*" "$target\bad.zip"
$failed=$false
try{& "$root\scripts\apply-update.ps1" -Package "$target\bad.zip" -Target $target -LauncherPid 0 -NoRestart}catch{$failed=$true}
if(!$failed){throw 'Corrupt package accepted'}
if((Get-FileHash "$target\MythLauncher.exe").Hash -ne (Get-FileHash "$root\dist\MythLauncher.exe").Hash){throw 'Corrupt package changed installed file'}
Write-Output 'PASS corrupt package rejected before changing installed files'
$lockedTarget=Join-Path $target 'rollback'
New-Item -ItemType Directory $lockedTarget | Out-Null
Set-Content "$lockedTarget\MythLauncher.exe" 'old executable'
Set-Content "$lockedTarget\PATCHNOTES.md" 'locked notes'
$lock=[IO.File]::Open("$lockedTarget\PATCHNOTES.md",[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$failed=$false
try{try{& "$root\scripts\apply-update.ps1" -Package "$root\dist\MythLauncher.zip" -Target $lockedTarget -LauncherPid 0 -NoRestart}catch{$failed=$true}}finally{$lock.Dispose()}
if(!$failed){throw 'Expected file lock failure'}
if((Get-Content "$lockedTarget\MythLauncher.exe") -ne 'old executable'){throw 'Rollback did not restore old launcher'}
$entrypoint=(Get-Content "$root\dist\package.json" -Raw | ConvertFrom-Json).Entrypoint
if(Test-Path (Join-Path $lockedTarget $entrypoint)){throw 'Rollback left new entrypoint'}
Write-Output 'PASS mid-install file lock rolls back earlier writes'
