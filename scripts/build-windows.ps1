param(
    [string]$Python = '',
    [string]$LibreOfficeDirectory = '',
    [string]$PandocDirectory = ''
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'Windows-only build: run this script on Windows 11, not Kubuntu or WSL'
}
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$environmentDirectory = Join-Path $root '.venv-build314'
$buildPython = Join-Path $environmentDirectory 'Scripts\python.exe'
$distribution = Join-Path $root 'dist\Filewheel'
$lock = Join-Path $root 'packaging\windows-py314.lock'
$portableSource = $null
if ($LibreOfficeDirectory) {
    $portableSource = (Resolve-Path -LiteralPath $LibreOfficeDirectory).Path
    if (-not (Test-Path -LiteralPath $portableSource -PathType Container)) {
        throw 'LibreOfficeDirectory must be the complete extracted installation directory'
    }
    $sourceFull = [IO.Path]::GetFullPath($portableSource).TrimEnd('\')
    $distFull = [IO.Path]::GetFullPath($distribution).TrimEnd('\')
    if ($sourceFull.Equals($distFull, [StringComparison]::OrdinalIgnoreCase) -or
        $sourceFull.StartsWith($distFull + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $distFull.StartsWith($sourceFull + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'LibreOffice source and build output must not contain each other'
    }
}
$pandocSource = $null
if ($PandocDirectory) {
    $pandocSource = (Resolve-Path -LiteralPath $PandocDirectory).Path
    if (-not (Test-Path -LiteralPath $pandocSource -PathType Container)) {
        throw 'PandocDirectory must be the complete extracted flat release directory'
    }
    $pandocFull = [IO.Path]::GetFullPath($pandocSource).TrimEnd('\')
    $distFull = [IO.Path]::GetFullPath($distribution).TrimEnd('\')
    if ($pandocFull.Equals($distFull, [StringComparison]::OrdinalIgnoreCase) -or
        $pandocFull.StartsWith($distFull + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $distFull.StartsWith($pandocFull + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Pandoc source and build output must not contain each other'
    }
}
$checkPython = "import sys,struct,sysconfig; assert sys.platform=='win32' and sys.implementation.name=='cpython' and sys.version_info[:2]==(3,14) and struct.calcsize('P')==8 and sysconfig.get_platform()=='win-amd64' and not sysconfig.get_config_var('Py_GIL_DISABLED'), 'Windows CPython 3.14 amd64 is required'"
if (Test-Path -LiteralPath $environmentDirectory) {
    if (-not (Test-Path -LiteralPath $buildPython -PathType Leaf)) {
        throw 'Existing .venv-build314 is not a usable environment; refusing to overwrite it'
    }
} else {
    if ($Python) {
        & $Python -c $checkPython
        if ($LASTEXITCODE -ne 0) { throw 'Selected Python is not Windows CPython 3.14 amd64' }
        & $Python -m venv $environmentDirectory
    } else {
        $launcher = Get-Command py.exe -ErrorAction Stop
        & $launcher.Source -3.14 -c $checkPython
        if ($LASTEXITCODE -ne 0) { throw 'Install Windows CPython 3.14 amd64 or supply -Python' }
        & $launcher.Source -3.14 -m venv $environmentDirectory
    }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the dedicated build environment' }
}
& $buildPython -c $checkPython
if ($LASTEXITCODE -ne 0) { throw 'Existing build environment has the wrong interpreter; it was preserved' }
function Invoke-BuildPython {
    param([string[]]$PythonArguments)
    & $buildPython @PythonArguments
    if ($LASTEXITCODE -ne 0) { throw ('Build command failed: ' + ($PythonArguments -join ' ')) }
}
Push-Location $root
try {
    Invoke-BuildPython -PythonArguments @('-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:', '-r', $lock)
    Invoke-BuildPython -PythonArguments @('-m', 'pip', 'install', '--no-deps', '--no-build-isolation', $root)
    Invoke-BuildPython -PythonArguments @('-m', 'pip', 'check')
    if ($portableSource) {
        # G12 validator accepts a complete flat or PortableApps installation;
        # copying only soffice.exe is never sufficient.
        Invoke-BuildPython -PythonArguments @('-m', 'filewheel.libreoffice_bundle', '--validate', $portableSource, '--output-root', $distribution)
    }
    if ($pandocSource) {
        # Execute real reader/writer probes before PyInstaller rebuilds its output.
        Invoke-BuildPython -PythonArguments @('-m', 'filewheel.pandoc_tool', '--validate', $pandocSource, '--output-root', $distribution)
    }
    Invoke-BuildPython -PythonArguments @('-m', 'PyInstaller', '--clean', '--noconfirm', '--distpath', (Join-Path $root 'dist'), '--workpath', (Join-Path $root 'build\pyinstaller'), (Join-Path $root 'packaging\Filewheel.spec'))
    if ($portableSource) {
        $tools = Join-Path $distribution 'tools'
        [void][IO.Directory]::CreateDirectory($tools)
        $destination = Join-Path $tools 'libreoffice'
        if (Test-Path -LiteralPath $destination) { throw 'Refusing to replace an existing bundled LibreOffice directory' }
        Copy-Item -LiteralPath $portableSource -Destination $destination -Recurse
        Invoke-BuildPython -PythonArguments @('-m', 'filewheel.libreoffice_bundle', '--validate', $destination)
    }
    if ($pandocSource) {
        $tools = Join-Path $distribution 'tools'
        [void][IO.Directory]::CreateDirectory($tools)
        $pandocDestination = Join-Path $tools 'pandoc'
        if (Test-Path -LiteralPath $pandocDestination) { throw 'Refusing to replace an existing bundled Pandoc directory' }
        # Preserve the complete release, including COPYRIGHT.txt, COPYING.rtf and MANUAL.html.
        Copy-Item -LiteralPath $pandocSource -Destination $pandocDestination -Recurse
        Invoke-BuildPython -PythonArguments @('-m', 'filewheel.pandoc_tool', '--validate', $pandocDestination)
    }
    $executable = Join-Path $distribution 'Filewheel.exe'
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw 'PyInstaller did not create Filewheel.exe' }
    $selfTest = Start-Process -FilePath $executable -ArgumentList @('--self-test') -WorkingDirectory $distribution -PassThru
    if (-not $selfTest.WaitForExit(180000)) {
        & taskkill.exe /PID $selfTest.Id /T /F | Out-Null
        throw 'Frozen self-test exceeded its three-minute deadline'
    }
    if ($selfTest.ExitCode -ne 0) { throw ('Frozen self-test failed with exit code ' + $selfTest.ExitCode) }
    $freeze = & $buildPython -m pip freeze --all
    if ($LASTEXITCODE -ne 0) { throw 'Could not record installed build dependencies' }
    [IO.File]::WriteAllLines((Join-Path $distribution 'DEPENDENCIES.txt'), [string[]]$freeze, (New-Object Text.UTF8Encoding($false)))
    Copy-Item -LiteralPath $lock -Destination (Join-Path $distribution 'DEPENDENCIES.lock')
    Invoke-BuildPython -PythonArguments @((Join-Path $root 'packaging\build_manifest.py'), '--root', $root, '--output', (Join-Path $distribution 'BUILD-MANIFEST.json'))
    Write-Output ('Built: ' + $executable)
    Write-Output 'Self-test passed. Keep the entire Filewheel folder, including _internal and optional tools.'
} finally {
    Pop-Location
}
