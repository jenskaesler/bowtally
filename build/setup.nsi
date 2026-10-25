; NSIS installer script for BowTally (NSIS 3.x, Modern UI 2)
; Build the app first (build\build.bat), then:  makensis build\setup.nsi
; Optional: makensis /DVERSION=0.2.0 build\setup.nsi

Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"

SetCompressor /SOLID lzma   ; <-- hier, vor allen VI-Keys und Defines

; ============================================================
; Version und Konstanten
; ============================================================
!define APPNAME    "BowTally"
!ifndef VERSION
  !define VERSION  "0.4.0"
!endif
!define PUBLISHER  "jenskaesler"
!define URL        "https://github.com/jenskaesler/bowtally"
!define EXE        "BowTally.exe"
!define INSTALLERNAME "BowTally-${VERSION}-Setup"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"

!define /date YEAR "%Y"
!define COPYRIGHT  "Copyright ${YEAR} ${PUBLISHER} - GPLv3"

; ============================================================
; PE-Metadaten
; ============================================================
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName"      "${APPNAME}"
VIAddVersionKey "ProductVersion"   "${VERSION}"
VIAddVersionKey "CompanyName"      "${PUBLISHER}"
VIAddVersionKey "LegalCopyright"   "${COPYRIGHT}"
VIAddVersionKey "FileVersion"      "${VERSION}.0"
VIAddVersionKey "FileDescription"  "${APPNAME} Setup"
VIAddVersionKey "InternalName"     "${INSTALLERNAME}"
VIAddVersionKey "OriginalFilename" "${INSTALLERNAME}.exe"

; ============================================================
; MUI-Einstellungen
; ============================================================
!define MUI_ICON    "..\assets\icon.ico"
!define MUI_UNICON  "..\assets\icon.ico"
!define MUI_ABORTWARNING
!define MUI_LICENSEPAGE_CHECKBOX
!define MUI_COMPONENTSPAGE_SMALLDESC

!define MUI_FINISHPAGE_TEXT_LARGE
!define MUI_FINISHPAGE_LINK          "GitHub Repository"
!define MUI_FINISHPAGE_LINK_LOCATION "${URL}"

; App nach Installation als normaler Benutzer starten, nicht elevated
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT     "BowTally starten"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchAsUser

; ============================================================
; Seiten - Installer
; ============================================================
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_PAGE_HEADER_TEXT        "Hinweise"
!define MUI_PAGE_HEADER_SUBTEXT     "Wo BowTally Ihre Daten speichert"
!define MUI_LICENSEPAGE_TEXT_TOP    "Bitte beachten Sie:"
!define MUI_LICENSEPAGE_TEXT_BOTTOM " "
!define MUI_LICENSEPAGE_BUTTON      "$(^NextBtn)"
!insertmacro MUI_PAGE_LICENSE "install_info.txt"

!insertmacro MUI_PAGE_FINISH

; ============================================================
; Seiten - Deinstaller
; ============================================================
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "German"

; ============================================================
; Allgemein
; ============================================================
Name "${APPNAME} ${VERSION}"
OutFile "dist\${INSTALLERNAME}.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "${UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin
BrandingText "${APPNAME} ${VERSION} by ${PUBLISHER}"
ShowInstDetails   show
ShowUninstDetails show

ManifestDPIAware true
ManifestSupportedOS all

; ============================================================
; Callbacks
; ============================================================
Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "BowTally benötigt ein 64-Bit-Windows."
    Abort
  ${EndIf}
  SetRegView 64
FunctionEnd

Function un.onInit
  SetRegView 64
FunctionEnd

; Explorer erbt das Token des eingeloggten Benutzers, nicht das des Installers.
; Damit startet die App nach der Installation ohne Admin-Kontext.
Function LaunchAsUser
  Exec '"$WINDIR\explorer.exe" "$INSTDIR\${EXE}"'
FunctionEnd

; ============================================================
; Sections
; ============================================================
Section "BowTally" SecMain
  SectionIn RO
  SetShellVarContext all
  SetOverwrite on
  SetOutPath "$INSTDIR"

  ; Altes PyInstaller-Bundle entfernen, bevor neue Dateien geschrieben werden
  RMDir /r "$INSTDIR\_internal"
  File /r "dist\BowTally\*"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"                 "$INSTDIR\${EXE}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME} deinstallieren.lnk"  "$INSTDIR\Uninstall.exe"

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0

  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"          "${APPNAME}"
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"       "${VERSION}"
  WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"            "${PUBLISHER}"
  WriteRegStr   HKLM "${UNINST_KEY}" "URLInfoAbout"         "${URL}"
  WriteRegStr   HKLM "${UNINST_KEY}" "HelpLink"             "${URL}"
  WriteRegStr   HKLM "${UNINST_KEY}" "URLUpdateInfo"        "${URL}/releases"
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayIcon"          "$INSTDIR\${EXE}"
  WriteRegStr   HKLM "${UNINST_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString"      '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKLM "${UNINST_KEY}" "EstimatedSize"        "$0"
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify"             1
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair"             1
SectionEnd

Section /o "Desktop-Verknüpfung" SecDesktop
  SetShellVarContext all
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${EXE}"
SectionEnd

Section "Uninstall"
  SetShellVarContext all
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  ; Uninstaller explizit löschen, bevor das Verzeichnis entfernt wird
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "${UNINST_KEY}"
SectionEnd