[Setup]
AppName=World of Goo Level Editor
AppVerName=World of Goo Level Editor 0.75 Beta (Patch)
PrivilegesRequired=poweruser
DefaultDirName={pf}\WOGCorp\WoGEditor
DefaultGroupName=WOGCorp
LicenseFile=Copying.txt
VersionInfoVersion=0.7.5
VersionInfoCompany=WOGCorp
ChangesAssociations=true
VersionInfoDescription=World of Goo Level Editor
MinVersion=4.1.1998,4.0.1381sp5
SetupIconFile=src\images\wogedit.ico
OutputBaseFilename=WooGLE_patch
AlwaysRestart=false
CreateAppDir=true
DirExistsWarning=no

[Files]
Source: src\dist\wogeditor.exe; DestDir: {app}; Flags: ignoreversion
Source: src\dist\library.zip; DestDir: {app}; Flags: ignoreversion
Source: include\*.*; DestDir: {app}; Flags: ignoreversion recursesubdirs
Source: version.txt; DestDir: {app}; Flags: ignoreversion

[Tasks]
Name: startmenuicon; Description: Create a &Start Menu icon
Name: desktopicon; Description: Create a &desktop icon; GroupDescription: Additional icons:
Name: endecrypt; Description: Add &En/Decrypt to Right-Click menu; Flags: unchecked; GroupDescription: Windows Shell Extensions:

[Icons]
Name: {group}\World of Goo Level Editor; Filename: {app}\wogeditor.exe; WorkingDir: {app}; Tasks: startmenuicon
Name: {userdesktop}\World of Goo Level Editor; Filename: {app}\wogeditor.exe; WorkingDir: {app}; IconIndex: 0; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: .bin; ValueType: string; ValueName: ; ValueData: "binfile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: binfile; ValueType: string; ValueName: ; ValueData: Binary File; Flags: uninsdeletekey
Root: HKCR; Subkey: binfile\shell; Flags: uninsdeletekeyifempty; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt\command; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt; ValueType: string; ValueName: ; ValueData: Decrypt for World of Goo; Tasks: endecrypt
Root: HKCR; Subkey: binfile\shell\wog.decrypt\command; ValueType: string; ValueName: ; ValueData: """{app}\wogfile.exe"" --decrypt ""%1"""; Tasks: endecrypt

Root: HKCR; Subkey: xmlfile\shell; Flags: uninsdeletekeyifempty; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt\command; Flags: uninsdeletekey; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt; ValueType: string; ValueName: ; ValueData: Encrypt for World of Goo; Tasks: endecrypt
Root: HKCR; Subkey: xmlfile\shell\wog.encrypt\command; ValueType: string; ValueName: ; ValueData: """{app}\wogfile.exe"" --encrypt ""%1"""; Tasks: endecrypt
