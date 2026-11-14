param([string]$OutputDirectory='')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$out=if($OutputDirectory){[IO.Path]::GetFullPath($OutputDirectory)}else{Join-Path $root 'dist'}
New-Item -ItemType Directory -Force $out,(Join-Path $out 'compat') | Out-Null
$csc=Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
& "$root\native\build-replay.cmd"
if($LASTEXITCODE -ne 0){throw 'Native replay build failed'}
& $csc /nologo /target:winexe /platform:x86 /optimize+ /codepage:65001 /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll /reference:System.Net.Http.dll /resource:"$root\scripts\apply-update.ps1,Myth.UpdateInstaller" /resource:"$root\compat\portable.json,Myth.PortableRecipe" /resource:"$root\compat\hd.json,Myth.HDRecipe" /resource:"$root\compat\wide.json,Myth.WideRecipe" /resource:"$root\compat\replay-wide-0.6.0.json,Myth.LegacyWide060" /resource:"$root\third-party\ddraw.dll,Myth.DDraw" /resource:"$root\dist\native\MythReplay.dll,Myth.ReplayEngine" /out:"$out\MythLauncher.exe" "$root\src\Core.cs" "$root\src\Launcher.cs" "$root\src\Updates.cs" "$root\src\Replays.cs" "$root\src\ReplayArchive.cs" "$root\src\ReplayProcess.cs"
if($LASTEXITCODE -ne 0){throw 'Compile failed'}
$version=[regex]::Match((Get-Content "$root\src\Core.cs" -Raw),'Version="([^"]+)"').Groups[1].Value
$entrypoint="MythLauncher-$version.exe"
Copy-Item "$out\MythLauncher.exe" (Join-Path $out $entrypoint) -Force
Copy-Item "$root\PATCHNOTES.md","$root\scripts\apply-update.ps1" $out -Force
Copy-Item "$root\third-party\ddraw.dll","$root\third-party\LICENSE.cnc-ddraw","$root\compat\portable.json" (Join-Path $out 'compat') -Force
$files=@('MythLauncher.exe',$entrypoint,'PATCHNOTES.md','apply-update.ps1','compat\ddraw.dll','compat\LICENSE.cnc-ddraw','compat\portable.json')
@{Version=$version;Entrypoint=$entrypoint;Files=@($files|ForEach-Object{@{Path=$_;SHA256=(Get-FileHash (Join-Path $out $_)).Hash.ToLowerInvariant()}})}|ConvertTo-Json -Depth 5|Set-Content "$out\package.json" -Encoding utf8
Compress-Archive -Path "$out\MythLauncher.exe",(Join-Path $out $entrypoint),"$out\PATCHNOTES.md","$out\apply-update.ps1","$out\package.json","$out\compat" -DestinationPath "$out\MythLauncher.zip" -Force
(Get-FileHash "$out\MythLauncher.zip").Hash.ToLowerInvariant()|Set-Content "$out\MythLauncher.zip.sha256" -Encoding ascii

