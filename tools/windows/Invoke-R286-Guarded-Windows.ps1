[CmdletBinding()]
param(
    [string]$InputDir = $PSScriptRoot,
    [string]$Package = (Join-Path $PSScriptRoot 'SpawnPK_v309_R286_WINDOWS_GUARDED_ACCEPTANCE_SOURCE_ONLY.zip'),
    [string]$Output = (Join-Path ([Environment]::GetFolderPath('Desktop')) ('SpawnPK-R286-Acceptance-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))),
    [switch]$PreflightOnly
)
$ErrorActionPreference = 'Stop'
$PackageExpected = '2CACD2C551D6169BE45E695F324D6C70A6D2A0B73A59B15FC5BCE444F88A9877'
$Inputs = @{
    r278    = @{ Name='SpawnPK_v309_R278_FULL_SOURCE_OBJECT_AUTHORITY_GUARDS.zip'; Sha='E83F4211D96FFE4188807C79E50CC526EECBE020D010CDD8FECB4A10F2768280' }
    r265    = @{ Name='SpawnPK_v309_R265_UNIFIED_CACHE_R246_PLAYER_APPEARANCE_DIAGNOSTIC_PRIVATE.zip'; Sha='9579556AB5B941BB2697955E56CF4B9D43B68787A652C580A702228554B28DBB' }
    assets  = @{ Name='.spawnpk (4).zip'; Sha='8E15964F44B62A22D2C05F0AE2F63D45DDAD42016C721E586CF55A82D35DA565' }
    original= @{ Name='client(20261015-104312).jar'; Sha='FF5A58D9DC2BF7B75D7346AA6B711EBD423435E04C3F4E1F0D1DE874C6D08F38' }
    r230    = @{ Name='SpawnPK_v309_R230_AUTHENTIC_ASSETS_LOGIN_PRIVATE.zip'; Sha='5C21E5C643DE759DA80C4D18EBB6A49C84968D47A979CAA33F7D4AD2170A7125' }
}

if (Test-Path -LiteralPath $Output) { throw "R286_REFUSE_EXISTING_OUTPUT: $Output" }
if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) { throw "R286_INPUT_DIRECTORY_NOT_FOUND: $InputDir" }
if (-not (Test-Path -LiteralPath $Package -PathType Leaf)) { throw "R286_PACKAGE_NOT_FOUND: $Package" }
$ActualPackage = (Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash
if ($ActualPackage -ne $PackageExpected) { throw "R286_EVIDENCE_PACKAGE_SHA256_MISMATCH: $ActualPackage" }

$Found = @{}
foreach ($name in @('r278','r265','assets','original','r230')) {
    $File = Join-Path $InputDir $Inputs[$name].Name
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { throw "R286_REQUIRED_OWNER_ARCHIVE_MISSING: $File" }
    $Actual = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash
    if ($Actual -ne $Inputs[$name].Sha) { throw "R286_INPUT_SHA256_MISMATCH ($name): $Actual" }
    $Found[$name] = (Resolve-Path -LiteralPath $File).ProviderPath
}
Write-Host 'R286_ALL_FIVE_PRIVATE_OWNER_SHA256_PASS' -ForegroundColor Green
Write-Host 'R286_SOURCE_SAFE_PACKAGE_SHA256_PASS' -ForegroundColor Green
if ($PreflightOnly) {
    Write-Host 'R286_READ_ONLY_PREFLIGHT_PASS (no test home created)' -ForegroundColor Green
    return
}

$Py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($Py) { $PythonCommand = $Py.Source; $PythonPrefix = @('-3') }
else {
    $Py = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $Py) { throw 'Python 3.11+ is required for this source-only harness.' }
    $PythonCommand = $Py.Source; $PythonPrefix = @()
}

$Scratch = Join-Path $env:TEMP ('SpawnPK-R286-Source-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $Scratch) { throw 'R286_REFUSE_EXISTING_TEMP_SCRATCH' }
try {
    Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
    [System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Package).ProviderPath, $Scratch)
    $Main = Join-Path $Scratch 'scripts\R286-Windows-Acceptance.py'
    if (-not (Test-Path -LiteralPath $Main -PathType Leaf)) { throw 'R286_MISSING_VERIFIED_WINDOWS_HARNESS_ENTRY' }
    $RunArgs = @(
        $Main,
        '--r278', $Found.r278,
        '--r265', $Found.r265,
        '--assets', $Found.assets,
        '--original', $Found.original,
        '--r230', $Found.r230,
        '--output', $Output
    )
    & $PythonCommand @PythonPrefix @RunArgs
    if ($LASTEXITCODE -ne 0) { throw "R286_WINDOWS_RUNNER_FAILED exit=$LASTEXITCODE. See $Output for logs if it was created." }
    Write-Host "R286_NATIVE_WINDOWS_ACCEPTANCE_PASS Output=$Output" -ForegroundColor Green
}
finally {
    # Only delete this script's fresh temporary source extraction; never owner archives.
    if (Test-Path -LiteralPath $Scratch) {
        [System.IO.Directory]::Delete($Scratch, $true)
    }
}
