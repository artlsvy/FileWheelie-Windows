"""Portable conversion contracts; engines write only into a private staging folder."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Protocol

Progress = Callable[[float, str], None]


class ConversionError(RuntimeError):
    """A local conversion failed without replacing any pre-existing output."""


class ConversionCancelled(ConversionError):
    """A cancellation request was observed before publishing output."""


def check_cancel(cancel: Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise ConversionCancelled("Conversion cancelled")


@dataclass(frozen=True)
class Capability:
    input_extension: str
    category: str
    output_extension: str
    label: str
    engine_id: str


@dataclass(frozen=True)
class EngineOutput:
    path: Path
    suggested_name: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConversionResult:
    outputs: tuple[Path, ...]
    warnings: tuple[str, ...]
    engine_id: str

    @property
    def path(self) -> Path:
        """Convenience for single-output engines."""
        return self.outputs[0]


class Engine(Protocol):
    engine_id: str
    capabilities: tuple[Capability, ...]

    def available(self) -> bool: ...

    def convert(self, source: Path, extension: str, workdir: Path,
                progress: Progress, cancel: Event | None) -> tuple[EngineOutput, ...]: ...

    def validate(self, output: EngineOutput) -> None: ...
