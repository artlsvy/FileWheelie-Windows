"""Source and frozen entry point; multiprocessing children must not re-open UI."""
from multiprocessing import freeze_support

if __name__ == '__main__':
    freeze_support()
    from filewheel.app import main
    raise SystemExit(main())
