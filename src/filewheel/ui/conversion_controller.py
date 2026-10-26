"""Application-owned conversion lifetime, independent of popup visibility."""
from PySide6.QtCore import QObject, Signal

from filewheel.converters.base import ConversionError
from filewheel.ui.conversion_job import ConversionJob


class ConversionController(QObject):
    progress = Signal(float, str)
    completed = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job = None
        self._outcome = None

    def start(self, manager, source, extension):
        if self.job is not None:
            return False
        self._outcome = None
        self.job = ConversionJob(manager, source, extension, self)
        self.job.progress_changed.connect(self.progress)
        self.job.outcome.connect(self._capture)
        self.job.finished.connect(self._finished)
        self.job.start()
        return True

    def cancel(self):
        if self.job is not None:
            self.job.cancelled.set()

    def _capture(self, result, error):
        self._outcome = result, error

    def _finished(self):
        # QThread has actually stopped. Never join a worker from the GUI thread
        # while its outcome is still being delivered or native cleanup runs.
        job, self.job = self.job, None
        result, error = self._outcome or (None, ConversionError('Conversion worker stopped without a result'))
        self._outcome = None
        if job is not None:
            job.deleteLater()
        self.completed.emit(result, error)
