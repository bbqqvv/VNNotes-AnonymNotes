; VNNotes Official Inno Setup Script
; Note: This file is meant to be compiled by ISCC.exe

#define MyAppName "VNNotes"
#ifndef MyAppVersion
  #define MyAppVersion "2.1.1"
#endif
#define MyAppPublisher "VTech Digital Solution"
#define MyAppURL "https://github.com/bbqqvv/VNNotes"
#define MyAppExeName "VNNotes.exe"
#define MyAppId "vtech.vnnotes.stable.v3"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{{#MyAppId}}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=yes
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=VNNotes_Setup
SetupIconFile=..\appnote.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; IMPORTANT: The source path points to the directory created by PyInstaller
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; AppUserModelID: "{#MyAppId}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; AppUserModelID: "{#MyAppId}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Registry]
; Register custom URI scheme 'vnnotes://' for Deep Linking
Root: HKCU; Subkey: "Software\Classes\vnnotes"; ValueType: string; ValueName: ""; ValueData: "URL:VNNotes Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\vnnotes"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\vnnotes\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\vnnotes\shell"; ValueType: string; ValueName: ""; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\vnnotes\shell\open"; ValueType: string; ValueName: ""; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\vnnotes\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
