"""A short-lived Qt worker; converter code never accesses widgets."""
from threading import Event

from PySide6.QtCore import QThread, Signal


class ConversionJob(QThread):
    progress_changed = Signal(float, str)
    outcome = Signal(object, object)

    def __init__(self, manager, source, extension, parent=None):
        super().__init__(parent)
        self.manager, self.source, self.extension = manager, source, extension
        self.cancelled = Event()

    def run(self):
        try:
            result = self.manager.convert(
                self.source, self.extension,
                progress=lambda value, message: self.progress_changed.emit(value, message),
                cancel=self.cancelled,
            )
            self.outcome.emit(result, None)
        except Exception as error:  # noqa: BLE001 - worker boundary must report all engine failures
            self.outcome.emit(None, error)
