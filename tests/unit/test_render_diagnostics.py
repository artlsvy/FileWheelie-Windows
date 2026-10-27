import json
from unittest.mock import Mock

from test_progress_pill import app as app  # noqa: PLC0414

from filewheel.ui import render_diagnostics
from filewheel.ui.quick_popup import GlassPopup


def test_trace_disabled_keeps_only_backend_evidence(app, monkeypatch):
    monkeypatch.delenv('FILEWHEEL_UI_TRACE', raising=False)
    logger = Mock()
    monkeypatch.setattr(render_diagnostics, '_get_logger', lambda: logger)
    view = GlassPopup()
    trace = view.render_diagnostics
    trace.snapshot('ignored')
    logger.warning.assert_not_called()
    trace._initialized()
    record = json.loads(logger.warning.call_args.args[0])
    assert record['api'] == 'Software'
    assert record['event'] == 'scenegraph_initialized'
    view.deleteLater()


def test_trace_is_bounded_and_omits_private_properties(app, monkeypatch):
    monkeypatch.setenv('FILEWHEEL_UI_TRACE', '1')
    monkeypatch.setenv('QSG_RHI_BACKEND', 'C:/private/name.txt')
    logger = Mock()
    monkeypatch.setattr(render_diagnostics, '_get_logger', lambda: logger)
    view = GlassPopup()
    trace = view.render_diagnostics
    view.setTitle('private-name.txt')
    trace._initialized()
    trace.snapshot('operator_snapshot')
    values = [call.args[0] for call in logger.warning.call_args_list]
    assert not any('private' in value for value in values)
    trace.count = 10000
    logger.reset_mock()
    trace.snapshot('ignored')
    logger.warning.assert_not_called()
    view.deleteLater()
