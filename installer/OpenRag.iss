; Open RAG installer. installer/build.py stages the app and passes AppVersion, Stage and OutputDir.
;
; Per-user install (no administrator rights) into %LOCALAPPDATA%\Programs\Open RAG. The documents, indexes and chats
; live in %LOCALAPPDATA%\OpenRag and are kept on uninstall. The setup is split into OpenRag-Setup.exe and .bin parts,
; because the bundled language model alone is larger than GitHub's 2 GiB limit per release file; keep them together.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef Stage
  #define Stage "build\stage"
#endif
#ifndef OutputDir
  #define OutputDir "dist"
#endif

#define AppName "Open RAG"
#define AppExe "OpenRag.exe"
#define RepoUrl "https://github.com/Carthavate/open-rag-engine"

[Setup]
AppId={{CCCFBEFA-370C-43F7-B2C9-FE2E442E1CC1}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Carthavate
AppPublisherURL={#RepoUrl}
AppSupportURL={#RepoUrl}/issues
AppUpdatesURL={#RepoUrl}/releases
VersionInfoVersion={#AppVersion}
AppCopyright=Copyright (C) 2026 Wadi Touil and Ghassen Jamoussi
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
SetupIconFile=..\desktop\src\OpenRag.App\Assets\OpenRag.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern dynamic
OutputDir={#OutputDir}
OutputBaseFilename=OpenRag-Setup
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
DiskSpanning=yes
; Below GitHub's 2 GiB per release file (2147483648 bytes). "max" no longer means 2 GiB in Inno Setup 6.5+.
DiskSliceSize=2000000000
; The app holds this mutex while it runs, so setup can ask to close it before replacing its files.
AppMutex=Local\OpenRag.SingleInstance
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; An update replaces the whole engine, so packages a new version dropped don't linger.
Type: filesandordirs; Name: "{app}\engine"

[Files]
; The model is already compressed (4-bit GGUF); storing it as is saves minutes of build time and nothing in size.
Source: "{#Stage}\engine\llm\model.gguf"; DestDir: "{app}\engine\llm"; Flags: ignoreversion nocompression
Source: "{#Stage}\*"; DestDir: "{app}"; Excludes: "\engine\llm\model.gguf"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Python writes bytecode caches next to the bundled engine while the app runs.
Type: filesandordirs; Name: "{app}\engine"

[Code]
const
  // Where the WebView2 runtime registers itself: per machine (32-bit view) or per user.
  WebView2Client = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function Registered(Root: Integer; Key: String): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(Root, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

function HasWebView2: Boolean;
begin
  Result := Registered(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2Client) or Registered(HKCU, 'Software\' + WebView2Client);
end;

{ Windows 11 always has the WebView2 runtime; an old Windows 10 may not. The app can't show its window without it. }
function InitializeSetup: Boolean;
begin
  Result := True;
  if not HasWebView2 then
    Result := SuppressibleMsgBox(
      'Open RAG needs the Microsoft Edge WebView2 Runtime, which this computer doesn''t seem to have.' + #13#10#13#10 +
      'You can install it for free from Microsoft (search for "WebView2 Runtime"), before or after Open RAG.' + #13#10#13#10 +
      'Continue installing Open RAG?', mbConfirmation, MB_YESNO, IDYES) = IDYES;
end;
