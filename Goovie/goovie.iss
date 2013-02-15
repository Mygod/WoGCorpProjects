[Setup]
AppName=World of Goo Movie Maker
AppVerName=World of Goo Movie Maker v0.05 Beta
PrivilegesRequired=poweruser
DefaultDirName={pf}\WOGCorp\Goovie Maker
DefaultGroupName=WOGCorp
LicenseFile=Copying.txt
VersionInfoVersion=0.04
VersionInfoCompany=WOGCorp
ChangesAssociations=true
VersionInfoDescription=World of Goo Movie Maker
MinVersion=4.1.1998,4.0.1381sp5
SetupIconFile=src\images\goovie.ico
OutputBaseFilename=Goovie_setup
AlwaysRestart=false
CreateAppDir=true
DirExistsWarning=no

[Files]
Source: src\dist\*.*; DestDir: {app}; Flags: ignoreversion
Source: include\*.*; DestDir: {app}; Flags: ignoreversion recursesubdirs
Source: version.txt; DestDir: {app}; Flags: ignoreversion
Source: copying.txt; DestDir: {app}; Flags: ignoreversion

[Tasks]
Name: startmenuicon; Description: Create a &Start Menu icon
Name: desktopicon; Description: Create a &desktop icon; GroupDescription: Additional icons:

[Icons]
Name: {group}\World of Goo Movie Maker; Filename: {app}\goovie.exe; WorkingDir: {app}; Tasks: startmenuicon
Name: {userdesktop}\World of Goo Movie Maker; Filename: {app}\goovie.exe; WorkingDir: {app}; Tasks: desktopicon
