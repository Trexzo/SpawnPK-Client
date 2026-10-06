[CmdletBinding()]
param(
    [string[]]$Roots = @((Join-Path $env:USERPROFILE "Desktop\gpt_output2")),
    [string[]]$ZipNamePatterns = @(
        "*R8N*.zip",
        "*Validation-Backup*.zip",
        "*SourceM1*.zip",
        "*Authority*.zip"
    ),
    [string]$MaterializeDir,
    [switch]$SkipArchives
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$RequiredFiles = @(
    "v308-index.json",
    "class-lineage.accepted.json",
    "member-lineage.accepted.json",
    "member-safety.accepted.json"
)

function Get-StreamSha256 {
    param([Parameter(Mandatory = $true)][System.IO.Stream]$Stream)

    $Sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Bytes = $Sha.ComputeHash($Stream)
        return (($Bytes | ForEach-Object { $_.ToString("x2") }) -join "")
    }
    finally {
        $Sha.Dispose()
    }
}

function Get-FileFacts {
    param([Parameter(Mandatory = $true)][string]$Path)

    $Item = Get-Item -LiteralPath $Path -ErrorAction Stop
    $Stream = [System.IO.File]::OpenRead($Item.FullName)
    try {
        $Hash = Get-StreamSha256 -Stream $Stream
    }
    finally {
        $Stream.Dispose()
    }

    return @{
        Length = [int64]$Item.Length
        Sha256 = $Hash
        Path = $Item.FullName
        EntryName = $null
    }
}

function Get-ZipEntryFacts {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Entry
    )

    $Stream = $Entry.Open()
    try {
        $Hash = Get-StreamSha256 -Stream $Stream
    }
    finally {
        $Stream.Dispose()
    }

    return @{
        Length = [int64]$Entry.Length
        Sha256 = $Hash
        Path = $null
        EntryName = $Entry.FullName.Replace("\", "/")
    }
}

function Get-AuthoritySetFingerprint {
    param([Parameter(Mandatory = $true)][hashtable]$Facts)

    $Lines = New-Object System.Collections.Generic.List[string]
    foreach ($Name in $RequiredFiles) {
        $Fact = $Facts[$Name]
        $Lines.Add(
            $Name +
            [char]9 +
            [string]$Fact.Length +
            [char]9 +
            [string]$Fact.Sha256
        )
    }

    $Canonical = (($Lines -join [char]10) + [char]10)
    $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Canonical)
    $Stream = New-Object System.IO.MemoryStream(,$Bytes)
    try {
        return (Get-StreamSha256 -Stream $Stream)
    }
    finally {
        $Stream.Dispose()
    }
}

function Add-DirectoryCandidates {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]]$Candidates,
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [hashtable]$SeenAuthorityDirectories
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return
    }

    $Dirs = New-Object System.Collections.Generic.List[object]
    $RootItem = Get-Item -LiteralPath $Root
    if ($RootItem.Name -ieq "authority") {
        $Dirs.Add($RootItem)
    }

    @(
        Get-ChildItem -LiteralPath $Root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ieq "authority" }
    ) | ForEach-Object { $Dirs.Add($_) }

    foreach ($Dir in $Dirs) {
        $Key = $Dir.FullName.ToLowerInvariant()
        if ($SeenAuthorityDirectories.ContainsKey($Key)) {
            continue
        }
        $SeenAuthorityDirectories[$Key] = $true

        $Facts = @{}
        $Complete = $true
        foreach ($Name in $RequiredFiles) {
            $Path = Join-Path $Dir.FullName $Name
            if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
                $Complete = $false
                break
            }
            $Facts[$Name] = Get-FileFacts -Path $Path
        }

        if (-not $Complete) {
            continue
        }

        $Candidates.Add(
            [pscustomobject]@{
                Kind = "directory"
                Source = $Dir.FullName
                Prefix = ""
                Facts = $Facts
                SetSha256 = Get-AuthoritySetFingerprint -Facts $Facts
            }
        )
    }
}

function Zip-NameMatches {
    param([Parameter(Mandatory = $true)][string]$Name)

    foreach ($Pattern in $ZipNamePatterns) {
        if ($Name -like $Pattern) {
            return $true
        }
    }
    return $false
}

