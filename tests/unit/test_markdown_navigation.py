"""Real registry navigation and both renderers use the same direct MD route."""
import os
import time
from pathlib import PureWindowsPath

import pytest

from filewheel.converters.base import Capability
from filewheel.converters.registry import Registry
from filewheel.core.models import TargetResolution
from filewheel.ui.radial import RadialState


class DeclaredEngine:
    engine_id = 'fixture'
    capabilities = (Capability('.docx', 'Document', '.pdf', 'PDF', engine_id),
                    Capability('.docx', 'Markdown/Text', '.md', 'Markdown', engine_id),
                    Capability('.md', 'Document', '.docx', 'DOCX', engine_id),
                    Capability('.md', 'Markdown/Text', '.html', 'HTML', engine_id))

    def available(self):
        return True


def test_capability_derived_navigation_preserves_document_and_extraction_distinction():
    registry = Registry((DeclaredEngine(),))
    assert registry.categories(PureWindowsPath('C:/a.docx')) == ('Document', 'To MD')
    assert [c.output_extension for c in registry.formats(PureWindowsPath('a.docx'), 'To MD')] == ['.md']
    assert registry.categories(PureWindowsPath('C:/a.MD')) == ('From MD',)
    assert [c.output_extension for c in registry.formats(PureWindowsPath('a.md'), 'From MD')] == ['.docx', '.html']
    assert not Registry(()).categories(PureWindowsPath('a.md'))
    assert not registry.categories(PureWindowsPath('a.exe'))
    state = RadialState(registry)
    state.open(TargetResolution(PureWindowsPath('C:/a.docx'), 0, (300, 300), time.monotonic(), 'shell_explicit'))
    assert state.choose(1).output_extension == '.md'
    assert state.stage == 'confirmation'


@pytest.mark.parametrize('backend', ['widgets', 'quick'])
def test_direct_to_md_starts_shared_job_and_preserves_busy_target(backend):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    pytest.importorskip('PySide6.QtQuick')
    from PySide6.QtWidgets import QApplication
    from test_persistent_progress import BlockingManager
    from test_quick_popup import pump

    from filewheel.ui.backend import create_popup
    app = QApplication.instance() or QApplication(['markdown-navigation'])
    app.setQuitOnLastWindowClosed(False)
    manager = BlockingManager()
    manager.registry = Registry((DeclaredEngine(),))
    view = create_popup(manager.registry, backend=backend, manager=manager, point_mapper=lambda p, s: p)
    try:
        target = TargetResolution(PureWindowsPath('C:/a.docx'), 0, (300, 300), time.monotonic(), 'shell_explicit')
        view.present(target)
        if backend == 'quick':
            view.session.choose(1)
        else:
            view._choose(1)
        pump(app, manager.started.is_set)
        assert view.state.stage == 'converting'
        assert view.job.extension == '.md'
        assert not view.present(target)
        if backend == 'quick':
            view.collapse_progress()
            assert view.progress_view.isVisible()
        assert not view.job.cancelled.is_set()
        manager.release.set()
        pump(app, lambda: view.job is None)
        assert view.last_selection.action == 'converted'
    finally:
        manager.release.set()
        view.shutdown()
        pump(app, lambda: view.job is None)
        if backend == 'quick':
            if view.progress_view:
                view.progress_view.setSource('')
                view.progress_view.deleteLater()
            view.setSource('')
        view.deleteLater()
        app.processEvents()
