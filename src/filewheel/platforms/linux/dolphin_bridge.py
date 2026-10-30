"""Explicitly launched private-Dolphin event source. Never scans the desktop."""

import hmac
import secrets
import tempfile
from pathlib import Path
from time import monotonic, monotonic_ns
from urllib.parse import unquote_to_bytes, urlsplit

from PySide6.QtCore import SLOT, QObject, QProcess, QProcessEnvironment, Signal, Slot
from PySide6.QtDBus import QDBusConnection, QDBusMessage

from filewheel.platforms.linux.paths import validate_paths


def validated_click(values, *, token, previous, now):
    if len(values) != 4:
        raise ValueError("Invalid click payload")
    supplied, uri, sequence, captured = values
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied.encode(), token.encode()):
        raise ValueError("Wrong bridge run")
    if (
        type(sequence) is not int
        or sequence <= previous
        or type(captured) is not int
        or not 0 <= now - captured <= 2_000_000_000
    ):
        raise ValueError("Stale or replayed click")
    if not isinstance(uri, str) or len(uri) > 8192:
        raise ValueError("Invalid URI")
    parsed = urlsplit(uri)
    if parsed.scheme != "file" or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("Only local files are supported")
    path = unquote_to_bytes(parsed.path).decode("utf-8", errors="strict")
    validation = validate_paths([path])
    if validation.path is None:
        raise ValueError(validation.rejection)
    return str(validation.path), sequence, captured


class DolphinBridge(QObject):
    clicked = Signal(str, object)
    error = Signal(str)

    def __init__(self, executable, parent=None):
        super().__init__(parent)
        self.executable = Path(executable).resolve(strict=True)
        self.token = secrets.token_hex(32)
        self.sequence = 0
        self.enabled = True
        self.closing_at = None
        self.bus = QDBusConnection.sessionBus()
        self.process = QProcess(self)
        self.process.setProgram(str(self.executable))
        self.process.errorOccurred.connect(
            lambda _: self.error.emit("Private Dolphin could not run")
        )
        self.process.finished.connect(
            lambda *_: self.error.emit(
                "Private Dolphin closed; explicit-file invocation remains available"
            )
        )
        if not self.bus.connect(
            "",
            "/org/filewheel/DolphinProbe",
            "org.filewheel.DolphinProbe",
            "MiddleClicked",
            self,
            SLOT("message(QDBusMessage)"),
        ):
            raise RuntimeError("Could not connect the opt-in Dolphin signal")
        self.config = tempfile.TemporaryDirectory(prefix="filewheel-dolphin-config-")
        env = QProcessEnvironment.systemEnvironment()
        for key, sub in (
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_DATA_HOME", "data"),
        ):
            directory = Path(self.config.name) / sub
            directory.mkdir()
            env.insert(key, str(directory))
        env.insert("FILEWHEEL_DOLPHIN_PROBE_DEST", self.bus.baseService())
        env.insert("FILEWHEEL_DOLPHIN_PROBE_TOKEN", self.token)
        env.insert("QT_QPA_PLATFORM", "wayland")
        libraries = self.executable.parent.parent / "lib/x86_64-linux-gnu"
        if not libraries.is_dir():
            raise RuntimeError("Keep the complete private Dolphin prefix together")
        env.insert("LD_LIBRARY_PATH", str(libraries))
        # Do not let a frozen Filewheel Qt plugin path contaminate system-Qt Dolphin.
        for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH"):
            env.remove(key)
        self.process.setProcessEnvironment(env)

    def start(self, folder):
        if self.process.state() != QProcess.NotRunning:
            return False
        self.sequence = 0
        self.process.setArguments(["--new-window", str(Path(folder).resolve(strict=True))])
        self.process.start()

    @Slot(QDBusMessage)
    def message(self, message):
        if not self.enabled:
            return
        reply = self.bus.interface().servicePid(message.service())
        if not reply.isValid() or reply.value() != self.process.processId():
            return
        try:
            if Path(f"/proc/{reply.value()}/exe").resolve() != self.executable:
                return
            path, self.sequence, captured = validated_click(
                message.arguments(), token=self.token, previous=self.sequence, now=monotonic_ns()
            )
        except ValueError, OSError, UnicodeError:
            return
        self.clicked.emit(path, captured)

    def close(self, timeout=0):
        self.bus.disconnect(
            "",
            "/org/filewheel/DolphinProbe",
            "org.filewheel.DolphinProbe",
            "MiddleClicked",
            self,
            SLOT("message(QDBusMessage)"),
        )
        if self.process.state() != QProcess.NotRunning:
            # Asynchronous close; never wait on the GUI thread.
            if self.closing_at is None:
                self.closing_at = monotonic()
                self.process.terminate()
            elif monotonic() - self.closing_at > 1.5:
                self.process.kill()
            return False
        self.config.cleanup()
        return True
