"""Optional LibreOffice DOCX rendering in a bounded isolated local subprocess."""
import os
import shutil
import signal
import subprocess
from importlib.util import find_spec
from pathlib import Path
from threading import Event
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from filewheel.converters.base import Capability, ConversionError, EngineOutput, check_cancel


def run_office(arguments, *, workdir, timeout):
    """Bound the owned process tree, not only LibreOffice's launcher process."""
    process = subprocess.Popen(arguments, shell=False, cwd=workdir,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=os.name != 'nt',
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        if os.name == 'nt':
            # Only this still-running child tree is targeted; never user Office.
            try:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               shell=False, capture_output=True, timeout=10, check=False)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        raise ConversionError('LibreOffice timed out; conversion stopped') from error
    return process.returncode


class LibreOfficeEngine:
    engine_id = 'libreoffice'
    capabilities = (Capability('.docx', 'Document', '.pdf', 'PDF', engine_id),)

    def __init__(self, *, timeout=90):
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
            raise ValueError('Timeout must be between 0 and 600 seconds')
        self.timeout = timeout

    def executable(self):
        for name in (('soffice.com', 'libreoffice', 'soffice') if os.name == 'nt' else
                     ('libreoffice', 'soffice')):
            candidate = shutil.which(name)
            if candidate:
                return candidate
        if os.name == 'nt':
            for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)'):
                root = os.environ.get(variable)
                if root:
                    for name in ('soffice.com', 'soffice.exe'):
                        candidate = Path(root) / 'LibreOffice/program' / name
                        if candidate.is_file():
                            return str(candidate)
        return None

    def available(self):
        return self.executable() is not None and find_spec('pymupdf') is not None

    def convert(self, source: Path, extension: str, workdir: Path, progress, cancel: Event | None):
        check_cancel(cancel)
        executable = self.executable()
        if not executable:
            raise ConversionError('Install LibreOffice to convert DOCX to PDF')
        if source.suffix.lower() != '.docx' or extension != '.pdf':
            raise ConversionError('Unsupported Office conversion')
        if source.stat().st_size > 50 * 1024 * 1024:
            raise ConversionError('Office input exceeds the 50 MiB limit')
        try:
            with ZipFile(source) as archive:
                if sum(item.file_size for item in archive.infolist()) > 200 * 1024 * 1024:
                    raise ConversionError('Expanded Office document exceeds the size limit')
                if any('vbaProject' in name for name in archive.namelist()):
                    raise ConversionError('Macro-containing documents are not supported')
                for name in archive.namelist():
                    if name.endswith('.rels'):
                        relations = ElementTree.fromstring(archive.read(name))
                        for relation in relations:
                            if (relation.get('TargetMode') == 'External'
                                    and not relation.get('Type', '').endswith('/hyperlink')):
                                raise ConversionError('External document resources are unsupported')
                if 'word/document.xml' not in archive.namelist() or archive.testzip():
                    raise ConversionError('The input is not a readable DOCX')
        except (BadZipFile, ElementTree.ParseError) as error:
            raise ConversionError('The input is not a readable DOCX') from error
        # Copy only to our private directory. Fixed local input name avoids CLI
        # option/URI interpretation and path-dependent exporter names.
        local = workdir / 'input.docx'
        shutil.copyfile(source, local)
        output_dir = workdir / 'rendered'
        output_dir.mkdir()
        profile = (workdir / 'profile').as_uri()
        progress(.2, 'Rendering with LibreOffice')
        returncode = run_office([
            executable, f'-env:UserInstallation={profile}', '--headless',
            '--nologo', '--nodefault', '--norestore', '--convert-to',
            'pdf:writer_pdf_Export', '--outdir', str(output_dir), str(local),
        ], workdir=workdir, timeout=self.timeout)
        check_cancel(cancel)
        generated = output_dir / 'input.pdf'
        if returncode != 0 or not generated.is_file():
            raise ConversionError('LibreOffice could not render the document')
        output = workdir / 'output.pdf'
        generated.replace(output)
        progress(.8, 'Checking PDF output')
        return (EngineOutput(output, source.with_suffix('.pdf').name,
                             ('Layout and fonts depend on installed LibreOffice fonts.',)),)

    def validate(self, output):
        import pymupdf
        with pymupdf.open(output.path) as document:
            if not document.is_pdf or document.needs_pass or document.page_count < 1:
                raise ConversionError('LibreOffice output is not a readable PDF')
            for page in document:
                if min(page.rect.width, page.rect.height) <= 0:
                    raise ConversionError('LibreOffice output has an invalid page')
