#define MyAppName      "재와니의 레트로 게임 보관소"
#define MyAppNameEn    "Jaewani Retro Game Storage"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "JEWANI"
#define MyAppURL       "https://github.com/JEWANI/JRGS-launcher"
#define MyAppExeName   "JRGS.exe"

[Setup]
AppId={{B7A3F2D1-4E8C-4A9B-9F2E-1C3D5A7B9E0F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\JRGS
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=output
OutputBaseFilename=JRGS_{#MyAppVersion}_lite_setup
SetupIconFile=dist\JRGS_lite\ICON\JRGS.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 아이콘:"; Flags: unchecked
Name: "startmenuicon"; Description: "시작 메뉴에 바로가기 만들기"; GroupDescription: "추가 아이콘:"

[Files]
; 메인 실행파일 및 의존성
Source: "dist\JRGS_lite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 포함 폴더
Source: "fonts\*";         DestDir: "{app}\fonts";     Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ICON\*";          DestDir: "{app}\ICON";       Flags: ignoreversion recursesubdirs createallsubdirs
Source: "Emulators\*";     DestDir: "{app}\Emulators";  Flags: ignoreversion recursesubdirs createallsubdirs
Source: "CHANGELOG.md";    DestDir: "{app}";            Flags: ignoreversion
Source: "README.md";       DestDir: "{app}";            Flags: ignoreversion

[Dirs]
; 사용자 데이터 폴더 자동 생성
Name: "{app}\ROM_File"
Name: "{app}\GameData"
Name: "{app}\Screenshots"
Name: "{app}\Records"

[Icons]
Name: "{group}\{#MyAppName}";       Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 설치 폴더 내 사용자 생성 파일은 삭제하지 않음 (ROM, DB 등 보호)
Type: filesandordirs; Name: "{app}\__pycache__"
