"""Short display labels retain the exact multi-page export semantics."""
from filewheel.converters.pdf_images import PdfImagesEngine


def test_pdf_image_labels_are_short_and_describe_all_pages():
    caps = {c.output_extension: c for c in PdfImagesEngine._possible_capabilities}
    assert caps['.jpg'].label == 'JPG'
    assert caps['.png'].label == 'PNG'
    for suffix, label in (('.jpg', 'JPG'), ('.png', 'PNG')):
        assert caps[suffix].description == f'Export all PDF pages as {label} images'
        assert caps[suffix].input_extension == '.pdf'
        assert caps[suffix].engine_id == 'pymupdf-images'


def test_quick_format_tooltip_retains_page_export_description():
    import os
    import time
    from pathlib import PureWindowsPath

    import pytest
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    pytest.importorskip('PySide6.QtQuick')
    from PySide6.QtWidgets import QApplication

    from filewheel.converters.registry import Registry
    from filewheel.core.models import TargetResolution
    from filewheel.ui.quick_popup import GlassPopup
    engine = PdfImagesEngine()
    if not engine.available():
        pytest.skip('Optional PDF image dependencies unavailable')
    app = QApplication.instance() or QApplication(['short-labels'])
    app.setQuitOnLastWindowClosed(False)
    view = GlassPopup(Registry((engine,)), point_mapper=lambda p, s: p)
    try:
        view.session._reduced = True
        view.session.appearanceChanged.emit()
        view.present(TargetResolution(PureWindowsPath('C:/fixtures/pages.pdf'), 0, (300, 300),
                                      time.monotonic(), source='shell_explicit'))
        view.session.choose(0)
        assert view.session.labels == ['PNG', 'JPG']
        view.session.hoverAt(44, 120)
        assert view._tooltip_text() == 'Export all PDF pages as JPG images'
    finally:
        view.dismiss()
        view.setSource('')
        view.deleteLater()
        app.processEvents()
