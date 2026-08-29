$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.tools\python311full\python.exe'
$PyArmor = Join-Path $ProjectRoot '.tools\python311full\Scripts\pyarmor.exe'
$ProtectedRoot = Join-Path $ProjectRoot '.build\public-hardened\protected'
$RuntimeInput = Join-Path $ProjectRoot '.build\public-hardened\runtime-input\xomacito_runtime.py'
$RuntimeOutput = Join-Path $ProjectRoot '.build\public-hardened\runtime-output'
$WorkPath = Join-Path $ProjectRoot '.build\work-public'
$Spec = Join-Path $ProjectRoot '.build\XomacitoPublic.spec'

if (-not (Test-Path -LiteralPath $Python)) { throw 'Falta el Python privado de compilación.' }
if (-not (Test-Path -LiteralPath $PyArmor)) { throw 'Falta PyArmor para proteger el cargador público.' }

& $Python (Join-Path $PSScriptRoot 'build_hardened_source.py')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo cifrar la fuente pública.' }

& $PyArmor gen -O $RuntimeOutput $RuntimeInput
if ($LASTEXITCODE -ne 0) { throw 'No se pudo ofuscar el cargador de la versión pública.' }

Copy-Item -LiteralPath (Join-Path $RuntimeOutput 'xomacito_runtime.py') -Destination $ProtectedRoot -Force
$RuntimePackage = Get-ChildItem -LiteralPath $RuntimeOutput -Directory -Filter 'pyarmor_runtime_*' | Select-Object -First 1
if (-not $RuntimePackage) { throw 'PyArmor no generó su runtime nativo.' }
Copy-Item -LiteralPath $RuntimePackage.FullName -Destination $ProtectedRoot -Recurse -Force

& $Python -m PyInstaller --noconfirm --clean --workpath $WorkPath $Spec
if ($LASTEXITCODE -ne 0) { throw 'No se pudo compilar la versión pública protegida.' }

$Application = Join-Path $ProjectRoot 'dist\Xomacito\Xomacito.exe'
$SelfTest = Start-Process -FilePath $Application -ArgumentList '--self-test' -Wait -PassThru -WindowStyle Hidden
if ($SelfTest.ExitCode -ne 0) { throw 'La versión pública protegida no superó el auto-test.' }

& (Join-Path $PSScriptRoot 'build_release.ps1') -SkipApplicationBuild
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el instalador público.' }

$Installer = Join-Path $ProjectRoot 'release\Xomacito-1.1-Setup.exe'
Get-FileHash -Algorithm SHA256 -LiteralPath $Installer
