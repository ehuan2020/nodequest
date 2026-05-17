import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThreadPool
from cursor import CursorOverlay
from overlay import OverlayWindow
from worker import Worker


def _preload_omniparser_models():
    import screen_parser
    screen_parser.load_models()


def main():
    app = QApplication(sys.argv)

    preload_worker = Worker(_preload_omniparser_models)
    preload_worker.signals.error.connect(
        lambda e: print(f"[main] OmniParser preload failed: {e}")
    )
    QThreadPool.globalInstance().start(preload_worker)

    cursor = CursorOverlay()
    cursor.show()
    geo = cursor.geometry()
    print(f"[cursor] window geometry: x={geo.x()} y={geo.y()} w={geo.width()} h={geo.height()}")

    window = OverlayWindow(cursor_overlay=cursor)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
