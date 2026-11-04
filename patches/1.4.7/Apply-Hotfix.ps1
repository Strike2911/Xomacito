param(
    [Parameter(Mandatory=$true)][string]$InstallationPath,
    [switch]$CheckOnly,
    [switch]$Restore
)
$ErrorActionPreference = 'Stop'
$InstallRoot = (Resolve-Path -LiteralPath $InstallationPath).Path
$QmlRoot = Join-Path $InstallRoot '_internal/src/ui/qml'
$Manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw | ConvertFrom-Json
$BackupRoot = Join-Path $InstallRoot 'hotfix-backup-2026-11-04'
if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot 'Xomacito.exe'))) { throw 'No se encontró Xomacito.exe.' }
if ((Get-FileHash -LiteralPath (Join-Path $InstallRoot 'Xomacito.exe') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Manifest.executableSha256) {
    throw 'Este ejecutable no coincide con el Xomacito 1.4.7 verificado. No se modificó la instalación.'
}
if (-not $CheckOnly -and (Get-Process Xomacito -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq (Join-Path $InstallRoot 'Xomacito.exe') })) {
    throw 'Cierra Xomacito antes de aplicar o restaurar la corrección.'
}
# Validate every path and hash before changing any installation file.
foreach ($Entry in $Manifest.files) {
    $Target = [IO.Path]::GetFullPath((Join-Path $QmlRoot $Entry.path))
    if (-not $Target.StartsWith($QmlRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Ruta fuera de la instalación.' }
    $Current = if (Test-Path -LiteralPath $Target) { (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
    if ($Current -ne $Entry.before -and $Current -ne $Entry.after) { throw "Archivo distinto del 1.4.7 verificado: $($Entry.path). No se modificó la instalación." }
    $Payload = Join-Path (Join-Path $PSScriptRoot 'qml') $Entry.path
    if ((Get-FileHash -LiteralPath $Payload -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Entry.after) { throw "Corrección dañada: $($Entry.path)" }
    if ($Restore -and $Entry.before) {
        $BackupFile = Join-Path $BackupRoot $Entry.path
        if (-not (Test-Path -LiteralPath $BackupFile)) { throw "Falta el respaldo: $BackupFile" }
        if ((Get-FileHash -LiteralPath $BackupFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Entry.before) { throw "Respaldo distinto: $BackupFile" }
    }
}
if ($CheckOnly) { Write-Output 'Instalación y corrección verificadas. No se cambió ningún archivo.'; exit 0 }
if (-not $Restore) {
    foreach ($Entry in $Manifest.files) {
        $Target = Join-Path $QmlRoot $Entry.path
        $BackupFile = Join-Path $BackupRoot $Entry.path
        if ($Entry.before -and -not (Test-Path -LiteralPath $BackupFile)) {
            if ((Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Entry.before) { throw "No existe respaldo del original: $($Entry.path)" }
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BackupFile) | Out-Null
            Copy-Item -LiteralPath $Target -Destination $BackupFile
        }
    }
}
$Written = @()
try {
    foreach ($Entry in $Manifest.files) {
        $Target = Join-Path $QmlRoot $Entry.path
        if ($Restore -and -not $Entry.before) {
            # Nonrecursive removal, restricted to the new files in the verified manifest.
            if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target }
        } else {
            $Payload = if ($Restore) { Join-Path $BackupRoot $Entry.path } else { Join-Path (Join-Path $PSScriptRoot 'qml') $Entry.path }
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
            Copy-Item -LiteralPath $Payload -Destination ($Target + '.hotfix-tmp') -Force
            Move-Item -LiteralPath ($Target + '.hotfix-tmp') -Destination $Target -Force
        }
        $Written += $Entry
    }
} catch {
    if (-not $Restore) {
        foreach ($Entry in $Written) {
            $Target = Join-Path $QmlRoot $Entry.path
            if ($Entry.before) { Copy-Item -LiteralPath (Join-Path $BackupRoot $Entry.path) -Destination $Target -Force }
            elseif (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target }
        }
    }
    throw
}
Write-Output $(if ($Restore) { 'Interfaz original restaurada.' } else { "Corrección aplicada. Respaldo: $BackupRoot" })
