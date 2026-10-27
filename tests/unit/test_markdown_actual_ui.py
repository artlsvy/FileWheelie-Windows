"""Actual local Markdown engines through shared Qt jobs and both presentations."""
import os
import time
from pathlib import PureWindowsPath

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
pytest.importorskip('PySide6.QtQuick')
from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication
from test_quick_popup import pump

from filewheel.converters import ConversionManager, Registry
from filewheel.converters.pandoc import PandocEngine
from filewheel.converters.structured_markdown import StructuredMarkdownEngine
from filewheel.core.models import TargetResolution
from filewheel.ui.backend import create_popup


@pytest.mark.parametrize('backend', ['widgets', 'quick'])
@pytest.mark.parametrize('source_extension', ['.txt', '.md'])
def test_actual_markdown_families_use_shared_worker_and_observable_result(tmp_path, backend, source_extension):
    source = tmp_path / ('Résumé input' + source_extension)
    source.write_text('# Useful heading\n\nUseful text æøå.\n', encoding='utf-8')
    before = source.read_bytes()
    engine = StructuredMarkdownEngine() if source_extension == '.txt' else PandocEngine()
    if not engine.available():
        pytest.skip('Optional actual Pandoc executable unavailable')
    manager = ConversionManager(Registry((engine,)))
    app = QApplication.instance() or QApplication(['real-markdown-ui'])
    app.setQuitOnLastWindowClosed(False)
    view = create_popup(manager.registry, backend=backend, manager=manager,
                        source_mapper=lambda path: source, point_mapper=lambda p, s: p)
    try:
        target = TargetResolution(PureWindowsPath('C:/fixture') / source.name, 0, (300, 300),
                                  time.monotonic(), source='shell_explicit')
        view.present(target)
        QCursor.setPos(view.mapToGlobal(QPoint(view.width() // 2, view.height() // 2)))
        choose = view.session.choose if backend == 'quick' else view._choose
        assert view.state.options == (('To MD',) if source_extension == '.txt' else ('From MD',))
        choose(0)
        if source_extension == '.md':
            choose(next(i for i, c in enumerate(view.state.options) if c.output_extension == '.docx'))
        assert view.job is not None
        pump(app, lambda: view.job is None, seconds=15)
        assert view.last_selection.action == 'converted'
        output = view.last_selection.outputs[0]
        assert output.is_file()
        if source_extension == '.txt':
            assert 'Useful text æøå' in output.read_text(encoding='utf-8')
        assert source.read_bytes() == before
        assert not list(tmp_path.glob('.filewheel-*'))
        assert view.isVisible() or (backend == 'quick' and view.progress_view.isVisible())
    finally:
        view.shutdown()
        pump(app, lambda: view.job is None)
        if backend == 'quick':
            if view.progress_view:
                view.progress_view.setSource('')
                view.progress_view.deleteLater()
            view.setSource('')
        view.deleteLater()
        app.processEvents()
