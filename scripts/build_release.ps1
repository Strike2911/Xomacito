param(
    [switch]$SkipApplicationBuild
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.tools\python311full\python.exe'
$Spec = Join-Path $ProjectRoot '.build\XomacitoInstaller.spec'
$InstallerScript = Join-Path $ProjectRoot 'installer\Xomacito.iss'
$UninstallerLauncherSource = Join-Path $ProjectRoot 'installer\Desinstalar Xomacito.cmd'
$BuildWork = Join-Path $ProjectRoot '.build\work'

function Remove-VerifiedBuildWork {
    if (-not (Test-Path -LiteralPath $BuildWork)) {
        return
    }

    $ResolvedRoot = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\') + '\'
    $ResolvedWork = [IO.Path]::GetFullPath($BuildWork)
    if (-not $ResolvedWork.StartsWith($ResolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "La carpeta temporal quedo fuera del proyecto: $ResolvedWork"
    }

    Remove-Item -LiteralPath $ResolvedWork -Recurse -Force
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "No se encontró el Python de compilación: $Python"
}

if (-not $SkipApplicationBuild) {
    try {
        & $Python -m PyInstaller --noconfirm --clean --workpath $BuildWork $Spec
        if ($LASTEXITCODE -ne 0) {
            throw 'PyInstaller no pudo crear la distribución instalada.'
        }
    }
    finally {
        Remove-VerifiedBuildWork
    }
}

$Application = Join-Path $ProjectRoot 'dist\Xomacito\Xomacito.exe'
if (-not (Test-Path -LiteralPath $Application)) {
    throw "No existe la aplicación compilada: $Application"
}

$CompilerCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    (Join-Path ${env:ProgramFiles} 'Inno Setup 7\ISCC.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

$Compiler = $CompilerCandidates | Select-Object -First 1
if (-not $Compiler) {
    $Command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($Command) { $Compiler = $Command.Source }
}

if (-not $Compiler) {
    throw 'No se encontró Inno Setup 6 o 7.'
}

New-Item -ItemType Directory -Path (Join-Path $ProjectRoot 'release') -Force | Out-Null
& $Compiler $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw 'Inno Setup no pudo crear el instalador.'
}

$Installer = Join-Path $ProjectRoot 'release\Xomacito-2.1-Setup.exe'
if (-not (Test-Path -LiteralPath $Installer)) {
    throw "No se generó el instalador esperado: $Installer"
}

$UninstallerLauncher = Join-Path $ProjectRoot 'release\Desinstalar Xomacito.cmd'
Copy-Item -LiteralPath $UninstallerLauncherSource -Destination $UninstallerLauncher -Force

Get-Item -LiteralPath $Application, $Installer, $UninstallerLauncher |
    Select-Object FullName, Length, LastWriteTime
