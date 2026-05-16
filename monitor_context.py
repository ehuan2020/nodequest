from dataclasses import dataclass
import win32gui
import win32api
import win32con


@dataclass
class MonitorContext:
    monitor_id: int
    bounds: dict  # keys: left, top, right, bottom, width, height
    dpi_scale: float
    is_primary: bool


def get_ue5_hwnd() -> int | None:
    result = []

    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Unreal Editor" in title or "Unreal Engine" in title:
                result.append(hwnd)

    win32gui.EnumWindows(_cb, None)
    return result[0] if result else None


def is_exclusive_fullscreen(hwnd) -> bool:
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    has_caption = bool(style & win32con.WS_CAPTION)
    if has_caption:
        return False
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
    info = win32api.GetMonitorInfo(monitor)
    ml, mt, mr, mb = info["Monitor"]
    return left == ml and top == mt and right == mr and bottom == mb


def adjust_for_dpi(x: float, y: float, ctx: MonitorContext) -> tuple[float, float]:
    return float(x * ctx.dpi_scale), float(y * ctx.dpi_scale)


def get_ue5_monitor() -> MonitorContext | None:
    hwnd = get_ue5_hwnd()
    if hwnd is None:
        return None

    monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
    info = win32api.GetMonitorInfo(monitor)
    ml, mt, mr, mb = info["Monitor"]
    bounds = {
        "left": ml,
        "top": mt,
        "right": mr,
        "bottom": mb,
        "width": mr - ml,
        "height": mb - mt,
    }
    is_primary = bool(info["Flags"] & 1)

    try:
        raw_dpi = win32api.GetDpiForWindow(hwnd)
        dpi_scale = raw_dpi / 96.0
    except Exception:
        dpi_scale = 1.0

    return MonitorContext(
        monitor_id=int(monitor),
        bounds=bounds,
        dpi_scale=dpi_scale,
        is_primary=is_primary,
    )
