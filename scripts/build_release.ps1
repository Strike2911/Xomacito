param(
    [switch]$SkipApplicationBuild
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.tools\python311full\python.exe'
$Spec = Join-Path $ProjectRoot '.build\XomacitoInstaller.spec'
$LauncherSpec = Join-Path $ProjectRoot '.build\XomacitoLauncher.spec'
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

function Assert-ReadableApplicationSource {
    $SourceFiles = @(
        (Join-Path $ProjectRoot 'main.py'),
        (Join-Path $ProjectRoot 'launcher.py')
    ) + @(Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'src') -Recurse -File -Filter '*.py' |
        Select-Object -ExpandProperty FullName)

    $PyArmorMarkers = 'pyarmor_runtime|__pyarmor__|pytransform'
    $ObfuscatedFiles = Select-String -LiteralPath $SourceFiles -Pattern $PyArmorMarkers -CaseSensitive:$false
    if ($ObfuscatedFiles) {
        $Locations = ($ObfuscatedFiles | ForEach-Object { "$($_.Path):$($_.LineNumber)" }) -join ', '
        throw "Se detectó código ofuscado de PyArmor. El release solo acepta la fuente legible de main.py y src: $Locations"
    }

    $SpecContents = Get-Content -LiteralPath $Spec -Raw
    if ($SpecContents -notmatch 'PROJECT_ROOT / "main\.py"') {
        throw 'El spec de PyInstaller debe compilar directamente main.py desde la raíz del proyecto.'
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "No se encontró el Python de compilación: $Python"
}

Assert-ReadableApplicationSource

if (-not $SkipApplicationBuild) {
    try {
        New-Item -ItemType Directory -Path (Join-Path $BuildWork 'XomacitoInstaller') -Force | Out-Null
        & $Python -m PyInstaller --noconfirm --clean --workpath $BuildWork $Spec
        if ($LASTEXITCODE -ne 0) {
            throw 'PyInstaller no pudo crear la distribución instalada.'
        }
        $LauncherDist = Join-Path $BuildWork 'launcher-dist'
        & $Python -m PyInstaller --noconfirm --clean `
            --workpath (Join-Path $BuildWork 'launcher') `
            --distpath $LauncherDist `
            $LauncherSpec
        if ($LASTEXITCODE -ne 0) {
            throw 'PyInstaller no pudo crear el lanzador portable.'
        }
        Copy-Item -LiteralPath (Join-Path $LauncherDist 'XomacitoLauncher.exe') `
            -Destination (Join-Path $ProjectRoot 'Xomacito.exe') -Force
    }
    finally {
        Remove-VerifiedBuildWork
    }
}

$Application = Join-Path $ProjectRoot 'dist\Xomacito\Xomacito.exe'
if (-not (Test-Path -LiteralPath $Application)) {
    throw "No existe la aplicación compilada: $Application"
}

$Launcher = Join-Path $ProjectRoot 'Xomacito.exe'
if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "No existe el lanzador portable: $Launcher"
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

$Installer = Join-Path $ProjectRoot 'release\Xomacito-1.0.7-Definitive-Edition-Setup.exe'
if (-not (Test-Path -LiteralPath $Installer)) {
    throw "No se generó el instalador esperado: $Installer"
}

$UninstallerLauncher = Join-Path $ProjectRoot 'release\Desinstalar Xomacito.cmd'
Copy-Item -LiteralPath $UninstallerLauncherSource -Destination $UninstallerLauncher -Force

Get-Item -LiteralPath $Launcher, $Application, $Installer, $UninstallerLauncher |
    Select-Object FullName, Length, LastWriteTime
