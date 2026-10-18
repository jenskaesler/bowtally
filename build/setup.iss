; Inno Setup script for BowTally
; Build the app first (build\build.bat), then compile this file with ISCC.exe.

#define MyAppName "BowTally"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "jenskaesler"
#define MyAppURL "https://github.com/jenskaesler/bowtally"
#define MyAppExeName "BowTally.exe"

[Setup]
AppId={{6F1B2C4E-8A3D-4F5B-9C7E-2D1A0B3C4E5F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\BowTally
DefaultGroupName=BowTally
LicenseFile=..\LICENSE
InfoAfterFile=install_info.txt
OutputDir=Output
OutputBaseFilename=BowTally-{#MyAppVersion}-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\BowTally\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Only the program directory is removed. %APPDATA%\BowTally (database, log) is kept.
Type: filesandordirs; Name: "{app}"
