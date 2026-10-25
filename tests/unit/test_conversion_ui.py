"""Real image conversion through the Qt worker, with no GUI-thread engine calls."""
import os
import tempfile
import time
import unittest
from pathlib import Path, PureWindowsPath

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PIL import Image
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    from filewheel.converters import ConversionManager
    from filewheel.ui.popup import RadialPopup
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
from filewheel.core.models import TargetResolution


@unittest.skipUnless(AVAILABLE, 'Qt and Pillow required')
class ConversionUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['test'])
        cls.app.setQuitOnLastWindowClosed(False)

    def wait(self, predicate):
        deadline = time.monotonic() + 5
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def test_real_worker_converts_and_result_is_shown(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'Unicode æ input.png'
            Image.new('RGBA', (24, 18), (255, 0, 0, 0)).save(source)
            original = source.read_bytes()
            manager = ConversionManager()
            popup = RadialPopup(manager.registry, manager=manager,
                                source_mapper=lambda path: source,
                                point_mapper=lambda point, screens: point)
            target = TargetResolution(PureWindowsPath('C:/fixture/input.png'), 0,
                                      (300, 300), 1, 'shell_explicit')
            try:
                popup.present(target)
                popup._choose(0)
                popup._choose(0)
                self.assertEqual(popup.state.stage, 'converting')
                self.wait(lambda: popup.job is None)
                self.assertEqual(popup.status_title, 'Converted')
                self.assertEqual(popup.last_selection.action, 'converted')
                with Image.open(popup.conversion_result.path) as output:
                    self.assertEqual(output.format, 'JPEG')
                    self.assertEqual(output.size, (24, 18))
                self.assertEqual(source.read_bytes(), original)
            finally:
                popup.close()
                self.app.processEvents()
                popup.deleteLater()
                self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_background_failure_is_result_not_uncaught_qt_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'bad.png'
            source.write_bytes(b'not PNG')
            manager = ConversionManager()
            popup = RadialPopup(manager.registry, manager=manager,
                                source_mapper=lambda path: source,
                                point_mapper=lambda point, screens: point)
            try:
                popup.present(TargetResolution(PureWindowsPath('C:/bad.png'), 0,
                                               (300, 300), 1, 'shell_explicit'))
                popup._choose(0)
                popup._choose(0)
                self.wait(lambda: popup.job is None)
                self.assertEqual(popup.status_title, 'Conversion failed')
                self.assertEqual(list(Path(folder).iterdir()), [source])
            finally:
                popup.close()
                popup.deleteLater()
                self.app.processEvents()

    def test_selected_subscriber_dismissal_waits_for_worker_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'cancel.png'
            Image.new('RGB', (20, 20)).save(source)
            manager = ConversionManager()
            popup = RadialPopup(manager.registry, manager=manager,
                                source_mapper=lambda path: source,
                                point_mapper=lambda point, screens: point)
            completions = []
            popup.finished.connect(lambda: completions.append(True))
            popup.selected.connect(lambda selection: popup.dismiss())
            try:
                popup.present(TargetResolution(PureWindowsPath('C:/cancel.png'), 0,
                                               (300, 300), 1, 'shell_explicit'))
                popup._choose(0)
                popup._choose(0)
                self.wait(lambda: popup.job is None)
                self.assertEqual(completions, [True])
                self.assertFalse(popup.isVisible())
                self.assertFalse(list(Path(folder).glob('.filewheel-*')))
            finally:
                popup.close()
                popup.deleteLater()
                self.app.processEvents()
