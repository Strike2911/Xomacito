param(
    [string]$SourceBranch = "desarrollo",
    [string]$ObfuscatedBranch = "ofuscado",
    [switch]$Push
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

function Invoke-Git {
    git @args
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: $($args -join ' ')"
    }
}

function Invoke-Python {
    python @args
    if ($LASTEXITCODE -ne 0) {
        throw "python command failed: $($args -join ' ')"
    }
}

$CurrentBranch = (git branch --show-current).Trim()
if (-not $CurrentBranch) {
    throw "No se pudo detectar la rama actual."
}

$Dirty = git status --porcelain
if ($Dirty) {
    throw "El arbol de trabajo tiene cambios sin commit. Haz commit o guarda esos cambios antes de regenerar la rama ofuscada."
}

Invoke-Git rev-parse --verify $SourceBranch | Out-Null
$SourceSha = (git rev-parse $SourceBranch).Trim()
$ShortSha = $SourceSha.Substring(0, 12)

$SwitchedToGeneratedBranch = $false
$Succeeded = $false
try {
    Invoke-Git switch -C $ObfuscatedBranch $SourceBranch
    $SwitchedToGeneratedBranch = $true
    Invoke-Python scripts/obfuscate_python_tree.py

    $GeneratedChanges = git status --porcelain
    if (-not $GeneratedChanges) {
        throw "La ofuscacion no produjo cambios."
    }

    Invoke-Git add main.py launcher.py src
    Invoke-Git commit -m "Obfuscate build from $ShortSha"

    if ($Push) {
        Invoke-Git push --force-with-lease origin $ObfuscatedBranch
    }
    $Succeeded = $true
}
finally {
    if ($SwitchedToGeneratedBranch -and -not $Succeeded) {
        git reset --hard HEAD | Out-Null
    }
    git switch $CurrentBranch | Out-Null
}

Write-Host "Rama '$ObfuscatedBranch' regenerada desde '$SourceBranch' ($ShortSha)."
if ($Push) {
    Write-Host "Rama '$ObfuscatedBranch' enviada con --force-with-lease."
}
