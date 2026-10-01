[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [Parameter(Mandatory = $true)][string]$ClientJar,
    [Parameter(Mandatory = $true)][string]$SourceIndex,
    [Parameter(Mandatory = $true)][string]$ClassLineage,
    [Parameter(Mandatory = $true)][string]$MemberLineage,
    [Parameter(Mandatory = $true)][string]$MemberSafetyAcceptance,
    [Parameter(Mandatory = $true)][string]$DecompilerJar,
    [string]$Fixture = "",
    [string]$Jdk = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-Historical-v307-Release"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Require-File {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

function Invoke-PyChecked {
    param([string]$Label, [string[]]$Arguments)
    Write-Host ""
    Write-Host ("=== " + $Label + " ===") -ForegroundColor Cyan
    & py @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ($Label + " failed with exit=" + $LASTEXITCODE)
    }
}

function Get-JsonProjection {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][hashtable]$Fields,
        [hashtable]$OptionalFields = @{}
    )

    Require-File $Path
    $Arguments = @("-3.13", "-m", "spk_recovery.json_projection_cli", $Path)
    foreach ($Name in @($Fields.Keys | Sort-Object)) {
        $Arguments += @("--field", ($Name + "=" + [string]$Fields[$Name]))
    }
    foreach ($Name in @($OptionalFields.Keys | Sort-Object)) {
        $Arguments += @("--optional-field", ($Name + "=" + [string]$OptionalFields[$Name]))
    }

    $Output = @(& py @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Case-safe JSON projection failed: $Path"
    }
    $Raw = ($Output -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        throw "Case-safe JSON projection returned empty output: $Path"
    }
    return ($Raw | ConvertFrom-Json)
}

function Enable-CaseSensitiveWorkspace {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        $Existing = @(Get-ChildItem -LiteralPath $Path -Force)
        if ($Existing.Count -ne 0) {
            throw "Case-sensitive workspace must be empty: $Path"
        }
    } else {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }

    if ($env:OS -ne "Windows_NT") {
        return
    }

    $AdminScript = Join-Path ([System.IO.Path]::GetTempPath()) (
        "SpawnPK-Historical-CaseSensitive-" + [guid]::NewGuid().ToString("N") + ".ps1"
    )
    $AdminSource = @'
param([Parameter(Mandatory = $true)][string]$Target)
$ErrorActionPreference = "Continue"
& fsutil.exe file setCaseSensitiveInfo "$Target" enable
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& fsutil.exe file queryCaseSensitiveInfo "$Target"
exit $LASTEXITCODE
'@

    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($AdminScript, $AdminSource, $Utf8NoBom)

    try {
        $Args = @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            ('"' + $AdminScript + '"'),
            "-Target",
            ('"' + $Path + '"')
        )
        $Process = Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Verb RunAs -Wait -PassThru -ArgumentList $Args
    }
    finally {
        Remove-Item -LiteralPath $AdminScript -Force -ErrorAction SilentlyContinue
    }

    if ($null -eq $Process -or $Process.ExitCode -ne 0) {
        throw "Could not enable Windows directory case sensitivity."
    }
}

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Repo not found: $Repo"
}
if ([string]::IsNullOrWhiteSpace($Fixture)) {
    $Fixture = Join-Path $Repo "fixtures\v307-v308-source-regeneration.json"
}

foreach ($Path in @(
    $ClientJar,
    $SourceIndex,
    $ClassLineage,
    $MemberLineage,
    $MemberSafetyAcceptance,
    $DecompilerJar,
    $Fixture
)) {
    Require-File $Path
}

$Dirty = @(& git -C $Repo status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "git status failed" }
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "Repo is dirty."
}

& git -C $Repo fetch origin main
if ($LASTEXITCODE -ne 0) { throw "git fetch origin main failed" }

$Head = @(& git -C $Repo rev-parse HEAD)[0].Trim()
$RemoteMain = @(& git -C $Repo rev-parse origin/main)[0].Trim()
if ($Head -ne $RemoteMain) {
    throw "Local HEAD is not exact origin/main: head=$Head origin/main=$RemoteMain"
}

$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

$FixtureDoc = Get-JsonProjection -Path $Fixture -Fields @{
    kind = "/kind"
    fixture_id = "/fixture_id"
    old_build_id = "/old/build_id"
    old_client_sha256 = "/old/client_sha256"
    decompiler_engine = "/decompiler_authority/engine"
    decompiler_sha256 = "/decompiler_authority/sha256"
    decompiler_size_bytes = "/decompiler_authority/size_bytes"
    binary_backtest_id = "/binary_authority/backtest_id"
}

