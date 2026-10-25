"""Optional PySide6 radial preview popup. All actions are metadata-only."""

import math
import sys

from PySide6.QtCore import QEvent, QEventLoop, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from filewheel.core.models import TargetResolution
from filewheel.ui.desktop_errors import DesktopInitializationError
from filewheel.ui.placement import Rect, popup_position
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY, RadialState


def logical_point(point, screens):
    if sys.platform == "win32":
        from filewheel.platforms.windows.qt_position import logical_point as windows_point
        return windows_point(point, screens)
    return point


class RadialPopup(QWidget):
    """The same present(TargetResolution) boundary serves both invocation sources."""

    selected = Signal(object)
    finished = Signal()
    diameter = 324
    center_radius = 67
    outer_radius = 148

    def __init__(self, registry=DEFAULT_PREVIEW_REGISTRY, *, point_mapper=logical_point):
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.state = RadialState(registry)
        self.point_mapper = point_mapper
        self.hovered = -1
        self.keyboard_index = -1
        self.last_selection = None
        self._finished = True
        self._resetting = False
        self._hover_amounts = []
        self._list_offset = 0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(self.diameter, self.diameter)
        self.setWindowTitle("Filewheel preview")
        self._animation = QTimer(self)
        self._animation.setInterval(16)
        self._animation.timeout.connect(self._animate)
        self._focus_check = QTimer(self)
        self._focus_check.setSingleShot(True)
        self._focus_check.timeout.connect(self._dismiss_if_inactive)

    def present(self, target):
        self._resetting = True
        self.hide()
        self._resetting = False
        self.last_selection = None
        self.hovered = self.keyboard_index = -1
        self._list_offset = 0
        if not self.state.open(target):
            self._finish()
            return False
        app = QApplication.instance()
        try:
            point = self.point_mapper(target.point, app.screens())
            screen = app.screenAt(QPoint(round(point[0]), round(point[1])))
            if screen is None:
                raise DesktopInitializationError("find_logical_screen", {
                    "logical_point": list(point),
                    "screens": [{"name": item.name(),
                                 "geometry": [item.geometry().x(), item.geometry().y(),
                                              item.geometry().width(), item.geometry().height()]}
                                for item in app.screens()],
                })
            area = screen.availableGeometry()
            location = popup_position(point, Rect(area.x(), area.y(), area.width(), area.height()),
                                      (self.width(), self.height()))
        except Exception as error:
            self.state.dismiss()
            self._finish()
            if isinstance(error, DesktopInitializationError):
                raise
            raise DesktopInitializationError(
                "position_popup", {"error_type": type(error).__name__},
            ) from error
        self.move(*location)
        self._finished = False
        self._hover_amounts = [0.0] * len(self.state.options)
        try:
            self.show()
            self.raise_()
            self.activateWindow()
            self.setFocus(Qt.FocusReason.PopupFocusReason)
            self.update()
        except (RuntimeError, OSError) as error:
            self.dismiss()
            raise DesktopInitializationError(
                "show_popup", {"error_type": type(error).__name__},
            ) from error
        return True

    def dismiss(self):
        self.close()

    def _finish(self):
        self._animation.stop()
        self._focus_check.stop()
        if not self._finished and not self._resetting:
            self._finished = True
            self.state.dismiss()
            self.finished.emit()

    def hideEvent(self, event):
        self._finish()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._finish()
        super().closeEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._focus_check.start(0)

    def _dismiss_if_inactive(self):
        if self.isVisible() and not self.isActiveWindow():
            self.dismiss()

    def event(self, event):
        if event.type() == QEvent.Type.WindowDeactivate and self.isVisible():
            self._focus_check.start(0)
        return super().event(event)

    def _list_mode(self):
        return len(self.state.options) >= 6

    def _hit(self, point):
        x, y = point.x() - self.width() / 2, point.y() - self.height() / 2
        distance = math.hypot(x, y)
        if self.state.stage == "confirmation":
            return -2 if QRectF(54, 251, 216, 34).contains(point) else -1
        if self._list_mode():
            if QRectF(34, 34, 256, 32).contains(point):
                return -2
            index = int((point.y() - 72) // 30) + self._list_offset
            if 34 <= point.x() <= 290 and 72 <= point.y() < 282 and 0 <= index < len(self.state.options):
                return index
            return -1
        if distance < self.center_radius:
            return -2
        count = len(self.state.options)
        if distance > self.outer_radius or not count:
            return -1
        angle = (math.degrees(math.atan2(y, x)) + 90) % 360
        sweep = 360 / count
        # Match the visible separator gaps, so clicking a gap has no action.
        within = angle % sweep
        if count > 1 and (within < 1.5 or within > sweep - 1.5):
            return -1
        return int(angle // sweep)

    def mouseMoveEvent(self, event):
        self.hovered = self._hit(event.position())
        self._animation.start()
        self.update()

    def leaveEvent(self, event):
        self.hovered = -1
        self._animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        point = event.position()
        hit = self._hit(point)
        if (self.state.stage == "confirmation"
                and not QRectF(22, 35, 280, 262).contains(point)):
            self.dismiss()
        elif self._list_mode() and not QRectF(22, 22, 280, 280).contains(point):
            self.dismiss()
        elif not self.rect().contains(point.toPoint()) or (
            not self._list_mode() and self.state.stage != "confirmation"
            and math.hypot(point.x() - 162, point.y() - 162) > self.outer_radius
        ):
            self.dismiss()
        elif event.button() != Qt.MouseButton.LeftButton:
            return
        elif hit == -2:
            if self.state.stage == "confirmation":
                self.dismiss()
            else:
                self.state.back()
                self._reset_hover()
        elif hit >= 0:
            self._choose(hit)

    def _reset_hover(self):
        self.hovered = self.keyboard_index = -1
        self._list_offset = 0
        self._hover_amounts = [0.0] * len(self.state.options)
        self._animation.stop()
        self.update()

    def _choose(self, index):
        selection = self.state.choose(index)
        self._reset_hover()
        if selection is not None:
            self.last_selection = selection
            self.selected.emit(selection)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.dismiss()
        elif key in (Qt.Key.Key_Backspace, Qt.Key.Key_Left) and self.state.stage == "formats":
            self.state.back()
            self._reset_hover()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self.state.stage == "confirmation":
                self.dismiss()
            elif self.keyboard_index >= 0:
                self._choose(self.keyboard_index)
        elif key in (Qt.Key.Key_Tab, Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Up):
            count = len(self.state.options)
            if count:
                direction = -1 if key == Qt.Key.Key_Up else 1
                self.keyboard_index = (self.keyboard_index + direction) % count
                self.hovered = self.keyboard_index
                if self._list_mode():
                    self._list_offset = min(max(0, self.keyboard_index - 6), max(0, count - 7))
                self._animation.start()
                self.update()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        if self._list_mode():
            direction = -1 if event.angleDelta().y() > 0 else 1
            self._list_offset = min(max(0, self._list_offset + direction),
                                    max(0, len(self.state.options) - 7))
            self.hovered = -1
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)

    def _animate(self):
        moving = False
        for index, value in enumerate(self._hover_amounts):
            goal = 1.0 if index == self.hovered else 0.0
            updated = value + (goal - value) * .28
            if abs(updated - goal) < .015:
                updated = goal
            else:
                moving = True
            self._hover_amounts[index] = updated
        self.update()
        if not moving:
            self._animation.stop()

    def _colors(self):
        dark = self.palette().window().color().lightnessF() < .5
        return ((QColor("#17212e"), QColor("#eff5fc"), QColor("#a9b9cd"), QColor("#33465e"))
                if dark else
                (QColor("#f7f9fc"), QColor("#17283d"), QColor("#56687d"), QColor("#d5deea")))

    def _text(self, painter, rect, text, color, size=10, bold=False, wrap=False):
        painter.setPen(color)
        font = QFont("Segoe UI", size)
        font.setBold(bold)
        painter.setFont(font)
        flags = Qt.AlignmentFlag.AlignCenter
        if wrap:
            flags |= Qt.TextFlag.TextWordWrap
        else:
            text = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideMiddle, int(rect.width()))
        painter.drawText(rect, flags, text)

    def paintEvent(self, event):
        if self.state.target is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        base, foreground, muted, border = self._colors()
        # Painted ambient shadow keeps the transparent window compact and cheap.
        painter.setPen(Qt.PenStyle.NoPen)
        for spread in range(10, 0, -2):
            painter.setBrush(QColor(0, 0, 0, 3))
            painter.drawEllipse(QRectF(14-spread/2, 16-spread/2, 296+spread, 296+spread))
        painter.setBrush(base)
        painter.setPen(QPen(border, 1))
        if self.state.stage == "confirmation":
            painter.drawRoundedRect(QRectF(22, 35, 280, 262), 24, 24)
            self._text(painter, QRectF(42, 52, 240, 25), "Dry-run preview", foreground, 13, True)
            self._text(painter, QRectF(42, 82, 240, 24), "No files changed", muted, 9)
            selection = self.state.selection
            self._text(painter, QRectF(42, 113, 240, 28), selection.input_path.name, foreground, 11, True)
            self._text(painter, QRectF(42, 146, 240, 28),
                       f"{selection.original_format}  →  {selection.output_extension[1:].upper()}",
                       QColor("#3982da"), 13, True)
            self._text(painter, QRectF(42, 183, 240, 20), "Intended output", muted, 9)
            self._text(painter, QRectF(42, 207, 240, 30), selection.intended_path.name, foreground, 10)
            painter.setBrush(QColor("#236ec6"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(54, 251, 216, 34), 12, 12)
            self._text(painter, QRectF(54, 251, 216, 34), "Done", QColor("#ffffff"), 10, True)
            return
        if self._list_mode():
            painter.drawRoundedRect(QRectF(22, 22, 280, 280), 24, 24)
            self._text(painter, QRectF(34, 34, 256, 30), "‹ Back · Preview", foreground, 10, True)
            for row, option in enumerate(self.state.options[self._list_offset:self._list_offset+7]):
                index = row + self._list_offset
                rectangle = QRectF(34, 72 + row*30, 256, 28)
                if index == self.hovered:
                    painter.fillRect(rectangle, QColor(57, 130, 218, 55))
                self._text(painter, rectangle, getattr(option, "label", option), foreground, 10)
            return
        outer = QRectF(14, 14, 296, 296)
        painter.drawEllipse(outer)
        count = len(self.state.options)
        for index, option in enumerate(self.state.options):
            sweep = 360 / count
            start = -90 + index * sweep
            gap = 1.5 if count > 1 else 0
            path = QPainterPath()
            path.moveTo(162, 162)
            angle = math.radians(start + gap)
            path.lineTo(162 + 148*math.cos(angle), 162 + 148*math.sin(angle))
            path.arcTo(outer, -(start+gap), -(sweep-2*gap))
            path.closeSubpath()
            amount = self._hover_amounts[index] if index < len(self._hover_amounts) else 0
            fill = QColor(base)
            accent = QColor("#287bd6")
            fill.setRed(round(fill.red()*(1-amount*.25) + accent.red()*amount*.25))
            fill.setGreen(round(fill.green()*(1-amount*.25) + accent.green()*amount*.25))
            fill.setBlue(round(fill.blue()*(1-amount*.25) + accent.blue()*amount*.25))
            painter.setBrush(fill)
            painter.setPen(QPen(border, .8))
            painter.drawPath(path)
            angle = math.radians(start + sweep / 2)
            x, y = 162 + 105*math.cos(angle), 162 + 105*math.sin(angle)
            label = option if isinstance(option, str) else option.label
            self._text(painter, QRectF(x-47, y-25, 94, 50), label.replace("/", "/\n"),
                       foreground, 10, True, True)
        painter.setBrush(base)
        painter.setPen(QPen(border, 1))
        painter.drawEllipse(QRectF(95, 95, 134, 134))
        self._text(painter, QRectF(105, 113, 114, 20), "PREVIEW", QColor("#3982da"), 8, True)
        self._text(painter, QRectF(102, 140, 120, 33), self.state.target.path.name, foreground, 10, True)
        text = "‹ Back" if self.state.stage == "formats" else "Choose category"
        if not count:
            text = "No preview options"
        self._text(painter, QRectF(102, 180, 120, 22), text, muted, 8)
        self._text(painter, QRectF(102, 201, 120, 15), "Esc to dismiss", muted, 7)


def run_popup(target: TargetResolution | None, registry=DEFAULT_PREVIEW_REGISTRY):
    """Run one popup, returning its dry-run selection after it is dismissed.

    The caller must supply a controller-validated target, never a provisional
    diagnostic path. No filesystem API or conversion engine is used by this UI.
    """
    if not isinstance(target, TargetResolution):
        return None
    app = QApplication.instance()
    owned_app = app is None
    if owned_app:
        try:
            app = QApplication(["filewheel"])
        except (RuntimeError, OSError) as error:
            raise DesktopInitializationError(
                "create_qt_application", {"error_type": type(error).__name__},
            ) from error
    previous = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(False)
    popup = RadialPopup(registry)
    loop = QEventLoop()
    popup.finished.connect(loop.quit)
    try:
        popup.present(target)
        loop.exec()
        return popup.last_selection
    finally:
        popup._animation.stop()
        popup.close()
        popup.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.setQuitOnLastWindowClosed(previous)
        if owned_app:
            app.quit()
