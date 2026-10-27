"""Build the Windows family EXE with complete embedded Pandoc and LibreOffice."""
import argparse
import hashlib
import json
import os
import re
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
    parser.add_argument('--output', type=Path, default=ROOT / 'releases')
    parser.add_argument('--installer-payload', action='store_true',
                        help='build installed onedir payload with conditional-copy tools')
    parser.add_argument('--skip-tool-probes', action='store_true',
                        help='structure-only native tool checks; do not run conversion probes')
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
    pandoc_info = validate_pandoc(pandoc, execute=not args.skip_tool_probes)
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
    env = dict(os.environ, FILEWHEEL_BUILD_ONEFILE='0' if args.installer_payload else '1',
               FILEWHEEL_BUNDLE_LIBREOFFICE=str(copied_office),
               FILEWHEEL_BUNDLE_PANDOC=str(pandoc))
    # Do not capture unrelated applications' DLLs (for example a JDK on PATH).
    env['PATH'] = os.pathsep.join((str(Path(sys.executable).parent), str(system), str(system.parent)))
    env.pop('JAVA_HOME', None)
    env.pop('JDK_HOME', None)
    args.output.mkdir(parents=True, exist_ok=True)
    mode = 'installer-payload' if args.installer_payload else 'single-exe'
    log_path = ROOT / ('build/' + mode + '-build.log')
    print('Building ' + mode + '; log:', log_path, flush=True)
    with log_path.open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
            '--distpath', str(args.output), '--workpath', str(ROOT / 'build' / ('pyinstaller-' + mode)),
            str(ROOT / 'packaging/Filewheel.spec')], cwd=ROOT, env=env,
            stdout=log, stderr=subprocess.STDOUT, check=True)
    executable = args.output / ('Filewheel/Filewheel.exe' if args.installer_payload else 'Filewheel.exe')
    if args.installer_payload:
        # External tools are separate processes, not Python DLL dependencies.
        # Copy complete trees after Analysis to avoid DLL reclassification and
        # accidental collection of build-machine Java/Office dependencies.
        tools = executable.parent / '_internal/tools'
        shutil.copytree(copied_office, tools / 'libreoffice')
        shutil.copytree(pandoc, tools / 'pandoc')
        packages = re.findall(r'^([A-Za-z0-9_.-]+(?:\[[^]]+\])?==[^\s\\]+)',
                              (ROOT / 'packaging/windows-py314.lock').read_text(encoding='utf-8'), re.M)
        (executable.parent / 'DEPENDENCIES.txt').write_text(
            'Filewheel private runtime - Python 3.14\n'
            'Bundled fallback engines: LibreOffice and Pandoc.\n'
            'Compatible installed engines may be reused instead; see installation.ini.\n'
            'Pinned runtime/build environment inventory follows. Build-only packages\n'
            'may have metadata included without their tools being installed.\n\n'
            + '\n'.join(packages) + '\n', encoding='utf-8')
    with executable.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'file': executable.name, 'sha256': digest,
                'bytes': executable.stat().st_size, 'python': sys.version,
                'pandoc': pandoc_info.version, 'embedded_tools': ['LibreOffice', 'Pandoc'],
                'build_log': str(log_path.relative_to(ROOT)), 'tool_probes_run': not args.skip_tool_probes}
    (args.output / 'BUILD-INFO.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Built:', executable, '\nSHA256:', digest, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
