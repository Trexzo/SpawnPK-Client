[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).ProviderPath
$Launcher=Join-Path $Root 'tools\windows\Invoke-R291-Owner.ps1'
$Python=Join-Path $Root 'tools\windows\r291\R291-Windows-R290-Acceptance.py'
$Checks=0
function Assert-R291([bool]$Ok,[string]$Reason) {
 if (!$Ok) { throw "R291_NATIVE_SOURCE_SAFETY_FAIL $Reason" }
 $script:Checks++
}
Assert-R291 (Test-Path -LiteralPath $Launcher -PathType Leaf) 'missing launcher'
Assert-R291 (Test-Path -LiteralPath $Python -PathType Leaf) 'missing Python overlay'
Assert-R291 (((Get-FileHash -LiteralPath $Launcher -Algorithm SHA256).Hash) -eq '91B7F02A5985C37C43F1AD1C8917C407EB56FD213398F4FCE0E0E4F6249EBACC') 'launcher hash mismatch'
$Tok=$null;$Err=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($Launcher,[ref]$Tok,[ref]$Err)
Assert-R291 (@($Err).Count -eq 0) 'PowerShell parse error'
$Source=Get-Content -LiteralPath $Launcher -Raw
Assert-R291 ($Source.Contains('[switch]$RunNativeGui')) 'GUI opt-in switch missing'
Assert-R291 ($Source.Contains('$PackageSha256')) 'source bundle SHA gate missing'
Assert-R291 ($Source.Contains('R291_BOOTSTRAP_REFUSE_EXISTING_OUTPUT')) 'existing output guard missing'
$Test=Join-Path $env:TEMP ('r291-native-public-only-' + [guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($Test)
try {
 $Inputs=Join-Path $Test 'empty-inputs';[void][System.IO.Directory]::CreateDirectory($Inputs)
 $Out=Join-Path $Test 'NEVER_CREATED'
 $Missing=Join-Path $Test 'missing.zip'
 $ErrorText=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $Inputs -Package $Missing -Output $Out 2>&1 | Out-String)
 $Result=$LASTEXITCODE
 Assert-R291 ($Result -ne 0) 'missing source bundle unexpectedly accepted'
 Assert-R291 ($ErrorText -match 'R291_BOOTSTRAP_PACKAGE_MISSING') 'missing bundle rejection not explicit'
 Assert-R291 (-not (Test-Path -LiteralPath $Out)) 'missing bundle caused output write'
 $Fake=Join-Path $Test 'tampered.zip'
 [System.IO.File]::WriteAllBytes($Fake,[byte[]](11,22,33,44,55))
 $ErrorText=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $Inputs -Package $Fake -Output $Out 2>&1 | Out-String)
 $Result=$LASTEXITCODE
 Assert-R291 ($Result -ne 0) 'tampered bundle unexpectedly accepted'
 Assert-R291 ($ErrorText -match 'R291_BOOTSTRAP_PACKAGE_HASH_MISMATCH') 'tampered ZIP failure not explicit'
 Assert-R291 (-not (Test-Path -LiteralPath $Out)) 'tampered bundle caused output write'
 $ErrorText=(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -InputDir $Inputs -Package $Fake -Output $Out -RunNativeGui 2>&1 | Out-String)
 $Result=$LASTEXITCODE
 Assert-R291 ($Result -ne 0) 'opt-in with tampered source succeeded'
 Assert-R291 ($ErrorText -match 'R291_BOOTSTRAP_PACKAGE_HASH_MISMATCH') 'GUI opt-in bypassed ZIP hash gate'
 Assert-R291 (-not (Test-Path -LiteralPath $Out)) 'GUI opt-in with tampered source wrote output'
} finally {
 if (Test-Path -LiteralPath $Test) { [System.IO.Directory]::Delete($Test,$true) }
}
Write-Host "R291_NATIVE_WINDOWS_FAIL_CLOSED_PASS checks=$Checks owner_private_inputs=NOT_USED gui=NOT_TESTED"
exit 0
