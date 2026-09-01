#define MyAppName "Xomacito"
#define MyAppVersion "4.0.17"
#define MyAppDisplayVersion "1.1"
#define MyAppExeName "Xomacito.exe"
#define ProjectRoot ".."
#define UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\{8B474FFD-6C60-4B82-889E-7DD12563E7E5}_is1"

[Setup]
AppId={{8B474FFD-6C60-4B82-889E-7DD12563E7E5}
AppName={#MyAppName}
AppVersion={#MyAppDisplayVersion}
AppVerName={#MyAppName} {#MyAppDisplayVersion} - Actualización ligera
DefaultDirName={code:GetExistingInstallDir}
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#ProjectRoot}\release
OutputBaseFilename=Xomacito-1.1-Update-Light
SetupIconFile={#ProjectRoot}\Xomacito-icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern dynamic
CloseApplications=force
CloseApplicationsFilter=Xomacito.exe,ffmpeg.exe,ffprobe.exe
RestartApplications=no
CreateUninstallRegKey=no
Uninstallable=no
MinVersion=10.0.17763
VersionInfoVersion=4.0.17.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppDisplayVersion}
VersionInfoDescription=Xomacito 1.1 - Actualización ligera

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; El ejecutable contiene el código Python actualizado. Los recursos editables
; se reemplazan aparte; Qt, FFmpeg, ONNX y los modelos persistentes se conservan.
Source: "{#ProjectRoot}\dist\Xomacito\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\dist\Xomacito\_internal\src\ui\qml\*"; DestDir: "{app}\_internal\src\ui\qml"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\dist\Xomacito\_internal\src\ui\themes\*"; DestDir: "{app}\_internal\src\ui\themes"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\dist\Xomacito\_internal\assets\*"; DestDir: "{app}\_internal\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\dist\Xomacito\_internal\premiere-panel\*"; DestDir: "{app}\_internal\premiere-panel"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\dist\Xomacito\_internal\Xomacito-icon.ico"; DestDir: "{app}\_internal"; Flags: ignoreversion

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--updated"; WorkingDir: "{app}"; Flags: shellexec skipifnotsilent skipifdoesntexist; Check: IsAutoUpdate
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Xomacito"; WorkingDir: "{app}"; Flags: shellexec postinstall skipifsilent skipifdoesntexist

[Code]
function IsAutoUpdate: Boolean;
begin
  Result := ExpandConstant('{param:XOMACITOUPDATE|0}') = '1';
end;

function GetExistingInstallDir(Param: String): String;
var
  InstallDir: String;
begin
  Result := ExpandConstant('{localappdata}\Programs\Xomacito');
  if RegQueryStringValue(HKCU, '{#UninstallKey}', 'InstallLocation', InstallDir) and
     FileExists(AddBackslash(InstallDir) + '{#MyAppExeName}') then
    Result := InstallDir;
end;

function InitializeSetup: Boolean;
var
  InstallDir: String;
begin
  InstallDir := GetExistingInstallDir('');
  Result := FileExists(AddBackslash(InstallDir) + '{#MyAppExeName}');
  if not Result then
    MsgBox(
      'Esta actualización ligera necesita una instalación existente de Xomacito. ' +
      'Descarga el instalador completo para instalarlo por primera vez.',
      mbError,
      MB_OK
    );
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  if IsAutoUpdate then
  begin
    WizardForm.PreparingLabel.Caption := 'Aplicando únicamente los archivos nuevos…';
    WizardForm.PreparingLabel.Update;
    Exec(
      ExpandConstant('{sys}\taskkill.exe'),
      '/F /IM "{#MyAppExeName}"',
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    );
    Sleep(150);
  end;
end;
