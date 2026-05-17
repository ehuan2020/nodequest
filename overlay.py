from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QApplication,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer, QThreadPool
from PyQt6.QtGui import QFont

import win32api
import win32gui
import win32con
import time

from state_machine import StateMachine, AppState
from worker import Worker
import gemini_client
import locator
import screen_parser


class OverlayWindow(QWidget):
    def __init__(self, cursor_overlay=None):
        super().__init__()
        self._cursor = cursor_overlay
        self._drag_pos = None
        self._steps: list[dict] = []
        self._current_step = 0
        self._completed_steps: set[int] = set()
        self._step_items: list[dict] = []
        self._spinner_count = 0
        self._goal_text = ""
        self._workers: list[Worker] = []

        omni_worker = Worker(screen_parser.start_server)
        omni_worker.signals.finished.connect(
            lambda: self._workers.remove(omni_worker) if omni_worker in self._workers else None
        )
        self._workers.append(omni_worker)
        QThreadPool.globalInstance().start(omni_worker)

        self._current_target = (0, 0)
        self._step_shown_time = 0.0
        self._poll_timer = None
        self._last_left = False
        self._last_right = False

        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._tick_spinner)

        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self.enforce_topmost)

        self._sm = StateMachine()

        self._setup_window()
        self._build_ui()
        self._apply_styles()
        self.update_ui_for_state(AppState.IDLE)

    # ------------------------------------------------------------------ setup

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(380)

    def showEvent(self, event):
        super().showEvent(event)
        self.enforce_topmost()
        self._topmost_timer.start(1000)

    def enforce_topmost(self):
        hwnd = int(self.winId())
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )

    # ------------------------------------------------------------------ drag & keyboard

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and self._sm.current_state in (AppState.GUIDING, AppState.WAITING_FOR_USER):
            self.advance_step()
        elif event.key() == Qt.Key.Key_Escape:
            self.reset_to_idle()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        self._container = QWidget()
        self._container.setObjectName("container")
        outer.addWidget(self._container)

        lay = QVBoxLayout(self._container)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        self._title_lbl = QLabel("NodeQuest")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(13)
        self._title_lbl.setFont(title_font)
        header.addWidget(self._title_lbl, stretch=1)

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setToolTip("Close")
        self._close_btn.clicked.connect(QApplication.quit)
        header.addWidget(self._close_btn)

        lay.addLayout(header)

        self._goal_lbl = QLabel()
        self._goal_lbl.setWordWrap(True)
        self._goal_lbl.setVisible(False)
        lay.addWidget(self._goal_lbl)

        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(self._divider)

        # ==== IDLE panel ====
        self._idle_panel = QWidget()
        idle_lay = QVBoxLayout(self._idle_panel)
        idle_lay.setContentsMargins(0, 4, 0, 0)
        idle_lay.setSpacing(8)

        self._goal_edit = QLineEdit()
        self._goal_edit.setPlaceholderText("What do you want to learn in UE5?")
        self._goal_edit.returnPressed.connect(self._on_go_clicked)
        idle_lay.addWidget(self._goal_edit)

        self._go_btn = QPushButton("Go")
        self._go_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._go_btn.clicked.connect(self._on_go_clicked)
        idle_lay.addWidget(self._go_btn)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        idle_lay.addWidget(self._status_lbl)

        lay.addWidget(self._idle_panel)

        # ==== LOADING panel ====
        self._loading_panel = QWidget()
        loading_lay = QVBoxLayout(self._loading_panel)
        loading_lay.setContentsMargins(0, 8, 0, 8)

        self._loading_lbl = QLabel("Analyzing.")
        self._loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_lay.addWidget(self._loading_lbl)

        lay.addWidget(self._loading_panel)

        # ==== GUIDING panel ====
        self._guiding_panel = QWidget()
        guiding_lay = QVBoxLayout(self._guiding_panel)
        guiding_lay.setContentsMargins(0, 4, 0, 0)
        guiding_lay.setSpacing(8)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setMinimumHeight(120)
        self._scroll_area.setMaximumHeight(340)

        self._scroll_content = QWidget()
        self._steps_layout = QVBoxLayout(self._scroll_content)
        self._steps_layout.setContentsMargins(2, 2, 2, 2)
        self._steps_layout.setSpacing(4)

        self._scroll_area.setWidget(self._scroll_content)
        guiding_lay.addWidget(self._scroll_area)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._next_btn = QPushButton("Next  (Space)")
        self._next_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._next_btn.setFixedHeight(36)
        self._next_btn.clicked.connect(self.advance_step)
        btn_row.addWidget(self._next_btn, stretch=3)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._skip_btn.setFixedHeight(36)
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn, stretch=1)

        guiding_lay.addLayout(btn_row)

        self._progress_lbl = QLabel()
        self._progress_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        guiding_lay.addWidget(self._progress_lbl)

        self._guide_status_lbl = QLabel()
        self._guide_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._guide_status_lbl.setWordWrap(True)
        guiding_lay.addWidget(self._guide_status_lbl)

        lay.addWidget(self._guiding_panel)

        # ==== ERROR panel ====
        self._error_panel = QWidget()
        error_lay = QVBoxLayout(self._error_panel)
        error_lay.setContentsMargins(0, 4, 0, 0)
        error_lay.setSpacing(6)

        self._error_lbl = QLabel()
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_lay.addWidget(self._error_lbl)

        self._restart_btn = QPushButton("Restart")
        self._restart_btn.clicked.connect(self.reset_to_idle)
        error_lay.addWidget(self._restart_btn)

        lay.addWidget(self._error_panel)

    def _apply_styles(self):
        self._container.setStyleSheet("""
            QWidget#container { background-color: #1A1A2E; border-radius: 12px; }
        """)
        self._title_lbl.setStyleSheet("color: #4A90D9;")
        self._close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: white; border: none; font-size: 10pt; border-radius: 4px; }
            QPushButton:hover { background: rgba(255,255,255,30); }
            QPushButton:pressed { background: rgba(255,255,255,60); }
        """)
        self._goal_lbl.setStyleSheet("color: #888888; font-size: 9pt; padding: 0 2px;")
        self._divider.setStyleSheet("color: #333355; margin: 2px 0;")
        self._goal_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A4E; color: white;
                border: 1px solid #444466; border-radius: 6px;
                padding: 8px; font-size: 10pt;
            }
            QLineEdit:focus { border-color: #4A90D9; }
        """)
        self._go_btn.setStyleSheet("""
            QPushButton { background-color: #4A90D9; color: white; border-radius: 6px; padding: 8px; font-weight: bold; font-size: 10pt; }
            QPushButton:hover { background-color: #5AA0E9; }
            QPushButton:pressed { background-color: #3A80C9; }
        """)
        self._status_lbl.setStyleSheet("color: #888888; font-size: 9pt;")
        self._loading_lbl.setStyleSheet("color: #888888; font-size: 9pt;")
        self._scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: 1px solid #2A2A4A; border-radius: 6px; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical { background: #1A1A2E; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #444466; border-radius: 3px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self._scroll_content.setStyleSheet("background: transparent;")
        self._next_btn.setStyleSheet("""
            QPushButton { background-color: #4A90D9; color: white; border-radius: 6px; font-weight: bold; font-size: 10pt; }
            QPushButton:hover { background-color: #5AA0E9; }
            QPushButton:pressed { background-color: #3A80C9; }
        """)
        self._skip_btn.setStyleSheet("""
            QPushButton { background-color: #444466; color: #AAAACC; border-radius: 6px; font-size: 9pt; }
            QPushButton:hover { background-color: #555577; }
        """)
        self._progress_lbl.setStyleSheet("color: #555577; font-size: 9pt;")
        self._guide_status_lbl.setStyleSheet("color: #AAAACC; font-size: 9pt;")
        self._error_lbl.setStyleSheet("color: #FF4444; font-size: 9pt; padding: 4px;")
        self._restart_btn.setStyleSheet("""
            QPushButton { background-color: #884422; color: white; border-radius: 6px; padding: 8px; }
        """)

    # ------------------------------------------------------------------ reset

    def reset_to_idle(self):
        self._spinner_timer.stop()
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._sm.reset()
        self._goal_text = ""
        self._goal_lbl.setText("")
        self._goal_lbl.setVisible(False)
        self._goal_edit.clear()
        self._steps = []
        self._current_step = 0
        self._completed_steps = set()
        self._step_items = []
        if self._cursor:
            self._cursor.hide_cursor()
        self.update_ui_for_state(AppState.IDLE)

    # ------------------------------------------------------------------ state

    def update_ui_for_state(self, state: AppState):
        self._spinner_timer.stop()

        self._idle_panel.setVisible(state == AppState.IDLE)
        self._loading_panel.setVisible(state == AppState.LOADING)
        self._guiding_panel.setVisible(state in (AppState.GUIDING, AppState.WAITING_FOR_USER))
        self._error_panel.setVisible(state == AppState.ERROR)

        if state == AppState.LOADING:
            self._spinner_count = 0
            self._tick_spinner()
            self._spinner_timer.start(500)

        self.adjustSize()

    def _tick_spinner(self):
        dots = "." * ((self._spinner_count % 3) + 1)
        self._loading_lbl.setText(f"Analyzing{dots}")
        self._spinner_count += 1

    # ------------------------------------------------------------------ goal input

    def _on_go_clicked(self):
        text = self._goal_edit.text().strip()
        if not text:
            return
        self._goal_text = text
        self._goal_lbl.setText(text)
        self._goal_lbl.setVisible(True)
        self._sm.set_state(AppState.LOADING)
        self.update_ui_for_state(AppState.LOADING)

        worker = Worker(gemini_client.generate_steps, self._goal_text)
        worker.signals.result.connect(self._on_steps_received)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(
            lambda: self._workers.remove(worker) if worker in self._workers else None
        )
        self._workers.append(worker)
        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------ step callbacks

    def _on_steps_received(self, steps):
        self._steps = steps
        self._current_step = 0
        self._completed_steps = set()
        self._sm.set_state(AppState.GUIDING)
        self.update_ui_for_state(AppState.GUIDING)
        self._build_step_list(steps)
        self._update_step_visuals()
        self._update_progress_text()
        self._show_current_step()
        self.start_click_polling()

    def _on_error(self, msg):
        self._sm.set_state(AppState.ERROR)
        self.update_ui_for_state(AppState.ERROR)
        self._error_lbl.setText(f"Error: {msg}")

    def _on_skip(self):
        if not self._steps or self._sm.current_state not in (AppState.GUIDING, AppState.WAITING_FOR_USER):
            return
        if self._current_step < len(self._steps) - 1:
            self._current_step += 1
            self._update_step_visuals()
            self._update_progress_text()
            self._show_current_step()
        else:
            self._finish_tutorial()

    def _finish_tutorial(self):
        if self._poll_timer is not None:
            self._poll_timer.stop()
        if self._cursor:
            self._cursor.hide_cursor()
        self.reset_to_idle()
        self._status_lbl.setText("Tutorial complete!")

    # ------------------------------------------------------------------ cursor

    def _show_current_step(self):
        if not self._steps:
            return
        step = self._steps[self._current_step]
        x, y = locator.get_coordinates(step["anchor"])
        print(f"[overlay] moving cursor to {x}, {y} for step '{step['title']}'")
        self._sm.set_state(AppState.WAITING_FOR_USER)
        if self._cursor:
            self._cursor.show_cursor()
            self._cursor.move_to(x, y, step["action"])
        self._current_target = (x, y)
        self._step_shown_time = time.time()

    # ------------------------------------------------------------------ step list

    def _build_step_list(self, steps: list[dict]):
        while self._steps_layout.count():
            item = self._steps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._step_items = []

        for i, step in enumerate(steps):
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.NoFrame)

            row = QHBoxLayout(frame)
            row.setContentsMargins(10, 8, 10, 8)
            row.setSpacing(10)

            circle = QLabel(str(i + 1))
            circle.setFixedSize(26, 26)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(circle, alignment=Qt.AlignmentFlag.AlignTop)

            text_widget = QWidget()
            text_widget.setStyleSheet("background: transparent;")
            text_lay = QVBoxLayout(text_widget)
            text_lay.setContentsMargins(0, 0, 0, 0)
            text_lay.setSpacing(3)

            title_lbl = QLabel(step["title"])
            title_lbl.setWordWrap(True)

            desc_lbl = QLabel(step["description"])
            desc_lbl.setWordWrap(True)
            desc_lbl.setVisible(False)

            text_lay.addWidget(title_lbl)
            text_lay.addWidget(desc_lbl)
            row.addWidget(text_widget, stretch=1)

            self._steps_layout.addWidget(frame)
            self._step_items.append({
                "frame": frame,
                "circle": circle,
                "title": title_lbl,
                "desc": desc_lbl,
            })

        self.adjustSize()

    def _update_step_visuals(self):
        for i, item in enumerate(self._step_items):
            frame = item["frame"]
            circle = item["circle"]
            title = item["title"]
            desc = item["desc"]

            if i in self._completed_steps:
                frame.setStyleSheet(
                    "QFrame { background: #162016; border-left: 3px solid #27AE60; border-radius: 4px; }"
                )
                circle.setStyleSheet(
                    "QLabel { background: #27AE60; border-radius: 13px; color: white; font-weight: bold; font-size: 9pt; }"
                )
                circle.setText("✓")
                title.setStyleSheet("background: transparent; color: #4A7A4A; font-size: 10pt;")
                desc.setVisible(False)
            elif i == self._current_step:
                frame.setStyleSheet(
                    "QFrame { background: #1C1C3A; border-left: 3px solid #4A90D9; border-radius: 4px; }"
                )
                circle.setStyleSheet(
                    "QLabel { background: #4A90D9; border-radius: 13px; color: white; font-weight: bold; font-size: 9pt; }"
                )
                circle.setText(str(i + 1))
                title.setStyleSheet("background: transparent; color: white; font-size: 10pt; font-weight: bold;")
                desc.setStyleSheet("background: transparent; color: #9999BB; font-size: 9pt;")
                desc.setVisible(True)
                QTimer.singleShot(50, lambda f=frame: self._scroll_area.ensureWidgetVisible(f))
            else:
                frame.setStyleSheet(
                    "QFrame { background: transparent; border-left: 3px solid #2A2A4A; border-radius: 4px; }"
                )
                circle.setStyleSheet(
                    "QLabel { background: #2A2A4A; border-radius: 13px; color: #444466; font-weight: bold; font-size: 9pt; }"
                )
                circle.setText(str(i + 1))
                title.setStyleSheet("background: transparent; color: #555577; font-size: 10pt;")
                desc.setVisible(False)

    def _update_progress_text(self):
        self._progress_lbl.setText(f"Step {self._current_step + 1} of {len(self._steps)}")

    # ------------------------------------------------------------------ advance

    def advance_step(self):
        if not self._steps or self._sm.current_state not in (AppState.GUIDING, AppState.WAITING_FOR_USER):
            return
        self._completed_steps.add(self._current_step)
        if self._current_step < len(self._steps) - 1:
            self._current_step += 1
            self._update_step_visuals()
            self._update_progress_text()
            self._show_current_step()
        else:
            self._finish_tutorial()

    # ------------------------------------------------------------------ click polling

    def start_click_polling(self):
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_click)
        self._poll_timer.start(100)
        self._last_left = False
        self._last_right = False
        self._step_shown_time = time.time()

    def _check_click(self):
        if not self._sm.is_state(AppState.WAITING_FOR_USER):
            return
        ldown = bool(win32api.GetAsyncKeyState(0x01) & 0x8000)
        rdown = bool(win32api.GetAsyncKeyState(0x02) & 0x8000)
        clicked = (ldown and not self._last_left) or (rdown and not self._last_right)
        self._last_left = ldown
        self._last_right = rdown
        if not clicked:
            return
        if time.time() - self._step_shown_time < 1.0:
            return
        cx, cy = win32api.GetCursorPos()
        tx, ty = self._current_target
        dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
        print(f"[click] at ({cx},{cy}) target ({tx},{ty}) dist={dist:.0f}")
        if dist < 300:
            self._on_correct_click()
        else:
            self._on_wrong_click(cx, cy)

    def _on_correct_click(self):
        self._sm.set_state(AppState.GUIDING)
        self._cursor.flash_green()
        if self._current_step >= len(self._steps) - 1:
            QTimer.singleShot(600, self._finish_tutorial)
            return
        QTimer.singleShot(600, self._find_and_advance)

    def _on_wrong_click(self, cx, cy):
        self._cursor.flash_red()
        self._guide_status_lbl.setText("Try again — click closer to the cursor")
        QTimer.singleShot(2000, lambda: self._guide_status_lbl.setText(""))

    def _find_and_advance(self):
        next_idx = self._current_step + 1
        next_step = self._steps[next_idx]
        self._guide_status_lbl.setText("Finding next target...")

        def find_next():
            screenshot = screen_parser.take_screenshot()
            coords = screen_parser.find_element(next_step.get('anchor', ''), screenshot)
            if coords is None:
                coords = screen_parser.find_element(next_step.get('title', ''), screenshot)
            return (coords, next_step, next_idx)

        worker = Worker(find_next)
        worker.signals.result.connect(self._on_next_found)
        worker.signals.error.connect(lambda e: self._fallback_advance(next_step, next_idx))
        self._workers.append(worker)
        worker.signals.finished.connect(
            lambda: self._workers.remove(worker) if worker in self._workers else None
        )
        QThreadPool.globalInstance().start(worker)

    def _on_next_found(self, result):
        coords, next_step, next_idx = result
        self._completed_steps.add(self._current_step)
        self._current_step = next_idx
        if coords:
            x, y = coords
        else:
            x, y = locator.get_coordinates(next_step.get('anchor', ''))
        self._current_target = (x, y)
        self._step_shown_time = time.time()
        self._cursor.move_to(x, y, next_step.get('action', 'click'))
        self._sm.set_state(AppState.WAITING_FOR_USER)
        self._update_step_visuals()
        self._update_progress_text()
        self._guide_status_lbl.setText("")

    def _fallback_advance(self, next_step=None, next_idx=None):
        if next_step is None:
            next_idx = self._current_step + 1
            next_step = self._steps[next_idx]
        x, y = locator.get_coordinates(next_step.get('anchor', ''))
        self._on_next_found(((x, y), next_step, next_idx))
