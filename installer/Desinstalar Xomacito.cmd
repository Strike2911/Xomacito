@echo off
setlocal
set "XOMACITO_UNINSTALLER=%LOCALAPPDATA%\Programs\Xomacito\unins000.exe"

if not exist "%XOMACITO_UNINSTALLER%" (
    echo No se encontro una instalacion de Xomacito para este usuario.
    echo Tambien puedes buscar Xomacito en Configuracion ^> Aplicaciones instaladas.
    pause
    exit /b 1
)

start "" "%XOMACITO_UNINSTALLER%"
exit /b 0
