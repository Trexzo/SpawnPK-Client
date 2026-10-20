[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..\..'),
    [string]$InputDir = (Join-Path $env:USERPROFILE 'Downloads'),
    [string]$Output = (Join-Path ([Environment]::GetFolderPath('Desktop')) ('SpawnPK-R308-Native-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))),
    [switch]$Inventory,
    [switch]$Preflight,
    [switch]$RunNativeGui
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# The exact R309 Python worker, pinned by its public Git blob. R310 never
# downloads or extracts a script and never modifies the installed game.
$ExpectedGitBlob = '149c50e9ede9ca2ed70afcf6708ee9b882c84a10'
$Modes = @([bool]$Inventory, [bool]$Preflight, [bool]$RunNativeGui) | Where-Object { $_ }
if (@($Modes).Count -gt 1) { throw 'R310_REFUSE_MULTIPLE_MODES' }
if (-not $Inventory -and -not $Preflight -and -not $RunNativeGui) { $Inventory = $true }
if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw 'R310_PROJECT_CHECKOUT_MISSING'
}
$Entry = Join-Path $Root 'tools\windows\r309\R309-Windows-R308-Acceptance.py'
if (-not (Test-Path -LiteralPath $Entry -PathType Leaf)) {
    throw 'R310_PINNED_PYTHON_WORKER_MISSING'
}
if ((Get-Item -LiteralPath $Entry -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'R310_REFUSE_WORKER_REPARSE_POINT'
}

# Permit Git CRLF conversion only if LF-canonical bytes are the exact
# expected Git blob. Malformed source and stray CR are rejected.
$Raw = [IO.File]::ReadAllBytes($Entry)
$Utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
$Source = $Utf8Strict.GetString($Raw)
$CRLF = [string][char]13 + [string][char]10
$Source = $Source.Replace($CRLF, [string][char]10)
if ($Source.Contains([string][char]13)) {
    throw 'R310_REFUSE_MALFORMED_PYTHON_LINE_ENDINGS'
}
$Canonical = $Utf8Strict.GetBytes($Source)
$Header = 'blob ' + $Canonical.Length + [char]0
$GitPrefix = [Text.Encoding]::ASCII.GetBytes($Header)
$Payload = New-Object byte[] ($GitPrefix.Length + $Canonical.Length)
[Array]::Copy($GitPrefix, 0, $Payload, 0, $GitPrefix.Length)
[Array]::Copy($Canonical, 0, $Payload, $GitPrefix.Length, $Canonical.Length)
$Hasher = [Security.Cryptography.SHA1]::Create()
try {
    $Observed = [BitConverter]::ToString($Hasher.ComputeHash($Payload)).Replace('-', '').ToLowerInvariant()
}
finally {
    $Hasher.Dispose()
}
if ($Observed -cne $ExpectedGitBlob) {
    throw 'R310_PINNED_PYTHON_WORKER_GIT_BLOB_MISMATCH'
}
if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) {
    throw 'R310_OWNER_INPUT_DIRECTORY_MISSING'
}

$PythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($PythonLauncher) {
    $Exe = $PythonLauncher.Source
    $PrefixArgs = @('-3')
}
else {
    $PythonLauncher = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $PythonLauncher) { throw 'R310_PYTHON_3_LAUNCHER_MISSING' }
    $Exe = $PythonLauncher.Source
    $PrefixArgs = @()
}
$WorkerArgs = @($Entry, '--input-dir', $InputDir)
$Label = 'INVENTORY'
if ($Inventory) {
    $WorkerArgs += '--inventory'
}
else {
    if (Test-Path -LiteralPath $Output) {
        throw 'R310_REFUSE_EXISTING_OUTPUT'
    }
    $WorkerArgs += @('--output', $Output)
    if ($RunNativeGui) {
        $Label = 'NATIVE_GUI_OPT_IN'
        if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
            throw 'R310_REFUSE_NON_WINDOWS_GUI'
        }
        $WorkerArgs += '--run-native-gui'
    }
    else {
        $Label = 'READ_ONLY_PREFLIGHT'
    }
}
& $Exe @PrefixArgs @WorkerArgs
if ($LASTEXITCODE -ne 0) {
    throw "R310_$($Label)_NOT_ADMITTED exit=$LASTEXITCODE"
}
Write-Host "R310_$($Label)_WORKER_EXIT_ZERO; inventory/preflight do not prove native GUI success."
exit 0
