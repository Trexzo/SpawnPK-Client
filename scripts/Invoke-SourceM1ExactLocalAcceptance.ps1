[CmdletBinding()]
param(
    [string]$Repo = "C:\Users\Felix\Desktop\SpawnPK-Client",
    [Parameter(Mandatory = $true)]
    [string]$ClientJar,
    [Parameter(Mandatory = $true)]
    [string]$SourceIndex,
    [Parameter(Mandatory = $true)]
    [string]$ClassLineage,
    [Parameter(Mandatory = $true)]
    [string]$MemberLineage,
    [Parameter(Mandatory = $true)]
    [string]$MemberSafetyAcceptance,
    [Parameter(Mandatory = $true)]
    [string]$DecompilerJar,
    [string]$SourceRewriteAcceptance,
    [string]$Jdk = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot",
    [string]$OutDir = "$env:USERPROFILE\Desktop\SpawnPK-SourceM1-Exact"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$ExpectedV308 = "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
$ExpectedProcyon = "821da96012fc69244fa1ea298c90455ee4e021434bc796d3b9546ab24601b779"

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
function Get-JsonProjection {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [hashtable]$Fields,
        [hashtable]$OptionalFields = @{}
    )

    Require-File $Path

    $Arguments = @(
        "-3.13",
        "-m",
        "spk_recovery.json_projection_cli",
        $Path
    )

    foreach ($Name in @($Fields.Keys | Sort-Object)) {
        $Arguments += @(
            "--field",
            ($Name + "=" + [string]$Fields[$Name])
        )
    }

    foreach ($Name in @($OptionalFields.Keys | Sort-Object)) {
        $Arguments += @(
            "--optional-field",
            ($Name + "=" + [string]$OptionalFields[$Name])
        )
    }

    $Output = @(& py @Arguments)
    $Code = $LASTEXITCODE
    if ($Code -ne 0) {
        throw (
            "Case-safe JSON projection failed for " +
            $Path +
            " with exit=" +
            $Code
        )
    }

    $Raw = ($Output -join "`n").Trim()
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        throw "Case-safe JSON projection returned empty output: $Path"
    }

    try {
        # ConvertFrom-Json is safe here because Python emits only controlled
        # projection aliases. Raw authority keys never enter PowerShell.
        return ($Raw | ConvertFrom-Json)
    }
    catch {
        throw (
            "Case-safe JSON projection output was invalid for " +
            $Path +
            ": " +
            $_.Exception.Message
        )
    }
}

function Enable-CaseSensitiveWorkspace {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        $Existing = @(Get-ChildItem -LiteralPath $Path -Force)
        if ($Existing.Count -ne 0) {
            throw "Case-sensitive workspace must be empty before preparation: $Path"
        }
    } else {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }

    if ($env:OS -ne "Windows_NT") {
        Write-Host "CASE_SENSITIVE_WORKSPACE_NATIVE=$Path" -ForegroundColor Green
        return
    }

    $AdminScript = Join-Path (
        [System.IO.Path]::GetTempPath()
    ) (
        "SpawnPK-EnableCaseSensitive-" +
        [guid]::NewGuid().ToString("N") +
        ".ps1"
    )

    $AdminSource = @'
param(
    [Parameter(Mandatory = $true)]
    [string]$Target
)

$ErrorActionPreference = "Continue"

& fsutil.exe file setCaseSensitiveInfo "$Target" enable
$Code = $LASTEXITCODE
if ($Code -ne 0) {
    exit $Code
}

& fsutil.exe file queryCaseSensitiveInfo "$Target"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

