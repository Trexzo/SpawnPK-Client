[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [string]$V307Diagnostic = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest\recovery-release\release\javac-diagnostic-private.json",
    [string]$V307CleanRebuild = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest\recovery-release\release\rebuild\clean-rebuild.json",
    [string]$V307BindingReport = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Backtest\recovery-release\release\javac-build-binding.json",
    [string]$V308Diagnostic = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact\release\javac-diagnostic-private.json",
    [string]$V308CleanRebuild = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact\release\rebuild\clean-rebuild.json",
    [string]$V308BindingReport = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact\release\javac-build-binding.json",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-CrossVersion-Javac"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$V307Authority =
    "6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662"
$V308Authority =
    "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
$BinaryBacktestId = "XVERBIN_E56BD2FB8CCC172D6184"
$LegacyBaselineFixture = Join-Path $Repo (
    "fixtures\v307-v308-source-m1-exact-javac-parity-07ed6f9.json"
)

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
        [Parameter(Mandatory = $true)][string]$ToolingCommit,
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
        "--tooling-commit",
        $ToolingCommit,
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
Require-File $V307BindingReport
Require-File $V308Diagnostic
Require-File $V308CleanRebuild
Require-File $V308BindingReport
Require-File $LegacyBaselineFixture

if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$V307VerifiedBinding = Join-Path $OutDir "v307-javac-build-binding-verified.json"
$V308VerifiedBinding = Join-Path $OutDir "v308-javac-build-binding-verified.json"
$Report = Join-Path $OutDir "v307-v308-javac-frontier.json"
$Checkpoint = Join-Path $OutDir "v307-v308-javac-checkpoint.json"
$LegacyBaselineDelta = Join-Path $OutDir "legacy-350-to-current-delta.json"

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

$BindingFields = @{
    binding_id = "/binding_id"
    tooling_commit = "/tooling_commit"
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

$V307RecordedBinding = Get-Projection -Path $V307BindingReport -Fields $BindingFields
$V308RecordedBinding = Get-Projection -Path $V308BindingReport -Fields $BindingFields

if (
    [string]$V307RecordedBinding.tooling_commit -ne
    [string]$V308RecordedBinding.tooling_commit
) {
    throw (
        "Recovery tooling commit mismatch: v307=" +
        $V307RecordedBinding.tooling_commit +
        " v308=" +
        $V308RecordedBinding.tooling_commit
    )
}

$InputToolingCommit = [string]$V307RecordedBinding.tooling_commit
if ($InputToolingCommit -notmatch "^[0-9a-f]{40}$") {
    throw "Input tooling commit is not lowercase 40-hex."
}

Write-Host ""
Write-Host "=== VERIFY v307 BUILD + TOOLING BINDING ===" -ForegroundColor Cyan
Invoke-JavacBuildBinding `
    -Diagnostic $V307Diagnostic `
    -CleanRebuild $V307CleanRebuild `
    -BuildId "v307" `
    -AuthoritySha256 $V307Authority `
    -ToolingCommit $InputToolingCommit `
    -Out $V307VerifiedBinding

Write-Host ""
Write-Host "=== VERIFY v308 BUILD + TOOLING BINDING ===" -ForegroundColor Cyan
Invoke-JavacBuildBinding `
    -Diagnostic $V308Diagnostic `
    -CleanRebuild $V308CleanRebuild `
    -BuildId "v308" `
    -AuthoritySha256 $V308Authority `
    -ToolingCommit $InputToolingCommit `
    -Out $V308VerifiedBinding

$V307VerifiedBindingDoc = Get-Projection -Path $V307VerifiedBinding -Fields $BindingFields
$V308VerifiedBindingDoc = Get-Projection -Path $V308VerifiedBinding -Fields $BindingFields

if (
    [string]$V307RecordedBinding.binding_id -ne
    [string]$V307VerifiedBindingDoc.binding_id
) {
    throw "v307 recorded javac build binding failed verification."
}
if (
    [string]$V308RecordedBinding.binding_id -ne
    [string]$V308VerifiedBindingDoc.binding_id
) {
    throw "v308 recorded javac build binding failed verification."
}

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

if ($Summary.identifiers_included -ne $false) {
    throw "Refusing unexpected identifier-bearing cross-version report."
}
if (
    $V307VerifiedBindingDoc.identifiers_included -ne $false -or
    $V308VerifiedBindingDoc.identifiers_included -ne $false
) {
    throw "Refusing unexpected identifier-bearing build binding."
}
if (
    $V307VerifiedBindingDoc.diagnostic_report_id -ne
    $Summary.old_diagnostic_report_id -or
    $V307VerifiedBindingDoc.diagnostic_input_sha256 -ne
    $Summary.old_diagnostic_input_sha256 -or
    $V307VerifiedBindingDoc.frontier_id -ne
    $Summary.old_frontier_id
) {
    throw "v307 build binding does not match comparator input authority."
}
if (
    $V308VerifiedBindingDoc.diagnostic_report_id -ne
    $Summary.new_diagnostic_report_id -or
    $V308VerifiedBindingDoc.diagnostic_input_sha256 -ne
    $Summary.new_diagnostic_input_sha256 -or
    $V308VerifiedBindingDoc.frontier_id -ne
    $Summary.new_frontier_id
) {
    throw "v308 build binding does not match comparator input authority."
}

$CheckpointArguments = @(
    "-3.13",
    "-m",
    "spk_recovery.cross_version_javac_checkpoint_cli",
    $Report,
    $V307VerifiedBinding,
    $V308VerifiedBinding,
    "--binary-backtest-id",
    $BinaryBacktestId,
    "--out",
    $Checkpoint
)

Write-Host ""
Write-Host "=== EXPORT REDACTED CROSS-VERSION CHECKPOINT ===" -ForegroundColor Cyan
& py @CheckpointArguments
$CheckpointExit = $LASTEXITCODE
if ($CheckpointExit -ne 0) {
    throw "Cross-version javac checkpoint export failed with exit=$CheckpointExit"
}
Require-File $Checkpoint

$CheckpointSummary = Get-Projection -Path $Checkpoint -Fields @{
    checkpoint_id = "/checkpoint_id"
    tooling_commit = "/tooling_commit"
    old_build_id = "/old/build_id"
    new_build_id = "/new/build_id"
    comparison_report_id = "/comparison/report_id"
    exact_frontier_equal = "/comparison/summary/exact_frontier_equal"
    identifiers_included = "/identifiers_included"
}

if ($CheckpointSummary.identifiers_included -ne $false) {
    throw "Refusing unexpected identifier-bearing checkpoint."
}
if ([string]$CheckpointSummary.tooling_commit -ne $InputToolingCommit) {
    throw "Checkpoint tooling commit does not match comparator inputs."
}
if (
    [string]$CheckpointSummary.comparison_report_id -ne
    [string]$Summary.report_id
) {
    throw "Checkpoint does not bind the emitted comparator report."
}

$LegacyDeltaArguments = @(
    "-3.13",
    "-m",
    "spk_recovery.cross_version_javac_legacy_baseline_delta_cli",
    $LegacyBaselineFixture,
    $Checkpoint,
    "--out",
    $LegacyBaselineDelta
)

Write-Host ""
Write-Host "=== COMPARE CANONICAL 350 BASELINE -> CURRENT CHECKPOINT ===" -ForegroundColor Cyan
& py @LegacyDeltaArguments
$LegacyDeltaExit = $LASTEXITCODE
if ($LegacyDeltaExit -ne 0) {
    throw "Legacy 350 baseline delta failed with exit=$LegacyDeltaExit"
}
Require-File $LegacyBaselineDelta

$LegacyVerifyArguments = @(
    "-3.13",
    "-m",
    "spk_recovery.cross_version_javac_legacy_baseline_delta_verify_cli",
    $LegacyBaselineFixture,
    $Checkpoint,
    $LegacyBaselineDelta
)

Write-Host ""
Write-Host "=== VERIFY EMITTED LEGACY BASELINE DELTA ===" -ForegroundColor Cyan
& py @LegacyVerifyArguments
$LegacyVerifyExit = $LASTEXITCODE
if ($LegacyVerifyExit -ne 0) {
    throw "Legacy 350 baseline delta verification failed with exit=$LegacyVerifyExit"
}

$LegacyDeltaSummary = Get-Projection -Path $LegacyBaselineDelta -Fields @{
    delta_id = "/delta_id"
    baseline_fixture_id = "/baseline_fixture_id"
    current_checkpoint_id = "/current_checkpoint_id"
    baseline_tooling_commit = "/baseline_tooling_commit"
    current_tooling_commit = "/current_tooling_commit"
    old_total_errors_delta = "/scalar_delta/old_total_errors"
    new_total_errors_delta = "/scalar_delta/new_total_errors"
    exact_frontier_equality_transition = "/exact_frontier_equality_transition"
    identifiers_included = "/identifiers_included"
}

if ($LegacyDeltaSummary.identifiers_included -ne $false) {
    throw "Refusing unexpected identifier-bearing legacy baseline delta."
}
if (
    [string]$LegacyDeltaSummary.current_checkpoint_id -ne
    [string]$CheckpointSummary.checkpoint_id
) {
    throw "Legacy baseline delta does not bind the emitted checkpoint."
}
if (
    [string]$LegacyDeltaSummary.current_tooling_commit -ne
    $InputToolingCommit
) {
    throw "Legacy baseline delta tooling commit does not match comparator inputs."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " CROSS-VERSION JAVAC FRONTIER COMPARISON - PASS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "COMPARATOR_COMMIT=$Head"
Write-Host "REPORT_ID=$($Summary.report_id)"
Write-Host "INPUT_TOOLING_COMMIT=$InputToolingCommit"
Write-Host "V307_BINDING_ID=$($V307VerifiedBindingDoc.binding_id)"
Write-Host "V308_BINDING_ID=$($V308VerifiedBindingDoc.binding_id)"
Write-Host "V307_SOURCE_AUTHORITY=$($V307VerifiedBindingDoc.source_authority_sha256)"
Write-Host "V308_SOURCE_AUTHORITY=$($V308VerifiedBindingDoc.source_authority_sha256)"
Write-Host "V307_REBUILD_ID=$($V307VerifiedBindingDoc.rebuild_id)"
Write-Host "V308_REBUILD_ID=$($V308VerifiedBindingDoc.rebuild_id)"
Write-Host "V307_WORKSPACE_ID=$($V307VerifiedBindingDoc.workspace_id)"
Write-Host "V308_WORKSPACE_ID=$($V308VerifiedBindingDoc.workspace_id)"
Write-Host "V307_SOURCE_TREE_SHA256=$($V307VerifiedBindingDoc.source_tree_sha256)"
Write-Host "V308_SOURCE_TREE_SHA256=$($V308VerifiedBindingDoc.source_tree_sha256)"
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
Write-Host "V307_VERIFIED_BINDING_REPORT=$V307VerifiedBinding"
Write-Host "V308_VERIFIED_BINDING_REPORT=$V308VerifiedBinding"
Write-Host "REPORT=$Report"
Write-Host "CHECKPOINT_ID=$($CheckpointSummary.checkpoint_id)"
Write-Host "CHECKPOINT=$Checkpoint"
Write-Host "LEGACY_BASELINE_DELTA_ID=$($LegacyDeltaSummary.delta_id)"
Write-Host "LEGACY_BASELINE_FIXTURE_ID=$($LegacyDeltaSummary.baseline_fixture_id)"
Write-Host "LEGACY_BASELINE_TOOLING_COMMIT=$($LegacyDeltaSummary.baseline_tooling_commit)"
Write-Host "CURRENT_CHECKPOINT_TOOLING_COMMIT=$($LegacyDeltaSummary.current_tooling_commit)"
Write-Host "V307_ERRORS_DELTA_FROM_350=$($LegacyDeltaSummary.old_total_errors_delta)"
Write-Host "V308_ERRORS_DELTA_FROM_350=$($LegacyDeltaSummary.new_total_errors_delta)"
Write-Host "EXACT_FRONTIER_EQUALITY_TRANSITION=$($LegacyDeltaSummary.exact_frontier_equality_transition)"
Write-Host "LEGACY_BASELINE_DELTA=$LegacyBaselineDelta"
