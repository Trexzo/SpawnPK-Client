# Offline owner-device verification only; no production client, updater, or caches.
# Invoke from the repository root with the private build kit already on this PC.
param(
    [Parameter(Mandatory=$true)][string]$PrivateKit,
    [Parameter(Mandatory=$true)][string]$Java21Javac,
    [Parameter(Mandatory=$true)][string]$NewOutputDir,
    [Parameter(Mandatory=$false)][string]$ReferenceJar
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PrivateKit -PathType Leaf)) { throw 'PRIVATE_KIT_MISSING' }
if (-not (Test-Path -LiteralPath $Java21Javac -PathType Leaf)) { throw 'JDK21_JAVAC_MISSING' }
if (Test-Path -LiteralPath $NewOutputDir) { throw 'OUTPUT_EXISTS_REFUSED' }
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$runner = Join-Path $root 'tools/r383/verify_private_full_build.py'
$checker = Join-Path $root 'tools/r385/compare_local_build_jars.py'
$pythonCmd = Get-Command python -ErrorAction Stop
& $pythonCmd.Source $runner --private-bundle $PrivateKit --javac $Java21Javac --out-dir $NewOutputDir
if ($LASTEXITCODE -ne 0) { throw "PRIVATE_FULL_BUILD_FAILED exit=$LASTEXITCODE" }
if (-not [string]::IsNullOrWhiteSpace($ReferenceJar)) {
    if (-not (Test-Path -LiteralPath $ReferenceJar -PathType Leaf)) { throw 'REFERENCE_JAR_MISSING' }
    $builtJar = Join-Path $NewOutputDir 'R383-Source-Built-From-Private-Kit.jar'
    $report = Join-Path $NewOutputDir 'R385-Class-Comparison.json'
    & $pythonCmd.Source $checker --reference $ReferenceJar --candidate $builtJar --output $report
    if ($LASTEXITCODE -ne 0) { throw "BUILD_COMPARISON_NOT_EXACT exit=$LASTEXITCODE" }
}
Write-Output 'R385_OFFLINE_WINDOWS_FULL_BUILD_RUNNER_PASS — verify report platform=windows before counting native Windows acceptance.'
