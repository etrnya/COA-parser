; =====================================================================
; Inno Setup Script for AI COA Parser (Lab Suite v1.7)
; =====================================================================
; This script compiles the PyInstaller directory output into a standard
; Windows Setup installer (.exe) that supports full installation and uninstallation.
; Designed for Government / Corporate IT: Requires NO Administrator privileges.

[Setup]
AppName=AI COA Parser
AppVersion=1.7
AppPublisher=Antigravity Open Source
DefaultDirName={localappdata}\COA_Parser
DefaultGroupName=AI COA Parser
UninstallDisplayIcon={app}\COA_Parser.exe
OutputDir=dist_installer
OutputBaseFilename=COA_Parser_Setup
Compression=lzma
SolidCompression=yes
; "lowest" privilege level ensures standard user accounts can install without Admin / UAC prompts
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableWelcomePage=no

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Packages the entire PyInstaller build directory
Source: "dist\COA_Parser\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\AI COA Parser"; Filename: "{app}\COA_Parser.exe"
Name: "{userdesktop}\AI COA Parser"; Filename: "{app}\COA_Parser.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\COA_Parser.exe"; Description: "Launch AI COA Parser"; Flags: nowait postinstall skipifsilent
