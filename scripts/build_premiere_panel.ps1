$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PanelRoot = Join-Path $ProjectRoot 'premiere-panel'
$ManifestPath = Join-Path $PanelRoot 'manifest.json'
$PackagePath = Join-Path $PanelRoot 'Xomacito-Link.ccx'
$TemporaryZip = Join-Path $PanelRoot 'Xomacito-Link.zip'
$ValidationRoot = Join-Path $ProjectRoot '.build\premiere-panel-validation'
$PackageFiles = @(
    (Join-Path $PanelRoot 'manifest.json'),
    (Join-Path $PanelRoot 'index.html'),
    (Join-Path $PanelRoot 'index.js'),
    (Join-Path $PanelRoot 'styles.css')
)

foreach ($File in $PackageFiles) {
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
        throw "Falta un archivo obligatorio del panel: $File"
    }
}

$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($Manifest.manifestVersion -ne 5 -or $Manifest.host.app -ne 'premierepro') {
    throw 'El panel debe usar Manifest v5 y apuntar únicamente a Premiere.'
}
if ($Manifest.requiredPermissions.localFileSystem -ne 'request') {
    throw 'El panel debe solicitar sólo acceso explícito a una carpeta.'
}
if ($Manifest.requiredPermissions.PSObject.Properties.Name -contains 'network') {
    throw 'Xomacito Link no debe declarar acceso de red.'
}

foreach ($GeneratedPath in @($TemporaryZip, $PackagePath)) {
    if (Test-Path -LiteralPath $GeneratedPath) {
        Remove-Item -LiteralPath $GeneratedPath -Force
    }
}

Compress-Archive -LiteralPath $PackageFiles -DestinationPath $TemporaryZip -CompressionLevel Optimal
Move-Item -LiteralPath $TemporaryZip -Destination $PackagePath

$ResolvedProject = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\') + '\'
$ResolvedValidation = [IO.Path]::GetFullPath($ValidationRoot)
if (-not $ResolvedValidation.StartsWith($ResolvedProject, [StringComparison]::OrdinalIgnoreCase)) {
    throw "La validación quedó fuera del proyecto: $ResolvedValidation"
}
if (Test-Path -LiteralPath $ValidationRoot) {
    Remove-Item -LiteralPath $ValidationRoot -Recurse -Force
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($PackagePath, $ValidationRoot)
try {
    $PackagedManifest = Join-Path $ValidationRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $PackagedManifest -PathType Leaf)) {
        throw 'El paquete CCX no contiene manifest.json en su raíz.'
    }
    $Packaged = Get-Content -LiteralPath $PackagedManifest -Raw | ConvertFrom-Json
    if ($Packaged.id -ne $Manifest.id -or $Packaged.version -ne $Manifest.version) {
        throw 'El manifest incluido no coincide con el panel validado.'
    }
}
finally {
    if (Test-Path -LiteralPath $ValidationRoot) {
        Remove-Item -LiteralPath $ValidationRoot -Recurse -Force
    }
}

Get-Item -LiteralPath $PackagePath | Select-Object FullName, Length, LastWriteTime
