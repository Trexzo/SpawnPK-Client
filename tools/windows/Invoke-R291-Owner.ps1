[CmdletBinding()]
param(
    [string]$InputDir = (Join-Path $env:USERPROFILE 'Downloads'),
    [string]$Package = (Join-Path $PSScriptRoot 'SpawnPK_v309_R291_R290_NATIVE_WINDOWS_SOURCE_ONLY.zip'),
    [string]$Output = (Join-Path ([Environment]::GetFolderPath('Desktop')) ('SpawnPK-R291-Windows-Private-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))),
    [switch]$RunNativeGui
)
$ErrorActionPreference = 'Stop'
$PackageSha256 = 'F932BD9D83B0DDB94F2373D5BA06F9AA65456A6D8B06C4B62F4616992FC0763A'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'R291_BOOTSTRAP_REFUSE_NOT_WINDOWS' }
if (!(Test-Path -LiteralPath $InputDir -PathType Container)) { throw 'R291_BOOTSTRAP_INPUT_DIR_MISSING' }
if (!(Test-Path -LiteralPath $Package -PathType Leaf)) { throw 'R291_BOOTSTRAP_PACKAGE_MISSING' }
if ((Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash -ne $PackageSha256) { throw 'R291_BOOTSTRAP_PACKAGE_HASH_MISMATCH' }
if (Test-Path -LiteralPath $Output) { throw 'R291_BOOTSTRAP_REFUSE_EXISTING_OUTPUT' }
$Python = Get-Command py.exe -ErrorAction SilentlyContinue
if ($Python) { $Exe = $Python.Source; $Prefix = @('-3') }
else {
    $Python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (!$Python) { throw 'R291_BOOTSTRAP_PYTHON_MISSING' }
    $Exe = $Python.Source; $Prefix = @()
}
$Scratch = Join-Path $env:TEMP ('SpawnPK-R291-SafeScripts-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $Scratch) { throw 'R291_BOOTSTRAP_REFUSE_EXISTING_SCRATCH' }
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $Package).ProviderPath, $Scratch)
    $Entry = Join-Path $Scratch 'tools\windows\r291\R291-Windows-R290-Acceptance.py'
    if (!(Test-Path -LiteralPath $Entry -PathType Leaf)) { throw 'R291_BOOTSTRAP_SOURCE_ENTRY_MISSING' }
    $ArgsList = @($Entry, '--input-dir', $InputDir, '--output', $Output)
    if ($RunNativeGui) { $ArgsList += '--run-native-gui' }
    & $Exe @Prefix @ArgsList
    if ($LASTEXITCODE -ne 0) { throw "R291_OWNER_ACCEPTANCE_FAILED exit=$LASTEXITCODE" }
    if ($RunNativeGui) {
        Write-Host 'R291_OWNER_NATIVE_GUI_RUNNER_REPORTED_PASS; inspect private receipt for actual evidence' -ForegroundColor Green
    } else {
        Write-Host 'R291_READ_ONLY_PREFLIGHT_PASS; no game client launched' -ForegroundColor Green
    }
} finally {
    if (Test-Path -LiteralPath $Scratch) { [System.IO.Directory]::Delete($Scratch,$true) }
}
