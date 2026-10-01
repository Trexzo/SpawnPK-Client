[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [Parameter(Mandatory = $true)][string]$V307ClientJar,
    [Parameter(Mandatory = $true)][string]$V308ClientJar,
    [Parameter(Mandatory = $true)][string]$V308SourceIndex,
    [Parameter(Mandatory = $true)][string]$ClassLineage,
    [Parameter(Mandatory = $true)][string]$MemberLineage,
    [Parameter(Mandatory = $true)][string]$V308MemberSafetyAcceptance,
    [string]$Fixture = "",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Safety"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Require-File {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

function Invoke-PyChecked {
    param([string]$Label, [string[]]$Arguments)

    Write-Host ""
    Write-Host ("=== " + $Label + " ===") -ForegroundColor Cyan
    & py @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ($Label + " failed with exit=" + $LASTEXITCODE)
    }
}

function Get-JsonProjection {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][hashtable]$Fields
    )

    Require-File $Path

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
        throw "Case-safe JSON projection failed: $Path"
    }

    $Raw = ($Output -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        throw "Case-safe JSON projection returned empty output: $Path"
    }

    return ($Raw | ConvertFrom-Json)
}

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Repo not found: $Repo"
}

if ([string]::IsNullOrWhiteSpace($Fixture)) {
    $Fixture = Join-Path $Repo "fixtures\v307-v308-source-regeneration.json"
}

