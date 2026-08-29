#define MyAppName "Revsist"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Eduardo Matheus Figueira"
#define MyAppURL "https://github.com/eduardomatheusfigueira/RSACV2"
#define MyAppExeName "Revsist.exe"

[Setup]
AppId={{D37F8E45-927A-4C2E-8E11-3705C2B4E991}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_bin
OutputBaseFilename=Revsist-Setup
; Ícone do próprio Setup.exe, o mesmo do aplicativo. Antes apontava para
; `..\brand\icon.ico`, uma cópia solta que o gerador da marca não escreve e
; que por isso envelhecia sozinha; agora vem de onde a marca é gerada.
SetupIconFile=..\frontend\build\icon.ico
; Artes do assistente. Sem estas duas linhas o Inno usa as imagens de fábrica
; dele, e quem instala o programa não vê a marca em momento nenhum — foi o que
; aconteceu até aqui. A lista por escala existe para a arte não sair borrada em
; tela 150%, que é o padrão da maioria dos notebooks.
WizardImageFile=..\frontend\build\innoWizardImage.bmp,..\frontend\build\innoWizardImage2x.bmp,..\frontend\build\innoWizardImage3x.bmp
WizardSmallImageFile=..\frontend\build\innoWizardSmall.bmp,..\frontend\build\innoWizardSmall2x.bmp,..\frontend\build\innoWizardSmall3x.bmp
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\frontend\release\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
