#Requires -Version 5.1
<#
.SYNOPSIS
    Liest die aktuelle Version aus bowtally/__version__.py und passt sie
    in allen relevanten Projektdateien an.

.DESCRIPTION
    Liest die Version aus bowtally/__version__.py (Format JJJJ.MM.N),
    schlaegt die naechste Version vor und aktualisiert nach Bestaetigung:
      - bowtally/__version__.py
      - build/setup.nsi
      - README.md

.USAGE
    .\bump-version.ps1
    .\bump-version.ps1 -Patch              # nur Patch-Nummer hochzaehlen
    .\bump-version.ps1 -Month             # neuer Monat, Patch auf 0
    .\bump-version.ps1 -Version "2026.12.0"  # freie Eingabe

    Danach werden die Dateien committet ("chore: bump version to X"), mit vX getaggt und
    Commit und Tag nach origin gepusht. build\build.bat ruft das Skript als ersten Schritt auf.

.OUTPUTS
    Exit 0  - keine Aenderung (abgebrochen oder bereits aktuell)
    Exit 1  - Fehler
    Exit 10 - Version erhoeht, committet, getaggt und gepusht
#>

param(
    [switch]$Patch,
    [switch]$Month,
    [string]$Version = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$VersionFile = Join-Path $ScriptDir "bowtally\__version__.py"
$NsiFile     = Join-Path $ScriptDir "build\setup.nsi"
$ReadmeMd    = Join-Path $ScriptDir "README.md"

# Alle Dateien als UTF-8 lesen und schreiben (Windows PowerShell 5.1 nutzt sonst die
# ANSI-Codepage und beschaedigt Umlaute und Emojis). Ein vorhandenes BOM bleibt erhalten.
function Read-Utf8File {
    param([string]$Path)
    return [System.IO.File]::ReadAllText($Path, (New-Object System.Text.UTF8Encoding($false)))
}

function Write-Utf8File {
    param([string]$Path, [string]$Text)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($hasBom)))
}

function Get-CurrentVersion {
    param([string]$FilePath)
    if (-not (Test-Path $FilePath)) {
        throw "__version__.py nicht gefunden: " + $FilePath
    }
    $content = Read-Utf8File $FilePath
    if ($content -match '__version__\s*=\s*"([^"]+)"') {
        return $Matches[1]
    }
    throw "Keine __version__-Zeile in __version__.py gefunden."
}

function Parse-Version {
    param([string]$Ver)
    $parts = $Ver -split "\."
    if ($parts.Count -ne 3) {
        throw "Ungueltiges Versionsformat: " + $Ver + " (erwartet JJJJ.MM.N)"
    }
    return @{
        Year  = [int]$parts[0]
        Month = [int]$parts[1]
        Patch = [int]$parts[2]
    }
}

function Format-Version {
    param([hashtable]$Parts)
    $monthPadded = $Parts.Month.ToString("D2")
    return ($Parts.Year.ToString() + "." + $monthPadded + "." + $Parts.Patch.ToString())
}

function Suggest-NextVersions {
    param([hashtable]$Current)
    $now = Get-Date

    $nextPatch = @{
        Year  = $Current.Year
        Month = $Current.Month
        Patch = $Current.Patch + 1
    }

    $nextMonth = @{
        Year  = $now.Year
        Month = $now.Month
        Patch = 0
    }

    return @{
        Patch = $nextPatch
        Month = $nextMonth
    }
}

function Update-VersionFile {
    param([string]$Path, [string]$OldVer, [string]$NewVer)
    $content = Read-Utf8File $Path
    $pattern = '__version__\s*=\s*"' + [regex]::Escape($OldVer) + '"'
    $replace = '__version__ = "' + $NewVer + '"'
    if ($content -notmatch $pattern) {
        Write-Host "  [--] __version__.py: kein passendes Muster, uebersprungen."
        return
    }
    $updated = $content -replace $pattern, $replace
    Write-Utf8File -Path $Path -Text $updated
    Write-Host "  [OK] bowtally\__version__.py"
}

function Update-NsiFile {
    param([string]$Path, [string]$OldVer, [string]$NewVer)
    if (-not (Test-Path $Path)) { return }
    $content = Read-Utf8File $Path
    $pattern = '(!define VERSION\s+")' + [regex]::Escape($OldVer) + '"'
    if ($content -notmatch $pattern) {
        Write-Host "  [--] build\setup.nsi: kein passendes VERSION-Define, uebersprungen."
        return
    }
    $updated = $content -replace $pattern, ('${1}' + $NewVer + '"')
    Write-Utf8File -Path $Path -Text $updated
    Write-Host "  [OK] build\setup.nsi"
}

function Update-Readme {
    param([string]$Path, [string]$OldVer, [string]$NewVer)
    if (-not (Test-Path $Path)) { return }
    $content = Read-Utf8File $Path
    $escaped = [regex]::Escape($OldVer)
    if ($content -notmatch $escaped) {
        Write-Host "  [--] README.md: Version nicht gefunden, uebersprungen."
        return
    }
    $updated = $content -replace $escaped, $NewVer
    Write-Utf8File -Path $Path -Text $updated
    Write-Host "  [OK] README.md"
}

