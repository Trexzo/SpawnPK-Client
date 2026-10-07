[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [Parameter(Mandatory = $true)]
    [string]$ClientJar,
    [string]$Jdk = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot",
    [ValidateRange(1, 20)]
    [int]$FocusFiles = 20,
    [string]$OutDir,
    [string]$LogPath
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Require-File {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Repo not found: $Repo"
}

$Inner = Join-Path $Repo "scripts\Invoke-SourceM1ExactLocalAcceptance.ps1"
Require-File $Inner
Require-File $ClientJar

if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutDir = Join-Path $env:USERPROFILE ("Desktop\SpawnPK-SourceM1-Exact-" + $Stamp)
}

if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = $OutDir + ".log"
}

if (Test-Path -LiteralPath $LogPath -PathType Leaf) {
    throw "Log path already exists: $LogPath"
}

Write-Host ""
Write-Host "=== SOURCE M1 LOGGED EXACT-LOCAL LAUNCHER ===" -ForegroundColor Cyan
Write-Host "REPO=$Repo"
Write-Host "CLIENT=$ClientJar"
Write-Host "OUT=$OutDir"
Write-Host "LOG=$LogPath"
Write-Host ""

# Windows PowerShell 5.1 converts ordinary native stderr emitted by a child
# powershell.exe (for example Git's "From https://github.com/..." progress)
# into NativeCommandError records. Those records are not acceptance failures.
# Stream them into the log under Continue, then trust the child process exit.
$PreviousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"

    & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $Inner `
        -Repo $Repo `
        -ClientJar $ClientJar `
        -Jdk $Jdk `
        -OutDir $OutDir `
        -FocusFiles $FocusFiles `
        2>&1 | Tee-Object -FilePath $LogPath

    $Exit = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $PreviousErrorActionPreference
}

Write-Host ""
Write-Host "===== COMPACT SOURCE-M1 EVIDENCE =====" -ForegroundColor Cyan

Get-Content -LiteralPath $LogPath |
    Select-String -Pattern @(
        '^AUTHORITY_COMMIT=',
        '^V308_SHA256=',
        '^PROCYON_SHA256=',
        '^SOURCE_NORMALIZATION_ID=',
        '^SOURCE_NORMALIZATION_ACTIONS=',
        '^INVOKEDYNAMIC_CALLBACK_',
        '^INTPREDICATE_',
        '^ERASED_',
        '^GENERIC_KEY_OBJECT_CAST_',
        '^METHODHANDLE_INVOKEEXACT_',
        '^EXACT_STATIC_CALL_NESTED_TYPE_COLLISION_',
        '^SPK_SOURCE_M1_EXACT_LOCAL_',
        '^javac_total_errors=',
        '^javac_affected_files=',
        '^javac_cannot_find_symbol=',
        '^javac_frontier_id=',
        '^JAVAC_FRONTIER_ID=',
        '^JAVAC_TOTAL_ERRORS=',
        '^JAVAC_AFFECTED_FILES=',
        '^JAVAC_CANNOT_FIND_SYMBOL=',
        '^SRCCTX:',
        'FOCUSED JAVAC DIAGNOSTICS',
        'OsrsMapDependencyScanner\.java',
        'Recovered_CLIENT_CLASS_000109\.java',
        'EventBus\.java'
    ) |
    ForEach-Object { $_.Line }

Write-Host ""
Write-Host "SOURCE_M1_EXIT=$Exit"
Write-Host "SOURCE_M1_LOG=$LogPath"
Write-Host "SOURCE_M1_OUT=$OutDir"

if ($Exit -eq 3) {
    Write-Host "SOURCE_M1_MEASURED_FRONTIER_READY" -ForegroundColor Yellow
    exit 3
}
elseif ($Exit -eq 0) {
    Write-Host "SOURCE_M1_EXACT_LOCAL_PASS" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "SOURCE_M1_EXACT_LOCAL_FAILED exit=$Exit" -ForegroundColor Red
    exit $Exit
}
