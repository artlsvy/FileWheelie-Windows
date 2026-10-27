"""Bounded local lifecycle evidence. Never records paths or Qt error text."""
import json
import logging
import os
import platform
from logging.handlers import RotatingFileHandler
from time import monotonic

import PySide6
from PySide6.QtCore import QEvent, QObject, Qt, Slot, qVersion

from filewheel.converters.debugging import debug_log_path

_logger = None


def _get_logger():
    global _logger
    if _logger is None:
        path = debug_log_path().with_name('ui-renderer.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=1_000_000,
                                      backupCount=2, encoding='utf-8')
        _logger = logging.getLogger('filewheel.ui')
        _logger.propagate = False
        _logger.addHandler(handler)
    return _logger


def _setting(key, allowed):
    value = os.getenv(key, '')
    return value if value in allowed else 'other'


def record_instance(outcome):
    """Explain forwarding without logging the invocation or its file path."""
    try:
        _get_logger().warning(json.dumps({'event': 'single_instance', 'pid': os.getpid(),
            'outcome': outcome, 'qt': qVersion(), 'pyside': PySide6.__version__,
            'windows': platform.version(),
            'quick': _setting('QT_QUICK_BACKEND', ('', 'software', 'rhi')),
            'rhi': _setting('QSG_RHI_BACKEND', ('', 'opengl', 'd3d11', 'd3d12', 'vulkan', 'metal', 'null'))}))
    except OSError:
        pass


class RenderDiagnostics(QObject):
    def __init__(self, window, label):
        super().__init__(window)
        self.window, self.label = window, label
        self.api = window.rendererInterface().graphicsApi().name
        self.sequence = 0
        self.enabled = os.getenv('FILEWHEEL_UI_TRACE') == '1'
        self.count = 0
        self.frames = 0
        self.last_frame = None
        self._first_frame_seen = False
        # Never enter Python on the render thread while GUI code holds the GIL.
        # Qt documents graphicsApi() as callable on any thread (not getResource).
        window.sceneGraphInitialized.connect(self._initialized, Qt.ConnectionType.QueuedConnection)
        window.sceneGraphInvalidated.connect(self._invalidated, Qt.ConnectionType.QueuedConnection)
        window.sceneGraphError.connect(self._failed, Qt.ConnectionType.QueuedConnection)
        window.frameSwapped.connect(self._first_frame, Qt.ConnectionType.QueuedConnection)
        if self.enabled:
            window.installEventFilter(self)
            window.frameSwapped.connect(self._frame, Qt.ConnectionType.QueuedConnection)
        window.destroyed.connect(lambda: self.record('destroyed'))
        self.record('created')

    @Slot()
    def _first_frame(self):
        # Already queued notifications can arrive after disconnecting.
        if self._first_frame_seen:
            return
        self._first_frame_seen = True
        self.window.frameSwapped.disconnect(self._first_frame)
        self.api = self.window.rendererInterface().graphicsApi().name
        self.record('first_frame', always=True)

    @Slot()
    def _frame(self):
        self.frames += 1
        self.last_frame = monotonic()

    @Slot()
    def _initialized(self):
        self.api = self.window.rendererInterface().graphicsApi().name
        self.record('scenegraph_initialized', always=True, qt=qVersion(),
                    pyside=PySide6.__version__, windows=platform.version(),
                    quick=_setting('QT_QUICK_BACKEND', ('', 'software', 'rhi')),
                    rhi=_setting('QSG_RHI_BACKEND', ('', 'opengl', 'd3d11', 'd3d12', 'vulkan', 'metal', 'null')))

    @Slot()
    def _invalidated(self):
        self.record('scenegraph_invalidated')

    @Slot()
    def _failed(self):
        self.record('scenegraph_error', always=True)

    def record(self, event, *, always=False, **fields):
        if (not self.enabled and not always) or self.count >= 10000:
            return
        self.count += 1
        try:
            _get_logger().warning(json.dumps(dict(event=event, pid=os.getpid(),
                surface=self.label, sequence=self.sequence, api=self.api,
                time=round(monotonic(), 3), **fields)))
        except OSError:
            pass

    def snapshot(self, event):
        if not self.enabled:
            return
        window = self.window
        owner = getattr(window, 'owner', window)
        session = getattr(owner, 'session', None)
        root = window.rootObject()
        self.record(event, visible=window.isVisible(), exposed=window.isExposed(),
                    flags=int(window.flags()), available=root is not None,
                    presentation=session.presentation if session else '',
                    entrance=root.property('entrance') if root else None,
                    frames=self.frames, last_frame=self.last_frame,
                    transitioning=getattr(owner, '_transitioning', False))

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.Expose,
                            QEvent.Type.PlatformSurface, QEvent.Type.WinIdChange):
            self.record(event.type().name,
                        surface_event=(event.surfaceEventType().name
                            if event.type() == QEvent.Type.PlatformSurface else None))
        return False
