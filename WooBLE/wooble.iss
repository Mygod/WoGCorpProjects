[Setup]
AppName=World of Goo Ball Editor
AppVerName=World of Goo Ball Editor v0.14 RC2
PrivilegesRequired=poweruser
DefaultDirName={pf}\WOGCorp\WooBLE
DefaultGroupName=WOGCorp
LicenseFile=Copying.txt
VersionInfoVersion=0.14
VersionInfoCompany=WOGCorp
ChangesAssociations=true
VersionInfoDescription=World of Goo Ball Editor
MinVersion=4.1.1998,4.0.1381sp5
SetupIconFile=src\images\wooble.ico
OutputBaseFilename=WooBLE_setup
AlwaysRestart=false
CreateAppDir=true
DirExistsWarning=no

[Files]
Source: src\dist\*.*; DestDir: {app}; Flags: ignoreversion
Source: include\*.*; DestDir: {app}; Flags: ignoreversion recursesubdirs
Source: doc\*.*; DestDir: {app}; Flags: ignoreversion recursesubdirs
Source: version.txt; DestDir: {app}; Flags: ignoreversion
Source: copying.txt; DestDir: {app}; Flags: ignoreversion

[Tasks]
Name: startmenuicon; Description: Create a &Start Menu icon
Name: desktopicon; Description: Create a &desktop icon; GroupDescription: Additional icons:

[Icons]
Name: {group}\World of Goo Ball Editor; Filename: {app}\wooble.exe; WorkingDir: {app}; Tasks: startmenuicon
Name: {userdesktop}\World of Goo Ball Editor; Filename: {app}\wooble.exe; WorkingDir: {app}; Tasks: desktopicon
