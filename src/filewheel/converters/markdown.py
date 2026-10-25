"""Offline MarkItDown Python API for explicitly supported local document types."""

import os
import re
import sys
from importlib.util import find_spec
from pathlib import Path
from threading import Event
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

# Must precede any MarkItDown/Magika/ONNX import, including lazy conversions.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

from filewheel.converters.base import (
    Capability,
    ConversionError,
    EngineOutput,
    Progress,
    check_cancel,
)

_DEPENDENCIES = {
    ".docx": ("mammoth",),
    ".pdf": ("pdfminer", "pdfplumber", "pymupdf"),
    ".pptx": ("pptx",),
    ".xlsx": ("openpyxl", "pandas"),
    ".html": ("bs4",),
}
_OFFICE_DOCUMENTS = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}


class RejectRequestsSession:
    """Network-disabled session injected into MarkItDown; URLs are never inputs."""

    def __init__(self):
        self.headers = {}

    def request(self, *args, **kwargs):
        raise ConversionError("Network access is disabled for local document conversion")

    get = post = put = delete = head = options = request

    def close(self):
        pass


class MarkItDownEngine:
    engine_id = "markitdown"

    def __init__(self, *, max_bytes: int = 50 * 1024 * 1024, max_pages: int = 100):
        if (
            type(max_bytes) is not int
            or max_bytes < 1
            or type(max_pages) is not int
            or max_pages < 1
        ):
            raise ValueError("Document limits must be positive integers")
        self.max_bytes, self.max_pages = max_bytes, max_pages
        # MarkItDown 0.1.9 declares Python <3.15. Never claim an untested override
        # is a working pair on the user's Python 3.15 Windows interpreter.
        supported = sys.version_info < (3, 15) and find_spec("markitdown") is not None
        self.capabilities = tuple(
            Capability(extension, "Markdown/Text", ".md", "Markdown", self.engine_id)
            for extension, modules in _DEPENDENCIES.items()
            if supported and all(find_spec(module) is not None for module in modules)
        )

    def available(self) -> bool:
        return bool(self.capabilities)

    def convert(
        self, source: Path, extension: str, workdir: Path, progress: Progress, cancel: Event | None
    ) -> tuple[EngineOutput, ...]:
        check_cancel(cancel)
        if extension != ".md" or source.suffix.lower() not in {
            capability.input_extension for capability in self.capabilities
        }:
            raise ConversionError("This document-to-Markdown engine is unavailable or unsupported")
        if source.stat().st_size > self.max_bytes:
            raise ConversionError("Document exceeds the Markdown extraction size limit")
        progress(0.1, "Checking document")
        warnings = self._check_document(source, cancel)
        check_cancel(cancel)
        # Defense in depth if another dependency imported ONNX before this engine.
        os.environ["ORT_DISABLE_TELEMETRY"] = "1"
        import onnxruntime

        onnxruntime.disable_telemetry_events()
        from markitdown import MarkItDown
        from markitdown.converters import (
            DocxConverter,
            HtmlConverter,
            PdfConverter,
            PptxConverter,
            XlsxConverter,
        )

        local_converters = {
            ".docx": DocxConverter,
            ".pdf": PdfConverter,
            ".pptx": PptxConverter,
            ".xlsx": XlsxConverter,
            ".html": HtmlConverter,
        }
        session = RejectRequestsSession()
        progress(0.35, "Extracting Markdown locally")
        try:
            converter = MarkItDown(
                enable_builtins=False, enable_plugins=False, requests_session=session
            )
            converter.register_converter(local_converters[source.suffix.lower()]())
            result = converter.convert_local(source)
            markdown = result.markdown
        except ConversionError:
            raise
        except Exception as error:
            raise ConversionError(
                "The document is corrupt, unsupported or could not be extracted"
            ) from error
        finally:
            session.close()
        check_cancel(cancel)
        if not isinstance(markdown, str) or not markdown.strip():
            raise ConversionError(
                "No extractable document content was found; OCR is not implemented"
            )
        if len(markdown.encode("utf-8")) > self.max_bytes * 2:
            raise ConversionError("Extracted Markdown exceeds the output size limit")
        progress(0.8, "Writing UTF-8 Markdown")
        output = workdir / "output.md"
        output.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        return (EngineOutput(output, source.with_suffix(extension).name, tuple(warnings)),)

    def _check_document(self, source: Path, cancel: Event | None) -> list[str]:
        warnings = [
            (
                "Markdown is lossy content extraction: page layout, styling, images and some "
                "document structure may not be preserved. No OCR or cloud service is used."
            ),
        ]
        suffix = source.suffix.lower()
        if suffix in _OFFICE_DOCUMENTS:
            try:
                with ZipFile(source) as archive:
                    if sum(info.file_size for info in archive.infolist()) > self.max_bytes * 4:
                        raise ConversionError("Expanded Office document exceeds the size limit")
                    if archive.testzip() is not None:
                        raise ConversionError("The Office document archive is corrupt")
                    if "[Content_Types].xml" not in archive.namelist():
                        raise ConversionError("The input is not a supported Office document")
                    ElementTree.fromstring(archive.read(_OFFICE_DOCUMENTS[suffix]))
            except (BadZipFile, KeyError, ElementTree.ParseError, RuntimeError) as error:
                raise ConversionError(
                    "The Office document is corrupt or has the wrong format"
                ) from error
        elif suffix == ".pdf":
            import pymupdf

            try:
                document = pymupdf.open(source)
            except (RuntimeError, ValueError) as error:
                raise ConversionError("The PDF is unreadable or corrupt") from error
            text_pages = 0
            with document:
                if not document.is_pdf or document.needs_pass:
                    raise ConversionError("Input must be an unencrypted PDF")
                if not 0 < document.page_count <= self.max_pages:
                    raise ConversionError("PDF exceeds the Markdown page limit or is empty")
                count = document.page_count
                for page in document:
                    check_cancel(cancel)
                    text_pages += bool(page.get_text("text").strip())
            if not text_pages:
                raise ConversionError("No extractable PDF text; scanned or blank PDFs require OCR")
            if text_pages < count:
                warnings.append(
                    "Some PDF pages have no extractable text; scanned content requires OCR."
                )
        elif suffix == ".html":
            # Restrict this engine to actual HTML, not arbitrary renamed binaries
            # or remote URL targets that MarkItDown also supports elsewhere.
            prefix = source.read_bytes()[:65536].decode("utf-8-sig", errors="replace")
            if not re.search(
                r"<(?:!doctype\s+html|html|head|body|h[1-6]|p|div|table|ul|ol)(?:\s|>)",
                prefix,
                re.IGNORECASE,
            ):
                raise ConversionError("The input does not contain recognizable HTML")
        return warnings

    def validate(self, output: EngineOutput) -> None:
        try:
            text = output.path.read_text(encoding="utf-8")
        except UnicodeError as error:
            raise ConversionError("Generated Markdown is not valid UTF-8") from error
        if not text.strip() or "\x00" in text:
            raise ConversionError("Generated Markdown is empty or contains binary content")