if ([string]$FixtureDoc.kind -ne "historical_source_regeneration_fixture") {
    throw "Unsupported historical fixture kind."
}
if ([string]$FixtureDoc.old_build_id -ne "v307") {
    throw "Historical fixture old build is not v307."
}
if ([string]$FixtureDoc.decompiler_engine -ne "procyon") {
    throw "Historical fixture decompiler engine is not Procyon."
}

$ExpectedClient = ([string]$FixtureDoc.old_client_sha256).ToLowerInvariant()
$ExpectedProcyon = ([string]$FixtureDoc.decompiler_sha256).ToLowerInvariant()

$ClientSha = (Get-FileHash -LiteralPath $ClientJar -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ClientSha -ne $ExpectedClient) {
    throw "Exact historical v307 SHA mismatch: $ClientSha"
}

$DecompilerSha = (Get-FileHash -LiteralPath $DecompilerJar -Algorithm SHA256).Hash.ToLowerInvariant()
if ($DecompilerSha -ne $ExpectedProcyon) {
    throw "Exact Procyon SHA mismatch: $DecompilerSha"
}
$DecompilerSize = (Get-Item -LiteralPath $DecompilerJar).Length
if ($DecompilerSize -ne [int64]$FixtureDoc.decompiler_size_bytes) {
    throw "Exact Procyon size mismatch: $DecompilerSize"
}

$IndexDoc = Get-JsonProjection -Path $SourceIndex -Fields @{ sha256 = "/sha256" }
if (([string]$IndexDoc.sha256).ToLowerInvariant() -ne $ExpectedClient) {
    throw "Historical source index is not bound to exact v307."
}

$Java = Join-Path $Jdk "bin\java.exe"
$Javac = Join-Path $Jdk "bin\javac.exe"
Require-File $Java
Require-File $Javac

if (Test-Path -LiteralPath $OutDir) {
    $Existing = @(Get-ChildItem -LiteralPath $OutDir -Force)
    if ($Existing.Count -ne 0) {
        throw "Output directory must be empty: $OutDir"
    }
} else {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

Enable-CaseSensitiveWorkspace -Path $OutDir

$env:JAVA_HOME = $Jdk
$env:PATH = "$Jdk\bin;$env:PATH"

$BootstrapReadableDir = Join-Path $OutDir "bootstrap-readable"
$CollisionDir = Join-Path $OutDir "collision-authority"
$CollisionWorkspace = Join-Path $OutDir "collision-source"
$ReleaseDir = Join-Path $OutDir "release"
New-Item -ItemType Directory -Path $CollisionDir | Out-Null

Write-Host ""
Write-Host "=== HISTORICAL SOURCE RELEASE AUTHORITY ===" -ForegroundColor Cyan
Write-Host "AUTHORITY_COMMIT=$Head" -ForegroundColor Green
Write-Host "FIXTURE_ID=$($FixtureDoc.fixture_id)" -ForegroundColor Green
Write-Host "BUILD_ID=v307" -ForegroundColor Green
Write-Host "V307_SHA256=$ClientSha" -ForegroundColor Green
Write-Host "PROCYON_SHA256=$DecompilerSha" -ForegroundColor Green
Write-Host "BINARY_BACKTEST_ID=$($FixtureDoc.binary_backtest_id)" -ForegroundColor Green

$ReadableArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.readable_build_cli",
    $ClientJar,
    $ClassLineage,
    $MemberLineage,
    $SourceIndex,
    "--build-id",
    "v307",
    "--source-safe-fallback",
    "--fallback-name-prefix",
    "Recovered_",
    "--member-safety-acceptance",
    $MemberSafetyAcceptance,
    "--out-dir",
    $BootstrapReadableDir
)
Invoke-PyChecked "REBUILD HISTORICAL READABLE AUTHORITY" $ReadableArgs

$BootstrapReadableManifest = Join-Path $BootstrapReadableDir "readable-client-manifest.json"
$BootstrapReadableJar = Join-Path $BootstrapReadableDir "readable-client.jar"
Require-File $BootstrapReadableManifest
Require-File $BootstrapReadableJar

$ReadableDoc = Get-JsonProjection -Path $BootstrapReadableManifest -Fields @{
    build_id = "/build_id"
    status = "/status"
    verification_pass = "/verification_pass"
    source_sha256 = "/source_sha256"
}
if ([string]$ReadableDoc.build_id -ne "v307") {
    throw "Readable authority build drifted from v307."
}
if ($ReadableDoc.status -ne "complete" -or $ReadableDoc.verification_pass -ne $true) {
    throw "Historical readable authority is not complete and verified."
}
if (([string]$ReadableDoc.source_sha256).ToLowerInvariant() -ne $ExpectedClient) {
    throw "Historical readable authority is not exact v307."
}

$CollisionPlan = Join-Path $CollisionDir "namespace-collision-plan-private.json"
$CollisionReadableJar = Join-Path $CollisionDir "readable-client-collision-remapped.jar"
$CollisionTransform = Join-Path $CollisionDir "collision-transform.json"

