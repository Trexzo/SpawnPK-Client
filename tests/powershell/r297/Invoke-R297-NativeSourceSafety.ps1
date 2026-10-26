[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).ProviderPath
$Launcher=Join-Path $Root 'tools\windows\Invoke-R297-Owner.ps1'
$Gate=Join-Path $Root 'tools\windows\r297\R297-Owner-Readiness.py'
$Checks=0
function Assert-R297([bool]$Ok,[string]$Reason) {
 if (!$Ok) { throw "R297_WIN32_SAFETY_FAIL $Reason" }
 $script:Checks++
}
Assert-R297 (Test-Path -LiteralPath $Launcher -PathType Leaf) 'no launcher'
Assert-R297 (Test-Path -LiteralPath $Gate -PathType Leaf) 'no gate'
Assert-R297 (((Get-FileHash -LiteralPath $Launcher -Algorithm SHA256).Hash) -eq '2259805542FDAEF2C0EA48D2DB83A766528EF0CB692B4A33C8BD7C41E275067F') 'launcher digest drift'
$Tokens=$null;$Errors=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($Launcher,[ref]$Tokens,[ref]$Errors)
Assert-R297 (@($Errors).Count -eq 0) 'syntax error'
$Body=Get-Content -LiteralPath $Launcher -Raw
Assert-R297 ($Body.Contains('[switch]$RunNativeGui')) 'no GUI opt-in'
Assert-R297 ($Body.Contains('R297_R295_NOT_ADMITTED_OR_GUI_FAILED')) 'missing readiness block'
Assert-R297 ($Body.Contains('R297_SOURCE_BUNDLE_HASH_MISMATCH')) 'no source SHA protection'
Assert-R297 ($Body.IndexOf('R297_SOURCE_BUNDLE_HASH_MISMATCH') -lt $Body.IndexOf('ExtractToDirectory')) 'extraction before hash'
$Test=Join-Path $env:TEMP ('R297-Win32-Safe-'+[guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($Test)
try {
 $InputDir=Join-Path $Test 'empty-inputs'
 [void][System.IO.Directory]::CreateDirectory($InputDir)
 $Out=Join-Path $Test 'UNTOUCHED'
 $Missing=Join-Path $Test 'absent.zip'
 $Text=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $InputDir -Package $Missing -Output $Out 2>&1 | Out-String)
 $Status=$LASTEXITCODE
 Assert-R297 ($Status -ne 0) 'missing package accepted'
 Assert-R297 ($Text -match 'R297_SOURCE_BUNDLE_MISSING') 'missing package error absent'
 Assert-R297 (-not (Test-Path -LiteralPath $Out)) 'missing package wrote owner output'
 $Tampered=Join-Path $Test 'wrong.zip'
 [System.IO.File]::WriteAllBytes($Tampered,[byte[]](12,23,34))
 $Text=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $InputDir -Package $Tampered -Output $Out 2>&1 | Out-String)
 $Status=$LASTEXITCODE
 Assert-R297 ($Status -ne 0) 'tampered source ZIP accepted'
 Assert-R297 ($Text -match 'R297_SOURCE_BUNDLE_HASH_MISMATCH') 'bad ZIP SHA error absent'
 Assert-R297 (-not (Test-Path -LiteralPath $Out)) 'tampered ZIP wrote owner output'
 $Text=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $InputDir -Package $Tampered -Output $Out -RunNativeGui 2>&1 | Out-String)
 $Status=$LASTEXITCODE
 Assert-R297 ($Status -ne 0) 'GUI opt-in bypassed tampered source'
 Assert-R297 ($Text -match 'R297_SOURCE_BUNDLE_HASH_MISMATCH') 'opt-in source hash error absent'
 Assert-R297 (-not (Test-Path -LiteralPath $Out)) 'opt-in tampered ZIP wrote owner output'
} finally {
 if (Test-Path -LiteralPath $Test) { [System.IO.Directory]::Delete($Test,$true) }
}
Write-Host "R297_REAL_WINDOWS_FAIL_CLOSED_PASS checks=$Checks owner_game_assets=NONE gui=NOT_TESTED"
exit 0