foreach ($Path in @(
    $V307ClientJar,
    $V308ClientJar,
    $V308SourceIndex,
    $ClassLineage,
    $MemberLineage,
    $V308MemberSafetyAcceptance,
    $Fixture
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

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

$FixtureDoc = Get-JsonProjection -Path $Fixture -Fields @{
    kind = "/kind"
    fixture_id = "/fixture_id"
    v307_build_id = "/old/build_id"
    v307_sha256 = "/old/client_sha256"
    v308_build_id = "/new/build_id"
    v308_sha256 = "/new/client_sha256"
}

if ([string]$FixtureDoc.kind -ne "historical_source_regeneration_fixture") {
    throw "Unsupported historical fixture kind."
}
if ([string]$FixtureDoc.v307_build_id -ne "v307") {
    throw "Fixture old build is not v307."
}
if ([string]$FixtureDoc.v308_build_id -ne "v308") {
    throw "Fixture new build is not v308."
}

$ExpectedV307 = ([string]$FixtureDoc.v307_sha256).ToLowerInvariant()
$ExpectedV308 = ([string]$FixtureDoc.v308_sha256).ToLowerInvariant()

$ActualV307 = (
    Get-FileHash -LiteralPath $V307ClientJar -Algorithm SHA256
).Hash.ToLowerInvariant()
$ActualV308 = (
    Get-FileHash -LiteralPath $V308ClientJar -Algorithm SHA256
).Hash.ToLowerInvariant()

if ($ActualV307 -ne $ExpectedV307) {
    throw "Exact v307 SHA mismatch: $ActualV307"
}
if ($ActualV308 -ne $ExpectedV308) {
    throw "Exact v308 SHA mismatch: $ActualV308"
}

$V308IndexDoc = Get-JsonProjection -Path $V308SourceIndex -Fields @{
    sha256 = "/sha256"
}
if (([string]$V308IndexDoc.sha256).ToLowerInvariant() -ne $ExpectedV308) {
    throw "Supplied v308 index is not bound to exact v308."
}

if (Test-Path -LiteralPath $OutDir) {
    $Existing = @(Get-ChildItem -LiteralPath $OutDir -Force)
    if ($Existing.Count -ne 0) {
        throw "Output directory must be empty: $OutDir"
    }
} else {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$V307Dir = Join-Path $OutDir "v307"
$V308Dir = Join-Path $OutDir "v308"
$CarryDir = Join-Path $OutDir "carry-forward"
$LineageBackfillDir = Join-Path $OutDir "lineage-backfill"

New-Item -ItemType Directory -Path $V307Dir | Out-Null
New-Item -ItemType Directory -Path $V308Dir | Out-Null
New-Item -ItemType Directory -Path $CarryDir | Out-Null
New-Item -ItemType Directory -Path $LineageBackfillDir | Out-Null

$V307Index = Join-Path $V307Dir "index.json"
$V307Coverage = Join-Path $V307Dir "coverage.json"
$V308Coverage = Join-Path $V308Dir "coverage.json"
$V307NamespaceDir = Join-Path $V307Dir "semantic-namespace"
$V308NamespaceDir = Join-Path $V308Dir "semantic-namespace"
$V307MemberPlan = Join-Path $V307NamespaceDir "member-remap-plan.json"
$V308MemberPlan = Join-Path $V308NamespaceDir "member-remap-plan.json"
$V307SafetyReport = Join-Path $V307Dir "member-safety-report.json"
$V308SafetyReport = Join-Path $V308Dir "member-safety-report.json"
$CarryReport = Join-Path $CarryDir "member-safety-carryforward.json"
$V307Acceptance = Join-Path $CarryDir "member-safety.accepted.v307.json"
$DerivedClassLineage = Join-Path $LineageBackfillDir "class-lineage.json"
$DerivedMemberLineage = Join-Path $LineageBackfillDir "member-lineage.json"
$LineageBackfillReport = Join-Path $LineageBackfillDir "historical-lineage-backfill.json"

Write-Host ""
Write-Host "=== HISTORICAL v307 MEMBER-SAFETY PREPARATION ===" -ForegroundColor Cyan
Write-Host "AUTHORITY_COMMIT=$Head" -ForegroundColor Green
Write-Host "FIXTURE_ID=$($FixtureDoc.fixture_id)" -ForegroundColor Green
Write-Host "V307_SHA256=$ActualV307" -ForegroundColor Green
Write-Host "V308_SHA256=$ActualV308" -ForegroundColor Green

Invoke-PyChecked "BACKFILL EXACT v307 CANONICAL LINEAGE" @(
    "-3.13",
    "-m",
    "spk_recovery.historical_lineage_backfill_cli",
    $V308ClientJar,
    $V307ClientJar,
    $V308SourceIndex,
    $ClassLineage,
    $MemberLineage,
    $Fixture,
    "--out-dir",
    $LineageBackfillDir
)

Require-File $DerivedClassLineage
Require-File $DerivedMemberLineage
Require-File $LineageBackfillReport

$ClassLineage = $DerivedClassLineage
$MemberLineage = $DerivedMemberLineage

Invoke-PyChecked "INDEX EXACT v307" @(
    "-3.13",
    "-m",
    "spk_recovery.cli",
    "index",
    $V307ClientJar,
    "--expect-sha256",
    $ExpectedV307,
    "--out",
    $V307Index
)

Invoke-PyChecked "CHECK v307 CANONICAL COVERAGE" @(
    "-3.13",
    "-m",
    "spk_recovery.coverage_cli",
    $ClassLineage,
    $MemberLineage,
    "--build-id",
    "v307",
    "--out",
    $V307Coverage
)

Invoke-PyChecked "CHECK v308 CANONICAL COVERAGE" @(
    "-3.13",
    "-m",
    "spk_recovery.coverage_cli",
    $ClassLineage,
    $MemberLineage,
    "--build-id",
    "v308",
    "--out",
    $V308Coverage
)

Invoke-PyChecked "BUILD EXACT v307 SEMANTIC NAMESPACE" @(
    "-3.13",
    "-m",
    "spk_recovery.semantic_namespace_cli",
    $ClassLineage,
    $MemberLineage,
    $V307Index,
    "--build-id",
    "v307",
    "--source-safe-fallback",
    "--fallback-name-prefix",
    "Recovered_",
    "--out-dir",
    $V307NamespaceDir
)

Invoke-PyChecked "BUILD EXACT v308 SEMANTIC NAMESPACE" @(
    "-3.13",
    "-m",
    "spk_recovery.semantic_namespace_cli",
    $ClassLineage,
    $MemberLineage,
    $V308SourceIndex,
    "--build-id",
    "v308",
    "--source-safe-fallback",
    "--fallback-name-prefix",
    "Recovered_",
    "--out-dir",
    $V308NamespaceDir
)

Invoke-PyChecked "SCAN EXACT v307 MEMBER SAFETY" @(
    "-3.13",
    "-m",
    "spk_recovery.cli",
    "member-safety-scan",
    $V307ClientJar,
    $V307Index,
    $V307MemberPlan,
    "--out",
    $V307SafetyReport
)

Invoke-PyChecked "SCAN EXACT v308 MEMBER SAFETY" @(
    "-3.13",
    "-m",
    "spk_recovery.cli",
    "member-safety-scan",
    $V308ClientJar,
    $V308SourceIndex,
    $V308MemberPlan,
    "--out",
    $V308SafetyReport
)

Invoke-PyChecked "REPRODUCE REVIEWED v308 SAFETY ACCEPTANCE" @(
    "-3.13",
    "-m",
    "spk_recovery.cli",
    "member-safety-validate",
    $V308MemberPlan,
    $V308SafetyReport,
    $V308MemberSafetyAcceptance
)

Invoke-PyChecked "CARRY REVIEWED SAFETY TO EXACT v307" @(
    "-3.13",
    "-m",
    "spk_recovery.member_safety_carryforward_cli",
    $V308MemberPlan,
    $V308SafetyReport,
    $V308MemberSafetyAcceptance,
    $V307MemberPlan,
    $V307SafetyReport,
    "--report-out",
    $CarryReport,
    "--acceptance-out",
    $V307Acceptance
)

Require-File $V307Acceptance

Invoke-PyChecked "VALIDATE GENERATED v307 SAFETY ACCEPTANCE" @(
    "-3.13",
    "-m",
    "spk_recovery.cli",
    "member-safety-validate",
    $V307MemberPlan,
    $V307SafetyReport,
    $V307Acceptance
)

$CarryDoc = Get-JsonProjection -Path $CarryReport -Fields @{
    report_id = "/report_id"
    full_carryforward_ready = "/full_carryforward_ready"
    transferred_member_count = "/transferred_member_count"
    blocked_member_count = "/blocked_member_count"
    previous_report_id = "/previous_report_id"
    target_report_id = "/target_report_id"
}

if ($CarryDoc.full_carryforward_ready -ne $true) {
    throw "v307 member-safety carry-forward did not reach ready state."
}
if ([int]$CarryDoc.blocked_member_count -ne 0) {
    throw "v307 member-safety carry-forward retained blockers."
}

Write-Host ""
Write-Host "MEMBER_SAFETY_CARRY_FORWARD_ID=$($CarryDoc.report_id)" -ForegroundColor Green
Write-Host "PREVIOUS_MEMBER_SAFETY_REPORT=$($CarryDoc.previous_report_id)" -ForegroundColor Green
Write-Host "V307_MEMBER_SAFETY_REPORT=$($CarryDoc.target_report_id)" -ForegroundColor Green
Write-Host "TRANSFERRED_MEMBERS=$($CarryDoc.transferred_member_count)" -ForegroundColor Green
Write-Host ""
Write-Host "V307_INDEX=$V307Index"
Write-Host "V307_MEMBER_SAFETY_ACCEPTANCE=$V307Acceptance"
Write-Host "V307_CLASS_LINEAGE=$ClassLineage"
Write-Host "V307_MEMBER_LINEAGE=$MemberLineage"
Write-Host "V307_LINEAGE_BACKFILL_REPORT=$LineageBackfillReport"
Write-Host "V307_COVERAGE=$V307Coverage"
Write-Host "V308_COVERAGE=$V308Coverage"
Write-Host "CARRY_FORWARD_REPORT=$CarryReport"
Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host " HISTORICAL v307 MEMBER SAFETY PREPARATION - PASS" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Feed V307_INDEX and V307_MEMBER_SAFETY_ACCEPTANCE into:"
Write-Host "  scripts\Invoke-HistoricalV307RecoveryRelease.ps1"
