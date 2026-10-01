[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [string]$V307ClientJar = "C:\Users\Felix\Desktop\SpawnPK-Local-Backups\client(6)-before-854F-6232BAE20684.jar",
    [string]$V308ClientJar = "C:\Users\Felix\.spawnpk-data\client.jar",
    [string]$AuthorityRoot = "C:\Users\Felix\Desktop\gpt_output2\_archive_2026-09-27\SpawnPK\SpawnPK-R8N-Private",
    [string]$Jdk = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot",
    [string]$V307Out = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest",
    [string]$V308Out = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact",
    [string]$CompareOut = "$env:USERPROFILE\Desktop\SpawnPK-CrossVersion-Javac"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Require-File {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

function Backup-NonEmptyDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return
    }

    $Existing = @(Get-ChildItem -LiteralPath $Path -Force)
    if ($Existing.Count -eq 0) {
        Remove-Item -LiteralPath $Path -Force
        return
    }

    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $Backup = $Path + ".bak-" + $Stamp
    if (Test-Path -LiteralPath $Backup) {
        throw "Output backup already exists: $Backup"
    }

    Move-Item -LiteralPath $Path -Destination $Backup
    Write-Host "PREVIOUS_OUTPUT_BACKED_UP=$Backup" -ForegroundColor Yellow
}

function Get-Projection {
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
    $Exit = $LASTEXITCODE
    if ($Exit -ne 0) {
        throw "JSON projection failed with exit=$Exit for $Path"
    }

    $Raw = ($Output -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        throw "JSON projection returned empty output: $Path"
    }

    return ($Raw | ConvertFrom-Json)
}

function Invoke-ChildAllowBlocked {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host ""
    Write-Host ("=== " + $Label + " ===") -ForegroundColor Cyan
    & powershell.exe @Arguments
    $Exit = $LASTEXITCODE
    if ($Exit -ne 0 -and $Exit -ne 3) {
        throw "$Label failed with exit=$Exit"
    }
    return $Exit
}

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Repo not found: $Repo"
}
if (-not (Test-Path -LiteralPath $AuthorityRoot -PathType Container)) {
    throw "Archived authority root not found: $AuthorityRoot"
}

$HistoricalScript = Join-Path $Repo "scripts\Invoke-HistoricalV307FullBacktest.ps1"
$V308Script = Join-Path $Repo "scripts\Invoke-SourceM1ExactLocalAcceptance.ps1"
$CompareScript = Join-Path $Repo "scripts\Invoke-CrossVersionJavacFrontier.ps1"

$V308Index = Join-Path $AuthorityRoot "authority\v308-index.json"
$ClassLineage = Join-Path $AuthorityRoot "authority\class-lineage.accepted.json"
$MemberLineage = Join-Path $AuthorityRoot "authority\member-lineage.accepted.json"
$MemberSafetyAcceptance = Join-Path $AuthorityRoot "authority\member-safety.accepted.json"
$DecompilerJar = Join-Path $AuthorityRoot "tools\procyon-decompiler-0.6.0.jar"

foreach ($Path in @(
    $HistoricalScript,
    $V308Script,
    $CompareScript,
    $V307ClientJar,
    $V308ClientJar,
    $V308Index,
    $ClassLineage,
    $MemberLineage,
    $MemberSafetyAcceptance,
    $DecompilerJar
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
if ($Head -notmatch "^[0-9a-f]{40}$") {
    throw "Current authority commit is not lowercase 40-hex: $Head"
}

Backup-NonEmptyDirectory -Path $V307Out
Backup-NonEmptyDirectory -Path $V308Out
Backup-NonEmptyDirectory -Path $CompareOut

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " EQUIVALENT-TOOLING v307-v308 JAVAC BACKTEST" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "TOOLING_COMMIT=$Head" -ForegroundColor Green
Write-Host "V307_OUTPUT=$V307Out"
Write-Host "V308_OUTPUT=$V308Out"
Write-Host "COMPARE_OUTPUT=$CompareOut"

$HistoricalArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $HistoricalScript,
    "-Repo",
    $Repo,
    "-V307ClientJar",
    $V307ClientJar,
    "-V308ClientJar",
    $V308ClientJar,
    "-AuthorityRoot",
    $AuthorityRoot,
    "-Jdk",
    $Jdk,
    "-OutDir",
    $V307Out
)

$V307Exit = Invoke-ChildAllowBlocked -Label "RUN EXACT v307 HISTORICAL BACKTEST" -Arguments $HistoricalArgs

& git -C $Repo fetch origin main
if ($LASTEXITCODE -ne 0) {
    throw "git fetch origin main failed after v307 run"
}
$AfterV307Head = @(& git -C $Repo rev-parse HEAD)[0].Trim()
$AfterV307Remote = @(& git -C $Repo rev-parse origin/main)[0].Trim()
if ($AfterV307Head -ne $Head -or $AfterV307Remote -ne $Head) {
    throw (
        "Recovery tooling authority changed after v307 run: " +
        "captured=$Head head=$AfterV307Head origin/main=$AfterV307Remote"
    )
}

$V308Args = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $V308Script,
    "-Repo",
    $Repo,
    "-ClientJar",
    $V308ClientJar,
    "-SourceIndex",
    $V308Index,
    "-ClassLineage",
    $ClassLineage,
    "-MemberLineage",
    $MemberLineage,
    "-MemberSafetyAcceptance",
    $MemberSafetyAcceptance,
    "-DecompilerJar",
    $DecompilerJar,
    "-Jdk",
    $Jdk,
    "-OutDir",
    $V308Out
)

$V308Exit = Invoke-ChildAllowBlocked -Label "RUN EXACT v308 SOURCE M1 ACCEPTANCE" -Arguments $V308Args

