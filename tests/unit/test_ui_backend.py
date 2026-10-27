"""Renderer selection is reversible and never changes controller consent."""
import os
import time
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
pytest.importorskip('PySide6.QtQuick')
from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_desktop_consent import FakeRuntime
from test_quick_popup import pump

from filewheel.core.experimental import ExperimentalCandidate
from filewheel.core.explicit_paths import FileCheck
from filewheel.ui.backend import create_popup
from filewheel.ui.desktop import DesktopApplication
from filewheel.ui.popup import RadialPopup
from filewheel.ui.quick_popup import GlassPopup
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv('FILEWHEEL_LOG_DIR', str(tmp_path / 'logs'))
    application = QApplication.instance() or QApplication(['backend-tests'])
    application.setQuitOnLastWindowClosed(False)
    return application


def dispose(view, app):
    view.dismiss()
    pump(app, lambda: view.job is None)
    if isinstance(view, GlassPopup):
        view.setSource(QUrl())
    view.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_default_widget_and_quick_opt_in_are_reversible(app, monkeypatch):
    monkeypatch.delenv('FILEWHEEL_UI_BACKEND', raising=False)
    classic = create_popup(DEFAULT_PREVIEW_REGISTRY)
    assert isinstance(classic, RadialPopup)
    dispose(classic, app)
    monkeypatch.setenv('FILEWHEEL_UI_BACKEND', 'quick')
    quick = create_popup(DEFAULT_PREVIEW_REGISTRY)
    assert isinstance(quick, GlassPopup)
    dispose(quick, app)
    classic = create_popup(DEFAULT_PREVIEW_REGISTRY, backend='widgets')
    assert isinstance(classic, RadialPopup)
    dispose(classic, app)


def test_missing_module_and_qml_load_error_use_widget(app, monkeypatch):
    with patch('filewheel.ui.quick_popup.GlassPopup', side_effect=ImportError('missing Quick module')):
        view = create_popup(DEFAULT_PREVIEW_REGISTRY, backend='quick')
    assert isinstance(view, RadialPopup)
    dispose(view, app)
    def missing_scene(registry, **options):
        return GlassPopup(registry, _scene_file=Path('/absent/Filewheel/GlassWheel.qml'), **options)
    with patch('filewheel.ui.quick_popup.GlassPopup', side_effect=missing_scene):
        view = create_popup(DEFAULT_PREVIEW_REGISTRY, backend='quick')
    assert isinstance(view, RadialPopup)
    dispose(view, app)


def test_bad_quick_scene_releases_failed_top_level_window(app, tmp_path):
    before = len(app.allWindows())
    with pytest.raises(RuntimeError, match='Quick scene failed'):
        GlassPopup(_scene_file=tmp_path / 'missing.qml')
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert len(app.allWindows()) <= before


def test_unknown_backend_fails_safe_without_importing_quick(app):
    with patch('filewheel.ui.quick_popup.GlassPopup', side_effect=AssertionError('not requested')):
        view = create_popup(DEFAULT_PREVIEW_REGISTRY, backend='typo')
    assert isinstance(view, RadialPopup)
    dispose(view, app)


def test_quick_host_keeps_explicit_controller_validation_and_injected_consent(app):
    checked = []
    def inspect(path):
        checked.append(path)
        return FileCheck(True, True)
    host = DesktopApplication(tray=True, ui_backend='quick', runtime_factory=FakeRuntime,
                              inspector=inspect, point_mapper=lambda p, s: p)
    try:
        assert isinstance(host.popup, GlassPopup)
        assert not host.present_explicit([], (300, 300))
        assert not host.popup.isVisible()
        assert host.present_explicit(['C:/image.png'], (300, 300))
        assert host.popup.state.target.source == 'shell_explicit'
        host.popup.dismiss()
        host.set_confirmation(False)
        host.set_experiment(True, persist=False)
        pump(app, lambda: host._startup is None)
        now = time.monotonic()
        candidate = ExperimentalCandidate(PureWindowsPath('C:/image.png'), (300, 300),
                                          now-.1, now, native_flags=1)
        host.runtime.gate.offer(candidate)
        host.offer_candidate(candidate)
        assert host.dialog is not None
        assert not host.popup.isVisible()
        QTest.mouseClick(host.confirm_button, Qt.MouseButton.LeftButton)
        app.processEvents()
        assert host.popup.isVisible()
        assert host.popup.state.target.source == 'user_confirmed_candidate'
        assert len(checked) == 2
    finally:
        with patch.object(app, 'quit'):
            host.request_quit()
        dispose(host.popup, app)
        host.deleteLater()
        app.processEvents()


def test_quick_smoke_rejects_blank_transparent_frame(app, tmp_path):
    from PySide6.QtGui import QColor, QImage

    from filewheel import selftest
    blank = QImage(240, 240, QImage.Format.Format_ARGB32)
    blank.fill(QColor('transparent'))
    with patch.object(GlassPopup, 'grabWindow', return_value=blank):
        assert selftest.run(include_quick=True) == 1
    import json
    report = json.loads((tmp_path / 'logs/self-test.json').read_text())
    assert report['ok'] is False
    assert not any(row.get('quick_qml_render') for row in report['results'])


def test_selftest_cli_quick_is_explicit(app):
    from filewheel import app as entry
    with patch('filewheel.selftest.run', return_value=0) as run:
        assert entry.main(['--self-test', '--ui-backend', 'quick']) == 0
        run.assert_called_once_with(include_quick=True)
