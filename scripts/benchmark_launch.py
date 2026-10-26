"""Opt-in Windows EXE/source launch-to-first-render measurement; close with Esc."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from time import monotonic


def command(executable, source_python, backend, path):
    prefix = [str(executable)] if executable is not None else [str(source_python), '-m', 'filewheel']
    return [*prefix, '--ui-backend', backend, '--gui', '--', str(path)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--exe', type=Path)
    source.add_argument('--python', type=Path)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--backend', choices=('widgets', 'quick'), default='widgets')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Normal application launch requires an interactive Windows desktop')
    if (not args.file.is_absolute() or not args.file.is_file() or not args.output.is_absolute()
            or args.output.suffix.lower() != '.json' or args.output.exists()
            or not args.output.parent.is_dir()):
        parser.error('Use an existing absolute input file and a fresh absolute .json output')
    env = os.environ.copy()
    env['FILEWHEEL_TIMINGS'] = str(args.output)
    env['FILEWHEEL_LAUNCH_START'] = str(monotonic())
    print('Close other Filewheel instances first. When the menu appears, press Escape; do not choose a format.')
    process = subprocess.Popen(command(args.exe, args.python, args.backend, args.file), env=env)
    try:
        code = process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        print('Filewheel is still running; close it normally. No process was force-stopped.', file=sys.stderr)
        return 2
    if code != 0 or not args.output.is_file():
        return 3
    import json
    metrics = json.loads(args.output.read_text(encoding='utf-8'))['metrics']
    stage = 'launch_to_quick_frame' if 'launch_to_quick_frame' in metrics else 'launch_to_paint'
    if stage not in metrics:
        print('No first-render sample: an existing owner may have received this invocation.', file=sys.stderr)
        return 3
    print(stage, metrics[stage])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
