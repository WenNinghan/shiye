param(
    [string]$RuntimeRoot = '',
    [ValidateSet('cpu')][string]$Device = 'cpu',
    [switch]$SkipWarmup
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)." }
}

$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $RuntimeRoot) {
    $projectDrive = (Get-Item -LiteralPath $projectRoot).PSDrive
    if ($projectDrive.Free -ge 8GB) {
        $RuntimeRoot = Join-Path $projectRoot '.formula-runtime'
    } else {
        $drive = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Free -ge 8GB } | Sort-Object Free -Descending | Select-Object -First 1
        if (-not $drive) { throw 'Formula setup needs about 4 GB free space on one drive.' }
        $RuntimeRoot = Join-Path $drive.Root 'ShiyeFormulaRuntime'
    }
}
$RuntimeRoot = [IO.Path]::GetFullPath($RuntimeRoot)
$venv = Join-Path $RuntimeRoot 'venv'
$venvPython = Join-Path $venv 'Scripts/python.exe'
$cache = Join-Path $RuntimeRoot 'cache'
$temp = Join-Path $RuntimeRoot 'tmp'
New-Item -ItemType Directory -Path $RuntimeRoot,$cache,$temp -Force | Out-Null
$env:TEMP = $temp
$env:TMP = $temp

if (-not (Test-Path -LiteralPath $venvPython)) {
    $corePython = Join-Path $projectRoot '.venv/Scripts/python.exe'
    $basePython = ''
    if (Test-Path -LiteralPath $corePython) {
        $basePython = (& $corePython -c "import pathlib,sys; print(pathlib.Path(sys.base_prefix)/'python.exe')").Trim()
    }
    if ($basePython -and (Test-Path -LiteralPath $basePython)) {
        if ($uvCommand) {
            & uv venv --python $basePython $venv
        } else {
            & $basePython -m venv $venv
        }
        Assert-Exit 'Create formula environment'
    } elseif ($uvCommand) {
        $pythonRoot = Join-Path $RuntimeRoot 'python'
        & uv python install 3.12 --install-dir $pythonRoot --no-registry --no-bin
        Assert-Exit 'Install Python 3.12'
        $basePython = (Get-ChildItem -LiteralPath $pythonRoot -Filter python.exe -Recurse -File | Select-Object -First 1).FullName
        & uv venv --python $basePython $venv
        Assert-Exit 'Create formula environment'
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv $venv
        Assert-Exit 'Create formula environment'
    } else {
        throw 'Install Python 3.12 (or uv), run the core setup once, then retry.'
    }
}

if ($uvCommand) {
    & uv pip install --cache-dir (Join-Path $RuntimeRoot 'uv-cache') --python $venvPython -r (Join-Path $projectRoot 'backend/requirements-formula.txt')
} else {
    & $venvPython -m pip install --disable-pip-version-check -r (Join-Path $projectRoot 'backend/requirements-formula.txt')
}
Assert-Exit 'Install formula dependencies'

$env:PADDLE_PDX_CACHE_HOME = $cache
$env:PADDLE_PDX_MODEL_SOURCE = 'BOS'
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = 'True'
if (-not $SkipWarmup) {
    Write-Host 'Downloading and loading formula + layout models for the first time...' -ForegroundColor Cyan
    & $venvPython (Join-Path $projectRoot 'scripts/formula_engine.py') --warm --model PP-FormulaNet_plus-M --device $Device
    Assert-Exit 'Warm formula engine'
}

$data = Join-Path $projectRoot '.data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
$config = [ordered]@{
    python = $venvPython
    cache = $cache
    device = $Device
    model = 'PP-FormulaNet_plus-M'
} | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $data 'formula-runtime.json'), $config, [Text.UTF8Encoding]::new($false))
Write-Host "Formula engine installed at $RuntimeRoot" -ForegroundColor Green
Write-Host 'Restart Shiye to enable academic formula mode.'
