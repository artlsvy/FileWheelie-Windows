"""Packaged local smoke checks. No user documents, network or persistent outputs."""
import hashlib
import json
import tempfile
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from filewheel.converters import ConversionManager
from filewheel.converters.debugging import debug_log_path, record_failure


def run(*, include_quick=False):
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
        if include_quick:
            # Explicit opt-in: exercise actual QML/plugin loading and rendering,
            # not just Python imports. No user file or conversion is involved.
            from pathlib import PureWindowsPath
            from time import monotonic

            from filewheel.core.models import TargetResolution
            from filewheel.ui.quick_popup import GlassPopup
            application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(['Quick self-test'])
            application.setQuitOnLastWindowClosed(False)
            view = GlassPopup(manager.registry, point_mapper=lambda p, screens: p)
            try:
                # Plugin/raster smoke is deterministic, independent of the
                # interactive selection entrance's intentional first-frame alpha.
                view.session._reduced = True
                view.session.appearanceChanged.emit()
                center = application.primaryScreen().availableGeometry().center()
                view.present(TargetResolution(PureWindowsPath('C:/preview/self-test.png'), 0,
                                              (center.x(), center.y()), monotonic(), source='shell_explicit'))
                application.processEvents()
                view.session.choose(0)
                view.session.hoverAt(195, 120)
                application.processEvents()
                image = view.grabWindow()
                pixels = round(240 * view.devicePixelRatio())
                if (image.isNull() or image.width() != pixels or image.height() != pixels
                        or image.pixelColor(0, 0).alpha() != 0
                        or image.pixelColor(pixels // 2, pixels // 2).alpha() == 0):
                    raise RuntimeError('Quick render or transparent-corner self-test failed')
                results.append({'quick_qml_render': True, 'corner_alpha': 0,
                                'graphics_api': str(view.rendererInterface().graphicsApi()), 'ok': True})
                # The progress surface is a separate lazy QML resource. Verify
                # it renders in frozen/source mode too, without running a job.
                from filewheel.ui.progress_state import ProgressMode
                view.session._reduced = True
                view.session.appearanceChanged.emit()
                view.state.stage = 'result'
                view.session._status = 'Converted'
                view.session.presentation_state.mode = ProgressMode.SUCCEEDED
                view.session._refresh()
                view.set_persistent(True)
                view.collapse_progress()
                application.processEvents()
                if view.progress_view is None:
                    raise RuntimeError('Quick progress surface was unavailable')
                pill = view.progress_view.grabWindow()
                dpr = view.progress_view.devicePixelRatio()
                if (pill.isNull() or pill.width() != round(272*dpr) or pill.height() != round(72*dpr)
                        or pill.pixelColor(0, 0).alpha() != 0
                        or pill.pixelColor(round(25*dpr), round(25*dpr)).alpha() == 0):
                    raise RuntimeError('Quick progress surface render failed')
                results.append({'quick_progress_render': True, 'ok': True})
            finally:
                view.dismiss()
                if view.progress_view is not None:
                    view.progress_view.setSource('')
                    view.progress_view.deleteLater()
                view.setSource('')
                view.deleteLater()
                application.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        office = manager.registry.engines.get('libreoffice')
        if office is not None and hasattr(office, 'location'):
            location = office.location()
            results.append({'libreoffice_source': location.source,
                            'libreoffice_executable': str(location.executable), 'ok': True})
        pandoc = manager.registry.engines.get('pandoc')
        results.append({'pandoc': pandoc.location.version if pandoc else 'unavailable',
                        'pandoc_source': pandoc.location.source if pandoc else None,
                        'optional': True, 'ok': True})
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
            for suffix, text in (('.txt', 'Useful Unicode text æøå'),
                                 ('.csv', 'Name,Count\nWidgets,42'),
                                 ('.json', '{"useful": true, "value": 42}'),
                                 ('.xml', '<book title="Résumé"><chapter>Useful content</chapter></book>'),
                                 ('.htm', '<h1>Useful heading</h1><p>Local text</p>')):
                local = root / ('Résumé input' + suffix)
                local.write_text(text, encoding='utf-8')
                pairs.append((local, '.md'))
            epub = root / 'book.epub'
            with ZipFile(epub, 'w', compression=ZIP_STORED) as archive:
                archive.writestr('mimetype', 'application/epub+zip')
                archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="book.opf"/></rootfiles></container>')
                archive.writestr('book.opf', '<package xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Useful book</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/></spine></package>')
                archive.writestr('one.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Useful chapter</h1><p>Local book text</p></body></html>')
            collection = root / 'collection.zip'
            with ZipFile(collection, 'w', compression=ZIP_STORED) as archive:
                archive.writestr('notes.txt', 'Useful local archive text')
                archive.writestr('values.csv', 'Name,Value\nWidgets,42')
            pairs.extend(((epub, '.md'), (collection, '.md')))
            if pandoc is not None:
                markdown = root / 'publish.md'
                markdown.write_text('# Useful publishing heading\n\n- Local item\n\n| Name | Value |\n|---|---|\n| Widgets | 42 |\n\n![Local raster](image.png)\n', encoding='utf-8')
                pairs.extend((markdown, c.output_extension) for c in pandoc.capabilities)
            for source, extension in pairs:
                before = hashlib.sha256(source.read_bytes()).digest()
                result = manager.convert(source, extension)
                if hashlib.sha256(source.read_bytes()).digest() != before:
                    raise RuntimeError('Conversion smoke changed its source fixture')
                if extension == '.md' and not result.path.read_text(encoding='utf-8').strip():
                    raise RuntimeError('Markdown smoke generated no useful content')
                results.append({'pair': source.suffix + '->' + extension, 'engine': result.engine_id,
                                'outputs': len(result.outputs), 'ok': True})
            first_jpeg = root / 'image.jpg'
            first_hash = hashlib.sha256(first_jpeg.read_bytes()).digest()
            collision = manager.convert(image, '.jpg')
            if collision.path == first_jpeg or hashlib.sha256(first_jpeg.read_bytes()).digest() != first_hash:
                raise RuntimeError('Collision smoke replaced a pre-existing output')
            results.append({'collision_safe': True, 'ok': True})
            if getattr(sys, 'frozen', False):
                # Exercise THIS frozen executable as a multiprocessing worker.
                # Onefile children must reuse the parent's extraction directory.
                from threading import Event

                from filewheel.converters.base import ConversionCancelled
                from filewheel.converters.process_worker import run_in_process

                worker_ids = []
                spawned = run_in_process(manager, image, '.jpg', progress=lambda *args: None,
                                         cancel=Event(), on_started=worker_ids.append)
                if not spawned.path.is_file() or not worker_ids:
                    raise RuntimeError('Frozen conversion child produced no valid result')
                before_cancel = set(root.iterdir())
                cancelled = Event()
                def cancel_started(pid):
                    worker_ids.append(pid)
                    cancelled.set()
                try:
                    run_in_process(manager, image, '.jpg', progress=lambda *args: None,
                                   cancel=cancelled, on_started=cancel_started)
                except ConversionCancelled:
                    pass
                else:
                    raise RuntimeError('Frozen cancellation did not cancel')
                if set(root.iterdir()) != before_cancel:
                    raise RuntimeError('Frozen cancelled child leaked files or staging')
                retry = run_in_process(manager, image, '.jpg', progress=lambda *args: None,
                                       cancel=Event(), on_started=worker_ids.append)
                if not retry.path.is_file():
                    raise RuntimeError('Frozen cancellation retry failed')
                results.append({'frozen_spawn_cancel_retry': True,
                                'workers': len(worker_ids), 'ok': True})
            if list(root.glob('.filewheel-*')):
                raise RuntimeError('Conversion smoke leaked staging files')
            if any(c.input_extension == '.docx'  and c.output_extension == '.pdf' for c in manager.registry.capabilities):
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
