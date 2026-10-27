"""Build the Windows family EXE with complete embedded Pandoc and LibreOffice."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    from filewheel.libreoffice_bundle import find_libreoffice
    from filewheel.libreoffice_bundle import validate_bundle as validate_office
    from filewheel.pandoc_tool import validate_bundle as validate_pandoc
    from filewheel.paths import ensure_separate_tool_source
    from filewheel.runtime import require_runtime

    require_runtime()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--libreoffice', type=Path)
    parser.add_argument('--pandoc', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/standalone')
    args = parser.parse_args()
    office = args.libreoffice
    if office is None:
        location = find_libreoffice()
        if location is None:
            parser.error('Supply --libreoffice with a complete Windows installation directory')
        office = location.root
    pandoc = args.pandoc
    if pandoc is None:
        installed = shutil.which('pandoc')
        if installed is None:
            parser.error('Supply --pandoc with the complete Windows Pandoc directory')
        pandoc = Path(installed).parent
    office = ensure_separate_tool_source(office, args.output)
    pandoc = ensure_separate_tool_source(pandoc, args.output)
    validate_office(office)
    pandoc_info = validate_pandoc(pandoc)
    (ROOT / 'build').mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='single-exe-tools-', dir=ROOT / 'build'))
    copied_office = stage / 'libreoffice'
    print('Staging complete LibreOffice and native runtimes...', flush=True)
    shutil.copytree(office, copied_office)
    # External LO gets its own adjacent VC runtime; it must not depend on a JDK,
    # installed redistributable or PyInstaller's process-global DLL directory.
    system = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
    required = ('msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
                'vcruntime140.dll', 'vcruntime140_1.dll')
    for name in required:
        if not (system / name).is_file():
            raise RuntimeError('Missing build-machine native runtime: ' + name)
    for pattern in ('msvcp140*.dll', 'vcruntime140*.dll', 'concrt140.dll', 'vcomp140.dll'):
        for library in system.glob(pattern):
            shutil.copy2(library, copied_office / 'program' / library.name)
    env = dict(os.environ, FILEWHEEL_BUILD_ONEFILE='1',
               FILEWHEEL_BUNDLE_LIBREOFFICE=str(copied_office),
               FILEWHEEL_BUNDLE_PANDOC=str(pandoc))
    args.output.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / 'build/single-exe-build.log'
    print('Building single EXE; log:', log_path, flush=True)
    with log_path.open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
            '--distpath', str(args.output), '--workpath', str(ROOT / 'build/onefile'),
            str(ROOT / 'packaging/Filewheel.spec')], cwd=ROOT, env=env,
            stdout=log, stderr=subprocess.STDOUT, check=True)
    executable = args.output / 'Filewheel.exe'
    with executable.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'file': executable.name, 'sha256': digest,
                'bytes': executable.stat().st_size, 'python': sys.version,
                'pandoc': pandoc_info.version, 'embedded_tools': ['LibreOffice', 'Pandoc'],
                'build_log': str(log_path)}
    (args.output / 'BUILD-INFO.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Built:', executable, '\nSHA256:', digest, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