exit 0
'@

    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText(
        $AdminScript,
        $AdminSource,
        $Utf8NoBom
    )

    $Process = $null
    try {
        Write-Host ""
        Write-Host (
            "Windows requires one UAC prompt to enable per-directory " +
            "case sensitivity for the Source M1 resolver workspace."
        ) -ForegroundColor Yellow

        $Process = Start-Process `
            -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
            -Verb RunAs `
            -Wait `
            -PassThru `
            -ArgumentList @(
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "`"$AdminScript`"",
                "-Target",
                "`"$Path`""
            )
    }
    catch {
        throw (
            "Could not launch elevated case-sensitivity preparation: " +
            $_.Exception.Message
        )
    }
    finally {
        Remove-Item `
            -LiteralPath $AdminScript `
            -Force `
            -ErrorAction SilentlyContinue
    }

    if ($null -eq $Process -or $Process.ExitCode -ne 0) {
        $Code = if ($null -eq $Process) { "not_started" } else { $Process.ExitCode }
        throw "Could not enable Windows directory case sensitivity. Exit=$Code"
    }

    Write-Host "CASE_SENSITIVE_WORKSPACE_PREPARED=$Path" -ForegroundColor Green
}


Write-Host ""
Write-Host "=== SOURCE M1 EXACT LOCAL ACCEPTANCE ===" -ForegroundColor Cyan

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

foreach ($Path in @(
    $ClientJar,
    $SourceIndex,
    $ClassLineage,
    $MemberLineage,
    $MemberSafetyAcceptance,
    $DecompilerJar
)) {
    Require-File $Path
}
if (-not [string]::IsNullOrWhiteSpace($SourceRewriteAcceptance)) {
    Require-File $SourceRewriteAcceptance
}

$Java = Join-Path $Jdk "bin\java.exe"
$Javac = Join-Path $Jdk "bin\javac.exe"
Require-File $Java
Require-File $Javac

$ClientSha = (Get-FileHash -LiteralPath $ClientJar -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ClientSha -ne $ExpectedV308) {
    throw "Exact v308 SHA mismatch: $ClientSha"
}

$DecompilerSha = (Get-FileHash -LiteralPath $DecompilerJar -Algorithm SHA256).Hash.ToLowerInvariant()
if ($DecompilerSha -ne $ExpectedProcyon) {
    throw "Exact Procyon 0.6.0 SHA mismatch: $DecompilerSha"
}

if (Test-Path -LiteralPath $OutDir) {
    $Existing = @(Get-ChildItem -LiteralPath $OutDir -Force)
    if ($Existing.Count -ne 0) {
        throw "Output directory must be empty: $OutDir"
    }
} else {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

# Prepare the empty top-level output root before any child directories are
# created. On Windows, newly created descendants inherit per-directory NTFS
# case sensitivity, covering both Procyon resolver staging and clean-javac
# release/rebuild staging with one UAC elevation.
Enable-CaseSensitiveWorkspace -Path $OutDir

$BootstrapReadableDir = Join-Path $OutDir "bootstrap-readable"
$CollisionDir = Join-Path $OutDir "collision-authority"
$CollisionWorkspace = Join-Path $OutDir "collision-source"
$ReleaseDir = Join-Path $OutDir "release"
$AuthorityDir = Join-Path $OutDir "authority"
$MilestoneDir = Join-Path $OutDir "milestone"
$BundleDir = Join-Path $MilestoneDir "publication"

New-Item -ItemType Directory -Path $CollisionDir | Out-Null
New-Item -ItemType Directory -Path $MilestoneDir | Out-Null

$env:JAVA_HOME = $Jdk
$env:PATH = "$Jdk\bin;$env:PATH"
$env:PYTHONPATH = Join-Path $Repo "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host "AUTHORITY_COMMIT=$Head" -ForegroundColor Green
Write-Host "V308_SHA256=$ClientSha" -ForegroundColor Green
Write-Host "PROCYON_SHA256=$DecompilerSha" -ForegroundColor Green

$ReadableArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.readable_build_cli",
    $ClientJar,
    $ClassLineage,
    $MemberLineage,
    $SourceIndex,
    "--build-id",
    "v308",
    "--source-safe-fallback",
    "--fallback-name-prefix",
    "Recovered_",
    "--member-safety-acceptance",
    $MemberSafetyAcceptance,
    "--out-dir",
    $BootstrapReadableDir
)
Invoke-PyChecked "REBUILD EXACT READABLE AUTHORITY" $ReadableArgs

$BootstrapReadableManifest = Join-Path $BootstrapReadableDir "readable-client-manifest.json"
$BootstrapReadableJar = Join-Path $BootstrapReadableDir "readable-client.jar"
Require-File $BootstrapReadableManifest
Require-File $BootstrapReadableJar

$ReadableDoc = Get-JsonProjection `
    -Path $BootstrapReadableManifest `
    -Fields @{
        status = "/status"
        verification_pass = "/verification_pass"
        source_sha256 = "/source_sha256"
    }
if ($ReadableDoc.status -ne "complete" -or $ReadableDoc.verification_pass -ne $true) {
    throw "Readable authority is not complete and independently verified."
}
if ([string]$ReadableDoc.source_sha256 -ne $ExpectedV308) {
    throw "Readable authority is not bound to exact v308."
}

$CollisionPlan = Join-Path $CollisionDir "namespace-collision-plan-private.json"
$CollisionReadableJar = Join-Path $CollisionDir "readable-client-collision-remapped.jar"
$CollisionTransform = Join-Path $CollisionDir "collision-transform.json"

$CollisionPlanArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.namespace_collision_plan_cli",
    $BootstrapReadableJar,
    "--include-identifiers",
    "--out",
    $CollisionPlan
)
Invoke-PyChecked "BUILD PRIVATE COLLISION PLAN" $CollisionPlanArgs

$CollisionPlanDoc = Get-JsonProjection `
    -Path $CollisionPlan `
    -Fields @{
        identifiers_included = "/identifiers_included"
        plan_eliminates_all_collisions = "/summary/plan_eliminates_all_collisions"
        blocker_remap_count = "/summary/blocker_remap_count"
        plan_id = "/plan_id"
    }
if ($CollisionPlanDoc.identifiers_included -ne $true) {
    throw "Collision plan is not the required identifier-bearing private authority."
}
if ($CollisionPlanDoc.plan_eliminates_all_collisions -ne $true) {
    throw "Collision plan does not eliminate all namespace collisions."
}
if ([int]$CollisionPlanDoc.blocker_remap_count -lt 1) {
    throw "Exact readable authority unexpectedly has no collision blockers to remap."
}

$CollisionApplyArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.collision_bytecode_remap_cli",
    $BootstrapReadableJar,
    $CollisionPlan,
    $CollisionReadableJar,
    "--report-out",
    $CollisionTransform
)
Invoke-PyChecked "APPLY COLLISION-SAFE READABLE REMAP" $CollisionApplyArgs

Require-File $CollisionReadableJar
Require-File $CollisionTransform

$CollisionTransformDoc = Get-JsonProjection `
    -Path $CollisionTransform `
    -Fields @{
        post_collision_edge_count = "/summary/post_collision_edge_count"
        plan_id = "/plan_id"
        transform_id = "/transform_id"
    }
if ([int]$CollisionTransformDoc.post_collision_edge_count -ne 0) {
    throw "Collision-remapped readable JAR still has namespace collision edges."
}
if ([string]$CollisionTransformDoc.plan_id -ne [string]$CollisionPlanDoc.plan_id) {
    throw "Collision transform is not bound to the generated private plan."
}

$WorkspaceArgs = @(
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
Invoke-PyChecked "BUILD COLLISION-DERIVED SOURCE WORKSPACE" $WorkspaceArgs

$RecoveredManifest = Join-Path $CollisionWorkspace "recovered-source-manifest.json"
$RecoveredSourceRoot = Join-Path $CollisionWorkspace "src"
$PrivateDiagnostic = Join-Path $ReleaseDir "javac-diagnostic-private.json"
Require-File $RecoveredManifest
if (-not (Test-Path -LiteralPath $RecoveredSourceRoot -PathType Container)) {
    throw "Collision-derived source root is missing."
}

$Recovered = Get-JsonProjection `
    -Path $RecoveredManifest `
    -Fields @{
        build_id = "/build_id"
        source_authority_sha256 = "/source_authority_sha256"
        collision_transform_id = "/collision_transform_id"
        collision_plan_id = "/collision_plan_id"
        collision_report_id = "/collision_report_id"
        base_readable_jar_sha256 = "/base_readable_jar_sha256"
        workspace_id = "/workspace_id"
        java_file_count = "/java_file_count"
    }
if ([string]$Recovered.build_id -ne "v308") {
    throw "Recovered workspace is not v308."
}
if ([string]$Recovered.source_authority_sha256 -ne $ExpectedV308) {
    throw "Recovered workspace source authority is not exact v308."
}
foreach ($Name in @(
    "collision_transform_id",
    "collision_plan_id",
    "collision_report_id",
    "base_readable_jar_sha256"
)) {
    $Value = $Recovered.$Name
    if ([string]::IsNullOrWhiteSpace([string]$Value)) {
        throw "Recovered workspace is missing collision authority: $Name"
    }
}
if ([string]$Recovered.collision_transform_id -ne [string]$CollisionTransformDoc.transform_id) {
    throw "Recovered workspace collision transform ID drifted."
}
if ([string]$Recovered.collision_plan_id -ne [string]$CollisionPlanDoc.plan_id) {
    throw "Recovered workspace collision plan ID drifted."
}

Write-Host "COLLISION_PLAN_ID=$($Recovered.collision_plan_id)" -ForegroundColor Green
Write-Host "COLLISION_TRANSFORM_ID=$($Recovered.collision_transform_id)" -ForegroundColor Green
Write-Host "RECOVERED_WORKSPACE_ID=$($Recovered.workspace_id)" -ForegroundColor Green
Write-Host "RECOVERED_JAVA_FILES=$($Recovered.java_file_count)" -ForegroundColor Green

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
    "v308",
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
Write-Host "=== CURRENT-MAIN RECOVERED RELEASE ===" -ForegroundColor Cyan
& py @ReleaseArgs
$ReleaseExit = $LASTEXITCODE
if ($ReleaseExit -ne 0) {
    $RunPath = Join-Path $ReleaseDir "release-run.json"
    if (Test-Path -LiteralPath $RunPath -PathType Leaf) {
        $Run = Get-JsonProjection `
    -Path $RunPath `
    -Fields @{
        terminal_stage = "/terminal_stage"
        status = "/status"
        run_id = "/run_id"
    }
        Write-Host ""
        Write-Host "SPK_SOURCE_M1_EXACT_LOCAL_BLOCKED" -ForegroundColor Yellow
        Write-Host "terminal_stage=$($Run.terminal_stage)"
        Write-Host "status=$($Run.status)"
        Write-Host "run_id=$($Run.run_id)"
        $CleanPath = Join-Path $ReleaseDir "rebuild\clean-rebuild.json"
        if (Test-Path -LiteralPath $CleanPath -PathType Leaf) {
            $CleanDoc = Get-JsonProjection `
                -Path $CleanPath `
                -Fields @{
                    rebuild_id = "/rebuild_id"
                    status = "/status"
                    generated_project_classes = "/project_classes/generated_count"
                    expected_project_classes = "/project_classes/expected_count"
                    project_binary_fallback_count = "/project_classes/binary_fallback_count"
                } `
                -OptionalFields @{
                    javac_total_errors = "/compiler/diagnostic_classification/summary/total_errors"
                    javac_affected_files = "/compiler/diagnostic_classification/summary/affected_files"
                    javac_cannot_find_symbol = "/compiler/diagnostic_classification/summary/cannot_find_symbol/count"
                    javac_frontier_id = "/compiler/diagnostic_classification/frontier_id"
                }
            Write-Host "clean_rebuild_id=$($CleanDoc.rebuild_id)"
            Write-Host "clean_status=$($CleanDoc.status)"
            Write-Host "generated_project_classes=$($CleanDoc.generated_project_classes)"
            Write-Host "expected_project_classes=$($CleanDoc.expected_project_classes)"
            Write-Host "project_binary_fallback_count=$($CleanDoc.project_binary_fallback_count)"
            if ($null -ne $CleanDoc.javac_frontier_id) {
                Write-Host "javac_total_errors=$($CleanDoc.javac_total_errors)"
                Write-Host "javac_affected_files=$($CleanDoc.javac_affected_files)"
                Write-Host "javac_cannot_find_symbol=$($CleanDoc.javac_cannot_find_symbol)"
                Write-Host "javac_frontier_id=$($CleanDoc.javac_frontier_id)"
            }
        }
    }
    if (Test-Path -LiteralPath $PrivateDiagnostic -PathType Leaf) {
        Write-Host "private_javac_diagnostic=$PrivateDiagnostic"
        Write-Host ""
        & py -3.13 -m spk_recovery.javac_frontier_summary_cli `
            $PrivateDiagnostic `
            --top 20
        $PrivateSummaryExit = $LASTEXITCODE
        if ($PrivateSummaryExit -ne 0) {
            Write-Host (
                "private_javac_summary_failed=" +
                $PrivateSummaryExit
            ) -ForegroundColor Yellow
        }
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

$VerifyArgs = @(
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
if (-not [string]::IsNullOrWhiteSpace($SourceRewriteAcceptance)) {
    $VerifyArgs += @("--source-rewrite-acceptance", $SourceRewriteAcceptance)
}
Invoke-PyChecked "VERIFY RECOVERY RELEASE" $VerifyArgs

$AuthorityBuildArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.source_authority_artifact_cli",
    "build",
    "--authority-commit",
    $Head,
    "--class-lineage",
    $ClassLineage,
    "--member-lineage",
    $MemberLineage,
    "--readable-manifest",
    $ReadableManifest,
    "--recovered-manifest",
    $UsedRecoveredManifest,
    "--clean-rebuild",
    $CleanRebuild,
    "--release-manifest",
    $ReleaseManifest,
    "--release-verification",
    $ReleaseVerification,
    "--source-root",
    $RecoveredSourceRoot,
    "--out-dir",
    $AuthorityDir
)
Invoke-PyChecked "BUILD SOURCE M1 AUTHORITY ARTIFACT" $AuthorityBuildArgs

$AuthorityVerification = Join-Path $AuthorityDir "SOURCE-AUTHORITY-VERIFICATION.json"
$AuthorityVerifyArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.source_authority_artifact_cli",
    "verify",
    "--artifact-dir",
    $AuthorityDir,
    "--expected-authority-commit",
    $Head,
    "--out",
    $AuthorityVerification
)
Invoke-PyChecked "VERIFY SOURCE M1 AUTHORITY ARTIFACT" $AuthorityVerifyArgs