Invoke-PyChecked "BUILD HISTORICAL PRIVATE COLLISION PLAN" @(
    "-3.13",
    "-m",
    "spk_recovery.namespace_collision_plan_cli",
    $BootstrapReadableJar,
    "--include-identifiers",
    "--out",
    $CollisionPlan
)

$CollisionPlanDoc = Get-JsonProjection -Path $CollisionPlan -Fields @{
    identifiers_included = "/identifiers_included"
    plan_eliminates_all_collisions = "/summary/plan_eliminates_all_collisions"
    plan_id = "/plan_id"
}
if ($CollisionPlanDoc.identifiers_included -ne $true) {
    throw "Historical collision plan lacks private identifiers."
}
if ($CollisionPlanDoc.plan_eliminates_all_collisions -ne $true) {
    throw "Historical collision plan does not eliminate all collisions."
}

Invoke-PyChecked "APPLY HISTORICAL COLLISION REMAP" @(
    "-3.13",
    "-m",
    "spk_recovery.collision_bytecode_remap_cli",
    $BootstrapReadableJar,
    $CollisionPlan,
    $CollisionReadableJar,
    "--report-out",
    $CollisionTransform
)

$CollisionTransformDoc = Get-JsonProjection -Path $CollisionTransform -Fields @{
    transform_id = "/transform_id"
    plan_id = "/plan_id"
    post_collision_edge_count = "/summary/post_collision_edge_count"
}
if ([int]$CollisionTransformDoc.post_collision_edge_count -ne 0) {
    throw "Historical collision transform left collision edges."
}
if ([string]$CollisionTransformDoc.plan_id -ne [string]$CollisionPlanDoc.plan_id) {
    throw "Historical collision transform plan linkage mismatch."
}

Invoke-PyChecked "BUILD HISTORICAL COLLISION-DERIVED SOURCE" @(
    "-3.13",
    "-m",
    "spk_recovery.source_workspace_cli",
    $BootstrapReadableManifest,
    $CollisionReadableJar,
    $DecompilerJar,
    "--decompiler-sha256",
    $ExpectedProcyon,
    "--engine",
    "procyon",
    "--project-only",
    "--collision-transform-report",
    $CollisionTransform,
    "--out-dir",
    $CollisionWorkspace
)

$RecoveredManifest = Join-Path $CollisionWorkspace "recovered-source-manifest.json"
$RecoveredSourceRoot = Join-Path $CollisionWorkspace "src"
Require-File $RecoveredManifest
if (-not (Test-Path -LiteralPath $RecoveredSourceRoot -PathType Container)) {
    throw "Historical recovered source root is missing."
}

$RecoveredDoc = Get-JsonProjection -Path $RecoveredManifest -Fields @{
    build_id = "/build_id"
    source_authority_sha256 = "/source_authority_sha256"
    workspace_id = "/workspace_id"
    source_tree_sha256 = "/source_tree_sha256"
    java_file_count = "/java_file_count"
    collision_transform_id = "/collision_transform_id"
    collision_plan_id = "/collision_plan_id"
}
if ([string]$RecoveredDoc.build_id -ne "v307") {
    throw "Historical recovered workspace is not v307."
}
if (([string]$RecoveredDoc.source_authority_sha256).ToLowerInvariant() -ne $ExpectedClient) {
    throw "Historical recovered workspace is not bound to exact v307."
}
if ([string]$RecoveredDoc.collision_transform_id -ne [string]$CollisionTransformDoc.transform_id) {
    throw "Historical recovered workspace collision transform drifted."
}
if ([string]$RecoveredDoc.collision_plan_id -ne [string]$CollisionPlanDoc.plan_id) {
    throw "Historical recovered workspace collision plan drifted."
}

$PrivateDiagnostic = Join-Path $ReleaseDir "javac-diagnostic-private.json"
$ReleaseArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.release_workspace_orchestrator_cli",
    $ClientJar,
    $SourceIndex,
    $ClassLineage,
    $MemberLineage,
    $RecoveredManifest,
    $RecoveredSourceRoot,
    $CollisionPlan,
    "--build-id",
    "v307",
    "--source-safe-fallback",
    "--fallback-name-prefix",
    "Recovered_",
    "--member-safety-acceptance",
    $MemberSafetyAcceptance,
    "--source-prefix",
    "rs/",
    "--java-command",
    $Java,
    "--javac-command",
    $Javac,
    "--private-diagnostic-report-out",
    $PrivateDiagnostic,
    "--out-dir",
    $ReleaseDir
)

Write-Host ""
Write-Host "=== HISTORICAL RECOVERY RELEASE ===" -ForegroundColor Cyan
& py @ReleaseArgs
$ReleaseExit = $LASTEXITCODE

