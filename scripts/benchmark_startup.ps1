param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,
    [int]$Runs = 3,
    [int]$TimeoutSeconds = 45,
    [string]$ExpectedWindowTitle = "Xomacito"
)

$ErrorActionPreference = 'Stop'
$Executable = (Resolve-Path -LiteralPath $Executable).Path
$ProcessName = [IO.Path]::GetFileNameWithoutExtension($Executable)
$Results = @()

for ($Run = 1; $Run -le $Runs; $Run++) {
    Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Executable } |
        Stop-Process -Force
    Start-Sleep -Milliseconds 600

    $Timer = [Diagnostics.Stopwatch]::StartNew()
    Start-Process -FilePath $Executable -WorkingDirectory (Split-Path $Executable) | Out-Null
    $Visible = $null
    while ($Timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        $Visible = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
            Where-Object {
                $_.MainWindowHandle -ne 0 -and
                $_.Path -eq $Executable -and
                $_.MainWindowTitle -like "$ExpectedWindowTitle*"
            } |
            Select-Object -First 1
        if ($Visible) { break }
        Start-Sleep -Milliseconds 100
    }
    $Timer.Stop()

    if (-not $Visible) {
        $Log = Join-Path (Split-Path $Executable) "Xomacito-startup-error.log"
        if (Test-Path -LiteralPath $Log) {
            throw "Xomacito no inició correctamente:`n$(Get-Content -LiteralPath $Log -Raw)"
        }
        throw "La ventana principal no apareció antes de $TimeoutSeconds segundos."
    }

    Start-Sleep -Milliseconds 1200
    $Processes = @(Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Executable })

    $Results += [pscustomobject]@{
        Run = $Run
        StartupSeconds = [math]::Round($Timer.Elapsed.TotalSeconds, 2)
        Processes = $Processes.Count
        WorkingSetMB = [math]::Round((($Processes | Measure-Object WorkingSet64 -Sum).Sum) / 1MB, 1)
        PrivateMB = [math]::Round((($Processes | Measure-Object PrivateMemorySize64 -Sum).Sum) / 1MB, 1)
    }

    $Processes | Stop-Process -Force
    Start-Sleep -Milliseconds 700
}

$Results | Format-Table -AutoSize
[pscustomobject]@{
    Executable = $Executable
    AverageStartupSeconds = [math]::Round(($Results | Measure-Object StartupSeconds -Average).Average, 2)
    AverageProcesses = [math]::Round(($Results | Measure-Object Processes -Average).Average, 1)
    AverageWorkingSetMB = [math]::Round(($Results | Measure-Object WorkingSetMB -Average).Average, 1)
} | Format-List
