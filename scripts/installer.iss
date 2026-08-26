; ── Instalador do Windows — a única definição de instalação do RSAC V2 ──
;
; O empacotamento tem dois passos, com responsabilidades que não se
; sobrepõem:
;
;   1. `frontend/electron-builder.yml` monta o diretório do aplicativo
;      (`frontend/release/win-unpacked`), com o `app.asar`, o backend
;      congelado do PyInstaller e o ícone do executável.
;   2. este arquivo transforma aquele diretório em `dist_bin/RSAC-Setup.exe`.
;
; Os dois passos são orquestrados por `scripts/build_installer.py`, que é
; quem deve ser executado. Compilar este arquivo à mão também funciona: os
; `#ifndef` abaixo dão os valores de referência quando ninguém os injeta.
;
; O nome e a versão vêm do `package.json`, que é a origem única dos dois.
; Antes estavam escritos aqui à mão, e uma versão publicada com o número da
; anterior era só uma questão de tempo.
;
; A passagem é por arquivo gerado, e não por `/D` na linha de comando: o nome
; do produto tem espaço no meio ("RSAC V2"), e valor com espaço em `/D`
; depende de como o shell, o Windows e o pré-processador do Inno concordam
; sobre aspas — três camadas para uma coisa que o Python resolve escrevendo a
; string já entre aspas. Se o arquivo não existir, os `#ifndef` abaixo
; assumem, e compilar este script à mão continua funcionando.

#if FileExists(SourcePath + "installer_defs.generated.iss")
  #include "installer_defs.generated.iss"
#endif

#ifndef MyAppName
  #define MyAppName "RSAC V2"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "2.0.0"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "Eduardo Matheus Figueira"
#endif
#ifndef MyAppExeName
  #define MyAppExeName "RSAC V2.exe"
#endif
#ifndef UnpackedDir
  #define UnpackedDir "..\frontend\release\win-unpacked"
#endif

#define MyAppURL "https://github.com/eduardomatheusfigueira/RSACV2"

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
OutputBaseFilename=RSAC-Setup
; Mesmo ícone do executável do aplicativo (`electron-builder.yml`), gerado por
; `brand/generate_brand_assets.py` a partir da geometria da marca. Havia um
; segundo `.ico` em `brand/`, produzido pelo antigo `build_executables.py` a
; partir de um único PNG reescalado: com aquele script fora, ele ficou sem
; gerador — e o instalador exibia um ícone diferente do que o usuário veria
; depois no atalho.
SetupIconFile=..\frontend\build\icon.ico
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
Source: "{#UnpackedDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
