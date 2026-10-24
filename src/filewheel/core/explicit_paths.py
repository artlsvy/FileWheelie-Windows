"""Portable explicit Windows path validation; filesystem inspection is injected."""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import PureWindowsPath

from filewheel.core.models import TargetResolution


@dataclass(frozen=True)
class FileCheck:
    """Current metadata sampled by the caller's filesystem adapter."""

    exists: bool
    is_file: bool
    is_reparse_point: bool = False


@dataclass(frozen=True)
class ExplicitPathValidation:
    path: PureWindowsPath | None
    rejection: str | None


@dataclass(frozen=True)
class ExplicitInvocationResult:
    target: TargetResolution | None
    rejection: str | None


FileInspector = Callable[[PureWindowsPath], FileCheck]


def validate_explicit_paths(
    arguments: Sequence[str], inspect_file: FileInspector,
) -> ExplicitPathValidation:
    """Accept one ordinary local file path supplied directly by Shell/argv.

    The caller parses CLI options and removes its own ``--`` delimiter before
    passing the remaining arguments. No quote stripping, environment expansion,
    shell evaluation, directory/name reconstruction, or UIA lookup occurs here.
    Validation is a metadata snapshot, not a promise the file cannot change
    before a later action; that action must revalidate/open its own input.
    """
    if isinstance(arguments, (str, bytes)) or not isinstance(arguments, Sequence):
        return ExplicitPathValidation(None, "expected_one_path")
    if len(arguments) != 1:
        return ExplicitPathValidation(None, "expected_one_path")
    value = arguments[0]
    if (
        not isinstance(value, str) or not value or len(value) > 32767
        or any(ord(character) < 32 for character in value)
        or '"' in value
    ):
        return ExplicitPathValidation(None, "invalid_path")
    path = PureWindowsPath(value)
    if not path.is_absolute() or not re.fullmatch(r"[A-Za-z]:", path.drive):
        return ExplicitPathValidation(None, "absolute_local_path_required")
    if (
        value.endswith(("\\", "/"))
        or any(part in (".", "..") for part in value.replace("/", "\\").split("\\"))
        or not path.name
        or any(
            part.endswith((".", " "))
            or any(character in part for character in ':*?"<>|')
            or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", part)
            for part in path.parts[1:]
        )
    ):
        return ExplicitPathValidation(None, "unsupported_path")
    try:
        state = inspect_file(path)
    except (FileNotFoundError, NotADirectoryError):
        return ExplicitPathValidation(None, "missing_file")
    except PermissionError:
        return ExplicitPathValidation(None, "file_access_denied")
    except Exception:
        return ExplicitPathValidation(None, "file_check_failed")
    if not isinstance(state, FileCheck) or any(
        type(flag) is not bool for flag in (state.exists, state.is_file, state.is_reparse_point)
    ):
        return ExplicitPathValidation(None, "invalid_file_check")
    if not state.exists:
        return ExplicitPathValidation(None, "missing_file")
    if state.is_reparse_point:
        return ExplicitPathValidation(None, "unsupported_reparse_point")
    if not state.is_file:
        return ExplicitPathValidation(None, "not_a_file")
    return ExplicitPathValidation(path, None)
