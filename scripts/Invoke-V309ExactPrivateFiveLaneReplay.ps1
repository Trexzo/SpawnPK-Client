[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$V308Jar,
    [Parameter(Mandatory = $true)] [string]$V309Jar,
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [string]$Python = 'python',
    [string]$ReportDir = (Join-Path $env:USERPROFILE 'Desktop\SpawnPK-v309-private-research')
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$Pinned308 = '854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6'
$Pinned309 = 'ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38'

function Require-ExactFile {
    param([string]$Path, [string]$Expected, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label does not exist"
    }
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    if ($Actual -ine $Expected) {
        throw "$Label exact SHA-256 mismatch"
    }
}

$Repo = (Resolve-Path -LiteralPath $Repo -ErrorAction Stop).ProviderPath
$Source = Join-Path $Repo 'src\spk_recovery\v309_exact_private_concordance_replay.py'
$FrontierPath = Join-Path $Repo 'research\v309-field-recovery\frontier.json'
$LineagePath = Join-Path $Repo 'research\v309-field-recovery\class-lineage.json'
$GlobalPath = Join-Path $Repo 'research\v309-field-recovery\global-field-usage.json'
foreach ($Item in @($Source, $FrontierPath, $LineagePath, $GlobalPath)) {
    if (-not (Test-Path -LiteralPath $Item -PathType Leaf)) {
        throw 'Required repository source or authority file is missing'
    }
}

# Reject accidental use of an outdated or repinned client pair.
$Frontier = Get-Content -LiteralPath $FrontierPath -Raw | ConvertFrom-Json
if ($Frontier.kind -ne 'v309_recovery_frontier' -or
    $Frontier.state -ne 'ACCEPTED_INCOMPLETE' -or
    $Frontier.build_id -ne 'v309' -or
    $Frontier.frontier.unresolved -ne 143 -or
    $Frontier.frontier.descriptor_identity_guard_rejected -ne 26 -or
    $Frontier.exact_clients.v308_sha256 -ine $Pinned308 -or
    $Frontier.exact_clients.v309_sha256 -ine $Pinned309) {
    throw 'Expected protected v309 143/26 frontier is missing or changed'
}
Require-ExactFile -Path $V308Jar -Expected $Pinned308 -Label 'Original v308 client'
Require-ExactFile -Path $V309Jar -Expected $Pinned309 -Label 'Original v309 client'
$ProtectedInputs = @($FrontierPath, $LineagePath, $GlobalPath)
$ProtectedSHA = @{}
foreach ($Item in $ProtectedInputs) {
    $ProtectedSHA[$Item] = (Get-FileHash -LiteralPath $Item -Algorithm SHA256).Hash
}

$Command = Get-Command $Python -ErrorAction Stop
& $Command.Source -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required' }

# The only artifact is an aggregate JSON outside the Git repository.
$RepoPrefix = [IO.Path]::GetFullPath($Repo).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
$OutRoot = [IO.Path]::GetFullPath($ReportDir)
if ($OutRoot.TrimEnd('\', '/') -ieq $Repo.TrimEnd('\', '/') -or
    $OutRoot.StartsWith($RepoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'ReportDir cannot be inside the recovery source repository'
}
if (-not (Test-Path -LiteralPath $OutRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $OutRoot -Force | Out-Null
}
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Output = Join-Path $OutRoot ("v309-five-lane-concordance-$Stamp.json")
if (Test-Path -LiteralPath $Output) { throw 'Output already exists: no overwrite' }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $Repo 'src'
    if ($OldPythonPath) {
        $env:PYTHONPATH += [IO.Path]::PathSeparator + $OldPythonPath
    }
    $ReplayArguments = @(
        '-m', 'spk_recovery.v309_exact_private_concordance_replay',
        '--v308-jar', $V308Jar,
        '--v309-jar', $V309Jar,
        '--frontier', $FrontierPath,
        '--class-lineage', $LineagePath,
        '--global-report', $GlobalPath,
        '--out', $Output
    )
    & $Command.Source @ReplayArguments
    $Exit = $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
if ($Exit -ne 0) { throw "Exact-private replay failed closed (exit $Exit)" }
Require-ExactFile -Path $V308Jar -Expected $Pinned308 -Label 'Original v308 client after replay'
Require-ExactFile -Path $V309Jar -Expected $Pinned309 -Label 'Original v309 client after replay'
foreach ($Item in $ProtectedInputs) {
    if ((Get-FileHash -LiteralPath $Item -Algorithm SHA256).Hash -ine $ProtectedSHA[$Item]) {
        throw 'Protected repository research input changed during replay'
    }
}
if (-not (Test-Path -LiteralPath $Output -PathType Leaf)) {
    throw 'Replay returned success without an aggregate output file'
}
$Result = Get-Content -LiteralPath $Output -Raw | ConvertFrom-Json
if ($Result.canonical -ne $false -or
    $Result.state -ne 'CONCORDANCE_ONLY_NO_CLASS_OR_FIELD_ACCEPTANCE' -or
    $Result.summary.canonical_unresolved_field_relationships -ne 143 -or
    $Result.summary.blocked_field_relationships -ne 26 -or
    $Result.summary.canonical_class_identities_accepted -ne 0 -or
    $Result.summary.canonical_field_identities_accepted -ne 0) {
    throw 'Replay output violates research-only 143/26 authority'
}
$OutputSHA = (Get-FileHash -LiteralPath $Output -Algorithm SHA256).Hash
Write-Host 'SPK_V309_RESEARCH_ONLY_SUCCESS' -ForegroundColor Green
Write-Host "REPORT=$Output"
Write-Host "REPORT_SHA256=$OutputSHA"
Write-Host 'CANONICAL_MAPPINGS_CHANGED=NO'
Write-Host 'ORIGINAL_JARS_MODIFIED=NO'
