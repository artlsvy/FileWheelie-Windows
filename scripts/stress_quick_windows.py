"""Run from a fresh process; environment chooses the actual native backend."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--cycles', type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.cycles <= 1000:
        parser.error('cycles must be between 1 and 1000')
    from filewheel.ui.render_stress import run
    raise SystemExit(run(args.output, args.cycles))
