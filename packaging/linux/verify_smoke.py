"""Require bundled converter families; a source-style optional skip is not release success."""

import json
import sys
from pathlib import Path

REQUIRED = {
    "pillow",
    "pymupdf-images",
    "pdf2docx",
    "markitdown",
    "structured-markdown",
    "archive-markdown",
    "pandoc",
    "ffmpeg",
    "libreoffice",
}


def verify(value):
    if value.get("ok") is not True:
        raise RuntimeError("Frozen self-test failed; inspect its local debug log")
    results = value.get("results", [])
    engines = {item.get("engine") for item in results if item.get("ok") is True}
    if missing := REQUIRED - engines:
        raise RuntimeError("Frozen converter families missing: " + ", ".join(sorted(missing)))
    for key in (
        "quick_qml_render",
        "quick_progress_render",
        "frozen_spawn_cancel_retry",
        "linux_local_ocr",
        "linux_local_ocr_markdown",
        "linux_picture_only_markdown",
    ):
        if not any(item.get(key) is True and item.get("ok") is True for item in results):
            raise RuntimeError("Frozen check missing: " + key)
    if not any(item.get("libreoffice_source") == "bundled" for item in results):
        raise RuntimeError("LibreOffice must be bundled")
    if not any(item.get("ocr_source") == "bundled" for item in results):
        raise RuntimeError("Tesseract and its recognition data must be bundled")
    if not any(item.get("pandoc_source") == "bundled" for item in results):
        raise RuntimeError("Pandoc must be bundled")
    if not any("bundled_ffmpeg" in item for item in results):
        raise RuntimeError("Bundled FFmpeg must execute real media conversions")


if __name__ == "__main__":
    verify(json.loads(Path(sys.argv[1]).read_text()))
