# R425 owner-only convenience entrypoint. Never auto-runs or deploys a JAR.
# Requires -RunOwnerPrivateAcceptance. Only the isolated R421 TEMP source
# is accepted; the Python runner independently pins private source/class SHA.
[CmdletBinding()]
param(
    [switch]$RunOwnerPrivateAcceptance,
    [switch]$AuditOnly,
    [string]$ApprovedDependencyASha256,
    [string]$ApprovedDependencyBSha256,
    [string]$PythonExe = 'C:\Users\Felix\AppData\Local\Programs\Python\Python312\python.exe',
    [string]$JdkHome = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $RunOwnerPrivateAcceptance) {
    if (-not $AuditOnly) {
        throw 'R440_REFUSED: select -AuditOnly (read only) or -RunOwnerPrivateAcceptance (opt-in TEMP compile).'
    }
}
if ($RunOwnerPrivateAcceptance -and $AuditOnly) {
    throw 'R440_REFUSED: -AuditOnly and -RunOwnerPrivateAcceptance are mutually exclusive.'
}
foreach ($approved in @($ApprovedDependencyASha256, $ApprovedDependencyBSha256)) {
    if ([string]::IsNullOrWhiteSpace($approved) -or
        $approved -cnotmatch '^[0-9a-f]{64}
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
$r432Gate = Join-Path $repositoryRoot 'tools\r432\chain_private_process_acceptance.py'
$r440Audit = Join-Path $repositoryRoot 'tools\r440\read_only_private_acceptance_preflight.py'
$helper = Join-Path $repositoryRoot 'tests\fixtures\r424\LootLegacyCleanupR424.java'
$acceptance = Join-Path $repositoryRoot 'tests\fixtures\r425\R425ActualPrivateOverlayAcceptance.java'
$javac = Join-Path $JdkHome 'bin\javac.exe'
$java = Join-Path $JdkHome 'bin\java.exe'

foreach ($path in @($PythonExe, $javac, $java, $runner, $r432Gate, $r440Audit, $helper, $acceptance, $depA, $depB)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "R425_REFUSED: required owner-local test input not found: $path"
    }
}
foreach ($path in @($sourceRoot, $classesRoot)) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "R425_REFUSED: isolated R421 source/classes directory not found: $path"
    }
}

# Observed hashes are diagnostic ONLY. They cannot approve themselves.
# An independently approved baseline must be supplied by the owner and
# compared against the bytes before any staging or compile is allowed.
$observedAHash = (Get-FileHash -LiteralPath $depA -Algorithm SHA256).Hash.ToLowerInvariant()
$observedBHash = (Get-FileHash -LiteralPath $depB -Algorithm SHA256).Hash.ToLowerInvariant()
if ($observedAHash -cne $ApprovedDependencyASha256 -or
    $observedBHash -cne $ApprovedDependencyBSha256) {
    throw 'R440_REFUSED: dependency JAR hash does not match independently approved SHA256. No staging or compile performed.'
}
$depAHash = $ApprovedDependencyASha256
$depBHash = $ApprovedDependencyBSha256

# Mandatory read-only gate: source/class SHA pins, full inventory counts,
# patch shape, JDK21, safe owner-isolated TEMP location, dependency identity.
$preflightArgs = @(
    $r440Audit,
    '--prior-source-root', $sourceRoot,
    '--prior-classes-root', $classesRoot,
    '--public-helper-source', $helper,
    '--public-acceptance-source', $acceptance,
    '--dependency-a', $depA,
    '--dependency-b', $depB,
    '--dependency-a-sha256', $depAHash,
    '--dependency-b-sha256', $depBHash,
    '--javac', $javac,
    '--java', $java
)
& $PythonExe -B @preflightArgs
$preflightCode = $LASTEXITCODE
if ($preflightCode -ne 0) {
    throw "R440_PRIVATE_PREFLIGHT_REFUSED (exit=$preflightCode). No candidate, compile, history write or release authorized."
}
Write-Output 'R440_READ_ONLY_OWNER_PREFLIGHT_PASS - release gate remains closed'
if ($AuditOnly) {
    Write-Output 'R440_AUDIT_ONLY_COMPLETE - no candidate created or Java compilation attempted'
    return
}
$destination = Join-Path $env:TEMP ('R424-Private-Candidate-R425-' + [guid]::NewGuid().ToString('N'))
Write-Output 'R425_OWNER_TEMP_ONLY - no client launch, no live loot-history access, no JAR deployment'
Write-Output ('R425_APPROVED_DEPENDENCY_A_SHA256=' + $depAHash)
Write-Output ('R425_APPROVED_DEPENDENCY_B_SHA256=' + $depBHash)
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

