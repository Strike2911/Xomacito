#define MyAppName "Xomacito"
#define MyAppVersion "1.6.3"
#define MyAppPublisher "Xomacito"
#define MyAppExeName "Xomacito.exe"
#define ProjectRoot ".."

[Setup]
AppId={{8B474FFD-6C60-4B82-889E-7DD12563E7E5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#ProjectRoot}\release
OutputBaseFilename=Xomacito-Setup-{#MyAppVersion}
SetupIconFile={#ProjectRoot}\Xomacito-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern dynamic
WizardSizePercent=110
; Tcl/Tk y sus extensiones no deben retirarse mientras Xomacito siga abierto.
; "force" evita dejar un proceso huérfano usando una instalación parcialmente
; eliminada, incluso durante instalaciones o desinstalaciones silenciosas.
CloseApplications=force
CloseApplicationsFilter=*.*
RestartApplications=no
Uninstallable=yes
CreateUninstallRegKey=yes
MinVersion=10.0.17763
VersionInfoVersion=1.6.3.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription=Instalador de Xomacito
VersionInfoCompany={#MyAppPublisher}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\dist\Xomacito\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\_internal\bin\models\rembg"
Name: "{app}\_internal\bin\models\inspyrenet"
Name: "{app}\_internal\bin\models\rmbg2"
Name: "{app}\_internal\bin\models\upscaling"

[Icons]
Name: "{group}\Xomacito"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Desinstalar Xomacito"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Xomacito"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Xomacito"; Flags: nowait postinstall skipifsilent
; La instalación silenciosa iniciada desde Xomacito vuelve a abrir únicamente
; cuando lleva el parámetro privado del actualizador.
Filename: "{app}\{#MyAppExeName}"; Parameters: "--updated"; Flags: nowait skipifnotsilent; Check: IsAutoUpdate

[UninstallRun]
; Se ejecuta como primer paso del desinstalador. Inno espera a que taskkill
; termine antes de retirar Tcl/Tk y el resto del runtime.
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#MyAppExeName}"""; Flags: runhidden; RunOnceId: "StopXomacito"

[UninstallDelete]
; Solo elimina datos que crea Xomacito. Los videos y archivos exportados se
; guardan fuera de {app} y nunca forman parte de esta limpieza.
Type: filesandordirs; Name: "{app}\_internal\bin\models"
Type: filesandordirs; Name: "{app}\bin\models"
Type: filesandordirs; Name: "{userappdata}\Xomacito\cache"
Type: filesandordirs; Name: "{localappdata}\Xomacito\cache"
Type: files; Name: "{userappdata}\Xomacito\encoder_cache.json"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"

[Code]
function IsAutoUpdate: Boolean;
begin
  Result := ExpandConstant('{param:XOMACITOUPDATE|0}') = '1';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  if IsAutoUpdate then
  begin
    { Puente para actualizar desde 1.6.2: esa versión podía iniciar el }
    { setup antes de terminar de cerrar. Detenemos la instancia antigua antes }
    { de que Inno intente reemplazar Xomacito.exe. }
    Exec(
      ExpandConstant('{sys}\taskkill.exe'),
      '/F /IM "{#MyAppExeName}"',
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    );
    Sleep(1000);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataDir: String;
begin
  if (CurUninstallStep <> usPostUninstall) or UninstallSilent then
    exit;

  UserDataDir := ExpandConstant('{userappdata}\Xomacito');
  if DirExists(UserDataDir) and
     (MsgBox(
       '¿También deseas eliminar las preferencias, presets y temas personales de Xomacito?',
       mbConfirmation, MB_YESNO) = IDYES) then
    DelTree(UserDataDir, True, True, True);
end;
