$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { py -3.11 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -e .
Write-Host 'SPK_CLIENT_RECOVERY_BOOTSTRAP_PASS'
