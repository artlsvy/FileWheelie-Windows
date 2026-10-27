"""Test ONLY a copied EXE outside the checkout with installed tools unavailable."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, default=Path('dist/standalone/Filewheel.exe'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/single-exe'))
    parser.add_argument('--cycles', type=int, default=100)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    results = {'selftest': False, 'ui': False}
    with tempfile.TemporaryDirectory(prefix='Filewheel family check ') as folder:
        root = Path(folder)
        executable = root / 'Filewheel.exe'
        shutil.copy2(args.executable, executable)
        env = dict(os.environ)
        for key in tuple(env):
            if key.startswith(('PYTHON', 'FILEWHEEL_', 'QT_', 'QSG_', 'QML')) or key == 'JAVA_HOME':
                env.pop(key)
        extraction = root / 'temporary'
        extraction.mkdir()
        system = Path(env.get('SystemRoot', r'C:\Windows'))
        env.update(PATH=str(system / 'System32') + ';' + str(system),
                   PROGRAMFILES=str(root / 'no-installed-programs'),
                   **{'PROGRAMFILES(X86)': str(root / 'no-installed-programs')},
                   TEMP=str(extraction), TMP=str(extraction),
                   FILEWHEEL_BUNDLED_TOOLS_ONLY='1',
                   PYINSTALLER_STRICT_UNPACK_MODE='1',
                   QSG_INFO='1', QT_FORCE_STDERR_LOGGING='1')

        def invoke(arguments, name, timeout):
            output = args.output / name
            output.mkdir(exist_ok=True)
            env['FILEWHEEL_LOG_DIR'] = str(output)
            with (output / 'run.log').open('w', encoding='utf-8') as log:
                result = subprocess.run([str(executable), *arguments], cwd=root, env=env,
                                        stdout=log, stderr=subprocess.STDOUT,
                                        timeout=timeout, check=False)
            assert result.returncode == 0, f'{name} exit {result.returncode}; inspect {output}'
            leftovers = list(extraction.iterdir())
            assert not list(extraction.glob('_MEI*')), f'{name} left unpacked bundle after exit'
            results[name + '_auxiliary_temp_entries'] = [
                {'name': p.name, 'directory': p.is_dir(),
                 'bytes': p.stat().st_size if p.is_file() else None} for p in leftovers]
            return output

        print('Testing relocated onefile conversions, frozen workers and cancellation...', flush=True)
        folder = invoke(['--self-test', '--ui-backend', 'quick'], 'selftest', 360)
        report = json.loads((folder / 'self-test.json').read_text(encoding='utf-8'))
        assert report['ok']
        checks = report['results']
        assert any(c.get('pandoc_source') == 'bundled' for c in checks)
        assert any(c.get('libreoffice_source') == 'bundled' for c in checks)
        assert any(c.get('frozen_spawn_cancel_retry') and c['workers'] == 3 for c in checks)
        results.update(selftest=True, selftest_checks=len(checks),
                       conversion_pairs=sum('pair' in c for c in checks),
                       extraction_cleanup=True, installed_tools_disabled=True)
        print('Self-test passed. Testing native Quick cycles...', flush=True)
        folder = invoke(['--ui-stress-test', str(args.output / 'ui'),
                         '--ui-stress-cycles', str(args.cycles)], 'ui', args.cycles * 4 + 120)
        report = json.loads((folder / 'result.json').read_text(encoding='utf-8'))
        assert report['passed'] and len(report['cycles']) == args.cycles
        assert all(c['api'] == c['progress_api'] == 'OpenGL' for c in report['cycles'])
        results.update(ui=True, cycles=args.cycles,
                       selection_reopens=sum(c['selection_reopens'] for c in report['cycles']),
                       graphics_api='OpenGL')
    (args.output / 'verification.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
