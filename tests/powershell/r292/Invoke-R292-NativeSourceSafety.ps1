[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).ProviderPath
$Launcher=Join-Path $Root 'tools\windows\Invoke-R292-Owner.ps1'
$Gate=Join-Path $Root 'tools\windows\r292\R292-Owner-Readiness-Gate.py'
$Checks=0
function Assert-R292([bool]$Ok,[string]$Reason) {
 if (!$Ok) { throw "R292_WIN32_SAFETY_FAIL $Reason" }
 $script:Checks++
}
Assert-R292 (Test-Path -LiteralPath $Launcher -PathType Leaf) 'no launcher'
Assert-R292 (Test-Path -LiteralPath $Gate -PathType Leaf) 'no gate'
Assert-R292 (((Get-FileHash -LiteralPath $Launcher -Algorithm SHA256).Hash) -eq '9EE44BC5B872526D9021762A59004EFBB8C829AB74BD43882965DBA5BB6CAA9D') 'launcher digest drift'
$Tokens=$null;$Errors=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($Launcher,[ref]$Tokens,[ref]$Errors)
Assert-R292 (@($Errors).Count -eq 0) 'syntax error'
$Body=Get-Content -LiteralPath $Launcher -Raw
Assert-R292 ($Body.Contains('[switch]$RunNativeGui')) 'no GUI opt-in'
Assert-R292 ($Body.Contains('R292_NOT_ADMITTED_OR_GUI_FAILED')) 'missing readiness block'
Assert-R292 ($Body.Contains('R292_SOURCE_BUNDLE_SHA256_MISMATCH')) 'no source SHA protection'
Assert-R292 ($Body.IndexOf('R292_SOURCE_BUNDLE_SHA256_MISMATCH') -lt $Body.IndexOf('ExtractToDirectory')) 'extraction before hash'
$Test=Join-Path $env:TEMP ('R292-Win32-Safe-'+[guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($Test)
try {
 $InputDir=Join-Path $Test 'empty-inputs'
 [void][System.IO.Directory]::CreateDirectory($InputDir)
 $Out=Join-Path $Test 'UNTOUCHED'
 $Missing=Join-Path $Test 'absent.zip'
 $Text=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $InputDir -Package $Missing -Output $Out 2>&1 | Out-String)
 $Status=$LASTEXITCODE
 Assert-R292 ($Status -ne 0) 'missing package accepted'
 Assert-R292 ($Text -match 'R292_SOURCE_BUNDLE_MISSING') 'missing package error absent'
 Assert-R292 (-not (Test-Path -LiteralPath $Out)) 'missing package wrote owner output'
 $Tampered=Join-Path $Test 'wrong.zip'
 [System.IO.File]::WriteAllBytes($Tampered,[byte[]](12,23,34))
 $Text=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $InputDir -Package $Tampered -Output $Out 2>&1 | Out-String)
 $Status=$LASTEXITCODE
 Assert-R292 ($Status -ne 0) 'tampered source ZIP accepted'
 Assert-R292 ($Text -match 'R292_SOURCE_BUNDLE_SHA256_MISMATCH') 'bad ZIP SHA error absent'
 Assert-R292 (-not (Test-Path -LiteralPath $Out)) 'tampered ZIP wrote owner output'
 $Text=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $InputDir -Package $Tampered -Output $Out -RunNativeGui 2>&1 | Out-String)
 $Status=$LASTEXITCODE
 Assert-R292 ($Status -ne 0) 'GUI opt-in bypassed tampered source'
 Assert-R292 ($Text -match 'R292_SOURCE_BUNDLE_SHA256_MISMATCH') 'opt-in source hash error absent'
 Assert-R292 (-not (Test-Path -LiteralPath $Out)) 'opt-in tampered ZIP wrote owner output'
} finally {
 if (Test-Path -LiteralPath $Test) { [System.IO.Directory]::Delete($Test,$true) }
}
Write-Host "R292_REAL_WINDOWS_FAIL_CLOSED_PASS checks=$Checks owner_game_assets=NONE gui=NOT_TESTED"
exit 0