& git -C $Repo fetch origin main
if ($LASTEXITCODE -ne 0) {
    throw "git fetch origin main failed after v308 run"
}
$AfterV308Head = @(& git -C $Repo rev-parse HEAD)[0].Trim()
$AfterV308Remote = @(& git -C $Repo rev-parse origin/main)[0].Trim()
if ($AfterV308Head -ne $Head -or $AfterV308Remote -ne $Head) {
    throw (
        "Recovery tooling authority changed after v308 run: " +
        "captured=$Head head=$AfterV308Head origin/main=$AfterV308Remote"
    )
}

$V307Diagnostic = Join-Path $V307Out "recovery-release\release\javac-diagnostic-private.json"
$V307CleanRebuild = Join-Path $V307Out "recovery-release\release\rebuild\clean-rebuild.json"
$V307Binding = Join-Path $V307Out "recovery-release\release\javac-build-binding.json"

$V308Diagnostic = Join-Path $V308Out "release\javac-diagnostic-private.json"
$V308CleanRebuild = Join-Path $V308Out "release\rebuild\clean-rebuild.json"
$V308Binding = Join-Path $V308Out "release\javac-build-binding.json"

foreach ($Path in @(
    $V307Diagnostic,
    $V307CleanRebuild,
    $V307Binding,
    $V308Diagnostic,
    $V308CleanRebuild,
    $V308Binding
)) {
    Require-File $Path
}

$BindingFields = @{
    binding_id = "/binding_id"
    tooling_commit = "/tooling_commit"
    build_id = "/build_id"
    source_authority_sha256 = "/source_authority_sha256"
    frontier_id = "/frontier_id"
}

$V307BindingDoc = Get-Projection -Path $V307Binding -Fields $BindingFields
$V308BindingDoc = Get-Projection -Path $V308Binding -Fields $BindingFields

if ([string]$V307BindingDoc.tooling_commit -ne $Head) {
    throw (
        "v307 binding tooling commit drifted: " +
        $V307BindingDoc.tooling_commit +
        " != " +
        $Head
    )
}
if ([string]$V308BindingDoc.tooling_commit -ne $Head) {
    throw (
        "v308 binding tooling commit drifted: " +
        $V308BindingDoc.tooling_commit +
        " != " +
        $Head
    )
}
if ([string]$V307BindingDoc.build_id -ne "v307") {
    throw "v307 binding build ID drifted."
}
if ([string]$V308BindingDoc.build_id -ne "v308") {
    throw "v308 binding build ID drifted."
}

$CompareArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $CompareScript,
    "-Repo",
    $Repo,
    "-V307Diagnostic",
    $V307Diagnostic,
    "-V307CleanRebuild",
    $V307CleanRebuild,
    "-V307BindingReport",
    $V307Binding,
    "-V308Diagnostic",
    $V308Diagnostic,
    "-V308CleanRebuild",
    $V308CleanRebuild,
    "-V308BindingReport",
    $V308Binding,
    "-OutDir",
    $CompareOut
)

Write-Host ""
Write-Host "=== COMPARE SAME-COMMIT v307-v308 FRONTIERS ===" -ForegroundColor Cyan
& powershell.exe @CompareArgs
$CompareExit = $LASTEXITCODE
if ($CompareExit -ne 0) {
    throw "Cross-version javac comparison failed with exit=$CompareExit"
}

$CompareReport = Join-Path $CompareOut "v307-v308-javac-frontier.json"
Require-File $CompareReport

$CompareSummary = Get-Projection -Path $CompareReport -Fields @{
    report_id = "/report_id"
    old_frontier_id = "/old_frontier_id"
    new_frontier_id = "/new_frontier_id"
    old_total_errors = "/summary/old_total_errors"
    new_total_errors = "/summary/new_total_errors"
    shared_errors = "/summary/shared_errors"
    old_only_errors = "/summary/old_only_errors"
    new_only_errors = "/summary/new_only_errors"
    exact_frontier_equal = "/summary/exact_frontier_equal"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " EQUIVALENT-TOOLING v307-v308 JAVAC EVIDENCE - PASS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "TOOLING_COMMIT=$Head"
Write-Host "V307_RUN_EXIT=$V307Exit"
Write-Host "V308_RUN_EXIT=$V308Exit"
Write-Host "V307_BINDING_ID=$($V307BindingDoc.binding_id)"
Write-Host "V308_BINDING_ID=$($V308BindingDoc.binding_id)"
Write-Host "V307_FRONTIER=$($CompareSummary.old_frontier_id)"
Write-Host "V308_FRONTIER=$($CompareSummary.new_frontier_id)"
Write-Host "V307_ERRORS=$($CompareSummary.old_total_errors)"
Write-Host "V308_ERRORS=$($CompareSummary.new_total_errors)"
Write-Host "SHARED_ERRORS=$($CompareSummary.shared_errors)"
Write-Host "V307_ONLY_ERRORS=$($CompareSummary.old_only_errors)"
Write-Host "V308_ONLY_ERRORS=$($CompareSummary.new_only_errors)"
Write-Host "EXACT_FRONTIER_EQUAL=$($CompareSummary.exact_frontier_equal)"
Write-Host "REPORT_ID=$($CompareSummary.report_id)"
Write-Host "REPORT=$CompareReport"

if ($V307Exit -eq 0 -and $V308Exit -eq 0) {
    Write-Host "EQUIVALENT_TOOLING_RECOVERY_RELEASES_READY=true" -ForegroundColor Green
    exit 0
}

Write-Host "EQUIVALENT_TOOLING_RECOVERY_RELEASES_READY=false" -ForegroundColor Yellow
Write-Host "EQUIVALENT_TOOLING_V307_V308_BLOCKED_AT_SOURCE_FRONTIER" -ForegroundColor Yellow
exit 3