if ($ReleaseExit -ne 0) {
    $RunPath = Join-Path $ReleaseDir "release-run.json"
    if (Test-Path -LiteralPath $RunPath -PathType Leaf) {
        $RunDoc = Get-JsonProjection -Path $RunPath -Fields @{
            terminal_stage = "/terminal_stage"
            status = "/status"
            run_id = "/run_id"
            ready_for_release = "/ready_for_release"
        }
        Write-Host "HISTORICAL_RELEASE_BLOCKED" -ForegroundColor Yellow
        Write-Host "run_id=$($RunDoc.run_id)"
        Write-Host "terminal_stage=$($RunDoc.terminal_stage)"
        Write-Host "status=$($RunDoc.status)"
        Write-Host "ready_for_release=$($RunDoc.ready_for_release)"
    }

    if (Test-Path -LiteralPath $PrivateDiagnostic -PathType Leaf) {
        $SummaryArgs = @(
            "-3.13",
            "-m",
            "spk_recovery.javac_frontier_summary_cli",
            $PrivateDiagnostic,
            "--top",
            "20",
            "--focus-files",
            "3"
        )
        & py @SummaryArgs
    }
    exit 3
}

$ReadableManifest = Join-Path $ReleaseDir "readable\readable-client-manifest.json"
$ReadableJar = Join-Path $ReleaseDir "readable\readable-client.jar"
$UsedRecoveredManifest = Join-Path $ReleaseDir "source-authority\recovered-manifest.json"
$CleanRebuild = Join-Path $ReleaseDir "rebuild\clean-rebuild.json"
$RoundTrip = Join-Path $ReleaseDir "rebuild\roundtrip.json"
$ReleaseManifest = Join-Path $ReleaseDir "recovery-release.json"
$ReleaseVerification = Join-Path $ReleaseDir "release-verification.json"

foreach ($Path in @(
    $ReadableManifest,
    $ReadableJar,
    $UsedRecoveredManifest,
    $CleanRebuild,
    $RoundTrip,
    $ReleaseManifest
)) {
    Require-File $Path
}

Invoke-PyChecked "VERIFY HISTORICAL RECOVERY RELEASE" @(
    "-3.13",
    "-m",
    "spk_recovery.release_verify_cli",
    $ReleaseManifest,
    $SourceIndex,
    $ClassLineage,
    $MemberLineage,
    $ReadableManifest,
    $UsedRecoveredManifest,
    $CleanRebuild,
    $RoundTrip,
    "--authority-jar",
    $ClientJar,
    "--readable-jar",
    $ReadableJar,
    "--decompiler-jar",
    $DecompilerJar,
    "--source-root",
    $RecoveredSourceRoot,
    "--javac",
    $Javac,
    "--private-collision-plan",
    $CollisionPlan,
    "--out",
    $ReleaseVerification
)

$ReleaseDoc = Get-JsonProjection -Path $ReleaseManifest -Fields @{
    build_id = "/build_id"
    authority_sha256 = "/authority_sha256"
    release_id = "/release_id"
    ready_for_release = "/ready_for_release"
    final_source_tree_sha256 = "/final_source_tree_sha256"
}
$VerifyDoc = Get-JsonProjection -Path $ReleaseVerification -Fields @{
    release_id = "/release_id"
    verified = "/verified"
}

if ([string]$ReleaseDoc.build_id -ne "v307") {
    throw "Historical release manifest build drifted from v307."
}
if (([string]$ReleaseDoc.authority_sha256).ToLowerInvariant() -ne $ExpectedClient) {
    throw "Historical release manifest is not bound to exact v307."
}
if ($ReleaseDoc.ready_for_release -ne $true) {
    throw "Historical release manifest is not release-ready."
}
if ($VerifyDoc.verified -ne $true) {
    throw "Historical release verification failed."
}
if ([string]$VerifyDoc.release_id -ne [string]$ReleaseDoc.release_id) {
    throw "Historical release verification linkage mismatch."
}

Write-Host ""
Write-Host "HISTORICAL_RELEASE_ID=$($ReleaseDoc.release_id)" -ForegroundColor Green
Write-Host "HISTORICAL_SOURCE_TREE_SHA256=$($ReleaseDoc.final_source_tree_sha256)" -ForegroundColor Green
Write-Host "HISTORICAL_RECOVERED_WORKSPACE_ID=$($RecoveredDoc.workspace_id)" -ForegroundColor Green
Write-Host "HISTORICAL_JAVA_FILES=$($RecoveredDoc.java_file_count)" -ForegroundColor Green
Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host " HISTORICAL v307 RECOVERY RELEASE - PASS" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Historical recovery evidence only; no Source-M1 publication bundle is built."
