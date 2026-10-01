[CmdletBinding()]
param(
    [string]$Repo = "$env:USERPROFILE\Desktop\SpawnPK-Client",
    [string]$ClientJar = "$env:USERPROFILE\.spawnpk-data\client.jar",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-External-v308-Oracle",
    [string]$ExternalRevision = "fff831c2d44c890833a868d9b02e4c5d99d58064",
    [string]$ExternalUrl = "https://github.com/i-iz-adam/SpawnPk-Open-Inject.git"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExpectedV308 = "854F26FF9F134B0317572E7AC1688E6F40A231D5A4C66F8DB5D655B7F45CE7C6"

function Require-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][scriptblock]$Command
    )

    Write-Host ""
    Write-Host "=== $Label ===" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$Repo = [System.IO.Path]::GetFullPath($Repo)
$ClientJar = [System.IO.Path]::GetFullPath($ClientJar)
$OutDir = [System.IO.Path]::GetFullPath($OutDir)

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "SpawnPK-Client repo is missing: $Repo"
}
Require-File $ClientJar

$ClientSha = (
    Get-FileHash -LiteralPath $ClientJar -Algorithm SHA256
).Hash.ToUpperInvariant()
if ($ClientSha -ne $ExpectedV308) {
    throw "Exact-v308 SHA mismatch expected=$ExpectedV308 actual=$ClientSha"
}

$Git = (Get-Command git.exe -ErrorAction Stop).Source
$Py = (Get-Command py.exe -ErrorAction Stop).Source

if (Test-Path -LiteralPath $OutDir) {
    $Existing = @(Get-ChildItem -LiteralPath $OutDir -Force)
    if ($Existing.Count -ne 0) {
        throw "Output directory must be empty: $OutDir"
    }
} else {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$ExternalRepo = Join-Path $OutDir "SpawnPk-Open-Inject"
$PrivateDir = Join-Path $OutDir "private"
$Capsule = Join-Path $PrivateDir "vendored-unidentified.jar"
$CapsuleReport = Join-Path $PrivateDir "dependency-capsule.json"
$OracleReport = Join-Path $PrivateDir "external-v308-oracle.json"

New-Item -ItemType Directory -Path $PrivateDir | Out-Null

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Invoke-Checked "CLONE PINNED EXTERNAL CORPUS" {
    & $Git clone --filter=blob:none --no-checkout $ExternalUrl $ExternalRepo
}
Invoke-Checked "FETCH EXTERNAL REVISION" {
    & $Git -C $ExternalRepo fetch --depth 1 origin $ExternalRevision
}
Invoke-Checked "CHECKOUT EXTERNAL REVISION" {
    & $Git -C $ExternalRepo checkout --detach $ExternalRevision
}

$ExternalHead = (
    & $Git -C $ExternalRepo rev-parse HEAD
).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read external HEAD."
}
if ($ExternalHead -ne $ExternalRevision.ToLowerInvariant()) {
    throw "External revision drift expected=$ExternalRevision actual=$ExternalHead"
}

$DirtyBefore = @(& $Git -C $ExternalRepo status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to inspect external worktree."
}
if ($DirtyBefore.Count -ne 0) {
    throw "Fresh external checkout is unexpectedly dirty."
}

$CapsuleArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.external_oracle_dependency_capsule_cli",
    $ClientJar,
    $Capsule,
    "--report-out",
    $CapsuleReport
)
Invoke-Checked "BUILD NON-RS DEPENDENCY CAPSULE" {
    & $Py @CapsuleArgs
}

Require-File $Capsule
Require-File $CapsuleReport

$LibDir = Join-Path $ExternalRepo "libs"
New-Item -ItemType Directory -Path $LibDir -Force | Out-Null
$Vendored = Join-Path $LibDir "vendored-unidentified.jar"
Copy-Item -LiteralPath $Capsule -Destination $Vendored -Force

& $Git -C $ExternalRepo check-ignore -q "libs/vendored-unidentified.jar"
if ($LASTEXITCODE -ne 0) {
    throw "External vendored dependency path is not gitignored; refusing private capsule injection."
}

$Gradlew = Join-Path $ExternalRepo "gradlew.bat"
Require-File $Gradlew
Unblock-File -LiteralPath $Gradlew -ErrorAction SilentlyContinue

Invoke-Checked "COMPILE EXTERNAL READABLE TREE" {
    & $Gradlew --no-daemon clean classes
}

$ExternalClasses = Join-Path $ExternalRepo "build\classes\java\main"
if (-not (Test-Path -LiteralPath $ExternalClasses -PathType Container)) {
    throw "External compiled class tree is missing: $ExternalClasses"
}
$ExternalRsRoot = Join-Path $ExternalClasses "rs"
if (-not (Test-Path -LiteralPath $ExternalRsRoot -PathType Container)) {
    throw "External compile produced no rs class root."
}
$ExternalRsClasses = @(
    Get-ChildItem -LiteralPath $ExternalRsRoot -Recurse -File -Filter "*.class"
)
if ($ExternalRsClasses.Count -lt 1) {
    throw "External compile produced no rs/** class files."
}

$OracleArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.external_source_oracle_cli",
    "--external-repo",
    $ExternalRepo,
    "--external-classes",
    $ExternalClasses,
    "--external-revision",
    $ExternalRevision,
    "--exact-v308-jar",
    $ClientJar,
    "--json-out",
    $OracleReport
)
Invoke-Checked "CORRELATE EXTERNAL TREE AGAINST EXACT v308" {
    & $Py @OracleArgs
}

Require-File $OracleReport

$DirtyAfter = @(
    & $Git -C $ExternalRepo status --porcelain --untracked-files=all
)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to inspect post-build external worktree."
}
if ($DirtyAfter.Count -ne 0) {
    Write-Host ""
    Write-Host "External worktree changes after build:" -ForegroundColor Yellow
    $DirtyAfter | ForEach-Object { Write-Host $_ }
    throw "External build mutated tracked/unignored source state."
}

$Oracle = Get-Content -LiteralPath $OracleReport -Raw | ConvertFrom-Json
if ($Oracle.research_only -ne $true) {
    throw "Oracle report lost research-only boundary."
}
if ($Oracle.source_authority -ne $false) {
    throw "External corpus was incorrectly marked as source authority."
}
if ($Oracle.semantic_authority -ne $false) {
    throw "External corpus was incorrectly marked as semantic authority."
}
if ($Oracle.source_mutation_allowed -ne $false) {
    throw "External corpus was incorrectly allowed to mutate source."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " EXTERNAL v308 ORACLE COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "AUTHORITY_V308_SHA256=$ClientSha"
Write-Host "EXTERNAL_REVISION=$ExternalHead"
Write-Host "EXTERNAL_COMPILED_RS_CLASSES=$($ExternalRsClasses.Count)"
Write-Host "ORACLE_ID=$($Oracle.oracle_id)"
Write-Host "CORPUS_ID=$($Oracle.corpus_id)"
Write-Host "MATCHED=$($Oracle.summary.matched)"
Write-Host "STRONG=$($Oracle.summary.strong_candidates)"
Write-Host "INFERRED=$($Oracle.summary.inferred_candidates)"
Write-Host "AMBIGUOUS=$($Oracle.summary.ambiguous)"
Write-Host "UNMATCHED_EXTERNAL=$($Oracle.summary.unmatched_old)"
Write-Host "UNMATCHED_EXACT_V308=$($Oracle.summary.unmatched_new)"
Write-Host "PROJECT_BINARY_FALLBACK=0"
Write-Host "REPORT=$OracleReport"
