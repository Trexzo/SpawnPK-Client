# R425 owner-only convenience entrypoint. Never auto-runs or deploys a JAR.
# Requires -RunOwnerPrivateAcceptance. Only the isolated R421 TEMP source
# is accepted; the Python runner independently pins private source/class SHA.
[CmdletBinding()]
param(
    [switch]$RunOwnerPrivateAcceptance,
    [switch]$AuditOnly,
    [string]$ApprovedDependencyASha256,
    [string]$ApprovedDependencyBSha256,
    [string]$ApprovedSourceInventorySha256,
    [string]$ApprovedClassInventorySha256,
    [string]$ApprovedR421ManifestPath,
    [string]$ApprovedR421ManifestSha256,
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
# The four optional R440/R441 parameters are consistency cross-checks,
# not authorities. They must all derive from a separately SHA-approved R421
# reference manifest verified BEFORE any private source or JAR admission.
if ([string]::IsNullOrWhiteSpace($ApprovedR421ManifestPath) -or
    $ApprovedR421ManifestSha256 -cnotmatch '^[0-9a-f]{64}$') {
    throw 'R442_REFUSED: a prior R421 manifest path and independently approved lowercase manifest SHA256 are mandatory.'
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
$r440Audit = Join-Path $repositoryRoot 'tools\r440\read_only_private_acceptance_preflight.py'
$r442Verify = Join-Path $repositoryRoot 'tools\r442\verify_prior_r421_manifest.py'
$helper = Join-Path $repositoryRoot 'tests\fixtures\r424\LootLegacyCleanupR424.java'
$acceptance = Join-Path $repositoryRoot 'tests\fixtures\r425\R425ActualPrivateOverlayAcceptance.java'
$javac = Join-Path $JdkHome 'bin\javac.exe'
$java = Join-Path $JdkHome 'bin\java.exe'

foreach ($path in @($PythonExe, $javac, $java, $runner, $r432Gate, $r440Audit, $r442Verify, $helper, $acceptance, $depA, $depB, $ApprovedR421ManifestPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "R425_REFUSED: required owner-local test input not found: $path"
    }
}
foreach ($path in @($sourceRoot, $classesRoot)) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "R425_REFUSED: isolated R421 source/classes directory not found: $path"
    }
}

# Validate an independently reviewed historical R421 manifest. A freshly
# hashed current tree or manifest is NOT independent approval. The externally
# supplied SHA256 binds the entire prior per-file inventory byte-for-byte.
$referenceArgs = @(
    $r442Verify,
    '--manifest-path', $ApprovedR421ManifestPath,
    '--approved-manifest-sha256', $ApprovedR421ManifestSha256
)
$referenceOutput = & $PythonExe -B @referenceArgs
$referenceExit = $LASTEXITCODE
if ($referenceExit -ne 0 -or @($referenceOutput).Count -ne 1) {
    throw 'R442_REFERENCE_BASELINE_REFUSED: no validated prior R421 manifest; no compile authorized.'
}
try {
    $reference = ($referenceOutput | ConvertFrom-Json)
} catch {
    throw 'R442_REFERENCE_BASELINE_REFUSED: invalid reference receipt JSON.'
}
if ($reference.status -cne 'R442_PRIOR_R421_REFERENCE_BYTES_VERIFIED' -or
    $reference.approved_manifest_sha256 -cne $ApprovedR421ManifestSha256 -or
    $reference.baseline_java_sources -ne 1277 -or
    $reference.baseline_compiled_classes -ne 1394 -or
    $reference.release_authorized -ne $false -or
    $reference.reference_origin_independently_verified -ne $false) {
    throw 'R442_REFERENCE_BASELINE_REFUSED: inconsistent or unsafe manifest receipt.'
}

# Cross-check any legacy caller-supplied hashes against the verified reference.
# Empty legacy parameters are permitted; the verified reference alone fills
# all four pins. No hash is calculated from current private files to approve.
$approvedReferenceHashes = @{
    ApprovedDependencyASha256 = [string]$reference.approved_dependency_a_sha256
    ApprovedDependencyBSha256 = [string]$reference.approved_dependency_b_sha256
    ApprovedSourceInventorySha256 = [string]$reference.approved_source_inventory_sha256
    ApprovedClassInventorySha256 = [string]$reference.approved_class_inventory_sha256
}
foreach ($entry in $approvedReferenceHashes.GetEnumerator()) {
    if ($entry.Value -cnotmatch '^[0-9a-f]{64}$') {
        throw 'R442_REFERENCE_BASELINE_REFUSED: malformed manifest-derived SHA256.'
    }
    $callerValue = [string](Get-Variable -Name $entry.Key -ValueOnly)
    if (-not [string]::IsNullOrWhiteSpace($callerValue) -and
        $callerValue -cne $entry.Value) {
        throw 'R442_REFERENCE_BASELINE_REFUSED: caller-provided SHA disagrees with approved manifest.'
    }
    Set-Variable -Name $entry.Key -Value $entry.Value
}
Write-Output 'R442_R421_REFERENCE_MANIFEST_SHA_MATCHED - provenance requires independent owner review'

# Observed hashes do not approve themselves. They must match the
# independently reviewed, externally supplied known-good reference hashes.
$observedAHash = (Get-FileHash -LiteralPath $depA -Algorithm SHA256).Hash.ToLowerInvariant()
$observedBHash = (Get-FileHash -LiteralPath $depB -Algorithm SHA256).Hash.ToLowerInvariant()
if ($observedAHash -cne $ApprovedDependencyASha256 -or
    $observedBHash -cne $ApprovedDependencyBSha256) {
    throw 'R440_REFUSED: dependency JAR hash does not match supplied approved SHA256. No staging or compile performed.'
}
$depAHash = $ApprovedDependencyASha256
$depBHash = $ApprovedDependencyBSha256

# Always run the read-only gate before making any new candidate.
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
    '--approved-source-inventory-sha256', $ApprovedSourceInventorySha256,
    '--approved-class-inventory-sha256', $ApprovedClassInventorySha256,
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
    '--approved-source-inventory-sha256', $ApprovedSourceInventorySha256,
    '--approved-class-inventory-sha256', $ApprovedClassInventorySha256,
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
    '--approved-source-inventory-sha256', $ApprovedSourceInventorySha256,
    '--approved-class-inventory-sha256', $ApprovedClassInventorySha256,
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
