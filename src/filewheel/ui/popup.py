"""Compact translucent radial menu with local conversion worker feedback."""

import math
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QEvent, QEventLoop, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from filewheel.core.models import TargetResolution
from filewheel.ui.arc_text import arc_direction, arc_glyphs
from filewheel.ui.desktop_errors import DesktopInitializationError
from filewheel.ui.placement import Rect, popup_position
from filewheel.ui.radial import DEFAULT_PREVIEW_REGISTRY, RadialState
from filewheel.ui.theme import DARK, LIGHT


def logical_point(point, screens):
    if sys.platform == "win32":
        from filewheel.platforms.windows.qt_position import logical_point as windows_point

        return windows_point(point, screens)
    return point


_SEPARATOR_WIDTH = 0.8
_SURFACE_ALPHA = 235


def radial_separators(count, inner_radius=67, outer_radius=148):
    """One segment per angular boundary, confined to the annulus.

    A full-circle single choice has no boundary. Geometry is shared by paint
    and hit testing so thin separators do not leave wide inactive wedges.
    """
    if count < 2:
        return ()
    return tuple(
        (
            (
                162 + inner_radius * math.sin(index * 2 * math.pi / count),
                162 - inner_radius * math.cos(index * 2 * math.pi / count),
            ),
            (
                162 + outer_radius * math.sin(index * 2 * math.pi / count),
                162 - outer_radius * math.cos(index * 2 * math.pi / count),
            ),
        )
        for index in range(count)
    )


def radial_hit(point, count, inner_radius=67, outer_radius=148):
    """Return center=-2, separator/outside=-1, or a clockwise choice index."""
    x, y = point[0] - 162, point[1] - 162
    distance = math.hypot(x, y)
    if distance < inner_radius:
        return -2
    if distance > outer_radius or not count:
        return -1
    for start, end in radial_separators(count, inner_radius, outer_radius):
        dx, dy = end[0] - start[0], end[1] - start[1]
        projection = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)
        projection = min(1.0, max(0.0, projection))
        if (
            math.hypot(point[0] - start[0] - projection * dx, point[1] - start[1] - projection * dy)
            <= _SEPARATOR_WIDTH / 2
        ):
            return -1
    angle = (math.degrees(math.atan2(y, x)) + 90) % 360
    return min(count - 1, int(angle / (360 / count)))


def _annular_sector(start_degrees, sweep_degrees, inner_radius=67, outer_radius=148):
    """Fill geometry only: sector paths deliberately have no painted outline."""
    outer = QRectF(162 - outer_radius, 162 - outer_radius, 2 * outer_radius, 2 * outer_radius)
    inner = QRectF(162 - inner_radius, 162 - inner_radius, 2 * inner_radius, 2 * inner_radius)
    start = math.radians(start_degrees)
    end = math.radians(start_degrees + sweep_degrees)
    path = QPainterPath()
    path.moveTo(162 + inner_radius * math.cos(start), 162 + inner_radius * math.sin(start))
    path.lineTo(162 + outer_radius * math.cos(start), 162 + outer_radius * math.sin(start))
    path.arcTo(outer, -start_degrees, -sweep_degrees)
    path.lineTo(162 + inner_radius * math.cos(end), 162 + inner_radius * math.sin(end))
    path.arcTo(inner, -(start_degrees + sweep_degrees), sweep_degrees)
    path.closeSubpath()
    return path


