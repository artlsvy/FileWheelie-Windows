"""Bounded native probe failures without exception messages or private payloads."""

from collections.abc import Callable
from typing import TypeVar


_Result = TypeVar("_Result")
_MAX_STAGES = 32
_MAX_TEXT = 160
_HRESULT_NAMES = {
    0x80004001: "E_NOTIMPL",
    0x80004002: "E_NOINTERFACE",
    0x80004005: "E_FAIL",
    0x80070005: "E_ACCESSDENIED",
    0x8001010D: "RPC_E_CANTCALLOUT_ININPUTSYNCCALL",
    0x8001010E: "RPC_E_WRONG_THREAD",
    0x800401F0: "CO_E_NOTINITIALIZED",
    0x80020003: "DISP_E_MEMBERNOTFOUND",
}


class ProbeFailure(Exception):
    """Contains only the sanitized evidence produced by :func:`probe_step`."""

    def __init__(self, evidence: dict):
        super().__init__("native probe failed")
        self.evidence = evidence


def _normalize_hresult(value) -> int | None:
    if type(value) is not int or not -(2**31) <= value <= 2**32 - 1:
        return None
    return value - 2**32 if value >= 2**31 else value


def _hresult(error: Exception) -> int | None:
    try:
        result = _normalize_hresult(getattr(error, "hresult", None))
    except Exception:
        result = None
    if result is not None:
        return result
    # COMError exposes the code as args[0] on some bindings. Never copy other
    # arguments, error-info strings, traceback data, or str(error).
    return _normalize_hresult(error.args[0]) if error.args else None


def probe_step(
    completed_stages: list[str], stage: str, operation: Callable[..., _Result], *args
) -> _Result:
    """Run an internal named step and retain bounded success/error metadata.

    Stage labels are static call-site strings, never values obtained from an
    Explorer window or an exception. HRESULTs are normalized to signed 32 bits;
    booleans, strings and out-of-range values are not error codes.
    """
    label = stage[:_MAX_TEXT]
    try:
        result = operation(*args)
    except ProbeFailure:
        raise  # Preserve the original failing stage through nested operations.
    except Exception as error:
        code = _hresult(error)
        unsigned = code & 0xFFFFFFFF if code is not None else None
        evidence = {
            "stage": label,
            "error_type": type(error).__name__[:_MAX_TEXT],
            "hresult": code,
            "hresult_hex": f"0x{unsigned:08X}" if unsigned is not None else None,
            "hresult_name": _HRESULT_NAMES.get(unsigned),
            "completed_stages": [value[:_MAX_TEXT] for value in completed_stages[-_MAX_STAGES:]],
        }
        raise ProbeFailure(evidence) from None
    completed_stages.append(label)
    del completed_stages[:-_MAX_STAGES]
    return result
