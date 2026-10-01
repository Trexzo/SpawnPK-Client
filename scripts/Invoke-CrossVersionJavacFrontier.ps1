[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [string]$V307Diagnostic = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest\recovery-release\release\javac-diagnostic-private.json",
    [string]$V307CleanRebuild = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest\recovery-release\release\rebuild\clean-rebuild.json",
    [string]$V308Diagnostic = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact\release\javac-diagnostic-private.json",
    [string]$V308CleanRebuild = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact\release\rebuild\clean-rebuild.json",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-CrossVersion-Javac"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$V307Authority =
    "6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662"
$V308Authority =
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

function Invoke-JavacBuildBinding {
    param(
        [Parameter(Mandatory = $true)][string]$Diagnostic,
        [Parameter(Mandatory = $true)][string]$CleanRebuild,
        [Parameter(Mandatory = $true)][string]$BuildId,
        [Parameter(Mandatory = $true)][string]$AuthoritySha256,
        [Parameter(Mandatory = $true)][string]$Out
    )

    $Arguments = @(
        "-3.13",
        "-m",
        "spk_recovery.javac_build_binding_cli",
        $Diagnostic,
        $CleanRebuild,
        "--expected-build-id",
        $BuildId,
        "--expected-authority-sha256",
        $AuthoritySha256,
        "--out",
        $Out
    )

    & py @Arguments
    $Exit = $LASTEXITCODE
    if ($Exit -ne 0) {
        throw "Javac build binding failed for $BuildId with exit=$Exit"
    }

    Require-File $Out
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
Require-File $V307CleanRebuild
Require-File $V308Diagnostic
Require-File $V308CleanRebuild

if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$V307BindingReport = Join-Path $OutDir "v307-javac-build-binding.json"
$V308BindingReport = Join-Path $OutDir "v308-javac-build-binding.json"
$Report = Join-Path $OutDir "v307-v308-javac-frontier.json"

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host ""
Write-Host "=== BIND v307 DIAGNOSTIC TO EXACT CLEAN REBUILD ===" -ForegroundColor Cyan
Invoke-JavacBuildBinding `
    -Diagnostic $V307Diagnostic `
    -CleanRebuild $V307CleanRebuild `
    -BuildId "v307" `
    -AuthoritySha256 $V307Authority `
    -Out $V307BindingReport

Write-Host ""
Write-Host "=== BIND v308 DIAGNOSTIC TO EXACT CLEAN REBUILD ===" -ForegroundColor Cyan
Invoke-JavacBuildBinding `
    -Diagnostic $V308Diagnostic `
    -CleanRebuild $V308CleanRebuild `
    -BuildId "v308" `
    -AuthoritySha256 $V308Authority `
    -Out $V308BindingReport

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
    old_diagnostic_report_id = "/old_diagnostic_report_id"
    new_diagnostic_report_id = "/new_diagnostic_report_id"
    old_diagnostic_input_sha256 = "/old_diagnostic_input_sha256"
    new_diagnostic_input_sha256 = "/new_diagnostic_input_sha256"
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

$BindingFields = @{
    binding_id = "/binding_id"
    build_id = "/build_id"
    source_authority_sha256 = "/source_authority_sha256"
    rebuild_id = "/rebuild_id"
    workspace_id = "/workspace_id"
    source_tree_sha256 = "/source_tree_sha256"
    diagnostic_report_id = "/diagnostic_report_id"
    diagnostic_input_sha256 = "/diagnostic_input_sha256"
    frontier_id = "/frontier_id"
    project_binary_fallback_count = "/project_binary_fallback_count"
    identifiers_included = "/identifiers_included"
}

$V307Binding = Get-Projection -Path $V307BindingReport -Fields $BindingFields
$V308Binding = Get-Projection -Path $V308BindingReport -Fields $BindingFields

if ($Summary.identifiers_included -ne $false) {
    throw "Refusing unexpected identifier-bearing cross-version report."
}
if (
    $V307Binding.identifiers_included -ne $false -or
    $V308Binding.identifiers_included -ne $false
) {
    throw "Refusing unexpected identifier-bearing build binding."
}
if (
    $V307Binding.diagnostic_report_id -ne
    $Summary.old_diagnostic_report_id -or
    $V307Binding.diagnostic_input_sha256 -ne
    $Summary.old_diagnostic_input_sha256 -or
    $V307Binding.frontier_id -ne
    $Summary.old_frontier_id
) {
    throw "v307 build binding does not match comparator input authority."
}
if (
    $V308Binding.diagnostic_report_id -ne
    $Summary.new_diagnostic_report_id -or
    $V308Binding.diagnostic_input_sha256 -ne
    $Summary.new_diagnostic_input_sha256 -or
    $V308Binding.frontier_id -ne
    $Summary.new_frontier_id
) {
    throw "v308 build binding does not match comparator input authority."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " CROSS-VERSION JAVAC FRONTIER COMPARISON - PASS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "COMPARATOR_COMMIT=$Head"
Write-Host "REPORT_ID=$($Summary.report_id)"
Write-Host "V307_BINDING_ID=$($V307Binding.binding_id)"
Write-Host "V308_BINDING_ID=$($V308Binding.binding_id)"
Write-Host "V307_SOURCE_AUTHORITY=$($V307Binding.source_authority_sha256)"
Write-Host "V308_SOURCE_AUTHORITY=$($V308Binding.source_authority_sha256)"
Write-Host "V307_REBUILD_ID=$($V307Binding.rebuild_id)"
Write-Host "V308_REBUILD_ID=$($V308Binding.rebuild_id)"
Write-Host "V307_WORKSPACE_ID=$($V307Binding.workspace_id)"
Write-Host "V308_WORKSPACE_ID=$($V308Binding.workspace_id)"
Write-Host "V307_SOURCE_TREE_SHA256=$($V307Binding.source_tree_sha256)"
Write-Host "V308_SOURCE_TREE_SHA256=$($V308Binding.source_tree_sha256)"
Write-Host "V307_DIAGNOSTIC_REPORT_ID=$($Summary.old_diagnostic_report_id)"
Write-Host "V308_DIAGNOSTIC_REPORT_ID=$($Summary.new_diagnostic_report_id)"
Write-Host "V307_DIAGNOSTIC_INPUT_SHA256=$($Summary.old_diagnostic_input_sha256)"
Write-Host "V308_DIAGNOSTIC_INPUT_SHA256=$($Summary.new_diagnostic_input_sha256)"
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
Write-Host "V307_BINDING_REPORT=$V307BindingReport"
Write-Host "V308_BINDING_REPORT=$V308BindingReport"
Write-Host "REPORT=$Report"
