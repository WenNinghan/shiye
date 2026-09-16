param(
    [int]$Port = 8765,
    [string]$Python = '',
    [switch]$NoBrowser,
    [switch]$SkipSetup
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
$webRoot = Join-Path $projectRoot 'web'

function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)." }
}

try {
    Set-Location -LiteralPath $projectRoot
    if (-not $SkipSetup) {
        if (-not (Test-Path -LiteralPath $venvPython)) {
            if ($Python) {
                & $Python -m venv (Join-Path $projectRoot '.venv')
                Assert-Exit 'Create Python environment'
            } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
                & uv venv --python 3.12 (Join-Path $projectRoot '.venv')
                Assert-Exit 'Create Python environment'
            } elseif (Get-Command py -ErrorAction SilentlyContinue) {
                & py -3.12 -m venv (Join-Path $projectRoot '.venv')
                Assert-Exit 'Create Python environment'
            } else {
                throw 'Install Python 3.12 + the py launcher, or uv, then retry. Alternatively pass -Python C:/path/to/python.exe.'
            }
        }
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            & uv pip install --python $venvPython -r (Join-Path $projectRoot 'backend/requirements-lock.txt')
        } else {
            & $venvPython -m pip install -r (Join-Path $projectRoot 'backend/requirements-lock.txt')
        }
        Assert-Exit 'Install Python dependencies'
        & $venvPython (Join-Path $projectRoot 'scripts/make_samples.py')
        Assert-Exit 'Generate samples'
        if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
            throw 'Install Node.js 22.12+ or 24 LTS, including npm.'
        }
        Push-Location -LiteralPath $webRoot
        try {
            & npm.cmd ci --no-fund --no-audit
            Assert-Exit 'Install frontend dependencies'
            & npm.cmd run build
            Assert-Exit 'Build frontend'
        } finally { Pop-Location }
    }
    if (-not (Test-Path -LiteralPath $venvPython)) { throw 'The .venv is missing. Run without -SkipSetup first.' }
    if (-not (Test-Path -LiteralPath (Join-Path $webRoot 'dist/index.html'))) { throw 'Frontend build missing. Run without -SkipSetup first.' }
    $url = "http://127.0.0.1:$Port"
    Write-Host "`nShiye is starting at $url" -ForegroundColor Green
    Write-Host 'Keep this console open. Ctrl+C stops the local server.'
    if (-not $NoBrowser) { Start-Process $url }
    Set-Location -LiteralPath (Join-Path $projectRoot 'backend')
    & $venvPython -m uvicorn shiye.main:app --host 127.0.0.1 --port $Port --workers 1
    Assert-Exit 'Run local server'
} catch {
    Write-Error $_
    exit 1
}
