"""Bounded local Linux OCR; prefer the AppImage's executable and language data."""

import os
import shutil
from pathlib import Path

from filewheel.converters.base import ConversionError, DependencyUnavailable, check_cancel
from filewheel.converters.office import run_office
from filewheel.paths import bundled_tool_root


def location():
    root = bundled_tool_root() / "tools/tesseract"
    executable = root / "tesseract"
    if executable.is_file() and os.access(executable, os.X_OK):
        data = root / "tessdata"
        if not (data / "eng.traineddata").is_file():
            raise DependencyUnavailable("Bundled Tesseract English recognition data is missing")
        return executable, data, "bundled"
    if os.getenv("FILEWHEEL_BUNDLED_TOOLS_ONLY") != "1":
        system = shutil.which("tesseract")
        if system:
            return Path(system), None, "system"
    raise DependencyUnavailable(
        "Scanned PDF conversion needs local OCR. Reinstall the complete Filewheel AppImage "
        "or install tesseract-ocr and tesseract-ocr-eng for source use."
    )


def recognize_image(image, workdir, cancel):
    check_cancel(cancel)
    executable, data, _ = location()
    output = workdir / "ocr-result.txt"
    output.unlink(missing_ok=True)
    arguments = [str(executable), str(image), str(output.with_suffix("")), "-l", "eng"]
    if data is not None:
        arguments.extend(("--tessdata-dir", str(data)))
    try:
        result = run_office(
            arguments, workdir=workdir, timeout=60, cancel=cancel, tool_name="Tesseract OCR"
        )
    except OSError as error:
        raise DependencyUnavailable("Local Tesseract OCR could not start") from error
    check_cancel(cancel)
    if result:
        detail = result.stderr.strip()[:500]
        if "Failed loading language" in detail or "Error opening data file" in detail:
            raise DependencyUnavailable("Local Tesseract English recognition data is unavailable")
        raise ConversionError("Local Tesseract OCR failed. " + detail)
    try:
        if output.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("OCR response too large")
        text = output.read_text(encoding="utf-8")
        if "\0" in text:
            raise ValueError("Binary OCR response")
    except (OSError, ValueError) as error:
        raise ConversionError("Local Tesseract OCR returned an invalid result") from error
    finally:
        output.unlink(missing_ok=True)
    return text.splitlines(), "eng"
