param(
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [string]$CorePython = '',
    [string]$FormulaPython = '',
    [string]$FormulaCache = '',
    [ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version = '0.3.1',
    [switch]$WithFormula
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$buildRoot = [IO.Path]::GetFullPath($OutputRoot)
if ($buildRoot -eq [IO.Path]::GetPathRoot($buildRoot) -or $buildRoot -eq $projectRoot) { throw 'Choose a dedicated build subdirectory.' }
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
if (-not $CorePython) { $CorePython = Join-Path $projectRoot '.venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $CorePython)) { throw 'Core Python 3.12 build environment missing.' }
function Assert-Step([string]$name) { if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" } }
Push-Location -LiteralPath $projectRoot
try {
    Push-Location web
    try { & npm.cmd ci --no-audit --no-fund; Assert-Step 'Frontend install'; & npm.cmd run build; Assert-Step 'Frontend build' }
    finally { Pop-Location }
    & $CorePython -m PyInstaller --noconfirm --distpath (Join-Path $buildRoot 'engine') --workpath (Join-Path $buildRoot 'core-work') packaging/backend.spec
    Assert-Step 'Core bundle'
    $releaseRoot = Join-Path $buildRoot 'release'
    New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
    if ($WithFormula) {
        if (-not $FormulaPython -or -not $FormulaCache) { throw 'WithFormula requires FormulaPython and FormulaCache.' }
        & $FormulaPython -m PyInstaller --noconfirm --distpath (Join-Path $buildRoot 'formula') --workpath (Join-Path $buildRoot 'formula-work') packaging/formula.spec
        Assert-Step 'Formula bundle'
        & $CorePython packaging/build_model_pack.py --runtime (Join-Path $buildRoot 'formula/shiye-formula') --cache $FormulaCache --output (Join-Path $releaseRoot "Shiye-Formula-$Version-Windows-x64.shiye-model") --manifest desktop/trusted-models.json --version $Version
        Assert-Step 'Model package'
    }
    $env:SHIYE_ENGINE_DIR = Join-Path $buildRoot 'engine/shiye-engine'
    $env:CSC_IDENTITY_AUTO_DISCOVERY = 'false'
    Push-Location desktop
    try {
        & npm.cmd ci --no-audit --no-fund; Assert-Step 'Desktop install'
        & npm.cmd run dist -- "--config.directories.output=$releaseRoot" "--config.extraMetadata.version=$Version"; Assert-Step 'Desktop installer'
    } finally { Pop-Location }
    if (-not (Test-Path -LiteralPath (Join-Path $releaseRoot 'win-unpacked/resources/engine/shiye-engine.exe'))) { throw 'Packaged engine resource is missing.' }
    Copy-Item -LiteralPath (Join-Path $projectRoot 'docs/desktop-guide.md') -Destination (Join-Path $releaseRoot '使用说明.md')
    Write-Host "Output: $releaseRoot"
} finally { Pop-Location }
