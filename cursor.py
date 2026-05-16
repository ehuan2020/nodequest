from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygonF, QBrush

import win32gui
import win32con


class CursorOverlay(QWidget):
    target_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_x: float = 0.0
        self.current_y: float = 0.0
        self.target_x: float = 0.0
        self.target_y: float = 0.0
        self.label_text: str = ""
        self.arrow_color: QColor = QColor("#4A90D9")
        self.pulse_radius: float = 20.0
        self.pulse_growing: bool = True
        self.visible: bool = False

        self._move_timer = QTimer(self)
        self._move_timer.timeout.connect(self._step_toward_target)
        self._move_debug_frame = 0

        self._setup_window()

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulse)
        self._pulse_timer.start(50)

    # ------------------------------------------------------------------ setup

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

    def showEvent(self, event):
        super().showEvent(event)
        hwnd = int(self.winId())
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )
        # Start click-through so UE5 is usable during IDLE;
        # overlay.py calls enable_interception() when guiding or calibrating.
        self._set_click_through(True)

    # ------------------------------------------------------------------ click interception

    def _set_click_through(self, enabled: bool):
        hwnd = int(self.winId())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if enabled:
            style |= win32con.WS_EX_TRANSPARENT
        else:
            style &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)

    def enable_interception(self):
        self._set_click_through(False)

    def disable_interception(self):
        self._set_click_through(True)

    # ------------------------------------------------------------------ arrow helpers

    def _arrow_polygon(self, cx: float, cy: float) -> QPolygonF:
        return QPolygonF([
            QPointF(cx - 8,  cy - 40),
            QPointF(cx - 8,  cy - 20),
            QPointF(cx - 15, cy - 20),
            QPointF(cx,      cy),
            QPointF(cx + 15, cy - 20),
            QPointF(cx + 8,  cy - 20),
            QPointF(cx + 8,  cy - 40),
        ])

    # ------------------------------------------------------------------ paint

    def paintEvent(self, event):
        if not self.visible:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.current_x
        cy = self.current_y
        arrow = self._arrow_polygon(cx, cy)

        # 1. Drop shadow
        shadow = self._arrow_polygon(cx + 4, cy + 4)
        painter.setBrush(QBrush(QColor(0, 0, 0, 128)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(shadow)

        # 2. Arrow fill
        painter.setBrush(QBrush(self.arrow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(arrow)

        # 3. Arrow outline
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("white"), 2))
        painter.drawPolygon(arrow)

        # 4. Pulsing circle at tip
        pulse_fill = QColor(self.arrow_color)
        pulse_fill.setAlpha(102)  # 40%
        painter.setBrush(QBrush(pulse_fill))
        painter.setPen(QPen(QColor("white"), 2))
        r = self.pulse_radius
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 5 & 6. Label
        if self.label_text:
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(self.label_text) + 16
            text_h = fm.height() + 8
            lx = cx - text_w / 2
            ly = cy + 15

            bg = QColor("#1A1A2E")
            bg.setAlpha(217)  # 85%
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(lx, ly, text_w, text_h), 6, 6)

            painter.setPen(QPen(QColor("white")))
            painter.drawText(QRectF(lx, ly, text_w, text_h), Qt.AlignmentFlag.AlignCenter, self.label_text)

        painter.end()

    # ------------------------------------------------------------------ animation

    def _tick_pulse(self):
        if self.pulse_growing:
            self.pulse_radius += 1.0
            if self.pulse_radius >= 35.0:
                self.pulse_growing = False
        else:
            self.pulse_radius -= 1.0
            if self.pulse_radius <= 15.0:
                self.pulse_growing = True
        if self.visible:
            self.update()

    def move_to(self, x: float, y: float, label: str, color: str = "#4A90D9"):
        self.target_x = x
        self.target_y = y
        self.label_text = label
        self.arrow_color = QColor(color)
        self.visible = True
        self._start_move_animation()

    def _start_move_animation(self):
        if self._move_timer.isActive():
            self._move_timer.stop()
        self._move_timer.start(16)  # ~60fps

    def _step_toward_target(self):
        self._move_debug_frame += 1
        dx = self.target_x - self.current_x
        dy = self.target_y - self.current_y
        if self._move_debug_frame % 10 == 0:
            print(f"[cursor] current=({self.current_x:.1f},{self.current_y:.1f}) "
                  f"target=({self.target_x:.1f},{self.target_y:.1f})")
        if abs(dx) < 1.0 and abs(dy) < 1.0:
            self.current_x = self.target_x
            self.current_y = self.target_y
            self._move_timer.stop()
            print("[cursor] reached target")
        else:
            self.current_x += dx * 0.15
            self.current_y += dy * 0.15
        self.update()

    # ------------------------------------------------------------------ public API

    def show_cursor(self):
        self.visible = True
        self.update()

    def hide_cursor(self):
        self.visible = False
        self.update()

    def set_recovery_mode(self, active: bool):
        self.arrow_color = QColor("#F5A623") if active else QColor("#4A90D9")
        self.update()

    def flash(self, color: str, duration_ms: int, restore_color: str = "#4A90D9"):
        self.arrow_color = QColor(color)
        self.update()
        QTimer.singleShot(duration_ms, lambda: self._finish_flash(restore_color))

    def _finish_flash(self, color: str):
        self.arrow_color = QColor(color)
        self.update()
