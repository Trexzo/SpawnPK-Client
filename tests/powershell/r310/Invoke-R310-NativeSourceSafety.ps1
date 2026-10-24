[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).ProviderPath
$Entry = Join-Path $Root 'tools\windows\Invoke-R310-R308-Owner.ps1'
$RealWorker = Join-Path $Root 'tools\windows\r309\R309-Windows-R308-Acceptance.py'
$Checks = 0
function Assert-R310([bool]$Ok, [string]$Why) {
    if (-not $Ok) { throw "R310_WINDOWS_SAFETY_FAIL $Why" }
    $script:Checks += 1
}
Assert-R310 (Test-Path -LiteralPath $Entry -PathType Leaf) 'entry missing'
Assert-R310 (Test-Path -LiteralPath $RealWorker -PathType Leaf) 'pinned Python source missing'
$Tokens = $null; $Syntax = $null
[void][Management.Automation.Language.Parser]::ParseFile($Entry, [ref]$Tokens, [ref]$Syntax)
Assert-R310 (@($Syntax).Count -eq 0) 'PowerShell parser errors'
$Body = Get-Content -LiteralPath $Entry -Raw
Assert-R310 ($Body.Contains("149c50e9ede9ca2ed70afcf6708ee9b882c84a10")) 'Python blob not pinned'
Assert-R310 ($Body.Contains("R310_PINNED_PYTHON_WORKER_GIT_BLOB_MISMATCH")) 'source hash guard missing'
Assert-R310 ($Body.Contains("'--run-native-gui'")) 'GUI opt-in guard missing'
Assert-R310 (-not ($Body.Contains('Invoke-WebRequest') -or $Body.Contains('taskkill'))) 'unexpected download or process kill'

