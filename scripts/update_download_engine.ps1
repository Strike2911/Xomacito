$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Destination = Join-Path $ProjectRoot 'bin\ytdlp'
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$Staging = Join-Path $Destination 'yt-dlp.download'
Invoke-WebRequest -Uri 'https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp' -OutFile $Staging
if ((Get-FileHash -LiteralPath $Staging -Algorithm SHA256).Hash -ne '1fa6733c37ea6fb51c99ad8fe785e7b7e5f3246c9b980230329d4fb72ed8d4d6') {
    throw 'La descarga del motor no coincide con la suma SHA256 oficial.'
}
Move-Item -LiteralPath $Staging -Destination (Join-Path $Destination 'yt-dlp.zip') -Force
Set-Content -LiteralPath (Join-Path $Destination 'ytdlp_version.txt') -Value '2026.08.19' -Encoding ASCII
