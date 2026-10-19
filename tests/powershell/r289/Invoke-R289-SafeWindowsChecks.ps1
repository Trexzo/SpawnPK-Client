[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).ProviderPath
$R288 = Join-Path $Root 'tools\windows\Invoke-R288-Owner-Acceptance.ps1'
$R286 = Join-Path $Root 'tools\windows\Invoke-R286-Guarded-Windows.ps1'
$R287 = Join-Path $Root 'tools\windows\R287-Owner-Readiness.py'
$ExpectedHash = '7F7BE191DBC01CC3E2117D6ED005C34ABC68811112CACB993843F87EF9A4BA32'
$Checks = 0
function Assert-R289([bool]$Ok,[string]$Message) {
    if (-not $Ok) { throw "R289_WINDOWS_FAIL $Message" }
    $script:Checks++
}
Assert-R289 (Test-Path -LiteralPath $R288 -PathType Leaf) 'R288 launcher missing'
Assert-R289 (Test-Path -LiteralPath $R286 -PathType Leaf) 'R286 launcher missing'
Assert-R289 (Test-Path -LiteralPath $R287 -PathType Leaf) 'R287 probe missing'
Assert-R289 (((Get-FileHash -LiteralPath $R288 -Algorithm SHA256).Hash) -eq $ExpectedHash) 'R288 source drift'
foreach ($Script in @($R286,$R288)) {
    $Tokens=$null; $Errors=$null
    $Null=[System.Management.Automation.Language.Parser]::ParseFile($Script,[ref]$Tokens,[ref]$Errors)
    Assert-R289 (@($Errors).Count -eq 0) "PowerShell parse error: $Script"
}
$TestRoot = Join-Path $env:TEMP ('SpawnPK-R289-PublicOnly-' + [guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($TestRoot)
try {
    $Inputs = Join-Path $TestRoot 'owner-inputs-empty'
    [void][System.IO.Directory]::CreateDirectory($Inputs)
    $Output = Join-Path $TestRoot 'SHOULD_NOT_EXIST'
    $Missing = Join-Path $TestRoot 'missing.zip'
    $Text = (& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $R288 -InputDir $Inputs -Package $Missing -Output $Output 2>&1 | Out-String)
    $Exit = $LASTEXITCODE
    Assert-R289 ($Exit -ne 0) 'missing source ZIP returned success'
    Assert-R289 ($Text -match 'R288_MISSING_SOURCE_ZIP') 'missing source ZIP rejection missing'
    Assert-R289 (-not (Test-Path -LiteralPath $Output)) 'missing ZIP created output'
    $Fake = Join-Path $TestRoot 'invalid.zip'
    [System.IO.File]::WriteAllBytes($Fake,[byte[]](1,2,3,4))
    $Text = (& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $R288 -InputDir $Inputs -Package $Fake -Output $Output 2>&1 | Out-String)
    $Exit = $LASTEXITCODE
    Assert-R289 ($Exit -ne 0) 'wrong package checksum returned success'
    Assert-R289 ($Text -match 'R288_SOURCE_ZIP_HASH_MISMATCH') 'bad ZIP SHA refusal missing'
    Assert-R289 (-not (Test-Path -LiteralPath $Output)) 'bad ZIP created output'
    $Json = & python $R287 --input-dir $Inputs --output $Output
    $Exit = $LASTEXITCODE
    Assert-R289 ($Exit -eq 2) 'missing private archives did not fail closed'
    $Report = ($Json -join "`n") | ConvertFrom-Json
    Assert-R289 ($Report.ready -eq $false) 'archive-less probe reported ready'
    Assert-R289 (($Report.checks | Where-Object { $_.check -eq 'native_windows' }).pass -eq $true) 'Win32 environment was not detected'
    Assert-R289 ($Report.type -eq 'READ_ONLY_ADVISORY_NOT_GUI_ACCEPTANCE') 'readiness confused with gameplay'
    Assert-R289 (-not (Test-Path -LiteralPath $Output)) 'probe created output'
}
finally {
    if (Test-Path -LiteralPath $TestRoot) {
        [System.IO.Directory]::Delete($TestRoot,$true)
    }
}
Write-Host "R289_REAL_WINDOWS_SAFE_ENTRY_TESTS_PASS checks=$Checks gui=NOT_TESTED owner_inputs=NOT_USED"
# Expected negative probes leave LASTEXITCODE=2; terminate CI cleanly on true success.
exit 0