$Tmp = Join-Path $env:TEMP ('R310-public-only-'+[Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($Tmp)
try {
    $Fake = Join-Path $Tmp 'checkout'
    $Scripts = Join-Path $Fake 'tools\windows\r309'
    [void][IO.Directory]::CreateDirectory($Scripts)
    $Worker = Join-Path $Scripts 'R309-Windows-R308-Acceptance.py'
    # R309 intentionally refuses to load without both pinned *public* R297 sources.
    # Copy these verbatim; no owner-private ZIPs, cache or binaries are staged.
    $R297Fake = Join-Path $Fake 'tools\windows\r297'
    [void][IO.Directory]::CreateDirectory($R297Fake)
    foreach ($Name in @('R297-Owner-Readiness.py', 'R297-Windows-R295-Acceptance.py')) {
        Copy-Item -LiteralPath (Join-Path $Root ('tools\windows\r297\' + $Name)) -Destination (Join-Path $R297Fake $Name)
    }
    $Owner = Join-Path $Tmp 'owner'
    [void][IO.Directory]::CreateDirectory($Owner)
    $Output = Join-Path $Tmp 'SHOULD-NOT-EXIST'
    $Native = (Get-Command powershell.exe -ErrorAction Stop).Source
    function Invoke-Entry([string[]]$Options) {
        $OutputText = (& $Native -NoProfile -ExecutionPolicy Bypass -File $Entry -Root $Fake -InputDir $Owner -Output $Output @Options 2>&1 | Out-String)
        return [pscustomobject]@{ Text=$OutputText; Exit=$LASTEXITCODE }
    }

    $Missing = Invoke-Entry @('-Inventory')
    Assert-R310 ($Missing.Exit -ne 0) 'missing worker accepted'
    Assert-R310 ($Missing.Text -match 'R310_PINNED_PYTHON_WORKER_MISSING') 'missing worker message lost'
    Assert-R310 (-not (Test-Path -LiteralPath $Output)) 'missing worker wrote owner output'

    [IO.File]::WriteAllText($Worker, 'tampered worker', (New-Object Text.UTF8Encoding $false))
    $Tamper = Invoke-Entry @('-RunNativeGui')
    Assert-R310 ($Tamper.Exit -ne 0) 'tampered worker accepted for GUI'
    Assert-R310 ($Tamper.Text -match 'R310_PINNED_PYTHON_WORKER_GIT_BLOB_MISMATCH') 'worker hash failure lost'
    Assert-R310 (-not (Test-Path -LiteralPath $Output)) 'tampered worker wrote owner output'

    $Source = [IO.File]::ReadAllBytes($RealWorker)
    [IO.File]::WriteAllBytes($Worker, $Source)
    $Multiple = Invoke-Entry @('-Inventory','-RunNativeGui')
    Assert-R310 ($Multiple.Exit -ne 0) 'mutually exclusive flags accepted'
    Assert-R310 ($Multiple.Text -match 'R310_REFUSE_MULTIPLE_MODES') 'multiple modes error absent'

    $SafeInventory = Invoke-Entry @('-Inventory')
    Assert-R310 ($SafeInventory.Exit -ne 0) 'missing private archives approved'
    Assert-R310 ($SafeInventory.Text -match 'R309_R308_INPUT_INVENTORY') 'inventory report absent'
    Assert-R310 ($SafeInventory.Text -match 'R310_INVENTORY_NOT_ADMITTED') 'inventory failed to propagate worker exit'
    Assert-R310 (-not (Test-Path -LiteralPath $Output)) 'inventory created output'

    $Preflight = Invoke-Entry @('-Preflight')
    Assert-R310 ($Preflight.Exit -ne 0) 'missing private archives approved in preflight'
    Assert-R310 ($Preflight.Text -match 'R309_R308_READINESS') 'preflight report missing'
    Assert-R310 ($Preflight.Text -match 'R310_READ_ONLY_PREFLIGHT_NOT_ADMITTED') 'preflight failed to propagate status'
    Assert-R310 (-not (Test-Path -LiteralPath $Output)) 'preflight created output'

    # Real owner invocation used -File without -Root. Previously, parameter
    # binding evaluated $PSScriptRoot as empty; test from an unrelated cwd.
    Push-Location -LiteralPath $Tmp
    try {
        $DefaultInventoryText = (& $Native -NoProfile -ExecutionPolicy Bypass -File $Entry -InputDir $Owner -Inventory 2>&1 | Out-String)
        $DefaultInventoryExit = $LASTEXITCODE
        Assert-R310 ($DefaultInventoryExit -eq 1) 'default checkout root did not refuse absent private inputs'
        Assert-R310 ($DefaultInventoryText -match 'R309_R308_INPUT_INVENTORY') 'default checkout root did not find pinned worker'
        Assert-R310 ($DefaultInventoryText -match 'R310_INVENTORY_NOT_ADMITTED') 'default root inventory failed to propagate input refusal'
        Assert-R310 (-not ($DefaultInventoryText -match 'Cannot bind argument to parameter')) 'default root still fails in param binding'

        $DefaultPreflightText = (& $Native -NoProfile -ExecutionPolicy Bypass -File $Entry -InputDir $Owner -Output $Output -Preflight 2>&1 | Out-String)
        $DefaultPreflightExit = $LASTEXITCODE
        Assert-R310 ($DefaultPreflightExit -eq 1) 'default checkout root did not refuse incomplete preflight'
        Assert-R310 ($DefaultPreflightText -match 'R309_R308_READINESS') 'default root preflight did not run readiness'
        Assert-R310 (-not (Test-Path -LiteralPath $Output)) 'default root preflight created output'
    }
    finally {
        Pop-Location
    }

    $CRLF = [Text.Encoding]::UTF8.GetString($Source).Replace([string][char]10, ([string][char]13+[string][char]10))
    [IO.File]::WriteAllText($Worker, $CRLF, (New-Object Text.UTF8Encoding $false))
    $CrLfResult = Invoke-Entry @('-Inventory')
    Assert-R310 ($CrLfResult.Text -match 'R309_R308_INPUT_INVENTORY') 'Git CRLF checkout wrongly rejected'

    [IO.File]::WriteAllBytes($Worker, ($Source + [byte[]]@(13)))
    $Stray = Invoke-Entry @('-Inventory')
    Assert-R310 ($Stray.Exit -ne 0) 'malformed line ending accepted'
    Assert-R310 ($Stray.Text -match 'R310_REFUSE_MALFORMED_PYTHON_LINE_ENDINGS') 'stray CR not identified'
    Assert-R310 (-not (Test-Path -LiteralPath $Output)) 'negative cases wrote owner output'
}
finally {
    if (Test-Path -LiteralPath $Tmp) { [IO.Directory]::Delete($Tmp, $true) }
}
Write-Host "R310_NATIVE_WINDOWS_SOURCE_SAFETY_PASS checks=$Checks private_input=NONE native_game_gui=NOT_TESTED"
exit 0
