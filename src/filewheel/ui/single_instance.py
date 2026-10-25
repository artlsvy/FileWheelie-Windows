"""Current-user bounded local IPC for repeated frozen/source GUI invocations."""
import hashlib
import json
from time import monotonic

from PySide6.QtCore import QLockFile, QObject, QTimer, Slot
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from filewheel.converters.debugging import debug_log_path, record_failure

MAX_MESSAGE = 262_144


def valid_packet(packet):
    if not isinstance(packet, dict) or set(packet) != {'paths', 'point'}:
        return False
    paths, point = packet['paths'], packet['point']
    return (isinstance(paths, list) and len(paths) <= 1
            and all(isinstance(path, str) and 0 < len(path) <= 32767 for path in paths)
            and isinstance(point, list) and len(point) == 2
            and all(type(value) is int and -(2**31) <= value < 2**31 for value in point))


def reply_outcome(reply):
    if (not isinstance(reply, dict) or set(reply) != {'accepted'}
            or type(reply['accepted']) is not bool):
        return 'invalid'
    return 'forwarded' if reply['accepted'] else 'busy'


class SingleInstance(QObject):
    def __init__(self, on_request, *, directory=None, parent=None):
        super().__init__(parent)
        self.on_request = on_request
        root = debug_log_path().parent if directory is None else directory
        root.mkdir(parents=True, exist_ok=True)
        self.name = 'filewheel-' + hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:24]
        self.lock = QLockFile(str(root / 'application.lock'))
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._connections)
        self._clients = set()
        self.owner = False

    def acquire_or_forward(self, packet, *, timeout=2500):
        if not valid_packet(packet):
            return 'invalid'
        if self.lock.tryLock(0):
            # Only an exclusive lock owner may remove a dead endpoint.
            QLocalServer.removeServer(self.name)
            if not self.server.listen(self.name):
                self.lock.unlock()
                raise RuntimeError('Could not create local Filewheel endpoint')
            self.owner = True
            return 'owner'
        expires = monotonic() + timeout / 1000
        socket = QLocalSocket()
        try:
            while monotonic() < expires:
                socket.connectToServer(self.name)
                if socket.waitForConnected(100):
                    break
                socket.abort()
            if socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
                return 'unresponsive'
            payload = json.dumps(packet, ensure_ascii=True).encode() + b'\n'
            if len(payload) > MAX_MESSAGE:
                return 'invalid'
            socket.write(payload)
            socket.waitForBytesWritten(max(1, int((expires-monotonic())*1000)))
            reply_bytes = bytearray()
            while b'\n' not in reply_bytes and monotonic() < expires:
                if not socket.bytesAvailable() and not socket.waitForReadyRead(max(1, int((expires-monotonic())*1000))):
                    return 'unresponsive'
                reply_bytes.extend(bytes(socket.readAll()))
                if len(reply_bytes) > 1024:
                    return 'invalid'
            reply = json.loads(bytes(reply_bytes))
            return reply_outcome(reply)
        except (ValueError, UnicodeError):
            return 'invalid'
        finally:
            socket.abort()

    @Slot()
    def _connections(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if len(self._clients) >= 8:
                socket.abort(); socket.deleteLater(); continue
            self._clients.add(socket)
            socket.setReadBufferSize(MAX_MESSAGE + 1)
            socket._packet = bytearray()
            socket._handled = False
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda s=socket: s.abort())
            timer.start(3000)
            socket._deadline = timer
            socket.readyRead.connect(lambda s=socket: self._receive(s))
            socket.disconnected.connect(lambda s=socket: self._discard(s))
            if socket.bytesAvailable():
                self._receive(socket)

    def _discard(self, socket):
        self._clients.discard(socket)
        socket.deleteLater()

    def _receive(self, socket):
        if socket._handled:
            socket.abort()
            return
        socket._packet.extend(bytes(socket.readAll()))
        if len(socket._packet) > MAX_MESSAGE:
            socket.abort(); return
        if b'\n' not in socket._packet:
            return
        socket._handled = True
        socket._deadline.stop()
        accepted = False
        try:
            raw, tail = bytes(socket._packet).split(b'\n', 1)
            packet = json.loads(raw)
            if not tail and valid_packet(packet):
                accepted = bool(self.on_request(packet))
        except (ValueError, TypeError, RuntimeError, OSError) as error:
            record_failure('application', 'local_request', error)
        socket.write(json.dumps({'accepted': accepted}).encode() + b'\n')
        socket.flush()
        socket.disconnectFromServer()

    def close(self):
        for socket in tuple(self._clients):
            socket.abort()
        self.server.close()
        if self.owner:
            self.lock.unlock()
            self.owner = False
