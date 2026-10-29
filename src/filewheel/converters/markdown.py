"""Offline MarkItDown Python API for explicitly supported local document types."""

import os
import posixpath
import re
import sys
from importlib.util import find_spec
from pathlib import Path
from threading import Event
from typing import ClassVar
from urllib.parse import quote, unquote, urlsplit
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

# Must precede any MarkItDown/Magika/ONNX import, including lazy conversions.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

from filewheel.converters.archive_safety import ArchiveLimits, read_archive, safe_member_name
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
    ".htm": ("bs4",),
    ".epub": ("bs4", "defusedxml"),
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
    execution_timeouts: ClassVar[dict[str, float]] = {".epub": 10.}

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
        warnings, pdf_needs_ocr = self._check_document(source, cancel)
        if pdf_needs_ocr:
            return self._ocr_pdf_markdown(source, workdir, progress, cancel)
        local_source = source
        if source.suffix.lower() == '.epub':
            members = self._check_epub(source, cancel)
            local_source = workdir / 'validated.epub'
            # Upstream reads only the immutable validated member snapshot, never
            # an original archive that could change after preflight.
            with ZipFile(local_source, 'w') as archive:
                archive.writestr('mimetype', members['mimetype'])
                for name, data in members.items():
                    check_cancel(cancel)
                    if name != 'mimetype':
                        archive.writestr(name, data)
        check_cancel(cancel)
        # Defense in depth if another dependency imported ONNX before this engine.
        os.environ["ORT_DISABLE_TELEMETRY"] = "1"
        import onnxruntime

        onnxruntime.disable_telemetry_events()
        from markitdown import MarkItDown
        from markitdown.converters import (
            DocxConverter,
            EpubConverter,
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
            ".htm": HtmlConverter,
            ".epub": EpubConverter,
        }
        session = RejectRequestsSession()
        progress(0.35, "Extracting Markdown locally")
        try:
            converter = MarkItDown(
                enable_builtins=False, enable_plugins=False, requests_session=session
            )
            converter.register_converter(local_converters[source.suffix.lower()]())
            result = converter.convert_local(local_source)
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
                "No extractable document content was found"
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
                "document structure may not be preserved. No cloud service is used."
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
                return warnings, True
            if text_pages < count:
                warnings.append(
                    "Some PDF pages have no extractable text; scanned content requires OCR."
                )
        elif suffix in (".html", ".htm"):
            # Restrict this engine to actual HTML, not arbitrary renamed binaries
            # or remote URL targets that MarkItDown also supports elsewhere.
            prefix = source.read_bytes()[:65536].decode("utf-8-sig", errors="replace")
            if not re.search(
                r"<(?:!doctype\s+html|html|head|body|h[1-6]|p|div|table|ul|ol)(?:\s|>)",
                prefix,
                re.IGNORECASE,
            ):
                raise ConversionError("The input does not contain recognizable HTML")
        return warnings, False

    def _ocr_pdf_markdown(self, source, workdir, progress, cancel):
        from filewheel.converters.windows_ocr import ocr_pdf_pages

        sections = []
        images = []
        languages = set()
        recognized = False
        image_tag = uuid4().hex
        for number, lines, language, image in ocr_pdf_pages(source, workdir, progress, cancel):
            check_cancel(cancel)
            languages.add(language)
            useful = [line.strip() for line in lines if line.strip()]
            recognized |= bool(useful)
            # Manager may rename colliding outputs when the same PDF is
            # converted again. A fresh tag keeps Markdown links paired with
            # this conversion's own page images.
            name = f'{source.stem}-{image_tag}-page-{number}.png'
            sections.append(f'## Page {number}\n\n' + '\n'.join(useful)
                            + f'\n\n![Original page {number}]({quote(name)})')
            images.append(EngineOutput(image, name))
        if not recognized:
            raise ConversionError('Local OCR could not recognize any text in this PDF. No Markdown was created.')
        markdown = ('# ' + source.stem + '\n\n'
                    + '\n\n'.join(sections).rstrip() + '\n')
        if len(markdown.encode('utf-8')) > self.max_bytes * 2:
            raise ConversionError('Extracted Markdown exceeds the output size limit')
        check_cancel(cancel)
        progress(.8, 'Writing OCR Markdown and page images')
        output = workdir / 'output.md'
        output.write_text(markdown, encoding='utf-8')
        warning = (f'Local Windows OCR ({", ".join(sorted(languages))}) was used. '
                   'Review recognized text; original page images are linked beside the Markdown file.')
        return (EngineOutput(output, source.with_suffix('.md').name, (warning,)), *images)

    def _check_epub(self, source, cancel):
        from defusedxml import ElementTree as SafeXML
        from defusedxml.common import DefusedXmlException
        members = read_archive(source, limits=ArchiveLimits(members=512), cancel=cancel)
        if members.get('mimetype', b'').strip() != b'application/epub+zip':
            raise ConversionError('Input is not an EPUB archive')
        try:
            container = SafeXML.fromstring(members['META-INF/container.xml'], forbid_dtd=True)
            roots = [node for node in container.iter() if node.tag.split('}')[-1] == 'rootfile']
            if not roots:
                raise ConversionError('EPUB has no package root')
            opf = safe_member_name(roots[0].get('full-path', ''))
            package = SafeXML.fromstring(members[opf], forbid_dtd=True)
            manifest = {}
            for node in package.iter():
                check_cancel(cancel)
                if node.tag.split('}')[-1] != 'item':
                    continue
                identity, href = node.get('id'), node.get('href', '')
                if not identity or identity in manifest:
                    raise ConversionError('EPUB manifest has missing or duplicate identifiers')
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or parsed.path.startswith('/'):
                    raise ConversionError('External EPUB resources are unsupported')
                path = safe_member_name(posixpath.normpath(posixpath.join(posixpath.dirname(opf), unquote(parsed.path))))
                manifest[identity] = (path, node.get('media-type'))
            if any(name.lower().endswith(('.zip', '.epub', '.docx', '.pptx', '.xlsx')) for name in members):
                raise ConversionError('Nested archives inside EPUB are unsupported')
            spine = [node.get('idref') for node in package.iter() if node.tag.split('}')[-1] == 'itemref']
            if not spine:
                raise ConversionError('EPUB has no readable spine')
            for identity in spine:
                check_cancel(cancel)
                path, media = manifest[identity]
                if path not in members or media not in ('application/xhtml+xml', 'text/html'):
                    raise ConversionError('EPUB spine contains missing or unsupported content')
                if media == 'application/xhtml+xml':
                    # Standard XHTML DOCTYPE is allowed, but entity declarations
                    # and external entities are rejected before HTML extraction.
                    SafeXML.fromstring(members[path], forbid_entities=True, forbid_external=True)
                elif re.search(r'<!\s*ENTITY', members[path].decode('utf-8-sig'), re.IGNORECASE):
                    raise ConversionError('EPUB content entities are unsupported')
            return members
        except (KeyError, SafeXML.ParseError, DefusedXmlException, ValueError) as error:
            raise ConversionError('EPUB package is corrupt, unsafe or incomplete') from error

    def validate(self, output: EngineOutput) -> None:
        if output.path.suffix.lower() == '.png':
            from PIL import Image

            try:
                with Image.open(output.path) as image:
                    if image.format != 'PNG' or image.width < 1 or image.height < 1:
                        raise ConversionError('Generated Markdown page image is invalid')
                    image.verify()
            except (OSError, ValueError) as error:
                raise ConversionError('Generated Markdown page image is invalid') from error
            return
        try:
            text = output.path.read_text(encoding="utf-8")
        except UnicodeError as error:
            raise ConversionError("Generated Markdown is not valid UTF-8") from error
        if not text.strip() or "\x00" in text:
            raise ConversionError("Generated Markdown is empty or contains binary content")
