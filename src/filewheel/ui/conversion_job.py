"""Qt supervisor; real converters run in a spawned interpreter, not the hook GIL."""
from threading import Event

from PySide6.QtCore import QThread, Signal

from filewheel.converters.manager import ConversionManager
from filewheel.converters.process_worker import ProgressThrottle, run_in_process


class ConversionJob(QThread):
    progress_changed = Signal(float, str)
    outcome = Signal(object, object)

    def __init__(self, manager, source, extension, parent=None):
        super().__init__(parent)
        self.manager, self.source, self.extension = manager, source, extension
        self.cancelled = Event()
        self.worker_pid = None

    def run(self):
        try:
            report = ProgressThrottle(lambda value, message: self.progress_changed.emit(value, message))
            if type(self.manager) is ConversionManager:
                result = run_in_process(self.manager, self.source, self.extension,
                                        progress=report, cancel=self.cancelled,
                                        on_started=self._started_child)
            else:
                # Explicit injected-manager seam for portable Qt lifecycle tests.
                # Production ConversionManager never falls back to a shared GIL.
                result = self.manager.convert(self.source, self.extension,
                                              progress=report, cancel=self.cancelled)
            self.outcome.emit(result, None)
        except Exception as error:  # noqa: BLE001 - worker boundary must report all engine failures
            self.outcome.emit(None, error)

    def _started_child(self, pid):
        self.worker_pid = pid
