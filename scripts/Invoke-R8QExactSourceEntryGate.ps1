[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [string]$Work = "C:\Users\Felix\Desktop\SpawnPK-R8N-Private",
    [string]$Jdk = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$Branch = "core/r8q-javac-source-entry-isolation"
$ExpectedPlan = "JCLASSPLAN_1D1CFBBE48CDC80F8E8C"
$ExpectedReadable = "e12e4f917ba2c48ea306e3b4d4cc19c58c5e23cd4f5c33f4ae339ea6fce53c99"
$ExpectedCapsule = "aaf38eb4fef38f30625746833c88e7461de7b2deeb79994a3169967f71ea1227"
$ExpectedCandidates = 8

$PrivatePlan = Join-Path $Work "r8o-private\r8p-class-recovery-plan-private.json"
$ReadableJar = Join-Path $Work "r4b-readable\readable-client.jar"
$Capsule = Join-Path $Work "r5d-clean\dependency-capsule.jar"
$Out = Join-Path $Work "r8o-private\r8q-source-entry-exact.json"
$Javac = Join-Path $Jdk "bin\javac.exe"

Write-Host ""
Write-Host "=== R8Q EXACT SOURCE-ENTRY GATE ===" -ForegroundColor Cyan

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

& git -C $Repo fetch origin $Branch
if ($LASTEXITCODE -ne 0) {
    throw "git fetch failed."
}

$RemoteHead = @(& git -C $Repo rev-parse "origin/$Branch")[0].Trim()
if ([string]::IsNullOrWhiteSpace($RemoteHead)) {
    throw "Could not resolve origin/$Branch."
}

& git -C $Repo checkout -B $Branch "origin/$Branch"
if ($LASTEXITCODE -ne 0) {
    throw "checkout failed."
}

$Head = @(& git -C $Repo rev-parse HEAD)[0].Trim()
if ($Head -ne $RemoteHead) {
    throw "HEAD/remote mismatch: head=$Head remote=$RemoteHead"
}

Write-Host "HEAD=$Head" -ForegroundColor Green

foreach ($Path in @($PrivatePlan, $ReadableJar, $Capsule, $Javac)) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required artifact: $Path"
    }
}

$ReadableSha = (Get-FileHash -LiteralPath $ReadableJar -Algorithm SHA256).Hash.ToLowerInvariant()
$CapsuleSha = (Get-FileHash -LiteralPath $Capsule -Algorithm SHA256).Hash.ToLowerInvariant()

if ($ReadableSha -ne $ExpectedReadable) {
    throw "Readable SHA mismatch: $ReadableSha"
}
if ($CapsuleSha -ne $ExpectedCapsule) {
    throw "Capsule SHA mismatch: $CapsuleSha"
}

Write-Host "READABLE_SHA256=$ReadableSha" -ForegroundColor Green
Write-Host "CAPSULE_SHA256=$CapsuleSha" -ForegroundColor Green

$env:JAVA_HOME = $Jdk
$env:PATH = "$Jdk\bin;$env:PATH"
$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Remove-Item -LiteralPath $Out -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== RUN ONE-COMMAND R8Q GATE ===" -ForegroundColor Cyan

$GateArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.r8q_source_entry_gate_cli",
    $PrivatePlan,
    $ReadableJar,
    $Capsule,
    "--javac-command",
    $Javac,
    "--release",
    "9",
    "--expected-plan-id",
    $ExpectedPlan,
    "--expected-readable-sha256",
    $ExpectedReadable,
    "--expected-capsule-sha256",
    $ExpectedCapsule,
    "--expected-candidates",
    "$ExpectedCandidates",
    "--out",
    $Out
)

& py @GateArgs
if ($LASTEXITCODE -ne 0) {
    throw "R8Q exact source-entry gate failed."
}

Write-Host ""
Write-Host "PUBLIC_AUDIT=$Out"
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " R8Q EXACT SOURCE-ENTRY GATE - PASS" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
