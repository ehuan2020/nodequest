import win32gui
from monitor_context import get_ue5_monitor, get_ue5_hwnd


def _print_all_windows():
    print("=== All visible window titles ===")
    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                safe = title.encode("cp1252", errors="replace").decode("cp1252")
                print(f"  [{hwnd}] {safe}")
    win32gui.EnumWindows(_cb, None)
    print()


if __name__ == "__main__":
    _print_all_windows()

    hwnd = get_ue5_hwnd()
    print(f"UE5 hwnd: {hwnd}")

    ctx = get_ue5_monitor()
    if ctx:
        print(f"MonitorContext: {ctx}")
        print(f"DPI scale: {ctx.dpi_scale}")
    else:
        print("UE5 window not found — open Unreal Editor and re-run.")
