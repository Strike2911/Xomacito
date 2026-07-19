[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')

function Assert-ProjectChild {
    param([Parameter(Mandatory)][string]$Path)

    $Resolved = [IO.Path]::GetFullPath($Path)
    $Prefix = $ProjectRoot + '\'
    if (-not $Resolved.StartsWith($Prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "La ruta de limpieza quedo fuera de Xomacito: $Resolved"
    }
    return $Resolved
}

$Targets = @(
    '.build\work',
    '.tools\python311',
    '.tools\get-pip.py',
    '.tools\innosetup-6.7.3.exe',
    '.tools\python-3.11.9-amd64.exe',
    '.tools\python-3.11.9-embed-amd64.zip',
    'dist\Xomacito.exe',
    'dist\XomacitoTitleFixer.exe',
    '__pycache__'
) | ForEach-Object { Join-Path $ProjectRoot $_ }

foreach ($SourceFolder in @('src', 'tests')) {
    $SourcePath = Join-Path $ProjectRoot $SourceFolder
    if (Test-Path -LiteralPath $SourcePath) {
        $Targets += Get-ChildItem -LiteralPath $SourcePath -Recurse -Force -Directory `
            -Filter '__pycache__' -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty FullName
    }
}

$RemovedBytes = [int64]0
$RemovedItems = 0
foreach ($Target in ($Targets | Select-Object -Unique)) {
    $SafeTarget = Assert-ProjectChild $Target
    if (-not (Test-Path -LiteralPath $SafeTarget)) {
        continue
    }

    $Item = Get-Item -LiteralPath $SafeTarget -Force
    if ($Item.PSIsContainer) {
        $Size = (Get-ChildItem -LiteralPath $SafeTarget -Recurse -Force -File `
            -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    }
    else {
        $Size = $Item.Length
    }

    if ($PSCmdlet.ShouldProcess($SafeTarget, 'Eliminar artefacto temporal u obsoleto')) {
        Remove-Item -LiteralPath $SafeTarget -Recurse -Force
        $RemovedBytes += [int64]$Size
        $RemovedItems++
    }
}

[pscustomobject]@{
    RemovedItems = $RemovedItems
    RecoveredMiB = [math]::Round($RemovedBytes / 1MB, 2)
    PreservedRuntime = (Join-Path $ProjectRoot '.tools\python311full')
    PreservedPortableApp = (Join-Path $ProjectRoot 'dist\Xomacito')
    PreservedInstaller = (Join-Path $ProjectRoot 'release\Xomacito-Setup-1.6.0.exe')
}
