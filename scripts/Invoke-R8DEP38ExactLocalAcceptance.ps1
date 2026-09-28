[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [Parameter(Mandatory = $true)]
    [string]$ClientJar,
    [Parameter(Mandatory = $true)]
    [string]$RuntimeReadiness,
    [Parameter(Mandatory = $true)]
    [string]$PrivateReplacementPlan,
    [Parameter(Mandatory = $true)]
    [string]$PrivateReplacementExtension,
    [Parameter(Mandatory = $true)]
    [string]$PrivateExtendedClosure,
    [Parameter(Mandatory = $true)]
    [string]$PrivateExtendedResource,
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

$Required = @(
    $ClientJar,
    $RuntimeReadiness,
    $PrivateReplacementPlan,
    $PrivateReplacementExtension,
    $PrivateExtendedClosure,
    $PrivateExtendedResource,
    $BundledJar
)
foreach ($Path in $Required) {
    Require-File $Path
}

if ($OfficialArtifacts.Count -lt 1) {
    throw "At least one official artifact is required."
}
$SeenArtifacts = @{}
foreach ($Artifact in $OfficialArtifacts) {
    Require-File $Artifact
    $Full = [System.IO.Path]::GetFullPath($Artifact)
    if ($SeenArtifacts.ContainsKey($Full)) {
        throw "Duplicate official artifact path: $Artifact"
    }
    $SeenArtifacts[$Full] = $true
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

$Plan = Join-Path $OutDir "runtime-substitution-plan-private.json"
$Postimage = Join-Path $OutDir "postimage"

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host "AUTHORITY_COMMIT=$Head" -ForegroundColor Green
Write-Host "V308_SHA256=$ClientSha" -ForegroundColor Green
Write-Host "BUNDLED_SHA256=$BundledSha" -ForegroundColor Green

$PlanArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.dependency_runtime_substitution_plan_cli",
    $RuntimeReadiness,
    $PrivateReplacementPlan,
    $PrivateReplacementExtension,
    $PrivateExtendedClosure,
    $PrivateExtendedResource,
    $BundledJar
)
foreach ($Artifact in $OfficialArtifacts) {
    $PlanArgs += @("--official-artifact", $Artifact)
}
$PlanArgs += @("--include-identifiers", "--out", $Plan)

Write-Host ""
Write-Host "=== BUILD EXACT PRIVATE SUBSTITUTION PLAN ===" -ForegroundColor Cyan
& py @PlanArgs
if ($LASTEXITCODE -ne 0) {
    throw "R8DEP37 private substitution plan failed."
}

$ApplyArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.dependency_runtime_substitution_apply_cli",
    "apply",
    $Plan,
    $BundledJar
)
foreach ($Artifact in $OfficialArtifacts) {
    $ApplyArgs += @("--official-artifact", $Artifact)
}
$ApplyArgs += @("--out-dir", $Postimage)

Write-Host ""
Write-Host "=== APPLY EXACT RUNTIME SUBSTITUTION ===" -ForegroundColor Cyan
& py @ApplyArgs
if ($LASTEXITCODE -ne 0) {
    throw "R8DEP38 exact substitution apply failed."
}

$VerifyArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.dependency_runtime_substitution_apply_cli",
    "verify",
    $Plan,
    $BundledJar
)
foreach ($Artifact in $OfficialArtifacts) {
    $VerifyArgs += @("--official-artifact", $Artifact)
}
$VerifyArgs += @("--out-dir", $Postimage)

Write-Host ""
Write-Host "=== VERIFY EXACT RUNTIME POSTIMAGE ===" -ForegroundColor Cyan
& py @VerifyArgs
if ($LASTEXITCODE -ne 0) {
    throw "R8DEP38 exact substitution verification failed."
}

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
Write-Host "RUNTIME_POSTIMAGE_ID=$($Manifest.runtime_postimage_id)" -ForegroundColor Green
Write-Host "PLAN=$Plan"
Write-Host "POSTIMAGE=$Postimage"
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " R8DEP38 EXACT LOCAL ACCEPTANCE - PASS" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
