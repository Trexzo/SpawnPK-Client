[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [Parameter(Mandatory = $true)][string]$V305ClientJar,
    [string]$V308ClientJar = "C:\Users\Felix\.spawnpk-data\client.jar",
    [string]$AuthorityRoot = "C:\Users\Felix\Desktop\gpt_output2\_archive_2026-09-27\SpawnPK\SpawnPK-R8N-Private",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v305-Lineage"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$ExpectedV305 =
    "a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385"
$ExpectedV308 =
    "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"

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
    if ($LASTEXITCODE -ne 0) {
        throw "JSON projection failed with exit=$LASTEXITCODE"
    }
    $Raw = ($Output -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        throw "JSON projection returned empty output."
    }
    return ($Raw | ConvertFrom-Json)
}

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Repo not found: $Repo"
}
if (-not (Test-Path -LiteralPath $AuthorityRoot -PathType Container)) {
    throw "Archived authority root not found: $AuthorityRoot"
}

$V308Index = Join-Path $AuthorityRoot "authority\v308-index.json"
$ClassLineage = Join-Path $AuthorityRoot "authority\class-lineage.accepted.json"
$MemberLineage = Join-Path $AuthorityRoot "authority\member-lineage.accepted.json"
$MatchExpectations = Join-Path $Repo "fixtures\v305-v308-historical-reverse-match-summary.json"

foreach ($Path in @(
    $V305ClientJar,
    $V308ClientJar,
    $V308Index,
    $ClassLineage,
    $MemberLineage,
    $MatchExpectations
)) {
    Require-File $Path
}

$Dirty = @(& git -C $Repo status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw "git status failed"
}
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "Repo is dirty."
}

& git -C $Repo fetch origin main
if ($LASTEXITCODE -ne 0) {
    throw "git fetch origin main failed"
}

$Head = @(& git -C $Repo rev-parse HEAD)[0].Trim()
$RemoteMain = @(& git -C $Repo rev-parse origin/main)[0].Trim()
if ($Head -ne $RemoteMain) {
    throw "Local HEAD is not exact origin/main: head=$Head origin/main=$RemoteMain"
}

$V305Sha = (
    Get-FileHash -LiteralPath $V305ClientJar -Algorithm SHA256
).Hash.ToLowerInvariant()
$V308Sha = (
    Get-FileHash -LiteralPath $V308ClientJar -Algorithm SHA256
).Hash.ToLowerInvariant()

if ($V305Sha -ne $ExpectedV305) {
    throw "Exact v305 SHA mismatch: $V305Sha"
}
if ($V308Sha -ne $ExpectedV308) {
    throw "Exact v308 SHA mismatch: $V308Sha"
}

if (Test-Path -LiteralPath $OutDir) {
    $Existing = @(Get-ChildItem -LiteralPath $OutDir -Force)
    if ($Existing.Count -ne 0) {
        $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $BackupOut = $OutDir + ".bak-" + $Stamp
        if (Test-Path -LiteralPath $BackupOut) {
            throw "Probe output backup already exists: $BackupOut"
        }
        Move-Item -LiteralPath $OutDir -Destination $BackupOut
        Write-Host "PREVIOUS_OUTPUT_BACKED_UP=$BackupOut" -ForegroundColor Yellow
    }
}
if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SPAWNPK HISTORICAL v305 LINEAGE PROBE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "AUTHORITY_COMMIT=$Head"
Write-Host "V305_SHA256=$V305Sha"
Write-Host "V308_SHA256=$V308Sha"
Write-Host "MATCH_EXPECTATIONS=$MatchExpectations"
Write-Host "OUTPUT_ROOT=$OutDir"

$Arguments = @(
    "-3.13",
    "-m",
    "spk_recovery.generic_historical_lineage_cli",
    $V308ClientJar,
    $V305ClientJar,
    $V308Index,
    $ClassLineage,
    $MemberLineage,
    "--current-build-id",
    "v308",
    "--historical-build-id",
    "v305",
    "--historical-build-number",
    "305",
    "--expected-current-sha256",
    $ExpectedV308,
    "--expected-historical-sha256",
    $ExpectedV305,
    "--expected-match-summary",
    $MatchExpectations,
    "--out-dir",
    $OutDir
)

Write-Host ""
Write-Host "=== DERIVE EXACT v305 HISTORICAL LINEAGE ===" -ForegroundColor Cyan
& py @Arguments
$ProbeExit = $LASTEXITCODE

if ($ProbeExit -ne 0 -and $ProbeExit -ne 3) {
    throw "Historical v305 lineage probe failed with exit=$ProbeExit"
}

$Report = Join-Path $OutDir "generic-historical-lineage-backfill.json"
Require-File $Report

$Summary = Get-Projection -Path $Report -Fields @{
    backfill_id = "/backfill_id"
    current_build_id = "/current_build_id"
    historical_build_id = "/historical_build_id"
    current_sha256 = "/current_sha256"
    historical_sha256 = "/historical_sha256"
    authority_report_id = "/authority_report_id"
    ready = "/ready_for_authority"
    matched = "/class_match_summary/matched"
    ambiguous = "/class_match_summary/ambiguous"
    current_unmatched = "/class_match_summary/unmatched_old"
    historical_unmatched = "/class_match_summary/unmatched_new"
    focused = "/focused_analysis_items"
    queue = "/paths/focused_analysis_queue"
    authority = "/paths/authority_candidate"
}

if ([string]$Summary.current_build_id -ne "v308") {
    throw "Historical probe current build drifted from v308."
}
if ([string]$Summary.historical_build_id -ne "v305") {
    throw "Historical probe target build drifted from v305."
}
if ([string]$Summary.current_sha256 -ne $ExpectedV308) {
    throw "Historical probe current SHA authority drifted."
}
if ([string]$Summary.historical_sha256 -ne $ExpectedV305) {
    throw "Historical probe historical SHA authority drifted."
}

Write-Host ""
if ($ProbeExit -eq 3) {
    if ($Summary.ready -ne $false) {
        throw "Exit 3 requires ready_for_authority=false."
    }
    Write-Host "HISTORICAL_V305_LINEAGE_BLOCKED" -ForegroundColor Yellow
} else {
    if ($Summary.ready -ne $true) {
        throw "Exit 0 requires ready_for_authority=true."
    }
    Write-Host "HISTORICAL_V305_LINEAGE_PASS" -ForegroundColor Green
}
Write-Host "BACKFILL_ID=$($Summary.backfill_id)"
Write-Host "AUTHORITY_REPORT_ID=$($Summary.authority_report_id)"
Write-Host "MATCHED_CLASSES=$($Summary.matched)"
Write-Host "AMBIGUOUS_CLASSES=$($Summary.ambiguous)"
Write-Host "CURRENT_UNMATCHED_CLASSES=$($Summary.current_unmatched)"
Write-Host "HISTORICAL_UNMATCHED_CLASSES=$($Summary.historical_unmatched)"
Write-Host "FOCUSED_ANALYSIS_ITEMS=$($Summary.focused)"
Write-Host "FOCUSED_ANALYSIS_QUEUE=$($Summary.queue)"
Write-Host "AUTHORITY_CANDIDATE=$($Summary.authority)"
Write-Host "REPORT=$Report"

exit $ProbeExit
