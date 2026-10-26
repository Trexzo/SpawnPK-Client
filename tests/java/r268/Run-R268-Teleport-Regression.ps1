# Read-only, exact-input offline R268 opcode-81 validation. Not yet executed on Windows.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$R265Zip)
$ErrorActionPreference='Stop'
$Expected='9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'
$ExpectedJar='dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503'
$R265Zip=(Resolve-Path -LiteralPath $R265Zip).Path
if((Get-FileHash -LiteralPath $R265Zip -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected){throw 'R265 private ZIP SHA256 mismatch'}
$Work=Join-Path ([IO.Path]::GetTempPath()) ('SpawnPK-R268-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Work | Out-Null
try {
  Expand-Archive -LiteralPath $R265Zip -DestinationPath $Work
  $Jar=Join-Path $Work 'evidence\R265_UNIFIED_SOURCE_BUILT.jar'
  if((Get-FileHash -LiteralPath $Jar -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedJar){throw 'R265 compiled JAR SHA256 mismatch'}
  $Lib1=Join-Path $Work 'dependencies\R239_EXACT_RUNTIME_LIB.jar'
  $Lib2=Join-Path $Work 'dependencies\R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar'
  foreach($Path in @($Lib1,$Lib2)){if(-not(Test-Path -LiteralPath $Path)){throw "Missing JAR $Path"}}
  $CP=[string]::Join([IO.Path]::PathSeparator,@($Jar,$Lib1,$Lib2))
  $Classes=Join-Path $Work 'classes';New-Item -ItemType Directory -Path $Classes | Out-Null
  $Source=Join-Path $PSScriptRoot 'R268TeleportAppearanceRegression.java'
  & javac.exe --release 11 -encoding UTF-8 -cp $CP -d $Classes $Source
  if($LASTEXITCODE -ne 0){throw "R268 test javac failed: $LASTEXITCODE"}
  $RuntimeCP=[string]::Join([IO.Path]::PathSeparator,@($Classes,$Jar,$Lib1,$Lib2))
  & java.exe -Djava.awt.headless=false -cp $RuntimeCP R268TeleportAppearanceRegression
  if($LASTEXITCODE -ne 0){throw "R268 regression failed: $LASTEXITCODE"}
  Write-Host 'R268_LOCAL_TELEPORT_PROTOCOL_PASS' -ForegroundColor Green
} finally {
  Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
}