$MilestoneManifest = Join-Path $MilestoneDir "SOURCE-MILESTONE.json"
$MilestoneVerification = Join-Path $MilestoneDir "SOURCE-MILESTONE-VERIFICATION.json"
$BundleVerification = Join-Path $MilestoneDir "SOURCE-BUNDLE-VERIFICATION.json"

$CommonMilestoneArgs = @(
    "--authority-commit",
    $Head,
    "--class-lineage",
    (Join-Path $AuthorityDir "class-lineage.json"),
    "--member-lineage",
    (Join-Path $AuthorityDir "member-lineage.json"),
    "--readable-manifest",
    (Join-Path $AuthorityDir "readable-client-manifest.json"),
    "--recovered-manifest",
    (Join-Path $AuthorityDir "recovered-source-manifest.json"),
    "--clean-rebuild",
    (Join-Path $AuthorityDir "clean-rebuild.json"),
    "--release-manifest",
    (Join-Path $AuthorityDir "recovery-release.json"),
    "--release-verification",
    (Join-Path $AuthorityDir "release-verification.json"),
    "--source-root",
    (Join-Path $AuthorityDir "src")
)

$BuildMilestoneArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.source_milestone_cli",
    "build"
)
$BuildMilestoneArgs += $CommonMilestoneArgs
$BuildMilestoneArgs += @("--out", $MilestoneManifest)
Invoke-PyChecked "BUILD SOURCE MILESTONE" $BuildMilestoneArgs

$VerifyMilestoneArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.source_milestone_cli",
    "verify"
)
$VerifyMilestoneArgs += $CommonMilestoneArgs
$VerifyMilestoneArgs += @(
    "--manifest",
    $MilestoneManifest,
    "--out",
    $MilestoneVerification
)
Invoke-PyChecked "VERIFY SOURCE MILESTONE" $VerifyMilestoneArgs

$BundleArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.source_milestone_cli",
    "bundle",
    "--manifest",
    $MilestoneManifest,
    "--source-root",
    (Join-Path $AuthorityDir "src"),
    "--out-dir",
    $BundleDir,
    "--provenance",
    ("recovery-release.json=" + (Join-Path $AuthorityDir "recovery-release.json")),
    "--provenance",
    ("release-verification.json=" + (Join-Path $AuthorityDir "release-verification.json")),
    "--provenance",
    ("SOURCE-AUTHORITY-VERIFICATION.json=" + $AuthorityVerification)
)
Invoke-PyChecked "BUILD SOURCE-ONLY PUBLICATION BUNDLE" $BundleArgs

$BundleVerifyArgs = @(
    "-3.13",
    "-m",
    "spk_recovery.source_milestone_cli",
    "verify-bundle",
    "--bundle-dir",
    $BundleDir,
    "--manifest",
    $MilestoneManifest,
    "--out",
    $BundleVerification
)
Invoke-PyChecked "VERIFY SOURCE-ONLY PUBLICATION BUNDLE" $BundleVerifyArgs

