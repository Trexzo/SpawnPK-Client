# Owner-private Windows offline acceptance; does not start the SpawnPK client.
# Run from the extracted R386 ZIP, not the production fullspkclient directory.
param(
    [string]$Java21Javac = '',
    [string]$NewOutputDir = ''
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'R386_WINDOWS_ONLY' }
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if ([string]::IsNullOrWhiteSpace($NewOutputDir)) {
    $NewOutputDir = Join-Path $env:TEMP ('SpawnPK-R386-Offline-' + [guid]::NewGuid().ToString('N'))
}
if (Test-Path -LiteralPath $NewOutputDir) { throw 'R386_REFUSE_EXISTING_OUTPUT' }
$python = (Get-Command python.exe -ErrorAction Stop).Source
if ([string]::IsNullOrWhiteSpace($Java21Javac)) {
    $candidates = @()
    if ($env:JAVA_HOME) { $candidates += (Join-Path $env:JAVA_HOME 'bin/javac.exe') }
    $adoptium = Join-Path $env:ProgramFiles 'Eclipse Adoptium'
    if (Test-Path -LiteralPath $adoptium) {
        $candidates += @(Get-ChildItem -LiteralPath $adoptium -Directory -Filter 'jdk-21*' |
            ForEach-Object { Join-Path $_.FullName 'bin/javac.exe' })
    }
    foreach ($item in $candidates) {
        if (Test-Path -LiteralPath $item -PathType Leaf) {
            $version = (& $item -version 2>&1 | Out-String).Trim()
            if ($version -match '^javac\s+21(?:\.|\s|$)') { $Java21Javac = $item; break }
        }
    }
}
if (-not (Test-Path -LiteralPath $Java21Javac -PathType Leaf)) { throw 'R386_JDK21_REQUIRED' }
$runner = Join-Path $PSScriptRoot 'run_self_contained_acceptance.py'
& $python $runner --bundle-dir $root --javac $Java21Javac --out-dir $NewOutputDir
if ($LASTEXITCODE -ne 0) { throw ('R386_FAILED_REPORT_AT ' + $NewOutputDir) }
$resultFile = Join-Path $NewOutputDir 'R386-Offline-Acceptance-Result.json'
$report = Get-Content -LiteralPath $resultFile -Raw | ConvertFrom-Json
if ($report.status -ne 'R386_WINDOWS_FULL_BUILD_PASS' -or
    $report.owner_windows_full_build_verified -ne $true) {
    throw ('R386_WINDOWS_ACCEPTANCE_NOT_ESTABLISHED ' + $NewOutputDir)
}
Write-Output ('R386_WINDOWS_FULL_BUILD_PASS ' + $NewOutputDir)
