[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [string]$V307Diagnostic = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest\recovery-release\release\javac-diagnostic-private.json",
    [string]$V308Diagnostic = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact\release\javac-diagnostic-private.json",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-CrossVersion-Javac"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Require-File {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

function Get-Projection {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][hashtable]$Fields
    )

    $Arguments = @(
        "-3.13",
        "-m",
        "spk_recovery.json_projection_cli",
        $Path
    )

    foreach ($Name in @($Fields.Keys | Sort-Object)) {
        $Arguments += @(
            "--field",
            ($Name + "=" + [string]$Fields[$Name])
        )
    }

    $Output = @(& py @Arguments)
    $Exit = $LASTEXITCODE
    if ($Exit -ne 0) {
        throw "JSON projection failed with exit=$Exit"
    }

    $Raw = ($Output -join "`n").Trim()
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        throw "JSON projection returned empty output."
    }

    return ($Raw | ConvertFrom-Json)
}

Write-Host ""
Write-Host "=== SPAWNPK v307-v308 JAVAC FRONTIER COMPARISON ===" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Repo not found: $Repo"
}

$Dirty = @(& git -C $Repo status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw "git status failed."
}
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "Repo is dirty."
}

& git -C $Repo fetch origin main
if ($LASTEXITCODE -ne 0) {
    throw "git fetch origin main failed."
}

$Head = @(& git -C $Repo rev-parse HEAD)[0].Trim()
$RemoteMain = @(& git -C $Repo rev-parse origin/main)[0].Trim()
if ($Head -ne $RemoteMain) {
    throw "Local HEAD is not exact origin/main: head=$Head origin/main=$RemoteMain"
}

Require-File $V307Diagnostic
Require-File $V308Diagnostic

if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$Report = Join-Path $OutDir "v307-v308-javac-frontier.json"

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

$Arguments = @(
    "-3.13",
    "-m",
    "spk_recovery.cross_version_javac_frontier_cli",
    $V307Diagnostic,
    $V308Diagnostic,
    "--out",
    $Report
)

Write-Host ""
Write-Host "=== COMPARE PRIVATE FRONTIERS -> REDACTED REPORT ===" -ForegroundColor Cyan
& py @Arguments
$Exit = $LASTEXITCODE
if ($Exit -ne 0) {
    throw "Cross-version javac comparison failed with exit=$Exit"
}

Require-File $Report

$Summary = Get-Projection -Path $Report -Fields @{
    report_id = "/report_id"
    old_frontier_id = "/old_frontier_id"
    new_frontier_id = "/new_frontier_id"
    identifiers_included = "/identifiers_included"
    old_total_errors = "/summary/old_total_errors"
    new_total_errors = "/summary/new_total_errors"
    shared_errors = "/summary/shared_errors"
    old_only_errors = "/summary/old_only_errors"
    new_only_errors = "/summary/new_only_errors"
    shared_percent_of_old = "/summary/shared_percent_of_old"
    shared_percent_of_new = "/summary/shared_percent_of_new"
    old_affected_files = "/summary/old_affected_files"
    new_affected_files = "/summary/new_affected_files"
    shared_affected_files = "/summary/shared_affected_files"
    exact_frontier_equal = "/summary/exact_frontier_equal"
}

if ($Summary.identifiers_included -ne $false) {
    throw "Refusing unexpected identifier-bearing cross-version report."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " CROSS-VERSION JAVAC FRONTIER COMPARISON - PASS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "AUTHORITY_COMMIT=$Head"
Write-Host "REPORT_ID=$($Summary.report_id)"
Write-Host "V307_FRONTIER=$($Summary.old_frontier_id)"
Write-Host "V308_FRONTIER=$($Summary.new_frontier_id)"
Write-Host "V307_ERRORS=$($Summary.old_total_errors)"
Write-Host "V308_ERRORS=$($Summary.new_total_errors)"
Write-Host "SHARED_ERRORS=$($Summary.shared_errors)"
Write-Host "V307_ONLY_ERRORS=$($Summary.old_only_errors)"
Write-Host "V308_ONLY_ERRORS=$($Summary.new_only_errors)"
Write-Host "SHARED_PERCENT_OF_V307=$($Summary.shared_percent_of_old)"
Write-Host "SHARED_PERCENT_OF_V308=$($Summary.shared_percent_of_new)"
Write-Host "V307_AFFECTED_FILES=$($Summary.old_affected_files)"
Write-Host "V308_AFFECTED_FILES=$($Summary.new_affected_files)"
Write-Host "SHARED_AFFECTED_FILES=$($Summary.shared_affected_files)"
Write-Host "EXACT_FRONTIER_EQUAL=$($Summary.exact_frontier_equal)"
Write-Host "REPORT=$Report"
