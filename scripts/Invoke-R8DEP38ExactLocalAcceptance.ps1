[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [Parameter(Mandatory = $true)]
    [string]$ClientJar,
    [Parameter(Mandatory = $true)]
    [string]$BundledJar,
    [Parameter(Mandatory = $true)]
    [string[]]$OfficialArtifacts,
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-R8DEP38-Exact"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$ExpectedV308 = "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
$ExpectedReadable = "e12e4f917ba2c48ea306e3b4d4cc19c58c5e23cd4f5c33f4ae339ea6fce53c99"

function Require-File {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

function Invoke-PyChecked {
    param(
        [string]$Label,
        [string[]]$Arguments
    )
    Write-Host ""
    Write-Host ("=== " + $Label + " ===") -ForegroundColor Cyan
    & py @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ($Label + " failed with exit=" + $LASTEXITCODE)
    }
}

function Invoke-PyJsonStdout {
    param(
        [string]$Label,
        [string[]]$Arguments,
        [string]$Out
    )
    Write-Host ""
    Write-Host ("=== " + $Label + " ===") -ForegroundColor Cyan
    $Rows = @(& py @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw ($Label + " failed with exit=" + $LASTEXITCODE)
    }
    $Text = ($Rows -join [Environment]::NewLine) + [Environment]::NewLine
    [System.IO.File]::WriteAllText(
        $Out,
        $Text,
        (New-Object System.Text.UTF8Encoding($false))
    )
    $null = Get-Content -LiteralPath $Out -Raw | ConvertFrom-Json
}

function Add-OfficialArtifactArgs {
    param([System.Collections.ArrayList]$Arguments)
    foreach ($Artifact in $OfficialArtifacts) {
        [void]$Arguments.Add("--official-artifact")
        [void]$Arguments.Add($Artifact)
    }
}

Write-Host ""
Write-Host "=== R8DEP38 EXACT LOCAL ACCEPTANCE ===" -ForegroundColor Cyan

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
if ($Head -notmatch "^[0-9a-f]{40}$") {
    throw "Current authority commit is not lowercase 40-hex: $Head"
}

Require-File $ClientJar
Require-File $BundledJar
if ($OfficialArtifacts.Count -lt 1) {
    throw "At least one official artifact is required."
}

$SeenArtifactPaths = @{}
$SeenArtifactNames = @{}
foreach ($Artifact in $OfficialArtifacts) {
    Require-File $Artifact
    $Full = [System.IO.Path]::GetFullPath($Artifact)
    $Name = [System.IO.Path]::GetFileName($Full)
    if ($SeenArtifactPaths.ContainsKey($Full)) {
        throw "Duplicate official artifact path: $Artifact"
    }
    if ($SeenArtifactNames.ContainsKey($Name)) {
        throw "Duplicate official artifact basename: $Name"
    }
    $SeenArtifactPaths[$Full] = $true
    $SeenArtifactNames[$Name] = $true
}

$ClientSha = (Get-FileHash -LiteralPath $ClientJar -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ClientSha -ne $ExpectedV308) {
    throw "Exact v308 SHA mismatch: $ClientSha"
}

$BundledSha = (Get-FileHash -LiteralPath $BundledJar -Algorithm SHA256).Hash.ToLowerInvariant()
if ($BundledSha -ne $ExpectedReadable) {
    throw "Readable/bundled SHA mismatch: $BundledSha"
}

if (Test-Path -LiteralPath $OutDir) {
    $Existing = @(Get-ChildItem -LiteralPath $OutDir -Force)
    if ($Existing.Count -ne 0) {
        throw "Output directory must be empty: $OutDir"
    }
} else {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$AuthorityDir = Join-Path $OutDir "authority"
$RuntimeDir = Join-Path $OutDir "runtime"
$Postimage = Join-Path $OutDir "postimage"
New-Item -ItemType Directory -Path $AuthorityDir | Out-Null
New-Item -ItemType Directory -Path $RuntimeDir | Out-Null

$ReferenceSurface = Join-Path $AuthorityDir "dependency-reference-surface.json"
$RemapProof = Join-Path $AuthorityDir "dependency-remap-proof.json"
$Retention = Join-Path $AuthorityDir "dependency-retention.json"
$ReplacementPlan = Join-Path $AuthorityDir "dependency-replacement-plan-private.json"

$RuntimeFrontier = Join-Path $RuntimeDir "dependency-runtime-frontier-private.json"
$RuntimeClosure = Join-Path $RuntimeDir "dependency-runtime-closure-private.json"
$RuntimeResource = Join-Path $RuntimeDir "dependency-runtime-resource-private.json"
$RuntimeDynamic = Join-Path $RuntimeDir "dependency-runtime-dynamic-private.json"
$RuntimeDynamicTarget = Join-Path $RuntimeDir "dependency-runtime-dynamic-target-private.json"
$RuntimeAugmented = Join-Path $RuntimeDir "dependency-runtime-augmented-closure-private.json"
$RuntimeDynamicMapping = Join-Path $RuntimeDir "dependency-runtime-dynamic-mapping-private.json"
$RuntimeDynamicMember = Join-Path $RuntimeDir "dependency-runtime-dynamic-member-private.json"
$ReplacementExtension = Join-Path $RuntimeDir "dependency-replacement-extension-private.json"
$ExtendedClosure = Join-Path $RuntimeDir "dependency-runtime-extended-closure-private.json"
$ExtendedResource = Join-Path $RuntimeDir "dependency-runtime-extended-resource-private.json"
$RuntimeReadiness = Join-Path $RuntimeDir "dependency-runtime-readiness.json"
$SubstitutionPlan = Join-Path $RuntimeDir "runtime-substitution-plan-private.json"

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host "AUTHORITY_COMMIT=$Head" -ForegroundColor Green
Write-Host "V308_SHA256=$ClientSha" -ForegroundColor Green
Write-Host "BUNDLED_SHA256=$BundledSha" -ForegroundColor Green
Write-Host "OFFICIAL_ARTIFACT_COUNT=$($OfficialArtifacts.Count)" -ForegroundColor Green

$ReferenceArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.dependency_reference_surface",
    $BundledJar,
    "--project-prefix",
    "rs/"
)
Invoke-PyJsonStdout "REBUILD DEPREF AUTHORITY" $ReferenceArgs $ReferenceSurface

$RemapArgs = [System.Collections.ArrayList]@(
    "-3.13",
    "-m",
    "spk_recovery.dependency_remap_proof",
    $ReferenceSurface,
    $BundledJar
)
foreach ($Artifact in $OfficialArtifacts) {
    [void]$RemapArgs.Add($Artifact)
}
[void]$RemapArgs.Add("--java-release")
[void]$RemapArgs.Add("9")
Invoke-PyJsonStdout "REBUILD DEPREMAP AUTHORITY" ([string[]]$RemapArgs) $RemapProof

$RetentionArgs = [System.Collections.ArrayList]@(
    "-3.13",
    "-m",
    "spk_recovery.dependency_retention",
    $ReferenceSurface,
    $RemapProof,
    $BundledJar
)
foreach ($Artifact in $OfficialArtifacts) {
    [void]$RetentionArgs.Add($Artifact)
}
[void]$RetentionArgs.Add("--java-release")
[void]$RetentionArgs.Add("9")
Invoke-PyJsonStdout "REBUILD DEPRETAIN AUTHORITY" ([string[]]$RetentionArgs) $Retention

$ReplacementArgs = [System.Collections.ArrayList]@(
    "-3.13",
    "-m",
    "spk_recovery.dependency_replacement_plan_cli",
    $ReferenceSurface,
    $RemapProof,
    $BundledJar
)
foreach ($Artifact in $OfficialArtifacts) {
    [void]$ReplacementArgs.Add($Artifact)
}
[void]$ReplacementArgs.Add("--retention-report")
[void]$ReplacementArgs.Add($Retention)
[void]$ReplacementArgs.Add("--include-identifiers")
[void]$ReplacementArgs.Add("--out")
[void]$ReplacementArgs.Add($ReplacementPlan)
Invoke-PyChecked "REBUILD PRIVATE DEPREPLACE AUTHORITY" ([string[]]$ReplacementArgs)

function New-RuntimeArgs {
    param(
        [string]$Module,
        [string[]]$Positionals,
        [string]$Out,
        [bool]$IncludeIdentifiers = $true,
        [bool]$WithArtifacts = $true
    )
    $ArgsList = [System.Collections.ArrayList]@("-3.13", "-m", $Module)
    foreach ($Value in $Positionals) {
        [void]$ArgsList.Add($Value)
    }
    if ($WithArtifacts) {
        Add-OfficialArtifactArgs $ArgsList
    }
    if ($IncludeIdentifiers) {
        [void]$ArgsList.Add("--include-identifiers")
    }
    [void]$ArgsList.Add("--out")
    [void]$ArgsList.Add($Out)
    return [string[]]$ArgsList
}

Invoke-PyChecked "R8DEP24 RUNTIME FRONTIER" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_frontier_cli" @(
        $ReplacementPlan, $BundledJar
    ) $RuntimeFrontier
)

