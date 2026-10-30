"""Native local POSIX path boundary, independent of Windows lexical rules."""

import stat
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from filewheel.core.explicit_paths import ExplicitPathValidation, FileCheck


def inspect_file(path):
    path = Path(path)
    # Conservative first port: reject symlinks in any existing component.
    if any(p.is_symlink() for p in (path, *path.parents)):
        return FileCheck(path.exists(), False, True)
    try:
        metadata = path.stat()
    except FileNotFoundError:
        return FileCheck(False, False)
    return FileCheck(True, stat.S_ISREG(metadata.st_mode))


def validate_paths(arguments, inspector=inspect_file):
    if (
        isinstance(arguments, (str, bytes))
        or not isinstance(arguments, Sequence)
        or len(arguments) != 1
    ):
        return ExplicitPathValidation(None, "expected_one_path")
    value = arguments[0]
    if not isinstance(value, str) or not value or "\0" in value:
        return ExplicitPathValidation(None, "invalid_path")
    path = PurePosixPath(value)
    if not path.is_absolute() or value.startswith("//"):
        return ExplicitPathValidation(None, "absolute_local_path_required")
    if value.endswith("/") or ".." in path.parts:
        return ExplicitPathValidation(None, "unsupported_path")
    try:
        state = inspector(path)
    except PermissionError:
        return ExplicitPathValidation(None, "file_access_denied")
    except OSError:
        return ExplicitPathValidation(None, "file_check_failed")
    if not isinstance(state, FileCheck) or any(
        type(x) is not bool for x in (state.exists, state.is_file, state.is_reparse_point)
    ):
        return ExplicitPathValidation(None, "invalid_file_check")
    rejection = (
        "missing_file"
        if not state.exists
        else "unsupported_reparse_point"
        if state.is_reparse_point
        else "not_a_file"
        if not state.is_file
        else None
    )
    return ExplicitPathValidation(None if rejection else path, rejection)