function Add-ZipCandidates {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[object]]$Candidates,
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [hashtable]$SeenArchives
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $Archives = @(
        Get-ChildItem -LiteralPath $Root -File -Recurse -Filter "*.zip" -Force -ErrorAction SilentlyContinue |
            Where-Object { Zip-NameMatches -Name $_.Name }
    )

    foreach ($ArchiveFile in $Archives) {
        $ArchiveKey = $ArchiveFile.FullName.ToLowerInvariant()
        if ($SeenArchives.ContainsKey($ArchiveKey)) {
            continue
        }
        $SeenArchives[$ArchiveKey] = $true

        $Archive = [System.IO.Compression.ZipFile]::OpenRead($ArchiveFile.FullName)
        try {
            $ByName = @{}
            foreach ($Entry in $Archive.Entries) {
                $Normalized = $Entry.FullName.Replace("\", "/")
                if ($ByName.ContainsKey($Normalized)) {
                    throw (
                        "Duplicate ZIP entry path is ambiguous: " +
                        $ArchiveFile.FullName +
                        " :: " +
                        $Normalized
                    )
                }
                $ByName[$Normalized] = $Entry
            }

            $FirstName = $RequiredFiles[0]
            $FirstEntries = @(
                $Archive.Entries |
                    Where-Object {
                        $Normalized = $_.FullName.Replace("\", "/")
                        $Normalized -match (
                            "(?i)(^|/)authority/" +
                            [regex]::Escape($FirstName) +
                            "$"
                        )
                    }
            )

            foreach ($FirstEntry in $FirstEntries) {
                $NormalizedFirst = $FirstEntry.FullName.Replace("\", "/")
                $Slash = $NormalizedFirst.LastIndexOf("/")
                if ($Slash -lt 0) {
                    continue
                }
                $Prefix = $NormalizedFirst.Substring(0, $Slash + 1)

                $Facts = @{}
                $Complete = $true
                foreach ($Name in $RequiredFiles) {
                    $EntryName = $Prefix + $Name
                    if (-not $ByName.ContainsKey($EntryName)) {
                        $Complete = $false
                        break
                    }
                    $Facts[$Name] = Get-ZipEntryFacts -Entry $ByName[$EntryName]
                }

                if (-not $Complete) {
                    continue
                }

                $Candidates.Add(
                    [pscustomobject]@{
                        Kind = "zip"
                        Source = $ArchiveFile.FullName
                        Prefix = $Prefix
                        Facts = $Facts
                        SetSha256 = Get-AuthoritySetFingerprint -Facts $Facts
                    }
                )
            }
        }
        finally {
            $Archive.Dispose()
        }
    }
}

function Write-Candidate {
    param(
        [Parameter(Mandatory = $true)][object]$Candidate,
        [Parameter(Mandatory = $true)][int]$Index
    )

    Write-Host ("AUTHORITY_CANDIDATE_" + $Index + "_KIND=" + $Candidate.Kind)
    Write-Host ("AUTHORITY_CANDIDATE_" + $Index + "_SOURCE=" + $Candidate.Source)
    if (-not [string]::IsNullOrWhiteSpace($Candidate.Prefix)) {
        Write-Host ("AUTHORITY_CANDIDATE_" + $Index + "_PREFIX=" + $Candidate.Prefix)
    }
    Write-Host (
        "AUTHORITY_CANDIDATE_" +
        $Index +
        "_SET_SHA256=" +
        $Candidate.SetSha256
    )

    foreach ($Name in $RequiredFiles) {
        $Fact = $Candidate.Facts[$Name]
        $Key = ($Name -replace "[^A-Za-z0-9]", "_").ToUpperInvariant()
        Write-Host (
            "AUTHORITY_CANDIDATE_" +
            $Index +
            "_" +
            $Key +
            "_BYTES=" +
            [string]$Fact.Length
        )
        Write-Host (
            "AUTHORITY_CANDIDATE_" +
            $Index +
            "_" +
            $Key +
            "_SHA256=" +
            $Fact.Sha256
        )
    }
}

function Materialize-Candidate {
    param(
        [Parameter(Mandatory = $true)][object]$Candidate,
        [Parameter(Mandatory = $true)][string]$TargetDir
    )

    if (Test-Path -LiteralPath $TargetDir) {
        $Existing = @(
            Get-ChildItem -LiteralPath $TargetDir -Force -ErrorAction Stop
        )
        if ($Existing.Count -ne 0) {
            throw "Materialize directory must be empty: $TargetDir"
        }
    }
    else {
        New-Item -ItemType Directory -Path $TargetDir | Out-Null
    }

    if ($Candidate.Kind -eq "directory") {
        foreach ($Name in $RequiredFiles) {
            Copy-Item -LiteralPath $Candidate.Facts[$Name].Path -Destination (Join-Path $TargetDir $Name)
        }
    }
    elseif ($Candidate.Kind -eq "zip") {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $Archive = [System.IO.Compression.ZipFile]::OpenRead($Candidate.Source)
        try {
            $ByName = @{}
            foreach ($Entry in $Archive.Entries) {
                $Normalized = $Entry.FullName.Replace("\", "/")
                if ($ByName.ContainsKey($Normalized)) {
                    throw (
                        "Duplicate ZIP entry path is ambiguous during materialization: " +
                        $Candidate.Source +
                        " :: " +
                        $Normalized
                    )
                }
                $ByName[$Normalized] = $Entry
            }

            foreach ($Name in $RequiredFiles) {
                $EntryName = $Candidate.Prefix + $Name
                if (-not $ByName.ContainsKey($EntryName)) {
                    throw "ZIP authority entry disappeared: $EntryName"
                }

                $Input = $ByName[$EntryName].Open()
                $OutputPath = Join-Path $TargetDir $Name
                $Output = [System.IO.File]::Open(
                    $OutputPath,
                    [System.IO.FileMode]::CreateNew,
                    [System.IO.FileAccess]::Write,
                    [System.IO.FileShare]::None
                )
                try {
                    $Input.CopyTo($Output)
                }
                finally {
                    $Output.Dispose()
                    $Input.Dispose()
                }
            }
        }
        finally {
            $Archive.Dispose()
        }
    }
    else {
        throw "Unsupported candidate kind: $($Candidate.Kind)"
    }

    $VerifiedFacts = @{}
    foreach ($Name in $RequiredFiles) {
        $Path = Join-Path $TargetDir $Name
        $VerifiedFacts[$Name] = Get-FileFacts -Path $Path
        $Expected = $Candidate.Facts[$Name]
        $Actual = $VerifiedFacts[$Name]
        if (
            $Actual.Length -ne $Expected.Length -or
            $Actual.Sha256 -ne $Expected.Sha256
        ) {
            throw "Materialized authority file drifted: $Name"
        }
    }

    $VerifiedSet = Get-AuthoritySetFingerprint -Facts $VerifiedFacts
    if ($VerifiedSet -ne $Candidate.SetSha256) {
        throw "Materialized authority set fingerprint drifted."
    }

    Write-Host "SOURCE_M1_PRIVATE_AUTHORITY_MATERIALIZED=1"
    Write-Host "MATERIALIZED_DIR=$TargetDir"
    Write-Host "MATERIALIZED_SET_SHA256=$VerifiedSet"
    Write-Host ("MATERIALIZED_SOURCE_INDEX=" + (Join-Path $TargetDir "v308-index.json"))
    Write-Host ("MATERIALIZED_CLASS_LINEAGE=" + (Join-Path $TargetDir "class-lineage.accepted.json"))
    Write-Host ("MATERIALIZED_MEMBER_LINEAGE=" + (Join-Path $TargetDir "member-lineage.accepted.json"))
    Write-Host ("MATERIALIZED_MEMBER_SAFETY=" + (Join-Path $TargetDir "member-safety.accepted.json"))
}

$Candidates = New-Object System.Collections.Generic.List[object]
$SeenAuthorityDirectories = @{}
$SeenArchives = @{}

foreach ($Root in $Roots) {
    Add-DirectoryCandidates -Candidates $Candidates -Root $Root -SeenAuthorityDirectories $SeenAuthorityDirectories
    if (-not $SkipArchives) {
        Add-ZipCandidates -Candidates $Candidates -Root $Root -SeenArchives $SeenArchives
    }
}

if ($Candidates.Count -eq 0) {
    Write-Host "SOURCE_M1_PRIVATE_AUTHORITY_NOT_FOUND=1"
    exit 3
}

$OrderedCandidates = @(
    $Candidates |
        Sort-Object @{ Expression = { if ($_.Kind -eq "directory") { 0 } else { 1 } } }, Source, Prefix
)

$Groups = @($OrderedCandidates | Group-Object SetSha256)
if ($Groups.Count -ne 1) {
    Write-Host "SOURCE_M1_PRIVATE_AUTHORITY_CONFLICT=1"
    Write-Host "AUTHORITY_SET_VARIANT_COUNT=$($Groups.Count)"
    for ($Index = 0; $Index -lt $OrderedCandidates.Count; $Index++) {
        Write-Candidate -Candidate $OrderedCandidates[$Index] -Index ($Index + 1)
    }
    exit 4
}

Write-Host "SOURCE_M1_PRIVATE_AUTHORITY_FOUND=1"
Write-Host "AUTHORITY_CANDIDATE_COUNT=$($OrderedCandidates.Count)"
Write-Host "AUTHORITY_SET_VARIANT_COUNT=1"
Write-Host "AUTHORITY_SET_SHA256=$($Groups[0].Name)"

for ($Index = 0; $Index -lt $OrderedCandidates.Count; $Index++) {
    Write-Candidate -Candidate $OrderedCandidates[$Index] -Index ($Index + 1)
}

if (-not [string]::IsNullOrWhiteSpace($MaterializeDir)) {
    Materialize-Candidate -Candidate $OrderedCandidates[0] -TargetDir $MaterializeDir
}

exit 0