Invoke-PyChecked "R8DEP25 RUNTIME CLOSURE" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_closure_cli" @(
        $ReplacementPlan, $RuntimeFrontier, $BundledJar
    ) $RuntimeClosure
)

Invoke-PyChecked "R8DEP26 RESOURCE EQUIVALENCE" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_resource_cli" @(
        $RuntimeClosure, $BundledJar
    ) $RuntimeResource
)

Invoke-PyChecked "R8DEP27-28 DYNAMIC INVENTORY" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_dynamic_cli" @(
        $RuntimeResource, $BundledJar
    ) $RuntimeDynamic $true $false
)

Invoke-PyChecked "R8DEP29 DYNAMIC TARGETS" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_dynamic_target_cli" @(
        $RuntimeDynamic, $ReplacementPlan, $RuntimeResource, $BundledJar
    ) $RuntimeDynamicTarget $true $false
)

Invoke-PyChecked "R8DEP30 AUGMENTED CLOSURE" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_augmented_closure_cli" @(
        $ReplacementPlan, $RuntimeClosure, $RuntimeDynamicTarget, $BundledJar
    ) $RuntimeAugmented
)

Invoke-PyChecked "R8DEP31 DYNAMIC MAPPING" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_dynamic_mapping_cli" @(
        $RuntimeAugmented, $ReplacementPlan, $BundledJar
    ) $RuntimeDynamicMapping
)

