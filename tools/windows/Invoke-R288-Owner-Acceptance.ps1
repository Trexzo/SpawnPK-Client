[CmdletBinding()]
param(
    [string]$InputDir = (Join-Path $env:USERPROFILE 'Downloads'),
    [string]$Package = (Join-Path $PSScriptRoot 'SpawnPK_v309_R288_OWNER_ACCEPTANCE_GATE_SOURCE_ONLY.zip'),
    [string]$Output = (Join-Path ([Environment]::GetFolderPath('Desktop')) ('SpawnPK-R286-Acceptance-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))),
    [switch]$RunNativeGui
)
$ErrorActionPreference = 'Stop'
# Exact hash of the R288 source-only ZIP. Update only when publishing a new release.
$PackageExpected = '5824E59136C88296DFFCFD7F6610556C5DF68B1F889A2A606AC61A8CC83462C0'
$R286ZipName = 'SpawnPK_v309_R286_WINDOWS_GUARDED_ACCEPTANCE_SOURCE_ONLY.zip'
$R286ScriptName = 'Invoke-R286-Guarded-Windows.ps1'
$R286ScriptExpected = '2186740003AFB75DF8DD79E2DA6A721C121026733DC20CA087973F1D0CD70246'

if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core') {
    throw 'R288_REFUSE_NOT_WINDOWS'
}
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'R288_REFUSE_NOT_WINDOWS'
}
if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) {
    throw "R288_MISSING_INPUT_DIR: $InputDir"
}
if (-not (Test-Path -LiteralPath $Package -PathType Leaf)) {
    throw "R288_MISSING_SOURCE_ZIP: $Package"
}
$Actual = (Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash
if ($Actual -ne $PackageExpected) {
    throw "R288_SOURCE_ZIP_HASH_MISMATCH actual=$Actual"
}
if (Test-Path -LiteralPath $Output) {
    throw "R288_REFUSE_EXISTING_OUTPUT: $Output"
}
$R286Script = Join-Path $InputDir $R286ScriptName
$R286Zip = Join-Path $InputDir $R286ZipName
if (-not (Test-Path -LiteralPath $R286Script -PathType Leaf)) {
    throw "R288_MISSING_R286_BOOTSTRAP: $R286Script"
}
if (-not (Test-Path -LiteralPath $R286Zip -PathType Leaf)) {
    throw "R288_MISSING_R286_SOURCE_ZIP: $R286Zip"
}
$R286Hash = (Get-FileHash -LiteralPath $R286Script -Algorithm SHA256).Hash
if ($R286Hash -ne $R286ScriptExpected) {
    throw "R288_REFUSE_STALE_R286_BOOTSTRAP actual=$R286Hash"
}

$Python = Get-Command py.exe -ErrorAction SilentlyContinue
if ($Python) { $PythonCommand = $Python.Source; $PythonPrefix = @('-3') }
else {
    $Python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $Python) { throw 'R288_PYTHON_NOT_FOUND' }
    $PythonCommand = $Python.Source; $PythonPrefix = @()
}

$Scratch = Join-Path $env:TEMP ('SpawnPK-R288-Safe-Source-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $Scratch) { throw 'R288_REFUSE_EXISTING_SCRATCH' }
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Package).ProviderPath, $Scratch)
    $Probe = Join-Path $Scratch 'tools\windows\R287-Owner-Readiness.py'
    if (-not (Test-Path -LiteralPath $Probe -PathType Leaf)) {
        throw 'R288_SOURCE_PACKAGE_MISSING_PINNED_READINESS'
    }
    # Read-only: R287 reports JSON on stdout. It validates all six archives,
    # the R286 bootstrap, runtime dependencies, DPI, and localhost port.
    & $PythonCommand @PythonPrefix $Probe '--input-dir' $InputDir '--r286-evidence' $R286Zip '--output' $Output
    if ($LASTEXITCODE -ne 0) {
        throw "R288_READINESS_FAILED exit=$LASTEXITCODE; no native client launched"
    }
    Write-Host 'R288_READ_ONLY_OWNER_PREFLIGHT_PASS' -ForegroundColor Green
    if (-not $RunNativeGui) {
        Write-Host 'R288_PREFLIGHT_ONLY: no game launched, no owner files changed.' -ForegroundColor Green
        return
    }
    # Explicit opt-in only. The original SHA-locked R286 runner retains its own
    # authority checks; never bypass it or call the game launcher directly.
    $Rehash = (Get-FileHash -LiteralPath $R286Script -Algorithm SHA256).Hash
    if ($Rehash -ne $R286ScriptExpected) { throw 'R288_R286_BOOTSTRAP_CHANGED_DURING_PREFLIGHT' }
    if (Test-Path -LiteralPath $Output) { throw 'R288_OUTPUT_CREATED_DURING_PREFLIGHT' }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $R286Script -InputDir $InputDir -Package $R286Zip -Output $Output
    if ($LASTEXITCODE -ne 0) {
        throw "R288_R286_NATIVE_GUI_FAILED exit=$LASTEXITCODE; inspect disposable output if created"
    }
    Write-Host "R288_R286_NATIVE_GUI_RUNNER_REPORTED_PASS Output=$Output" -ForegroundColor Green
}
finally {
    # Delete only this run's random source scratch. Never remove owner archives.
    if (Test-Path -LiteralPath $Scratch) {
        [System.IO.Directory]::Delete($Scratch, $true)
    }
}
