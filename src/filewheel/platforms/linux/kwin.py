"""Opt-in current-session scripted KWin bridge; owned scripts, no installation."""

import json
import os
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtDBus import (
    QDBus,
    QDBusConnection,
    QDBusMessage,
    QDBusPendingCallWatcher,
    QDBusVirtualObject,
)


class _Reports(QDBusVirtualObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner

    def introspect(self, path):
        return '<interface name="org.filewheel.Position"><method name="Report"><arg type="s" direction="in"/></method></interface>'

    def handleMessage(self, message, connection):
        values = message.arguments()
        if (
            message.interface() != "org.filewheel.Position"
            or message.member() != "Report"
            or message.service() != self.owner.kwin_owner
            or len(values) != 1
            or not isinstance(values[0], str)
            or len(values[0]) > 4096
        ):
            return False
        connection.send(message.createReply())
        try:
            data = json.loads(values[0])
            self.owner.deliver(data)
        except ValueError, TypeError, KeyError:
            pass
        return True


class KWinBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bus = QDBusConnection.sessionBus()
        reply = self.bus.interface().serviceOwner("org.kde.KWin")
        if not reply.isValid():
            raise RuntimeError("KWin is unavailable; native cursor placement cannot be promised")
        self.kwin_owner = reply.value()
        self.path = "/org/filewheel/Position"
        self.reports = _Reports(self)
        if not self.bus.registerVirtualObject(self.path, self.reports):
            raise RuntimeError("Could not register scoped KWin bridge")
        self.pending = {}
        self.scripts = {}
        self.directory = tempfile.TemporaryDirectory(prefix="filewheel-kwin-")
        self.closed = False

    def call(self, path, method, args, done=None):
        message = QDBusMessage.createMethodCall(
            "org.kde.KWin",
            path,
            "org.kde.kwin.Scripting" if path == "/Scripting" else "org.kde.kwin.Script",
            method,
        )
        message.setArguments(args)
        watcher = QDBusPendingCallWatcher(self.bus.asyncCall(message, 500), self)

        def finished(w):
            reply = w.reply()
            if done:
                done(reply)
            w.deleteLater()

        watcher.finished.connect(finished)

    def run(self, script, callback=None, *, retain=False):
        if self.closed:
            if callback:
                callback(None)
            return
        token = uuid.uuid4().hex
        name = "filewheel-" + token
        file = Path(self.directory.name) / (token + ".js")
        suffix = "\ncallDBus(DEST, '/org/filewheel/Position', 'org.filewheel.Position', 'Report', JSON.stringify({token:TOKEN,point:[workspace.cursorPos.x,workspace.cursorPos.y]}));"
        file.write_text(
            (script + suffix)
            .replace("DEST", json.dumps(self.bus.baseService()))
            .replace("TOKEN", json.dumps(token))
        )
        self.scripts[token] = (name, file, retain)
        timer = QTimer(self)
        timer.setSingleShot(True)
        self.pending[token] = (callback, timer)
        timer.timeout.connect(lambda: self.complete(token, None))
        timer.start(1200)

        def loaded(reply):
            if (
                reply.type() == QDBusMessage.ErrorMessage
                or not reply.arguments()
                or reply.arguments()[0] < 0
            ):
                self.complete(token, None)
                return
            if self.closed or token not in self.pending:
                self.call("/Scripting", "unloadScript", [name])
                return
            self.call("/Scripting/Script" + str(reply.arguments()[0]), "run", [])

        self.call("/Scripting", "loadScript", [str(file), name], loaded)

    def deliver(self, data):
        point = data["point"]
        if (
            not isinstance(point, list)
            or len(point) != 2
            or any(type(x) not in (int, float) for x in point)
        ):
            return
        self.complete(data["token"], tuple(round(x) for x in point))

    def complete(self, token, point):
        entry = self.pending.pop(token, None)
        if entry is None:
            return
        callback, timer = entry
        timer.stop()
        timer.deleteLater()
        name, file, retain = self.scripts[token]
        if not retain or point is None:
            self.call("/Scripting", "unloadScript", [name])
            file.unlink(missing_ok=True)
            self.scripts.pop(token, None)
        if callback and not self.closed:
            callback(point)

    def install_placement(self, callback=None):
        self.run(
            """
var lastArea=null;
function place(w) {
 if(w.pid!==APP_PID)return;
 var caption=w.caption;
 if(caption.indexOf('Filewheel — ')!==0 && caption!=='Filewheel progress')return;
 var area=workspace.clientArea(KWin.MaximizeArea,w);
 var g=w.frameGeometry;
 var p=workspace.cursorPos;
 var x,y;
 if(caption==='Filewheel progress') {
  area=lastArea||area;x=area.x+area.width-g.width-16;y=area.y+area.height-g.height-16;
 } else {
  lastArea=area;x=p.x-g.width/2;y=p.y-g.height/2;
 }
 w.frameGeometry={x:Math.max(area.x,Math.min(x,area.x+area.width-g.width)),
  y:Math.max(area.y,Math.min(y,area.y+area.height-g.height)),width:g.width,height:g.height};
 w.keepAbove=true;
 if(caption.indexOf('Filewheel — ')===0) workspace.activeWindow=w;
}
workspace.windowAdded.connect(place);
""".replace("APP_PID", str(os.getpid())),
            callback,
            retain=True,
        )

    def request_point(self, callback):
        self.run("", callback)

    def close(self):
        self.closed = True
        for token in list(self.pending):
            self.complete(token, None)
        # Shutdown is bounded and may precede Qt event-loop termination.
        for name, file, _ in self.scripts.values():
            message = QDBusMessage.createMethodCall(
                "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", "unloadScript"
            )
            message.setArguments([name])
            self.bus.call(message, QDBus.CallMode.Block, 500)
        self.scripts.clear()
        self.bus.unregisterObject(self.path)
        self.directory.cleanup()
