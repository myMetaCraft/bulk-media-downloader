; The Windows installer: iscc /DAppVersion=0.1.0 BulkMediaDownloader.iss (after stage.ps1)
; Installs for the current user only (no administrator prompt) into %LOCALAPPDATA%\Programs\Bulk Media Downloader.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{B7D2E4C9-5A13-4F68-9E2B-71C0D8A3F5E6}
AppName=Bulk Media Downloader
AppVersion={#AppVersion}
AppVerName=Bulk Media Downloader {#AppVersion}
AppPublisher=Bulk Media Downloader
AppPublisherURL=https://bulkmediadownloader.com
AppSupportURL=https://bulkmediadownloader.com
DefaultDirName={localappdata}\Programs\Bulk Media Downloader
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\build\installer
OutputBaseFilename=BulkMediaDownloader-Setup-{#AppVersion}
SetupIconFile=bmd.ico
UninstallDisplayIcon={app}\bmd.ico
UninstallDisplayName=Bulk Media Downloader
WizardStyle=modern
Compression=lzma2/normal
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Put Bulk Media Downloader on the desktop"; GroupDescription: "Shortcuts:"

[InstallDelete]
; a new version replaces the program files (settings and the fetched download engine live in %LOCALAPPDATA%\Bulk Media Downloader)
Type: filesandordirs; Name: "{app}\app"
Type: filesandordirs; Name: "{app}\python"

[Files]
Source: "..\build\BulkMediaDownloader\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Bulk Media Downloader"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\bmd.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\bmd.ico"; Comment: "Download videos and photos from many links at once"
Name: "{autodesktop}\Bulk Media Downloader"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\bmd.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\bmd.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\app\bmd.py"""; WorkingDir: "{app}\app"; Description: "Open Bulk Media Downloader now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