Invoke-PyChecked "R8DEP32 DYNAMIC MEMBER TRANSPORT" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_dynamic_member_cli" @(
        $RuntimeDynamicMapping, $ReplacementPlan, $BundledJar
    ) $RuntimeDynamicMember
)

Invoke-PyChecked "R8DEP33 REPLACEMENT EXTENSION" (
    New-RuntimeArgs "spk_recovery.dependency_replacement_extension_cli" @(
        $ReplacementPlan, $RuntimeDynamicMapping, $RuntimeDynamicMember, $BundledJar
    ) $ReplacementExtension
)

Invoke-PyChecked "R8DEP34 EXTENDED CLOSURE" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_extended_closure_cli" @(
        $ReplacementPlan,
        $ReplacementExtension,
        $RuntimeClosure,
        $RuntimeDynamicTarget,
        $BundledJar
    ) $ExtendedClosure
)

Invoke-PyChecked "R8DEP35 EXTENDED RESOURCE" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_extended_resource_cli" @(
        $ExtendedClosure, $RuntimeResource, $BundledJar
    ) $ExtendedResource
)

Invoke-PyChecked "R8DEP36 SUBSTITUTION READINESS" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_readiness_cli" @(
        $ExtendedClosure, $ExtendedResource, $RuntimeDynamicTarget, $BundledJar
    ) $RuntimeReadiness $false $true
)

