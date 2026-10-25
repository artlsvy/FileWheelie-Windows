import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication

    from filewheel.ui.single_instance import SingleInstance, reply_outcome, valid_packet
    QT = True
except ImportError:
    QT = False


@unittest.skipUnless(QT, 'Qt optional')
class InstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['instance-tests'])

    def test_repeated_launch_forwards_to_one_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            directory = Path(folder)
            owner = SingleInstance(lambda packet: calls.append(packet) or True, directory=directory)
            packet = {'paths':['C:/example.png'], 'point':[-200,400]}
            self.assertEqual(owner.acquire_or_forward(packet), 'owner')
            script = """
import json,sys
from pathlib import Path
from PySide6.QtCore import QCoreApplication
from filewheel.ui.single_instance import SingleInstance
app=QCoreApplication(['client'])
instance=SingleInstance(lambda packet:False,directory=Path(sys.argv[1]))
print(instance.acquire_or_forward(json.loads(sys.argv[2])), flush=True)
instance.close()
"""
            try:
                import json
                for _ in range(2):
                    client = subprocess.Popen([sys.executable, '-c', script, str(directory), json.dumps(packet)],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    end = time.monotonic() + 5
                    while client.poll() is None and time.monotonic() < end:
                        self.app.processEvents(); time.sleep(.005)
                    if client.poll() is None:
                        client.kill()
                    out, err = client.communicate(timeout=2)
                    self.assertEqual(out.strip(), 'forwarded', f'calls={calls} errors={err}')
                self.assertEqual(calls, [packet,packet])
            finally:
                owner.close()
            replacement = SingleInstance(lambda packet: True, directory=directory)
            self.assertEqual(replacement.acquire_or_forward(packet), 'owner')
            replacement.close()

    def test_packet_cannot_enable_experiment_or_batch_paths(self):
        self.assertTrue(valid_packet({'paths':[], 'point':[0,0]}))
        self.assertFalse(valid_packet({'paths':['a','b'], 'point':[0,0]}))
        self.assertFalse(valid_packet({'paths':['a'], 'point':[True,0]}))
        self.assertFalse(valid_packet({'paths':['a'], 'point':[0,0], 'experimental':True}))

    def test_malformed_replies_reject_without_attribute_errors(self):
        for reply in (None, [], 42, 'message', {}, {'accepted':1}, {'accepted':True,'extra':1}):
            with self.subTest(reply=reply):
                self.assertEqual(reply_outcome(reply), 'invalid')
        self.assertEqual(reply_outcome({'accepted': True}), 'forwarded')
        self.assertEqual(reply_outcome({'accepted': False}), 'busy')
