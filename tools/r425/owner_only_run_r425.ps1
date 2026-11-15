# R425 owner-only convenience entrypoint. Never auto-runs or deploys a JAR.
# Requires -RunOwnerPrivateAcceptance. Only the isolated R421 TEMP source
# is accepted; the Python runner independently pins private source/class SHA.
[CmdletBinding()]
param(
    [switch]$RunOwnerPrivateAcceptance,
    [string]$PythonExe = 'C:\Users\Felix\AppData\Local\Programs\Python\Python312\python.exe',
    [string]$JdkHome = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $RunOwnerPrivateAcceptance) {
    throw 'R425_REFUSED: pass -RunOwnerPrivateAcceptance for isolated owner-TEMP tests; never use on live client.'
}
if ([string]::IsNullOrWhiteSpace($env:TEMP)) {
    throw 'R425_REFUSED: TEMP is not available.'
}

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$isolatedParent = Join-Path $env:TEMP 'SpawnPK-R386-Isolated-Acceptance\R421-Private-NoFollow-Cache-Directory-Preflight'
$sourceCandidate = Join-Path $isolatedParent 'Source-Candidate-R421'
$sourceRoot = Join-Path $sourceCandidate 'source'
$classesRoot = Join-Path $isolatedParent 'R421-Compiled-Classes'
$dependencies = Join-Path $sourceCandidate 'dependencies'
$depA = Join-Path $dependencies 'R239_filtered.jar'
$depB = Join-Path $dependencies 'R218.jar'

$runner = Join-Path $repositoryRoot 'tools\r425\compile_and_accept_private_overlay.py'
$helper = Join-Path $repositoryRoot 'tests\fixtures\r424\LootLegacyCleanupR424.java'
$acceptance = Join-Path $repositoryRoot 'tests\fixtures\r425\R425ActualPrivateOverlayAcceptance.java'
$javac = Join-Path $JdkHome 'bin\javac.exe'
$java = Join-Path $JdkHome 'bin\java.exe'

foreach ($path in @($PythonExe, $javac, $java, $runner, $helper, $acceptance, $depA, $depB)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "R425_REFUSED: required owner-local test input not found: $path"
    }
}
foreach ($path in @($sourceRoot, $classesRoot)) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "R425_REFUSED: isolated R421 source/classes directory not found: $path"
    }
}

# Hashes are collected as exact file identities in this invocation; the
# compiled class delta and pinned R421 store SHA remain independent checks.
$depAHash = (Get-FileHash -LiteralPath $depA -Algorithm SHA256).Hash.ToLowerInvariant()
$depBHash = (Get-FileHash -LiteralPath $depB -Algorithm SHA256).Hash.ToLowerInvariant()
$destination = Join-Path $env:TEMP ('R424-Private-Candidate-R425-' + [guid]::NewGuid().ToString('N'))

Write-Output 'R425_OWNER_TEMP_ONLY - no client launch, no live loot-history access, no JAR deployment'
Write-Output ('R425_PINNED_DEPENDENCY_A_SHA256=' + $depAHash)
Write-Output ('R425_PINNED_DEPENDENCY_B_SHA256=' + $depBHash)
Write-Output ('R425_FRESH_ISOLATED_DESTINATION=' + $destination)

$arguments = @(
    $runner,
    '--prior-source-root', $sourceRoot,
    '--prior-classes-root', $classesRoot,
    '--public-helper-source', $helper,
    '--public-acceptance-source', $acceptance,
    '--dependency-a', $depA,
    '--dependency-b', $depB,
    '--dependency-a-sha256', $depAHash,
    '--dependency-b-sha256', $depBHash,
    '--javac', $javac,
    '--java', $java,
    '--fresh-temp-destination', $destination
)
& $PythonExe @arguments
$code = $LASTEXITCODE
if ($code -ne 0) {
    throw "R425_PRIVATE_ACCEPTANCE_NOT_APPROVED (exit=$code). Isolated receipts, if any, are under $destination. Do not merge or release."
}
$receipt = Join-Path $destination 'R425-Final-Private-Acceptance-Receipt.json'
if (-not (Test-Path -LiteralPath $receipt -PathType Leaf)) {
    throw 'R425_PRIVATE_ACCEPTANCE_NOT_APPROVED: final receipt absent.'
}
Write-Output ('R425_PRIVATE_ISOLATED_ACCEPTANCE_RECEIPT=' + $receipt)
Write-Output 'R425_RELEASE_GATE_REMAINS_CLOSED'
