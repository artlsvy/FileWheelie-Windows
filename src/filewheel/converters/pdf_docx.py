"""Best-effort editable PDF→DOCX via local pdf2docx; no OCR or Office required."""

from importlib.util import find_spec
from pathlib import Path
from threading import Event
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from filewheel.converters.base import (
    Capability,
    ConversionError,
    EngineOutput,
    Progress,
    check_cancel,
)


class PdfDocxEngine:
    engine_id = "pdf2docx"
    capabilities = (Capability(".pdf", "Document", ".docx", "DOCX", engine_id),)

    def __init__(self, *, max_pages: int = 100, max_bytes: int = 50 * 1024 * 1024):
        if type(max_pages) is not int or max_pages < 1 or type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("PDF limits must be positive integers")
        self.max_pages = max_pages
        self.max_bytes = max_bytes

    def available(self) -> bool:
        return all(find_spec(module) is not None for module in ("pdf2docx", "pymupdf", "docx"))

    def convert(self, source: Path, extension: str, workdir: Path,
                progress: Progress, cancel: Event | None) -> tuple[EngineOutput, ...]:
        import pymupdf
        from pdf2docx import Converter

        check_cancel(cancel)
        if source.suffix.lower() != ".pdf" or extension != ".docx":
            raise ConversionError("Unsupported PDF conversion")
        if source.stat().st_size > self.max_bytes:
            raise ConversionError("PDF exceeds the editable-conversion size limit")
        progress(.1, "Checking PDF text")
        try:
            document = pymupdf.open(source)
        except (RuntimeError, ValueError) as error:
            raise ConversionError("The PDF is unreadable or corrupt") from error
        text_pages = 0
        empty_pages = 0
        with document:
            if not document.is_pdf:
                raise ConversionError("The input is not a PDF")
            if document.needs_pass:
                raise ConversionError("Password-protected PDFs are not supported")
            if not 0 < document.page_count <= self.max_pages:
                raise ConversionError("PDF exceeds the editable-conversion page limit or is empty")
            for index, page in enumerate(document):
                check_cancel(cancel)
                if page.get_text("text").strip():
                    text_pages += 1
                else:
                    empty_pages += 1
                progress(.1 + .15 * (index + 1) / document.page_count, "Inspecting PDF pages")
        if not text_pages:
            raise ConversionError(
                "No extractable text: this PDF may be scanned or blank. "
                "Editable text requires OCR, which is not implemented."
            )
        check_cancel(cancel)
        output = workdir / "output.docx"
        progress(.35, "Reconstructing editable document")
        converter = Converter(str(source))
        try:
            # Fail on page errors rather than silently publishing a partial DOCX.
            # OCR/cloud services and converter-internal multiprocessing stay off.
            converter.convert(str(output), multi_processing=False, ignore_page_error=False,
                              raw_exceptions=True, ocr=0)
        except Exception as error:
            raise ConversionError("PDF layout reconstruction failed") from error
        finally:
            converter.close()
        check_cancel(cancel)
        progress(.8, "Validating editable document")
        warnings = [
            ("PDF→DOCX reconstructs editable text and basic layout; fonts, tables and "
            "complex positioning may differ from the PDF."),
        ]
        if empty_pages:
            warnings.append(
                f"{empty_pages} page(s) contain no extractable text; scanned content remains "
                "non-editable and may require OCR. Blank pages may also be included."
            )
        return (EngineOutput(output, source.with_suffix(extension).name, tuple(warnings)),)

    def validate(self, output: EngineOutput) -> None:
        try:
            with ZipFile(output.path) as archive:
                if archive.testzip() is not None:
                    raise ConversionError("Generated DOCX has corrupt archive content")
                if "[Content_Types].xml" not in archive.namelist():
                    raise ConversionError("Generated DOCX lacks required document metadata")
                document = ElementTree.fromstring(archive.read("word/document.xml"))
                namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                text = "".join(node.text or "" for node in document.iter(namespace + "t")).strip()
                if not text:
                    raise ConversionError("Generated DOCX contains no editable text")
        except (BadZipFile, KeyError, ElementTree.ParseError) as error:
            raise ConversionError("Generated DOCX failed document validation") from error
