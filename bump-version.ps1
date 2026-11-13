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

function Get-CurrentVersion {
    param([string]$FilePath)
    if (-not (Test-Path $FilePath)) {
        throw "__version__.py nicht gefunden: " + $FilePath
    }
    $content = Get-Content $FilePath -Raw
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
    $content = Get-Content $Path -Raw
    $pattern = '__version__\s*=\s*"' + [regex]::Escape($OldVer) + '"'
    $replace = '__version__ = "' + $NewVer + '"'
    if ($content -notmatch $pattern) {
        Write-Host "  [--] __version__.py: kein passendes Muster, uebersprungen."
        return
    }
    $updated = $content -replace $pattern, $replace
    Set-Content $Path -Value $updated -NoNewline
    Write-Host "  [OK] bowtally\__version__.py"
}

function Update-NsiFile {
    param([string]$Path, [string]$OldVer, [string]$NewVer)
    if (-not (Test-Path $Path)) { return }
    $content = Get-Content $Path -Raw
    $pattern = '(!define VERSION\s+")' + [regex]::Escape($OldVer) + '"'
    if ($content -notmatch $pattern) {
        Write-Host "  [--] build\setup.nsi: kein passendes VERSION-Define, uebersprungen."
        return
    }
    $updated = $content -replace $pattern, ('${1}' + $NewVer + '"')
    Set-Content $Path -Value $updated -NoNewline
    Write-Host "  [OK] build\setup.nsi"
}

function Update-Readme {
    param([string]$Path, [string]$OldVer, [string]$NewVer)
    if (-not (Test-Path $Path)) { return }
    $content = Get-Content $Path -Raw
    $escaped = [regex]::Escape($OldVer)
    if ($content -notmatch $escaped) {
        Write-Host "  [--] README.md: Version nicht gefunden, uebersprungen."
        return
    }
    $updated = $content -replace $escaped, $NewVer
    Set-Content $Path -Value $updated -NoNewline
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
    $nsiContent = Get-Content $NsiFile -Raw
    if ($nsiContent -match ([regex]::Escape($currentVer))) { Write-Host "  - build\setup.nsi" }
}
if (Test-Path $ReadmeMd) {
    $readmeContent = Get-Content $ReadmeMd -Raw
    if ($readmeContent -match ([regex]::Escape($currentVer))) { Write-Host "  - README.md" }
}
Write-Host ""

$confirm = Read-Host "Bestaetigen und durchfuehren? (j/N)"
if ($confirm.Trim().ToLower() -ne "j") {
    Write-Host "Abgebrochen." -ForegroundColor Gray
    exit 0
}

Write-Host ""
Write-Host "Dateien aktualisieren..." -ForegroundColor Cyan

Update-VersionFile -Path $VersionFile -OldVer $currentVer -NewVer $targetVer
Update-NsiFile     -Path $NsiFile     -OldVer $currentVer -NewVer $targetVer
Update-Readme      -Path $ReadmeMd   -OldVer $currentVer -NewVer $targetVer

Write-Host ""
Write-Host ("Fertig. Version " + $targetVer + " gesetzt.") -ForegroundColor Green
Write-Host ""
