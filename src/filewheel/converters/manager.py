"""Staged local conversion with atomic no-replacement publication and rollback."""

import os
import stat
import tempfile
from pathlib import Path
from threading import Event

from filewheel.converters.base import (
    ConversionCancelled,
    ConversionError,
    ConversionResult,
    DependencyUnavailable,
    EngineOutput,
    Progress,
    check_cancel,
)
from filewheel.converters.debugging import record_failure
from filewheel.converters.registry import Registry, default_registry


def _regular_file(path: Path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ConversionError("Input must be a regular file, not a link or directory")
    return info


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


class ConversionManager:
    def __init__(self, registry: Registry | None = None):
        self.registry = default_registry() if registry is None else registry

    def convert(self, source: Path, output_extension: str, *,
                progress: Progress | None = None, cancel: Event | None = None) -> ConversionResult:
        source = Path(source)
        if not source.is_absolute():
            raise ConversionError("Input path must be absolute")
        user_report = progress if progress is not None else lambda fraction, message: None
        engine_id = "unselected"
        def report(fraction, message):
            user_report(fraction, f"{engine_id}: {message}")
        published = []
        operation = "validate_input"
        try:
            before = _regular_file(source)
            operation = "select_engine"
            capability = self.registry.find(source.suffix, output_extension)
            engine_id = capability.engine_id
            engine = self.registry.engines[capability.engine_id]
            if not engine.available():
                raise DependencyUnavailable(f"{engine_id} is no longer available")
            check_cancel(cancel)
            report(0.0, "Preparing conversion")
            with tempfile.TemporaryDirectory(prefix=".filewheel-", dir=source.parent) as folder:
                workdir = Path(folder)
                operation = "convert"
                generated = tuple(engine.convert(source, capability.output_extension, workdir,
                                                 report, cancel))
                if not generated:
                    raise ConversionError("The engine generated no output")
                if _identity(before) != _identity(_regular_file(source)):
                    raise ConversionError("The input changed during conversion")
                operation = "validate_output"
                for output in generated:
                    self._validate_staged(output, workdir, source)
                    engine.validate(output)
                operation = "publish_output"
                report(.9, "Saving output")
                for output in generated:
                    check_cancel(cancel)
                    created = output.path.lstat()
                    destination = self._publish(output, source.parent)
                    published.append((destination, created))
                check_cancel(cancel)
                result = ConversionResult(tuple(path for path, _ in published),
                                          tuple(dict.fromkeys(warning for output in generated
                                                              for warning in output.warnings)),
                                          engine.engine_id)
            report(1.0, "Conversion complete")
            return result
        except Exception as error:
            for path, created in reversed(published):
                try:
                    current = path.lstat()
                    if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                        path.unlink()
                except OSError:
                    pass
            if isinstance(error, ConversionCancelled):
                error.engine_id, error.operation = engine_id, operation
                raise
            engine_id = getattr(error, "engine_id", engine_id)
            log = record_failure(engine_id, operation, error)
            # Dependency errors may be wrapped by an engine; inspect the chain.
            cause = error
            unavailable = isinstance(error, DependencyUnavailable)
            seen = set()
            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))
                unavailable |= isinstance(cause, (ImportError, ModuleNotFoundError, DependencyUnavailable))
                cause = cause.__cause__ or cause.__context__
            if unavailable:
                failure = DependencyUnavailable(f"Required dependency for {engine_id} is unavailable")
            elif isinstance(error, ConversionError):
                failure = error
            else:
                failure = ConversionError(
                    f"{type(error).__name__} during {operation}; no existing output was replaced"
                )
            failure.engine_id, failure.operation = engine_id, operation
            failure.debug_log = log
            failure.kind = "dependency_unavailable" if unavailable else "conversion_failed"
            if failure is error:
                raise
            raise failure from error

    @staticmethod
    def _validate_staged(output: EngineOutput, workdir: Path, source: Path):
        if (not isinstance(output, EngineOutput) or not output.path.is_absolute()
                or output.path.parent != workdir or not output.suggested_name
                or Path(output.suggested_name).name != output.suggested_name
                or any(character in output.suggested_name for character in '/\\:\x00')
                or output.suggested_name in (".", "..")
                or output.suggested_name.casefold() == source.name.casefold()):
            raise ConversionError("The engine returned an unsafe output path")
        info = _regular_file(output.path)
        if info.st_size == 0:
            raise ConversionError("The engine generated an empty output")

    @staticmethod
    def _publish(output: EngineOutput, directory: Path) -> Path:
        suggested = Path(output.suggested_name)
        for index in range(1, 10001):
            name = (suggested.name if index == 1 else
                    f"{suggested.stem} ({index}){suggested.suffix}")
            destination = directory / name
            try:
                # Same-volume hardlink publication is atomic and never replaces.
                # Unsupported filesystems fail safely rather than falling back to
                # a rename that could silently replace another user's file.
                os.link(output.path, destination)
                return destination
            except FileExistsError:
                continue
        raise ConversionError("No unused output filename is available")
