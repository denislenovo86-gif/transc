; ============================================
; TranscribeFlow — Установщик v2.0
; ============================================

[Setup]
AppName=TranscribeFlow
AppVersion=2.0
AppPublisher=TranscribeFlow
DefaultDirName={commonpf}\TranscribeFlow
DefaultGroupName=TranscribeFlow
UninstallDisplayIcon={app}\TranscribeFlow.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=TranscribeFlow_Setup
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
; Копируем ВСЮ папку dist\TranscribeFlow
Source: "dist\TranscribeFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Копируем модель Vosk
Source: "C:\Users\Pritvor\Desktop\transc\vosk-model-small-ru-0.22\*"; DestDir: "{app}\vosk-model-small-ru-0.22"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\TranscribeFlow"; Filename: "{app}\TranscribeFlow.exe"
Name: "{group}\Удалить TranscribeFlow"; Filename: "{uninstallexe}"
Name: "{commondesktop}\TranscribeFlow"; Filename: "{app}\TranscribeFlow.exe"

[Run]
Filename: "{app}\TranscribeFlow.exe"; Description: "Запустить TranscribeFlow"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}"