# --- Hauptprogramm ---

Write-Host ""
Write-Host "=== BowTally Version Bump ===" -ForegroundColor Cyan
Write-Host ""

$currentVer  = Get-CurrentVersion -FilePath $VersionFile
$parsed      = Parse-Version -Ver $currentVer
$suggestions = Suggest-NextVersions -Current $parsed

Write-Host "Aktuelle Version : $currentVer"
Write-Host ""

$targetVer = ""

if ($Version -ne "") {
    $targetVer = $Version
    Write-Host "Ziel-Version     : $targetVer  (manuell)"
} elseif ($Patch) {
    $targetVer = Format-Version -Parts $suggestions.Patch
    Write-Host "Ziel-Version     : $targetVer  (Patch)"
} elseif ($Month) {
    $targetVer = Format-Version -Parts $suggestions.Month
    Write-Host "Ziel-Version     : $targetVer  (neuer Monat)"
} else {
    $patchVer = Format-Version -Parts $suggestions.Patch
    $monthVer = Format-Version -Parts $suggestions.Month

    Write-Host "Welche Version soll es werden?" -ForegroundColor Yellow
    Write-Host "  [1] $patchVer  (Patch hochzaehlen)"
    Write-Host "  [2] $monthVer  (neuer Monat)"
    Write-Host "  [3] Freie Eingabe"
    Write-Host "  [Q] Abbrechen"
    Write-Host ""
    $choice = Read-Host "Auswahl"

    switch ($choice.Trim().ToUpper()) {
        "1" { $targetVer = $patchVer }
        "2" { $targetVer = $monthVer }
        "3" {
            $targetVer = (Read-Host "Neue Version (Format JJJJ.MM.N)").Trim()
        }
        "Q" {
            Write-Host "Abgebrochen." -ForegroundColor Gray
            exit 0
        }
        default {
            Write-Host "Ungueltige Auswahl. Abgebrochen." -ForegroundColor Red
            exit 1
        }
    }
}

# Format pruefen
try {
    $null = Parse-Version -Ver $targetVer
} catch {
    Write-Host ("Fehler: " + $_) -ForegroundColor Red
    exit 1
}

if ($targetVer -eq $currentVer) {
    Write-Host "Ziel-Version ist identisch mit aktueller Version. Nichts zu tun." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Zusammenfassung:" -ForegroundColor Yellow
Write-Host "  Version : $currentVer  ->  $targetVer"
Write-Host ""
Write-Host "Folgende Dateien werden geaendert:"
Write-Host "  - bowtally\__version__.py"
if (Test-Path $NsiFile) {
    $nsiContent = Read-Utf8File $NsiFile
    if ($nsiContent -match ([regex]::Escape($currentVer))) { Write-Host "  - build\setup.nsi" }
}
if (Test-Path $ReadmeMd) {
    $readmeContent = Read-Utf8File $ReadmeMd
    if ($readmeContent -match ([regex]::Escape($currentVer))) { Write-Host "  - README.md" }
}
Write-Host ""

$confirm = Read-Host "Bestaetigen und durchfuehren? (j/N)"
if ($confirm.Trim().ToLower() -ne "j") {
    Write-Host "Abgebrochen." -ForegroundColor Gray
    exit 0
}

# --- Git-Vorpruefung: abbrechen, bevor Dateien geaendert werden ---
$tag = "v" + $targetVer
function Invoke-Git {
    & git -C $ScriptDir @args
    if ($LASTEXITCODE -ne 0) {
        Write-Host ("Fehler: git " + ($args -join " ") + " fehlgeschlagen (Exit $LASTEXITCODE).") -ForegroundColor Red
        exit 1
    }
}
& git -C $ScriptDir rev-parse -q --verify "refs/tags/$tag" *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Fehler: Tag $tag existiert bereits." -ForegroundColor Red
    exit 1
}
# Nicht committete Aenderungen fehlten sonst im getaggten Release
if (& git -C $ScriptDir status --porcelain --untracked-files=no) {
    Write-Host "Fehler: Es gibt nicht committete Aenderungen. Bitte zuerst committen." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Dateien aktualisieren..." -ForegroundColor Cyan

Update-VersionFile -Path $VersionFile -OldVer $currentVer -NewVer $targetVer
Update-NsiFile     -Path $NsiFile     -OldVer $currentVer -NewVer $targetVer
Update-Readme      -Path $ReadmeMd   -OldVer $currentVer -NewVer $targetVer

# --- Commit, Tag und Push (der Tag muss auf dem Bump-Commit sitzen) ---
Invoke-Git commit -q -m "chore: bump version to $targetVer" -- bowtally/__version__.py build/setup.nsi README.md
Invoke-Git tag $tag
Invoke-Git push -q
Invoke-Git push -q origin $tag
Write-Host "  [OK] committet, getaggt ($tag) und gepusht"

Write-Host ""
Write-Host ("Fertig. Version " + $targetVer + " gesetzt.") -ForegroundColor Green
Write-Host ""
exit 10
