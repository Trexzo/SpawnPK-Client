[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$R265Zip,
  [string]$JavaHome = ''
)
$ErrorActionPreference = 'Stop'
$ExpectedZip = '9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'
$ExpectedJar = 'dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503'
if (-not (Test-Path -LiteralPath $R265Zip -PathType Leaf)) { throw "R265 ZIP not found: $R265Zip" }
$ActualZip = (Get-FileHash -LiteralPath $R265Zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualZip -ne $ExpectedZip) { throw "R265 ZIP SHA256 mismatch: $ActualZip" }
if ($JavaHome) {
  $Javac = Join-Path $JavaHome 'bin\javac.exe'
  $Java = Join-Path $JavaHome 'bin\java.exe'
} else { $Javac = 'javac.exe'; $Java = 'java.exe' }
$Src = Join-Path $PSScriptRoot 'R266RealClientPlayerSyncRegression.java'
if (-not (Test-Path -LiteralPath $Src -PathType Leaf)) { throw 'R266 test source missing' }
$Workspace = Join-Path ([IO.Path]::GetTempPath()) ('spawnpk-r266-' + [Guid]::NewGuid().ToString('N'))
try {
  New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
  $Extract = Join-Path $Workspace 'r265'
  Expand-Archive -LiteralPath $R265Zip -DestinationPath $Extract -Force
  $Jar = Join-Path $Extract 'evidence\R265_UNIFIED_SOURCE_BUILT.jar'
  $ActualJar = (Get-FileHash -LiteralPath $Jar -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($ActualJar -ne $ExpectedJar) { throw "R265 JAR SHA256 mismatch: $ActualJar" }
  $Runtime = Join-Path $Extract 'dependencies\R239_EXACT_RUNTIME_LIB.jar'
  $Compile = Join-Path $Extract 'dependencies\R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar'
  $Classpath = "$Jar;$Runtime;$Compile"
  $Classes = Join-Path $Workspace 'classes'
  New-Item -ItemType Directory -Force -Path $Classes | Out-Null
  & $Javac '--release' '11' '-encoding' 'UTF-8' '-cp' $Classpath '-d' $Classes $Src
  if ($LASTEXITCODE -ne 0) { throw "R266 javac exited with $LASTEXITCODE" }
  & $Java '-Djava.awt.headless=false' '-Xmx700m' '-cp' "$Classes;$Classpath" 'R266RealClientPlayerSyncRegression'
  if ($LASTEXITCODE -ne 0) { throw "R266 regression exited with $LASTEXITCODE" }
  Write-Host 'R266_READ_ONLY_FULL_CLIENT_TEST_PASS' -ForegroundColor Green
} finally {
  if (Test-Path -LiteralPath $Workspace) { Remove-Item -LiteralPath $Workspace -Recurse -Force }
}
