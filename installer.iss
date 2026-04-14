[Setup]
AppId={{B7D4E9F1-2C36-4A58-8E0D-9B7F3C1A2E45}
AppName=HS2 Studio Cleanup
AppVersion=1.0.0
AppPublisher=NikoCloud
AppPublisherURL=https://github.com/NikoCloud/HS2-Studio-Cleanup
AppSupportURL=https://github.com/NikoCloud/HS2-Studio-Cleanup/issues
AppUpdatesURL=https://github.com/NikoCloud/HS2-Studio-Cleanup/releases
DefaultDirName={autopf}\HS2 Studio Cleanup
DefaultGroupName=HS2 Studio Cleanup
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=HS2StudioCleanup_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\HS2_Studio_Cleanup.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HS2 Studio Cleanup"; Filename: "{app}\HS2_Studio_Cleanup.exe"
Name: "{group}\{cm:UninstallProgram,HS2 Studio Cleanup}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\HS2 Studio Cleanup"; Filename: "{app}\HS2_Studio_Cleanup.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\HS2_Studio_Cleanup.exe"; Description: "{cm:LaunchProgram,HS2 Studio Cleanup}"; Flags: nowait postinstall skipifsilent
