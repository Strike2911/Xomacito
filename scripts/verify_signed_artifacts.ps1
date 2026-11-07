param(
    [Parameter(Mandatory)][string]$Directory,
    [Parameter(Mandatory)][ValidateSet('application', 'installers')][string]$Phase,
    [Parameter(Mandatory)][ValidatePattern('^\d+\.\d+\.\d+(\.\d+)?$')][string]$Version,
    [switch]$Unsigned
)
$ErrorActionPreference = 'Stop'
$Expected = if ($Phase -eq 'application') {
    @('Xomacito.exe', 'XomacitoLauncher.exe')
} else {
    @("Xomacito-$Version-Setup.exe", "Xomacito-$Version-Update-Light.exe")
}
$Root = (Resolve-Path -LiteralPath $Directory -ErrorAction Stop).Path
$Items = @(Get-ChildItem -LiteralPath $Root -Force)
$Actual = @($Items | Select-Object -ExpandProperty Name)
if ($Items.Count -ne $Expected.Count -or (Compare-Object $Expected $Actual)) {
    throw "El artefacto debe contener exactamente: $($Expected -join ', ')"
}
foreach ($Name in $Expected) {
    $Item = Get-Item -LiteralPath (Join-Path $Root $Name)
    if ($Item.PSIsContainer -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "No se permiten carpetas ni enlaces: $Name"
    }
    $Info = $Item.VersionInfo
    if ($Info.ProductName -cne 'Xomacito' -or $Info.ProductVersion -cne $Version) {
        throw "Metadatos inesperados en $Name (se esperaba Xomacito $Version)"
    }
    if (-not $Unsigned) {
        $Signature = Get-AuthenticodeSignature -LiteralPath $Item.FullName
        if ($Signature.Status -ne 'Valid' -or -not $Signature.SignerCertificate -or -not $Signature.TimeStamperCertificate) {
            throw "Firma no válida o sin sello de tiempo: $Name ($($Signature.Status))"
        }
    }
    Get-FileHash -Algorithm SHA256 -LiteralPath $Item.FullName
}
