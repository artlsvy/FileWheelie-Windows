"""Packaged local smoke checks. No user documents, network or persistent outputs."""
import json
import tempfile
from pathlib import Path

from filewheel.converters import ConversionManager
from filewheel.converters.debugging import debug_log_path, record_failure


def run():
    results = []
    try:
        import pymupdf
        from docx import Document
        from openpyxl import Workbook
        from PIL import Image
        from pptx import Presentation
        from PySide6 import QtCore, QtGui, QtWidgets
        results.append({'qt_version': QtCore.qVersion(), 'widgets': QtWidgets.QWidget.__name__,
                        'image_width': QtGui.QImage(1, 1, QtGui.QImage.Format.Format_RGB32).width(), 'ok': True})
        import sys
        if sys.platform == "win32":
            import comtypes.client
            results.append({"comtypes": comtypes.__version__, "ok": True})
        manager = ConversionManager()
        office = manager.registry.engines.get('libreoffice')
        if office is not None and hasattr(office, 'location'):
            location = office.location()
            results.append({'libreoffice_source': location.source,
                            'libreoffice_executable': str(location.executable), 'ok': True})
        with tempfile.TemporaryDirectory(prefix='filewheel-selftest-') as folder:
            root = Path(folder)
            image = root / 'image.png'
            Image.new('RGBA', (32, 24), (100, 30, 10, 128)).save(image)
            pdf = root / 'editable.pdf'
            with pymupdf.open() as document:
                document.new_page().insert_text((50, 60), 'Editable Filewheel smoke text')
                document.save(pdf)
            docx = root / 'document.docx'
            document = Document(); document.add_heading('Filewheel heading', 1); document.save(docx)
            pptx = root / 'slides.pptx'
            slides = Presentation(); slide = slides.slides.add_slide(slides.slide_layouts[1]); slide.shapes.title.text = 'Slide text'; slides.save(pptx)
            xlsx = root / 'sheet.xlsx'
            book = Workbook(); book.active.append(['Heading', 'Value']); book.active.append(['Row', 1]); book.save(xlsx); book.close()
            html = root / 'page.html'; html.write_text('<h1>HTML smoke</h1><p>Local text</p>', encoding='utf-8')
            pairs = [(image, '.jpg'), (image, '.webp'), (image, '.pdf'), (pdf, '.docx'),
                     (pdf, '.png'), (docx, '.md'), (pdf, '.md'), (pptx, '.md'), (xlsx, '.md'), (html, '.md')]
            for source, extension in pairs:
                result = manager.convert(source, extension)
                results.append({'pair': source.suffix + '->' + extension, 'engine': result.engine_id,
                                'outputs': len(result.outputs), 'ok': True})
            if any(c.input_extension == '.docx' and c.output_extension == '.pdf' for c in manager.registry.capabilities):
                result = manager.convert(docx, '.pdf')
                results.append({'pair': '.docx->.pdf', 'engine': result.engine_id, 'ok': True})
            else:
                results.append({'pair': '.docx->.pdf', 'skipped': 'LibreOffice not installed/bundled'})
        report = {'ok': True, 'results': results}
        code = 0
    except Exception as error:  # noqa: BLE001 - frozen diagnostic entry
        path = record_failure('self-test', 'conversion_smoke', error)
        report = {'ok': False, 'results': results, 'error_type': type(error).__name__, 'debug_log': str(path)}
        code = 1
    path = debug_log_path().parent / 'self-test.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return code
