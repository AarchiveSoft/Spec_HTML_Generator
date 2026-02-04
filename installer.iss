; Inno Setup Script for Claudias Spezifikationen Assistent
; Supports German and English languages
; Output to installer_output/

#define MyAppName "Claudias Listenwichtel"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "GraphicArt"
#define MyAppExeName "SpecHTMLGenerator.exe"
#define MyAppURL "https://graphicart.ch"

[Setup]
; Application identity
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directories - use user folder to avoid permission issues
DefaultDirName={userpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output configuration
OutputDir=installer_output
OutputBaseFilename=SpecHTMLGenerator_Setup_{#MyAppVersion}
SetupIconFile=icons\icon_gra.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Visual settings
WizardStyle=modern
WizardSizePercent=100

; Privileges - install for current user only (no admin required)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Misc
Uninstallable=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
german.CreateDesktopIcon=Desktop-Symbol erstellen
german.LaunchAfterInstall=Anwendung nach der Installation starten
english.CreateDesktopIcon=Create desktop icon
english.LaunchAfterInstall=Launch application after installation

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\SpecHTMLGenerator\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; All files from dist directory (PyInstaller output)
Source: "dist\SpecHTMLGenerator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Icons directory (if not bundled by PyInstaller)
Source: "icons\*"; DestDir: "{app}\icons"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Optional translations file for French export
Source: "translations_fr.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start Menu - use user's start menu, not common
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Desktop (optional) - use user's desktop, not common desktop
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any leftover files
Type: filesandordirs; Name: "{app}"