class RadialPopup(QWidget):
    """The same present(TargetResolution) boundary serves both invocation sources."""

    selected = Signal(object)
    finished = Signal()
    diameter = 170
    reference_diameter = 324
    center_radius = 30
    outer_radius = 148

    def __init__(
        self,
        registry=DEFAULT_PREVIEW_REGISTRY,
        *,
        point_mapper=logical_point,
        manager=None,
        source_mapper=lambda path: Path(str(path)),
        diameter=170,
    ):
        if type(diameter) is not int or not 170 <= diameter <= 324:
            raise ValueError("Wheel diameter must be an integer between 170 and 324")
        super().__init__(
            None,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.diameter = diameter
        self._scale = diameter / self.reference_diameter
        self.state = RadialState(registry)
        self.manager, self.source_mapper = manager, source_mapper
        self.job = None
        self._closing = False
        self.status_title = ""
        self.status_message = ""
        self.progress_fraction = 0.0
        self.conversion_result = None
        self.conversion_error = None
        self.point_mapper = point_mapper
        self.hovered = -1
        self.keyboard_index = -1
        self.last_selection = None
        self._finished = True
        self._resetting = False
        self._changing_window_mode = False
        self._hover_amounts = []
        self._list_offset = 0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(self.diameter, self.diameter)
        self.setWindowTitle(
            "Filewheel local converter" if manager is not None else "Filewheel preview"
        )
        self._animation = QTimer(self)
        self._animation.setInterval(16)
        self._animation.timeout.connect(self._animate)
        self._focus_check = QTimer(self)
        self._focus_check.setSingleShot(True)
        self._focus_check.timeout.connect(self._dismiss_if_inactive)

    def present(self, target):
        if self.job is not None:
            return False
        self._closing = False
        self.conversion_result = None
        self.conversion_error = None
        self.status_title = self.status_message = ""
        self.progress_fraction = 0.0
        self._resetting = True
        self.hide()
        self._set_persistent_window(False)
        self._resetting = False
        self.last_selection = None
        self.hovered = self.keyboard_index = -1
        self._list_offset = 0
        if not self.state.open(target):
            self._finish()
            return False
        self.setToolTip(str(target.path))
        app = QApplication.instance()
        try:
            point = self.point_mapper(target.point, app.screens())
            screen = app.screenAt(QPoint(round(point[0]), round(point[1])))
            if screen is None:
                raise DesktopInitializationError(
                    "find_logical_screen",
                    {
                        "logical_point": list(point),
                        "screens": [
                            {
                                "name": item.name(),
                                "geometry": [
                                    item.geometry().x(),
                                    item.geometry().y(),
                                    item.geometry().width(),
                                    item.geometry().height(),
                                ],
                            }
                            for item in app.screens()
                        ],
                    },
                )
            area = screen.availableGeometry()
            location = popup_position(
                point,
                Rect(area.x(), area.y(), area.width(), area.height()),
                (self.width(), self.height()),
            )
        except Exception as error:
            self.state.dismiss()
            self._finish()
            if isinstance(error, DesktopInitializationError):
                raise
            raise DesktopInitializationError(
                "position_popup",
                {"error_type": type(error).__name__},
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
                "show_popup",
                {"error_type": type(error).__name__},
            ) from error
        return True

    def dismiss(self):
        self.close()

    def _persistent_status(self):
        return self.state.stage in ("converting", "result")

    def _set_persistent_window(self, enabled):
        # Qt.Popup dismisses natively outside the window. A Tool window keeps
        # progress/results visible without grabbing mouse input from Explorer.
        kind = Qt.WindowType.Tool if enabled else Qt.WindowType.Popup
        if self.windowType() == kind:
            return
        geometry = self.geometry()
        visible = self.isVisible()
        self._focus_check.stop()
        self._changing_window_mode = True
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, enabled)
            self.setWindowFlags(kind | Qt.WindowType.FramelessWindowHint
                                | Qt.WindowType.WindowStaysOnTopHint
                                | Qt.WindowType.NoDropShadowWindowHint)
            self.setGeometry(geometry)
            if visible:
                self.show()
                self.raise_()
        finally:
            self._changing_window_mode = False

    def _request_cancel(self):
        if self.job is not None:
            self.job.cancelled.set()
            self.status_title = "Stopping…"
            self.update()

    def _finish(self):
        if self._changing_window_mode:
            return
        if self.job is not None:
            self._closing = True
            self.job.cancelled.set()
            return
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
        if not self._persistent_status() and not self._changing_window_mode:
            self._focus_check.start(0)

    def _dismiss_if_inactive(self):
        if (self.isVisible() and not self.isActiveWindow()
                and not self._persistent_status() and not self._changing_window_mode):
            self.dismiss()

    def event(self, event):
        if (event.type() == QEvent.Type.WindowDeactivate and self.isVisible()
                and not self._persistent_status() and not self._changing_window_mode):
            self._focus_check.start(0)
        return super().event(event)

    def _list_mode(self):
        return len(self.state.options) >= 6

    def _reference_point(self, point):
        return QPointF(point.x() / self._scale, point.y() / self._scale)

    def _hit(self, point):
        point = self._reference_point(point)
        if self.state.stage in ("converting", "result", "confirmation"):
            return -2 if self._action_rect().contains(point) else -1
        if self._list_mode():
            if QRectF(34, 34, 256, 32).contains(point):
                return -2
            index = int((point.y() - 72) // 30) + self._list_offset
            if (
                34 <= point.x() <= 290
                and 72 <= point.y() < 282
                and 0 <= index < len(self.state.options)
            ):
                return index
            return -1
        return radial_hit(
            (point.x(), point.y()), len(self.state.options), self.center_radius, self.outer_radius
        )

    def mouseMoveEvent(self, event):
        self.hovered = self._hit(event.position())
        if self.state.stage in ("categories", "formats"):
            if self.hovered >= 0:
                option = self.state.options[self.hovered]
                label = option if isinstance(option, str) else option.label
                self.setToolTip(f"{self.state.target.path}\n{label}")
            else:
                self.setToolTip(str(self.state.target.path))
        self._animation.start()
        self.update()

    def leaveEvent(self, event):
        self.hovered = -1
        self._animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        hit = self._hit(event.position())
        point = self._reference_point(event.position())
        if self._list_mode():
            outside = not QRectF(22, 22, 280, 280).contains(point)
        else:
            outside = math.hypot(point.x() - 162, point.y() - 162) > self.outer_radius
        if outside:
            if not self._persistent_status():
                self.dismiss()
        elif event.button() != Qt.MouseButton.LeftButton:
            return
        elif hit == -2:
            if self.state.stage == "converting":
                self._request_cancel()
            elif self.state.stage in ("confirmation", "result", "categories"):
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
            if self.manager is not None:
                from filewheel.ui.conversion_job import ConversionJob

                self.state.stage = "converting"
                self.last_selection = replace(selection, action="conversion_started")
                self.progress_fraction = 0.0
                self.status_title = "In progress"
                self.status_message = "Preparing local conversion"
                self._set_persistent_window(True)
                self.job = ConversionJob(
                    self.manager,
                    self.source_mapper(selection.input_path),
                    selection.output_extension,
                    self,
                )
                self.job.progress_changed.connect(self._conversion_progress)
                self.job.outcome.connect(self._conversion_done)
                self.job.start()
            self.selected.emit(self.last_selection)

    def _conversion_progress(self, value, message):
        self.progress_fraction = max(0.0, min(1.0, value)) if math.isfinite(value) else 0.0
        self.status_message = f"{round(self.progress_fraction * 100)}% · {message}"
        self.update()

    def _conversion_done(self, result, error):
        from filewheel.converters.base import ConversionCancelled, ConversionError

        job, self.job = self.job, None
        if job is not None:
            job.wait()
            job.deleteLater()
        if error is None and (result is None or not result.outputs):
            error = ConversionError("The conversion produced no output")
        # Record the outcome even when the user dismissed during conversion.
        # _finish() must not make a successful/failed action look like a preview.
        self.conversion_result, self.conversion_error = result, error
        input_detail = f"Input: {self.state.target.path}\n\n" if self.state.target else ""
        if error is not None:
            cancelled = isinstance(error, ConversionCancelled)
            self.status_title = "Cancelled" if cancelled else "Conversion failed"
            from filewheel.converters.debugging import describe_conversion_error, error_details

            self.status_message = describe_conversion_error(error)[:250]
            self.last_selection = replace(
                self.last_selection,
                action="conversion_cancelled" if cancelled else "conversion_failed",
                outputs=(),
            )
            self.setToolTip(input_detail + error_details(error))
        else:
            self.status_title = "Converted"
            self.status_message = result.outputs[0].name
            if len(result.outputs) > 1:
                self.status_message += f" (+{len(result.outputs) - 1} files)"
            self.last_selection = replace(
                self.last_selection,
                action="converted",
                intended_path=result.outputs[0],
                outputs=result.outputs,
            )
            self.setToolTip(
                input_detail + "\n".join(str(path) for path in result.outputs)
                + ("\n\n" + "\n".join(result.warnings) if result.warnings else "")
            )
        if self._closing:
            self._finish()
            return
        self.state.stage = "result"
        self._set_persistent_window(True)
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            if self.state.stage == "converting":
                self._request_cancel()
            else:
                self.dismiss()
        elif key in (Qt.Key.Key_Backspace, Qt.Key.Key_Left) and self.state.stage == "formats":
            self.state.back()
            self._reset_hover()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self.state.stage in ("confirmation", "result"):
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
            self._list_offset = min(
                max(0, self._list_offset + direction), max(0, len(self.state.options) - 7)
            )
            self.hovered = -1
            self.update()
            event.accept()
        else:
            super().wheelEvent(event)

    def _animate(self):
        moving = False
        for index, value in enumerate(self._hover_amounts):
            goal = 1.0 if index == self.hovered else 0.0
            updated = value + (goal - value) * 0.28
            if abs(updated - goal) < 0.015:
                updated = goal
            else:
                moving = True
            self._hover_amounts[index] = updated
        self.update()
        if not moving:
            self._animation.stop()

    def _theme(self):
        return DARK if self.palette().window().color().lightnessF() < 0.5 else LIGHT

    def _colors(self):
        theme = self._theme()
        return tuple(QColor(value) for value in
                     (theme.surface, theme.text, theme.muted, theme.outline))

    @staticmethod
    def _action_rect():
        return QRectF(104, 248, 116, 34)

    def _text(self, painter, rect, text, color, size=10, bold=False, wrap=False):
        painter.setPen(color)
        font = QFont("Segoe UI")
        # Typography stays readable when wheel geometry shrinks. The painter
        # applies _scale, so divide once to retain the requested logical size.
        font.setPointSizeF(max(9.0, size) / self._scale)
        font.setBold(bold)
        painter.setFont(font)
        flags = Qt.AlignmentFlag.AlignCenter
        if wrap:
            # Qt's ordinary word wrap lets a long unbroken category overflow its
            # rectangle. Balance only overlong words into short lines first.
            text = self._wrap_long_words(text, painter.fontMetrics(), rect.width())
            flags |= Qt.TextFlag.TextWordWrap
        else:
            text = painter.fontMetrics().elidedText(
                text, Qt.TextElideMode.ElideMiddle, int(rect.width())
            )
        painter.drawText(rect, flags, text)

    def _arc_text(self, painter, text, color, center_angle, sector_sweep):
        font = QFont("Segoe UI")
        font.setPointSizeF((9.5 if self.diameter < 220 else 10.5) / self._scale)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        # Ascenders point outward in the upper half and inward below the center.
        # Offset the two baselines to keep the visual glyph centers on one ring.
        radius = 102 if arc_direction(center_angle) == 1 else 124
        span = math.radians(min(140, max(0, sector_sweep - 20))) * radius
        label = metrics.elidedText(text, Qt.TextElideMode.ElideRight, int(span))
        advances = [max(0, metrics.horizontalAdvance(label[:index + 1])
                        - metrics.horizontalAdvance(label[:index])) for index in range(len(label))]
        painter.setPen(color)
        for glyph in arc_glyphs(label, advances, center_angle, radius):
            painter.save()
            painter.translate(glyph.x, glyph.y)
            painter.rotate(glyph.rotation)
            painter.drawText(QPointF(-glyph.advance / 2, 0), glyph.text)
            painter.restore()

    @staticmethod
    def _wrap_long_words(text, metrics, width):
        lines = []
        for line in text.split("\n"):
            words = []
            for word in line.split(" "):
                pieces = [word]
                for count in range(2, len(word) + 1):
                    if all(metrics.horizontalAdvance(piece) <= width for piece in pieces):
                        break
                    length = math.ceil(len(word) / count)
                    pieces = [word[index:index + length] for index in range(0, len(word), length)]
                words.append("\n".join(pieces))
            lines.append(" ".join(words))
        return "\n".join(lines)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Explicitly erase old alpha, including when switching between the wheel
        # and the smaller result panel. Never paint a rectangular backdrop.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if self.state.target is None:
            return
        painter.scale(self._scale, self._scale)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        base, foreground, muted, border = self._colors()
        base.setAlpha(_SURFACE_ALPHA)
        # Painted ambient shadow keeps the transparent window compact and cheap.
        painter.setPen(Qt.PenStyle.NoPen)
        for spread in range(10, 0, -2):
            painter.setBrush(QColor(0, 0, 0, 3))
            painter.drawEllipse(
                QRectF(14 - spread / 2, 16 - spread / 2, 296 + spread, 296 + spread)
            )
        painter.setBrush(base)
        painter.setPen(QPen(border, 1))
        theme = self._theme()
        if self.state.stage in ("converting", "result", "confirmation"):
            # All status stages retain the wheel's silhouette. The old rounded
            # rectangular card made conversion appear to open a square prompt.
            outer = QRectF(14, 14, 296, 296)
            painter.drawEllipse(outer)
            circle = QPainterPath()
            circle.addEllipse(outer)
            painter.setClipPath(circle)
            if self.state.stage == "confirmation":
                selection = self.state.selection
                title = "Preview"
                filename = selection.input_path.name
                message = f"{selection.original_format} → {selection.output_extension[1:].upper()}"
                detail = selection.intended_path.name
            else:
                # Keep technical engine chatter, filenames and traceback details
                # in metadata/tooltips. The small status face stays glanceable.
                filename = detail = ""
                if self.state.stage == "converting":
                    stopping = self.job is not None and self.job.cancelled.is_set()
                    title = "Stopping…" if stopping else "In progress"
                    message = f"{round(self.progress_fraction * 100)}%"
                elif self.last_selection and self.last_selection.action == "conversion_cancelled":
                    title, message = "Cancelled", ""
                elif self.conversion_error is not None:
                    title, message = "Failed", "Hover for details"
                else:
                    title, message = "Done", "File saved"
                    if self.conversion_result and len(self.conversion_result.outputs) > 1:
                        message = f"{len(self.conversion_result.outputs)} files saved"
            title_color = QColor(theme.error if self.conversion_error is not None else theme.accent)
            if self.state.stage == "confirmation":
                self._text(painter, QRectF(54, 60, 216, 34), title, title_color,
                           10.5 if self.diameter < 220 else 12, True)
                self._text(painter, QRectF(54, 103, 216, 29), filename, foreground, 10, True)
                self._text(painter, QRectF(54, 145, 216, 58), message, muted, 10, wrap=True)
                self._text(painter, QRectF(64, 210, 196, 25), detail, muted, 9)
            else:
                self._text(painter, QRectF(48, 112, 228, 38), title, title_color, 11, True)
                self._text(painter, QRectF(54, 166, 216, 36), message, muted, 10)
            if self.state.stage == "converting":
                track = QRectF(26, 26, 272, 272)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(border, 4))
                painter.drawEllipse(track)
                progress_pen = QPen(QColor(theme.accent), 4)
                progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(progress_pen)
                painter.drawArc(track, 90 * 16, round(-360 * 16 * self.progress_fraction))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.action))
            painter.drawRoundedRect(self._action_rect(), 15, 15)
            action = "Cancel" if self.state.stage == "converting" else "Done"
            self._text(painter, self._action_rect(), action, QColor(theme.on_action), 10, True)
            return
        if self._list_mode():
            painter.drawRoundedRect(QRectF(22, 22, 280, 280), 24, 24)
            self._text(
                painter,
                QRectF(34, 34, 256, 30),
                "‹ Back · Convert" if self.manager is not None else "‹ Back · Preview",
                foreground,
                10,
                True,
            )
            for row, option in enumerate(
                self.state.options[self._list_offset : self._list_offset + 7]
            ):
                index = row + self._list_offset
                rectangle = QRectF(34, 72 + row * 30, 256, 28)
                if index == self.hovered:
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                    painter.fillRect(rectangle, QColor(theme.hover))
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                self._text(painter, rectangle, getattr(option, "label", option), foreground, 10)
            return
        outer = QRectF(14, 14, 296, 296)
        inner = QRectF(162 - self.center_radius, 162 - self.center_radius,
                       self.center_radius * 2, self.center_radius * 2)
        # One continuous base disk; hover paints only its annular sector. Paths
        # have no pen, so neighboring choices never double-stroke a boundary.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(base)
        painter.drawEllipse(outer)
        count = len(self.state.options)
        for index in range(count):
            amount = self._hover_amounts[index] if index < len(self._hover_amounts) else 0
            if amount <= 0:
                continue
            fill = QColor(base)
            accent = QColor(theme.hover)
            for channel, setter in (("red", "setRed"), ("green", "setGreen"), ("blue", "setBlue")):
                getattr(fill, setter)(round(getattr(base, channel)() * (1 - amount)
                                           + getattr(accent, channel)() * amount))
            # SourceAtop changes the tint without compounding surface opacity.
            fill.setAlpha(255)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            painter.setBrush(fill)
            painter.drawPath(
                _annular_sector(
                    -90 + index * 360 / count, 360 / count, self.center_radius, self.outer_radius
                )
            )
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        # Stroke the two circles once, then each radial separator exactly once.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(border, 1))
        painter.drawEllipse(outer)
        painter.drawEllipse(inner)
        painter.setPen(QPen(border, _SEPARATOR_WIDTH))
        for start, end in radial_separators(count, self.center_radius, self.outer_radius):
            painter.drawLine(QPointF(*start), QPointF(*end))
        for index, option in enumerate(self.state.options):
            angle = -90 + (index + 0.5) * 360 / count
            label = option if isinstance(option, str) else option.label
            if self.diameter < 220 and isinstance(option, str):
                label = {"Document": "Docs", "Markdown/Text": "Text/MD"}.get(label, label)
            self._arc_text(painter, label, foreground, angle, 360 / count)
        self._text(painter, QRectF(125, 147, 74, 30),
                   "Back" if self.state.stage == "formats" else "Esc", muted, 9, True)
        if not count:
            self._text(painter, QRectF(62, 214, 200, 38), "No formats", muted, 10)



def run_popup(
    target: TargetResolution | None,
    registry=DEFAULT_PREVIEW_REGISTRY,
    *,
    manager=None,
    diameter=170,
):
    """Run one popup, returning its preview or real conversion outcome on dismissal.

    The caller must supply a controller-validated target, never a provisional
    diagnostic path. Real conversions run only in the managed worker thread.
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
                "create_qt_application",
                {"error_type": type(error).__name__},
            ) from error
    previous = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(False)
    popup = RadialPopup(registry, manager=manager, diameter=diameter)
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
