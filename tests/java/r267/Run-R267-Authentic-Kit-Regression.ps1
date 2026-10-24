# SHA-pinned, isolated R267 source-built-client + genuine asset-cache mesh regression.
# No client installation, no live server, no local SpawnPK cache writes.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$R265Zip,
    [Parameter(Mandatory=$true)][string]$AssetZip
)
$ErrorActionPreference = 'Stop'
$ExpectedR265 = '9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'
$ExpectedAssets = '8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565'
$ExpectedJar = 'dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503'
$R265Zip = (Resolve-Path -LiteralPath $R265Zip).Path
$AssetZip = (Resolve-Path -LiteralPath $AssetZip).Path
function Assert-Sha256([string]$Path, [string]$Expected) {
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -cne $Expected) { throw "SHA256 MISMATCH: $Path | Actual=$Actual" }
}
Assert-Sha256 $R265Zip $ExpectedR265
Assert-Sha256 $AssetZip $ExpectedAssets
$Work = Join-Path ([System.IO.Path]::GetTempPath()) ("SpawnPK-R267-" + [guid]::NewGuid().ToString('N'))
New-Item -Path $Work -ItemType Directory -Force | Out-Null
try {
    $Extracted = Join-Path $Work 'r265'
    Expand-Archive -LiteralPath $R265Zip -DestinationPath $Extracted
    $Jar = Join-Path $Extracted 'evidence\R265_UNIFIED_SOURCE_BUILT.jar'
    Assert-Sha256 $Jar $ExpectedJar
    $Lib1 = Join-Path $Extracted 'dependencies\R239_EXACT_RUNTIME_LIB.jar'
    $Lib2 = Join-Path $Extracted 'dependencies\R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar'
    foreach ($Path in @($Lib1, $Lib2)) {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing library: $Path" }
    }
    $Source = Join-Path $PSScriptRoot 'R267AuthenticKitRegression.java'
    $Classes = Join-Path $Work 'classes'
    New-Item -Path $Classes -ItemType Directory | Out-Null
    $CP = [string]::Join([IO.Path]::PathSeparator, @($Jar, $Lib1, $Lib2))
    & javac.exe --release 11 -encoding UTF-8 -cp $CP -d $Classes $Source
    if ($LASTEXITCODE -ne 0) { throw "R267 javac failed: $LASTEXITCODE" }
    $RuntimeCP = [string]::Join([IO.Path]::PathSeparator, @($Classes, $Jar, $Lib1, $Lib2))
    & java.exe -Djava.awt.headless=false -Xmx1000m -cp $RuntimeCP R267AuthenticKitRegression $AssetZip
    if ($LASTEXITCODE -ne 0) { throw "R267 regression failed: $LASTEXITCODE" }
    Write-Host 'R267_VERIFIED_REAL_CACHE_PLAYER_MESH_PASS' -ForegroundColor Green
} finally {
    Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
}