$Milestone = Get-JsonProjection `
    -Path $MilestoneManifest `
    -Fields @{
        publishable = "/publishable"
        milestone_id = "/milestone_id"
        source_tree_sha256 = "/source_tree/sha256"
    }
$MilestoneVerify = Get-JsonProjection `
    -Path $MilestoneVerification `
    -Fields @{
        verified = "/verified"
        publishable = "/publishable"
    }
$BundleVerify = Get-JsonProjection `
    -Path $BundleVerification `
    -Fields @{
        verified = "/verified"
    }

if ($Milestone.publishable -ne $true) {
    throw "Milestone publishable flag is false."
}
if ($MilestoneVerify.verified -ne $true -or $MilestoneVerify.publishable -ne $true) {
    throw "Milestone verification did not reproduce publishable=true."
}
if ($BundleVerify.verified -ne $true) {
    throw "Publication bundle verification failed."
}

Write-Host ""
Write-Host "MILESTONE_ID=$($Milestone.milestone_id)" -ForegroundColor Green
Write-Host "SOURCE_TREE_SHA256=$($Milestone.source_tree_sha256)" -ForegroundColor Green
Write-Host "PUBLICATION_BUNDLE=$BundleDir"
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " SOURCE M1 EXACT LOCAL ACCEPTANCE - PASS" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
