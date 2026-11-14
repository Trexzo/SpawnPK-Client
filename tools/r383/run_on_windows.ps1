# R383 isolated private-source compilation. No game launch, cache access or network use.
param(
 [Parameter(Mandatory=$true)][string]$PrivateBundle,
 [string]$OutputDir = "$env:USERPROFILE\Desktop\SpawnPK-R383-Windows-Offline-Results",
 [string]$Python = "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe",
 [string]$Javac = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\javac.exe'
)
$ErrorActionPreference='Stop'
if (!(Test-Path -LiteralPath $PrivateBundle -PathType Leaf)) { throw 'Missing private R382 bundle' }
if (!(Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Python 3.12 executable not found' }
if (!(Test-Path -LiteralPath $Javac -PathType Leaf)) { throw 'Explicit JDK21 javac not found' }
if (Test-Path -LiteralPath $OutputDir) { throw 'Refusing to overwrite existing output directory' }
$runner=Join-Path $PSScriptRoot 'verify_private_full_build.py'
& $Python $runner --private-bundle $PrivateBundle --javac $Javac --out-dir $OutputDir
if ($LASTEXITCODE -ne 0) { throw "R383 offline compilation failed. Inspect $OutputDir\R383-Verification-Report.json" }
Write-Host "R383 offline compilation completed. Inspect $OutputDir\R383-Verification-Report.json"
