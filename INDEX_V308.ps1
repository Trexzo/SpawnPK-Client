param(
  [Parameter(Mandatory=$true)][string]$ClientJar
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Expected = '854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6'
& .\.venv\Scripts\spk-recovery.exe index $ClientJar --expect-sha256 $Expected --out .\evidence\indexes\v308.json