$Readiness = Get-Content -LiteralPath $RuntimeReadiness -Raw | ConvertFrom-Json
if ($Readiness.summary.runtime_dependency_substitution_ready -ne $true) {
    Write-Host ""
    Write-Host "SPK_R8DEP_EXACT_LOCAL_BLOCKED" -ForegroundColor Yellow
    Write-Host "runtime_readiness_id=$($Readiness.runtime_readiness_id)"
    Write-Host "class_closure_ready=$($Readiness.summary.class_closure_ready)"
    Write-Host "dynamic_target_ready=$($Readiness.summary.dynamic_target_ready)"
    Write-Host "resource_equivalence_ready=$($Readiness.summary.resource_equivalence_ready)"
    Write-Host "native_runtime_ready=$($Readiness.summary.native_runtime_ready)"
    Write-Host "static_class_closure_blocker_count=$($Readiness.summary.static_class_closure_blocker_count)"
    Write-Host "dynamic_class_closure_blocker_count=$($Readiness.summary.dynamic_class_closure_blocker_count)"
    Write-Host "remaining_mapping_gap_count=$($Readiness.summary.remaining_mapping_gap_count)"
    Write-Host "dynamic_target_blocker_count=$($Readiness.summary.dynamic_target_blocker_count)"
    Write-Host "service_provider_discovery_blocker_count=$($Readiness.summary.service_provider_discovery_blocker_count)"
    Write-Host "dynamic_resource_target_blocker_count=$($Readiness.summary.dynamic_resource_target_blocker_count)"
    Write-Host "native_dynamic_loading_blocker_count=$($Readiness.summary.native_dynamic_loading_blocker_count)"
    Write-Host "non_native_resource_blocker_count=$($Readiness.summary.non_native_resource_blocker_count)"
    Write-Host "native_resource_entry_count=$($Readiness.summary.native_resource_entry_count)"
    Write-Host "native_resource_blocker_count=$($Readiness.summary.native_resource_blocker_count)"
    Write-Host "native_dynamic_requirement_count=$($Readiness.summary.native_dynamic_requirement_count)"
    exit 3
}

Invoke-PyChecked "R8DEP37 PRIVATE SUBSTITUTION PLAN" (
    New-RuntimeArgs "spk_recovery.dependency_runtime_substitution_plan_cli" @(
        $RuntimeReadiness,
        $ReplacementPlan,
        $ReplacementExtension,
        $ExtendedClosure,
        $ExtendedResource,
        $BundledJar
    ) $SubstitutionPlan
)

$ApplyArgs = [System.Collections.ArrayList]@(
    "-3.13",
    "-m",
    "spk_recovery.dependency_runtime_substitution_apply_cli",
    "apply",
    $SubstitutionPlan,
    $BundledJar
)
Add-OfficialArtifactArgs $ApplyArgs
[void]$ApplyArgs.Add("--out-dir")
[void]$ApplyArgs.Add($Postimage)
Invoke-PyChecked "R8DEP38 APPLY EXACT RUNTIME SUBSTITUTION" ([string[]]$ApplyArgs)

$VerifyArgs = [System.Collections.ArrayList]@(
    "-3.13",
    "-m",
    "spk_recovery.dependency_runtime_substitution_apply_cli",
    "verify",
    $SubstitutionPlan,
    $BundledJar
)
Add-OfficialArtifactArgs $VerifyArgs
[void]$VerifyArgs.Add("--out-dir")
[void]$VerifyArgs.Add($Postimage)
Invoke-PyChecked "R8DEP38 VERIFY EXACT RUNTIME POSTIMAGE" ([string[]]$VerifyArgs)

$ManifestPath = Join-Path $Postimage "DEPENDENCY-RUNTIME-SUBSTITUTION.json"
Require-File $ManifestPath
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($Manifest.verified -ne $true) {
    throw "Runtime postimage manifest is not verified."
}
if ([string]::IsNullOrWhiteSpace([string]$Manifest.runtime_postimage_id)) {
    throw "Runtime postimage ID is missing."
}

Write-Host ""
Write-Host "RUNTIME_READINESS_ID=$($Readiness.runtime_readiness_id)" -ForegroundColor Green
Write-Host "RUNTIME_POSTIMAGE_ID=$($Manifest.runtime_postimage_id)" -ForegroundColor Green
Write-Host "POSTIMAGE=$Postimage"
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " R8DEP38 EXACT LOCAL ACCEPTANCE - PASS" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
