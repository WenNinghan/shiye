[CmdletBinding(SupportsShouldProcess)]
param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$expectedPython = (Join-Path $projectRoot '.venv/Scripts/python.exe').Replace('/', '\')
$listeners = @(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if (-not $listeners.Count) {
    Write-Host "No Shiye listener at 127.0.0.1:$Port."
    exit 0
}
foreach ($listener in $listeners) {
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    $commandLine = ([string]$candidate.CommandLine).Replace('/', '\')
    $expectedPattern = '^"?' + [regex]::Escape($expectedPython) + '"?\s+-m\s+uvicorn\s+shiye\.main:app(?:\s|$)'
    if ($commandLine -notmatch $expectedPattern) {
        # Windows venv/python.exe can be a launcher; validate its exact parent.
        $launcher = Get-CimInstance Win32_Process -Filter "ProcessId=$($candidate.ParentProcessId)" -ErrorAction SilentlyContinue
        $launcherCommand = ([string]$launcher.CommandLine).Replace('/', '\')
        if ($launcherCommand -notmatch $expectedPattern -or $commandLine -notmatch '\s-m\s+uvicorn\s+shiye\.main:app(?:\s|$)') {
            throw "Port $Port belongs to a different process. Nothing was stopped."
        }
    }
    if ($PSCmdlet.ShouldProcess("Shiye PID $($candidate.ProcessId) at 127.0.0.1:$Port", 'Stop local server')) {
        Stop-Process -Id $candidate.ProcessId
        Write-Host 'Shiye stopped. Application data was preserved.'
    }
}
