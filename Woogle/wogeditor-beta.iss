[Setup]
AppName=WoG Editor (Beta)
AppVerName=WoG Editor 0.70 (Beta)
PrivilegesRequired=poweruser
DefaultDirName={pf}\WOGCorp\WoGEditor_Beta
DefaultGroupName=WOGCorp
LicenseFile=Copying.txt
VersionInfoVersion=0.7.0
VersionInfoCompany=WOGCorp
ChangesAssociations=true
VersionInfoDescription=WoG Editor
MinVersion=4.1.1998,4.0.1381sp5
SetupIconFile=src\images\wogedit.ico
OutputBaseFilename=WoGEditor_beta_setup
AlwaysRestart=false
CreateAppDir=true
DirExistsWarning=no

[Files]
Source: src\dist\*.*; DestDir: {app}; Flags: ignoreversion
Source: include\*.*; DestDir: {app}; Flags: ignoreversion
Source: version.txt; DestDir: {app}; Flags: ignoreversion
Source: copying.txt; DestDir: {app}; Flags: ignoreversion

[Tasks]
Name: startmenuicon; Description: Create a &Start Menu icon
Name: desktopicon; Description: Create a &desktop icon; GroupDescription: Additional icons:
Name: endecrypt; Description: Add &En/Decrypt to Right-Click menu; GroupDescription: Windows Shell Extensions:; Flags: unchecked

[Icons]
Name: {group}\WoG Editor (Beta); Filename: {app}\wogeditor.exe; WorkingDir: {app}; Tasks: startmenuicon
Name: {userdesktop}\WoG Editor (Beta); Filename: {app}\wogeditor; WorkingDir: {app}; IconIndex: 0; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: .bin; ValueType: string; ValueName: ; ValueData: "binfile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: binfile; ValueType: string; ValueName: ; ValueData: Binary File; Flags: uninsdeletekey
Root: HKCR; Subkey: binfile\shell; Flags: uninsdeletekeyifempty; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt\command; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt; ValueType: string; ValueName: ; ValueData: Decrypt for WoG; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt\command; ValueType: string; ValueName: ; ValueData: """{app}\wogfile.exe"" --decrypt ""%1"""; Tasks: endecrypt

Root: HKCR; Subkey: xmlfile\shell; Flags: uninsdeletekeyifempty; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt\command; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt; ValueType: string; ValueName: ; ValueData: Encrypt for WoG; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt\command; ValueType: string; ValueName: ; ValueData: """{app}\wogfile.exe"" --encrypt ""%1"""; Tasks: endecrypt
