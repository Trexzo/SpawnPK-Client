[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [string]$V307ClientJar = "C:\Users\Felix\Desktop\SpawnPK-Local-Backups\client(6)-before-854F-6232BAE20684.jar",
    [string]$V308ClientJar = "C:\Users\Felix\.spawnpk-data\client.jar",
    [string]$AuthorityRoot = "C:\Users\Felix\Desktop\gpt_output2\_archive_2026-09-27\SpawnPK\SpawnPK-R8N-Private",
    [string]$Jdk = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest"
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
if (-not (Test-Path -LiteralPath $AuthorityRoot -PathType Container)) {
    throw "Archived authority root not found: $AuthorityRoot"
}

$V308Index = Join-Path $AuthorityRoot "authority\v308-index.json"
$ClassLineage = Join-Path $AuthorityRoot "authority\class-lineage.accepted.json"
$MemberLineage = Join-Path $AuthorityRoot "authority\member-lineage.accepted.json"
$V308Acceptance = Join-Path $AuthorityRoot "authority\member-safety.accepted.json"
$DecompilerJar = Join-Path $AuthorityRoot "tools\procyon-decompiler-0.6.0.jar"

$PrepScript = Join-Path $Repo "scripts\Prepare-HistoricalV307MemberSafety.ps1"
$ReleaseScript = Join-Path $Repo "scripts\Invoke-HistoricalV307RecoveryRelease.ps1"

foreach ($Path in @(
    $V307ClientJar,
    $V308ClientJar,
    $V308Index,
    $ClassLineage,
    $MemberLineage,
    $V308Acceptance,
    $DecompilerJar,
    $PrepScript,
    $ReleaseScript
)) {
    Require-File $Path
}

$Dirty = @(& git -C $Repo status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "git status failed" }
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "Repo is dirty."
}

& git -C $Repo fetch origin main
if ($LASTEXITCODE -ne 0) { throw "git fetch origin main failed" }

$Head = @(& git -C $Repo rev-parse HEAD)[0].Trim()
$RemoteMain = @(& git -C $Repo rev-parse origin/main)[0].Trim()
if ($Head -ne $RemoteMain) {
    throw "Local HEAD is not exact origin/main: head=$Head origin/main=$RemoteMain"
}

if (Test-Path -LiteralPath $OutDir) {
    $Existing = @(Get-ChildItem -LiteralPath $OutDir -Force)
    if ($Existing.Count -ne 0) {
        throw "Output directory must be empty: $OutDir"
    }
} else {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$SafetyOut = Join-Path $OutDir "member-safety"
$ReleaseOut = Join-Path $OutDir "recovery-release"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SPAWNPK HISTORICAL v307 FULL RECOVERY BACKTEST" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "AUTHORITY_COMMIT=$Head" -ForegroundColor Green
Write-Host "V307_CLIENT=$V307ClientJar"
Write-Host "V308_CLIENT=$V308ClientJar"
Write-Host "AUTHORITY_ROOT=$AuthorityRoot"
Write-Host "OUTPUT_ROOT=$OutDir"

$PrepArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $PrepScript,
    "-Repo",
    $Repo,
    "-V307ClientJar",
    $V307ClientJar,
    "-V308ClientJar",
    $V308ClientJar,
    "-V308SourceIndex",
    $V308Index,
    "-ClassLineage",
    $ClassLineage,
    "-MemberLineage",
    $MemberLineage,
    "-V308MemberSafetyAcceptance",
    $V308Acceptance,
    "-OutDir",
    $SafetyOut
)

Write-Host ""
Write-Host "=== STAGE 1: PREPARE EXACT v307 MEMBER-SAFETY AUTHORITY ===" -ForegroundColor Cyan
& powershell.exe @PrepArgs
$PrepExit = $LASTEXITCODE
if ($PrepExit -ne 0) {
    throw "Historical v307 member-safety preparation failed with exit=$PrepExit"
}

$V307Index = Join-Path $SafetyOut "v307\index.json"
$V307Acceptance = Join-Path $SafetyOut "carry-forward\member-safety.accepted.v307.json"
Require-File $V307Index
Require-File $V307Acceptance

$ReleaseArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $ReleaseScript,
    "-Repo",
    $Repo,
    "-ClientJar",
    $V307ClientJar,
    "-SourceIndex",
    $V307Index,
    "-ClassLineage",
    $ClassLineage,
    "-MemberLineage",
    $MemberLineage,
    "-MemberSafetyAcceptance",
    $V307Acceptance,
    "-DecompilerJar",
    $DecompilerJar,
    "-Jdk",
    $Jdk,
    "-OutDir",
    $ReleaseOut
)

Write-Host ""
Write-Host "=== STAGE 2: RUN MODERN HISTORICAL v307 RECOVERY RELEASE ===" -ForegroundColor Cyan
& powershell.exe @ReleaseArgs
$ReleaseExit = $LASTEXITCODE

if ($ReleaseExit -eq 3) {
    Write-Host ""
    Write-Host "HISTORICAL_V307_BACKTEST_BLOCKED_AT_SHARED_SOURCE_FRONTIER" -ForegroundColor Yellow
    Write-Host "SAFETY_AUTHORITY_PASS=true"
    Write-Host "RECOVERY_RELEASE_PASS=false"
    Write-Host "RELEASE_EXIT=3"
    Write-Host "SAFETY_OUTPUT=$SafetyOut"
    Write-Host "RELEASE_OUTPUT=$ReleaseOut"
    exit 3
}

if ($ReleaseExit -ne 0) {
    throw "Historical v307 recovery release failed with exit=$ReleaseExit"
}

$ReleaseManifest = Join-Path $ReleaseOut "release\recovery-release.json"
Require-File $ReleaseManifest

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
$ProjectionArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.json_projection_cli",
    $ReleaseManifest,
    "--field",
    "build_id=/build_id",
    "--field",
    "release_id=/release_id",
    "--field",
    "ready=/ready_for_release",
    "--field",
    "source_tree=/final_source_tree_sha256"
)
$Projection = @(& py @ProjectionArgs)
if ($LASTEXITCODE -ne 0) {
    throw "Could not project final historical release manifest."
}

$Final = (($Projection -join [Environment]::NewLine) | ConvertFrom-Json)
if ([string]$Final.build_id -ne "v307") {
    throw "Final historical release build drifted from v307."
}
if ($Final.ready -ne $true) {
    throw "Final historical recovery release is not ready."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " HISTORICAL v307 FULL RECOVERY BACKTEST - PASS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "RELEASE_ID=$($Final.release_id)"
Write-Host "SOURCE_TREE_SHA256=$($Final.source_tree)"
Write-Host "SAFETY_OUTPUT=$SafetyOut"
Write-Host "RELEASE_OUTPUT=$ReleaseOut"
