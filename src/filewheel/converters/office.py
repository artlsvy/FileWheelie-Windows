"""Offline Office-to-PDF rendering in a bounded isolated local subprocess."""

import os
import re
import shutil
import subprocess
from importlib.util import find_spec
from pathlib import Path
from threading import Event
from time import monotonic
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from filewheel.converters.base import (
    Capability,
    ConversionCancelled,
    ConversionError,
    EngineOutput,
    check_cancel,
)
from filewheel.libreoffice_bundle import external_tool_environment, find_libreoffice

_PDF_INPUTS = {
    '.docx': ('word/document.xml', 'writer_pdf_Export'),
    '.pptx': ('ppt/presentation.xml', 'impress_pdf_Export'),
    '.xlsx': ('xl/workbook.xml', 'calc_pdf_Export'),
}


def _stop_office_tree(process, environment):
    executable = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/taskkill.exe'
    try:
        subprocess.run(
            [str(executable), '/PID', str(process.pid), '/T', '/F'],
            shell=False, capture_output=True, timeout=10, check=False,
            env=environment, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        process.kill()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class OfficeExit(int):
    """Integer-compatible exit status with bounded private diagnostic text."""
    def __new__(cls, code, stdout=b'', stderr=b''):
        result = super().__new__(cls, code)
        result.stdout = stdout[:8192].decode('utf-8', errors='replace')
        result.stderr = stderr[:8192].decode('utf-8', errors='replace')
        return result


def run_office(arguments, *, workdir, timeout, cancel=None, tool_name='LibreOffice'):
    """Bound the owned process tree and keep external libraries out of Qt's bundle."""
    process = None
    environment = None
    check_cancel(cancel)
    try:
        with external_tool_environment() as environment:
            process = subprocess.Popen(
                arguments,
                shell=False,
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except OSError:
        # If restoring the parent's DLL directory failed after Popen succeeded,
        # do not orphan a live child while reporting startup failure.
        if process is not None:
            _stop_office_tree(process, environment)
        raise
    deadline = monotonic() + timeout
    try:
        while True:
            check_cancel(cancel)
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(arguments, timeout)
            try:
                stdout, stderr = process.communicate(timeout=min(.1, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
    except ConversionCancelled:
        _stop_office_tree(process, environment)
        raise
    except subprocess.TimeoutExpired as error:
        _stop_office_tree(process, environment)
        raise ConversionError(f"{tool_name} timed out; conversion stopped") from error
    return OfficeExit(process.returncode, stdout, stderr)


class LibreOfficeEngine:
    engine_id = "libreoffice"
    capabilities = tuple(Capability(extension, 'Document', '.pdf', 'PDF', 'libreoffice')
                         for extension in _PDF_INPUTS)

    def __init__(self, *, timeout=90):
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
            raise ValueError("Timeout must be between 0 and 600 seconds")
        self.timeout = timeout

    def location(self):
        return find_libreoffice()

    def executable(self):
        location = self.location()
        return str(location.executable) if location is not None else None

    def available(self):
        return self.executable() is not None and find_spec("pymupdf") is not None

    def convert(self, source: Path, extension: str, workdir: Path, progress, cancel: Event | None):
        check_cancel(cancel)
        executable = self.executable()
        if not executable:
            raise ConversionError("LibreOffice is required for Office-to-PDF conversion")
        source_extension = source.suffix.lower()
        if source_extension not in _PDF_INPUTS or extension != ".pdf":
            raise ConversionError("Unsupported Office conversion")
        required_part, pdf_filter = _PDF_INPUTS[source_extension]
        if source.stat().st_size > 50 * 1024 * 1024:
            raise ConversionError("Office input exceeds the 50 MiB limit")
        try:
            with ZipFile(source) as archive:
                if sum(item.file_size for item in archive.infolist()) > 200 * 1024 * 1024:
                    raise ConversionError("Expanded Office document exceeds the size limit")
                if any("vbaproject" in name.lower() for name in archive.namelist()):
                    raise ConversionError("Macro-containing documents are not supported")
                if source_extension == '.xlsx':
                    for name in archive.namelist():
                        lowered = name.lower()
                        if (lowered == 'xl/connections.xml' or lowered.startswith(
                                ('xl/externallinks/', 'xl/querytables/', 'xl/macrosheets/'))):
                            raise ConversionError('External spreadsheet data and macro sheets are unsupported')
                        if lowered == 'xl/workbook.xml' or (
                                lowered.startswith('xl/worksheets/') and lowered.endswith('.xml')):
                            sheet = ElementTree.fromstring(archive.read(name))
                            for element in sheet.iter():
                                if element.tag.rsplit('}', 1)[-1] not in ('f', 'definedName'):
                                    continue
                                formula = element.text or ''
                                if ('|' in formula or '://' in formula or re.search(
                                    r'\b(?:WEBSERVICE|DDE|RTD|IMAGE|HYPERLINK|CALL|REGISTER|EXEC)\s*\(',
                                        formula, re.IGNORECASE)):
                                    raise ConversionError('Network or active spreadsheet formulas are unsupported')
                for name in archive.namelist():
                    if name.endswith(".rels"):
                        relations = ElementTree.fromstring(archive.read(name))
                        for relation in relations:
                            if relation.get("TargetMode") == "External" and not relation.get(
                                "Type", ""
                            ).endswith("/hyperlink"):
                                raise ConversionError("External document resources are unsupported")
                if required_part not in archive.namelist() or archive.testzip():
                    raise ConversionError("The input is not a readable Office document")
        except (BadZipFile, ElementTree.ParseError) as error:
            raise ConversionError("The input is not a readable Office document") from error
        # Copy only to our private directory. Fixed local input name avoids CLI
        # option/URI interpretation and path-dependent exporter names.
        local = workdir / ('input' + source_extension)
        shutil.copyfile(source, local)
        output_dir = workdir / "rendered"
        output_dir.mkdir()
        profile = (workdir / "profile").as_uri()
        progress(0.2, "Rendering with LibreOffice")
        returncode = run_office(
            [
                executable,
                f"-env:UserInstallation={profile}",
                "--headless",
                "--nologo",
                "--nodefault",
                "--norestore",
                "--convert-to",
                'pdf:' + pdf_filter,
                "--outdir",
                str(output_dir),
                str(local),
            ],
            workdir=workdir,
            timeout=self.timeout,
            cancel=cancel,
        )
        check_cancel(cancel)
        generated = output_dir / "input.pdf"
        if returncode != 0 or not generated.is_file():
            cause = RuntimeError(f"LibreOffice exit={int(returncode)} stdout={getattr(returncode, 'stdout', '')!r} stderr={getattr(returncode, 'stderr', '')!r}")
            raise ConversionError("LibreOffice could not render the document; see debug log") from cause
        output = workdir / "output.pdf"
        generated.replace(output)
        progress(0.8, "Checking PDF output")
        return (
            EngineOutput(
                output,
                source.with_suffix(".pdf").name,
                ("Layout and fonts depend on installed LibreOffice fonts.",),
            ),
        )

    def validate(self, output):
        import pymupdf

        with pymupdf.open(output.path) as document:
            if not document.is_pdf or document.needs_pass or document.page_count < 1:
                raise ConversionError("LibreOffice output is not a readable PDF")
            for page in document:
                if min(page.rect.width, page.rect.height) <= 0:
                    raise ConversionError("LibreOffice output has an invalid page")
