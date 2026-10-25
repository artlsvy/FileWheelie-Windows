"""Frozen entry point: spawned conversion workers exit before importing the UI."""

import multiprocessing

multiprocessing.freeze_support()

from filewheel.app import main

if __name__ == "__main__":
    raise SystemExit(main())
