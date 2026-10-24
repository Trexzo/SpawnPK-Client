[CmdletBinding()]
param(
 [string]$InputDir = (Join-Path $env:USERPROFILE 'Downloads'),
 [string]$Package = (Join-Path $PSScriptRoot 'SpawnPK_v309_R297_R295_NATIVE_WINDOWS_SOURCE_ONLY.zip'),
 [string]$Output = (Join-Path ([Environment]::GetFolderPath('Desktop')) ('SpawnPK-R297-R295-GUI-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))),
 [switch]$RunNativeGui
)
$ErrorActionPreference = 'Stop'
$Expected = '661EA36616E8FFCD2612A1921257E4E70473030E42799C563BB57C7AEA5DEC93'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'R297_REFUSE_NON_WINDOWS' }
if (!(Test-Path -LiteralPath $InputDir -PathType Container)) { throw 'R297_OWNER_INPUT_DIR_MISSING' }
if (!(Test-Path -LiteralPath $Package -PathType Leaf)) { throw 'R297_SOURCE_BUNDLE_MISSING' }
if ((Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash -ne $Expected) { throw 'R297_SOURCE_BUNDLE_HASH_MISMATCH' }
if (Test-Path -LiteralPath $Output) { throw 'R297_REFUSE_EXISTING_OUTPUT' }
$Python = Get-Command py.exe -ErrorAction SilentlyContinue
if ($Python) { $Exe = $Python.Source; $Prefix = @('-3') }
else {
 $Python = Get-Command python.exe -ErrorAction SilentlyContinue
 if (!$Python) { throw 'R297_PYTHON_MISSING' }
 $Exe = $Python.Source; $Prefix = @()
}
$Scratch = Join-Path $env:TEMP ('SpawnPK-R297-PublicSource-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $Scratch) { throw 'R297_REFUSE_EXISTING_SCRATCH' }
try {
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Package).ProviderPath, $Scratch)
 $Entry = Join-Path $Scratch 'tools\windows\r297\R297-Owner-Readiness.py'
 if (!(Test-Path -LiteralPath $Entry -PathType Leaf)) { throw 'R297_SOURCE_ENTRY_MISSING' }
 $Arguments = @($Entry, '--input-dir', $InputDir, '--output', $Output)
 if ($RunNativeGui) { $Arguments += '--run-native-gui' }
 & $Exe @Prefix @Arguments
 if ($LASTEXITCODE -ne 0) { throw "R297_R295_NOT_ADMITTED_OR_GUI_FAILED exit=$LASTEXITCODE" }
 if ($RunNativeGui) {
  Write-Host 'R297_R295_NATIVE_GUI_RUNNER_REPORTED_PASS. Inspect new owner-local R286 acceptance receipt.' -ForegroundColor Green
 } else {
  Write-Host 'R297_R295_WINDOWS_READINESS_PASS. NO GAME LAUNCHED AND NO OUTPUT CREATED.' -ForegroundColor Green
 }
} finally {
 if (Test-Path -LiteralPath $Scratch) { [System.IO.Directory]::Delete($Scratch,$true) }
}
