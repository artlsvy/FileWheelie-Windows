"""Qt-free, structured desktop startup failures with bounded JSON metadata."""

import math
import re


def _metadata(value, depth=0):
    if depth > 4:
        raise ValueError("desktop metadata nesting too deep")
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is str:
        return value[:256]
    if isinstance(value, (list, tuple)) and len(value) <= 32:
        return [_metadata(item, depth + 1) for item in value]
    if isinstance(value, dict) and len(value) <= 32 and all(type(key) is str for key in value):
        return {key: _metadata(item, depth + 1) for key, item in value.items()}
    raise ValueError("desktop metadata must contain bounded JSON values")


class DesktopInitializationError(RuntimeError):
    """A known desktop stage failed; caller supplies desktop metadata only.

    Do not put input paths or arbitrary exception messages into details. The
    exception text is only the stage; .as_record() exposes explicit metadata.
    """

    def __init__(self, stage: str, details: dict | None = None):
        if not isinstance(stage, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", stage):
            raise ValueError("invalid desktop stage")
        self.stage = stage
        self.details = _metadata(details if details is not None else {})
        super().__init__(stage)

    def as_record(self):
        return {"stage": self.stage, "details": self.details}