# R432 is a mandatory second gate. It never modifies real history or runs
# the original game. A completed R425 compile alone is NOT final acceptance.
$secondArgs = @(
    $r432Gate,
    '--candidate-temp-root', $destination,
    '--prior-source-root', $sourceRoot,
    '--prior-classes-root', $classesRoot,
    '--dependency-a', $depA,
    '--dependency-b', $depB,
    '--dependency-a-sha256', $depAHash,
    '--dependency-b-sha256', $depBHash,
    '--javac', $javac,
    '--java', $java
)
& $PythonExe @secondArgs
$processCode = $LASTEXITCODE
if ($processCode -ne 0) {
    throw "R432_CROSS_PROCESS_GATE_REFUSED (exit=$processCode). Never install or merge; see $destination"
}
$processReceipt = Join-Path $destination 'R432-Final-Private-CrossProcess-Receipt.json'
if (-not (Test-Path -LiteralPath $processReceipt -PathType Leaf)) {
    throw 'R432_REFUSED: final cross-process receipt missing.'
}
Write-Output ('R432_PRIVATE_CROSS_PROCESS_ACCEPTANCE_RECEIPT=' + $processReceipt)
# Preserve the R425 release-closed receipt for older safety tooling,
# in addition to the stricter R432 process gate.
Write-Output 'R425_RELEASE_GATE_REMAINS_CLOSED'
Write-Output 'R432_RELEASE_GATE_REMAINS_CLOSED'
) {
        throw 'R440_REFUSED: provide two independently approved lowercase SHA256 values via -ApprovedDependencyASha256 and -ApprovedDependencyBSha256. Current file hashes are NOT independent approval.'
    }
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
$r432Gate = Join-Path $repositoryRoot 'tools\r432\chain_private_process_acceptance.py'
$helper = Join-Path $repositoryRoot 'tests\fixtures\r424\LootLegacyCleanupR424.java'
$acceptance = Join-Path $repositoryRoot 'tests\fixtures\r425\R425ActualPrivateOverlayAcceptance.java'
$javac = Join-Path $JdkHome 'bin\javac.exe'
$java = Join-Path $JdkHome 'bin\java.exe'

foreach ($path in @($PythonExe, $javac, $java, $runner, $r432Gate, $helper, $acceptance, $depA, $depB)) {
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

# R432 is a mandatory second gate. It never modifies real history or runs
# the original game. A completed R425 compile alone is NOT final acceptance.
$secondArgs = @(
    $r432Gate,
    '--candidate-temp-root', $destination,
    '--prior-source-root', $sourceRoot,
    '--prior-classes-root', $classesRoot,
    '--dependency-a', $depA,
    '--dependency-b', $depB,
    '--dependency-a-sha256', $depAHash,
    '--dependency-b-sha256', $depBHash,
    '--javac', $javac,
    '--java', $java
)
& $PythonExe @secondArgs
$processCode = $LASTEXITCODE
if ($processCode -ne 0) {
    throw "R432_CROSS_PROCESS_GATE_REFUSED (exit=$processCode). Never install or merge; see $destination"
}
$processReceipt = Join-Path $destination 'R432-Final-Private-CrossProcess-Receipt.json'
if (-not (Test-Path -LiteralPath $processReceipt -PathType Leaf)) {
    throw 'R432_REFUSED: final cross-process receipt missing.'
}
Write-Output ('R432_PRIVATE_CROSS_PROCESS_ACCEPTANCE_RECEIPT=' + $processReceipt)
# Preserve the R425 release-closed receipt for older safety tooling,
# in addition to the stricter R432 process gate.
Write-Output 'R425_RELEASE_GATE_REMAINS_CLOSED'
Write-Output 'R432_RELEASE_GATE_REMAINS_CLOSED'
