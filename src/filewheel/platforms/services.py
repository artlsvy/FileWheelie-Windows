"""Small platform selector; Windows adapters stay unchanged."""

import sys


def path_flavour():
    return "posix" if sys.platform == "linux" else "windows"


def inspect_file(path):
    if sys.platform == "linux":
        from filewheel.platforms.linux.paths import inspect_file as inspect
    else:
        from filewheel.platforms.windows.explicit_path_diagnostics import inspect_file as inspect
    return inspect(path)


def startup():
    if sys.platform == "linux":
        from filewheel.platforms.linux import startup as adapter
    else:
        from filewheel.platforms.windows import startup as adapter
    return adapter
