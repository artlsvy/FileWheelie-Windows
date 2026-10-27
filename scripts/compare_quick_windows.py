"""Fresh-process, bounded native backend matrix; no resident app forwarding."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cycles', type=int, default=100)
parser.add_argument('--output', default='artifacts/f5/comparison')
parser.add_argument('--executable', type=Path, help='optional frozen Filewheel.exe')
parser.add_argument('--no-trace', action='store_true', help='verify normal untraced operation')
parser.add_argument('--backends', nargs='+', default=['default', 'd3d11', 'opengl', 'software'],
                    choices=['default', 'd3d11', 'opengl', 'software', 'preferred'])
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
failed = False
for backend in args.backends:
    env = dict(os.environ)
    for key in ('QT_QUICK_BACKEND', 'QSG_RHI_BACKEND', 'QMLSCENE_DEVICE',
                'QT_QPA_PLATFORM', 'QSG_RENDER_LOOP', 'QSG_RHI_PREFER_SOFTWARE_RENDERER',
                'QT_OPENGL', 'FILEWHEEL_TIMINGS', 'FILEWHEEL_QUICK_RHI'):
        env.pop(key, None)
    env.update(QSG_INFO='1', QT_FORCE_STDERR_LOGGING='1', FILEWHEEL_UI_TRACE='1')
    if args.no_trace:
        env.pop('FILEWHEEL_UI_TRACE', None)
    if backend == 'software':
        env['QT_QUICK_BACKEND'] = 'software'
    elif backend not in ('default', 'preferred'):
        env['QSG_RHI_BACKEND'] = backend
    if backend == 'default':
        env['FILEWHEEL_QUICK_RHI'] = 'default'
    folder = root / args.output / backend
    folder.mkdir(parents=True, exist_ok=True)
    env['FILEWHEEL_LOG_DIR'] = str(folder)
    if args.executable:
        env.pop('PYTHONPATH', None)
    else:
        env['PYTHONPATH'] = str(root / 'src')
    command = ([str(args.executable.resolve())] if args.executable else
               [sys.executable, '-m', 'filewheel'])
    command += ['--ui-stress-test', str(folder), '--ui-stress-cycles', str(args.cycles)]
    print('Starting', backend, flush=True)
    with (folder / 'qt.log').open('w') as log:
        try:
            result = subprocess.run(command,
                env=env, stdout=log, stderr=log, timeout=args.cycles * 4 + 30,
                cwd=args.executable.resolve().parent if args.executable else root, check=False)
            failed |= result.returncode != 0
            print(backend, 'exit', result.returncode, flush=True)
        except subprocess.TimeoutExpired:
            failed = True
            print(backend, 'TIMEOUT', flush=True)
raise SystemExit(int(failed))
