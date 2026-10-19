[CmdletBinding()]
param(
 [string]$InputDir = (Join-Path $env:USERPROFILE 'Downloads'),
 [string]$Package = (Join-Path $PSScriptRoot 'SpawnPK_v309_R292_WINDOWS_READINESS_GATE_SOURCE_ONLY.zip'),
 [string]$Output = (Join-Path ([Environment]::GetFolderPath('Desktop')) ('SpawnPK-R292-Private-Acceptance-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))),
 [switch]$RunNativeGui
)
$ErrorActionPreference = 'Stop'
$Expected = '54E45BA2869F003B5377C8593172A5A90C3E7DFC73BD9ACA12029F8D319D72FB'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'R292_REFUSE_NON_WINDOWS' }
if (!(Test-Path -LiteralPath $InputDir -PathType Container)) { throw 'R292_INPUT_DIR_MISSING' }
if (!(Test-Path -LiteralPath $Package -PathType Leaf)) { throw 'R292_SOURCE_BUNDLE_MISSING' }
if ((Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash -ne $Expected) { throw 'R292_SOURCE_BUNDLE_SHA256_MISMATCH' }
if (Test-Path -LiteralPath $Output) { throw 'R292_REFUSE_EXISTING_OUTPUT' }
$Python = Get-Command py.exe -ErrorAction SilentlyContinue
if ($Python) { $Executable = $Python.Source; $Prefix=@('-3') }
else {
 $Python = Get-Command python.exe -ErrorAction SilentlyContinue
 if (!$Python) { throw 'R292_PYTHON_MISSING' }
 $Executable=$Python.Source; $Prefix=@()
}
$Scratch=Join-Path $env:TEMP ('SpawnPK-R292-SourceOnly-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $Scratch) { throw 'R292_REFUSE_EXISTING_SCRATCH' }
try {
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Package).ProviderPath,$Scratch)
 $Gate=Join-Path $Scratch 'tools\windows\r292\R292-Owner-Readiness-Gate.py'
 if (!(Test-Path -LiteralPath $Gate -PathType Leaf)) { throw 'R292_SOURCE_GATE_MISSING' }
 $Arguments=@($Gate,'--input-dir',$InputDir,'--output',$Output)
 if ($RunNativeGui) { $Arguments+='--run-native-gui' }
 & $Executable @Prefix @Arguments
 if ($LASTEXITCODE -ne 0) { throw "R292_NOT_ADMITTED_OR_GUI_FAILED exit=$LASTEXITCODE" }
 if ($RunNativeGui) {
   Write-Host 'R292_OWNER_NATIVE_GUI_RUNNER_REPORTED_PASS; inspect private R286 acceptance receipt' -ForegroundColor Green
 } else {
   Write-Host 'R292_REAL_WINDOWS_PREREQUISITES_PASS; NO GAME LAUNCHED' -ForegroundColor Green
 }
} finally {
 if (Test-Path -LiteralPath $Scratch) { [System.IO.Directory]::Delete($Scratch,$true) }
}
