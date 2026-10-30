"""Build one offline Setup EXE with a pinned, private Inno Setup compiler."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
INNO_VERSION = '6.7.3'
INNO_SHA256 = '9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732'
INNO_URL = ('https://github.com/jrsoftware/issrc/releases/download/'
            'is-6_7_3/innosetup-6.7.3.exe')


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compiler():
    directory = ROOT / 'build-tools'
    directory.mkdir(exist_ok=True)
    setup = directory / ('innosetup-' + INNO_VERSION + '.exe')
    if not setup.is_file():
        temporary = setup.with_suffix('.download')
        try:
            with urlopen(INNO_URL, timeout=60) as response, temporary.open('wb') as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            if sha256(temporary) != INNO_SHA256:
                raise RuntimeError('Inno Setup download checksum differs')
            temporary.replace(setup)
        finally:
            temporary.unlink(missing_ok=True)
    if sha256(setup) != INNO_SHA256:
        raise RuntimeError('Inno Setup compiler bootstrap checksum differs')
    target = directory / 'InnoSetup'
    # Refresh from the verified installer, not an arbitrary compiler on PATH.
    subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                    '/SP-', '/CURRENTUSER', '/PORTABLE=1', '/NOICONS', '/DIR=' + str(target)],
                   check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return target / 'ISCC.exe'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--libreoffice', type=Path, required=True)
    parser.add_argument('--pandoc', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    parser.add_argument('--skip-tool-probes', action='store_true')
    parser.add_argument('--reuse-payload', action='store_true',
                        help='compile existing payload; only after its source build is current')
    args = parser.parse_args()
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 14):
        parser.error('Build using Windows CPython 3.14')
    output = ROOT / 'build/installer-payload'
    if not args.reuse_payload:
        command = [sys.executable, str(ROOT / 'packaging/build_single_exe.py'),
                   '--installer-payload', '--output', str(output),
                   '--libreoffice', str(args.libreoffice), '--pandoc', str(args.pandoc)]
        command.extend(['--ffmpeg', str(args.ffmpeg)])
        if args.skip_tool_probes:
            command.append('--skip-tool-probes')
        subprocess.run(command, check=True)
    payload = output / 'Filewheel'
    if not (payload / 'Filewheel.exe').is_file():
        raise RuntimeError('Installer payload is unavailable')
    log_path = ROOT / 'build/installer-compile.log'
    print('Compiling offline installer; log:', log_path, flush=True)
    iscc = compiler()
    with log_path.open('w', encoding='utf-8') as log:
        subprocess.run([str(iscc), '/DPayloadDir=' + str(payload),
                        str(ROOT / 'packaging/Filewheel.iss')], cwd=ROOT, check=True,
                       stdout=log, stderr=subprocess.STDOUT,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    executable = ROOT / 'releases/FilewheelSetup.exe'
    digest = sha256(executable)
    manifest = {'file': executable.name, 'sha256': digest,
                'bytes': executable.stat().st_size, 'version': '0.3.1',
                'built_utc': datetime.now(UTC).isoformat(),
                'compiler': 'Inno Setup ' + INNO_VERSION,
                'payload': json.loads((output / 'BUILD-INFO.json').read_text(encoding='utf-8')),
                'runtime_validation': 'not run by builder; record subsequent verification separately',
                'tool_reuse': {'LibreOffice': '7.6+', 'Pandoc': '3.1+', 'FFmpeg': '9+'},
                'ffmpeg_distribution_license': 'GPLv3 build; see installed tools/ffmpeg files'}
    (ROOT / 'releases/INSTALLER-BUILD-INFO.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    sums = ROOT / 'releases/SHA256SUMS.txt'
    sums.write_text(digest + '  FilewheelSetup.exe\n', encoding='utf-8')
    print('Built:', executable, '\nSHA256:', digest, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
