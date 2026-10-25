param([string]$Environment = '.venv-filewheel')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path -LiteralPath $Environment)) {
    & py -3.14 -m venv $Environment
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.14 before setup' }
}
$python = Join-Path $Environment 'Scripts/python.exe'
& $python -c "import sys; assert sys.version_info[:2] == (3,14), 'Existing environment is not Python 3.14; choose a new directory'"
if ($LASTEXITCODE -ne 0) { throw 'Refusing to replace an existing different runtime' }
& $python -m pip install -e '.[desktop]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $python -c "from filewheel.converters import default_registry; print([(c.input_extension,c.output_extension,c.engine_id) for c in default_registry().capabilities])"
if ($LASTEXITCODE -ne 0) { throw 'Capability initialization failed' }
