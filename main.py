import sys
from PyQt6.QtWidgets import QApplication
from cursor import CursorOverlay
from overlay import OverlayWindow


def main():
    app = QApplication(sys.argv)

    cursor = CursorOverlay()
    cursor.show()
    geo = cursor.geometry()
    print(f"[cursor] window geometry: x={geo.x()} y={geo.y()} w={geo.width()} h={geo.height()}")

    window = OverlayWindow(cursor_overlay=cursor)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
