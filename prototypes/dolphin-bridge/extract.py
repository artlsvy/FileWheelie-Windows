"""Copy only the private prototype prefix out of a new stopped build container."""

import argparse
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=Path("build/dolphin-probe"))
args = parser.parse_args()
if args.output.exists() or args.output.is_symlink():
    parser.error("Refusing an existing destination")
args.output.parent.mkdir(parents=True, exist_ok=True)
container = subprocess.check_output(
    ["docker", "create", "filewheel-dolphin-probe:25.12.3"], text=True
).strip()
try:
    subprocess.run(
        ["docker", "cp", container + ":/opt/filewheel-dolphin-probe", str(args.output)], check=True
    )
finally:
    subprocess.run(["docker", "rm", container], check=True, stdout=subprocess.DEVNULL)
print(args.output.resolve())
