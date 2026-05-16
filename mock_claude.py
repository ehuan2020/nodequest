def generate_steps(goal: str, screenshot_base64: str) -> list[dict]:
    return [
        {
            "step_number": 1,
            "title": "Open Content Browser",
            "description": "Click the Content Browser tab at the bottom of the screen",
            "action": "left-click",
            "anchor": "Main Toolbar",
            "relative_position": "tab",
            "recovery_hint": "Go to Window menu and click Content Browser",
            "recovery_anchor": "Main Toolbar",
        },
        {
            "step_number": 2,
            "title": "Create New Material",
            "description": "Right-click in an empty area of the Content Browser",
            "action": "right-click",
            "anchor": "Content Browser",
            "relative_position": "center",
            "recovery_hint": "Make sure Content Browser panel is open and visible",
            "recovery_anchor": "Content Browser",
        },
        {
            "step_number": 3,
            "title": "Select Material Option",
            "description": "Hover over Create Basic Asset and click Material",
            "action": "left-click",
            "anchor": "Content Browser",
            "relative_position": "context-menu",
            "recovery_hint": "Right-click empty space in Content Browser first",
            "recovery_anchor": "Content Browser",
        },
        {
            "step_number": 4,
            "title": "Name Your Material",
            "description": "Type a name for your new material and press Enter",
            "action": "type",
            "anchor": "Details Panel",
            "relative_position": "rename-field",
            "recovery_hint": "A new asset should appear waiting to be named",
            "recovery_anchor": "Details Panel",
        },
        {
            "step_number": 5,
            "title": "Open the Material",
            "description": "Double-click your new material to open the Material Editor",
            "action": "double-click",
            "anchor": "Viewport Center",
            "relative_position": "center",
            "recovery_hint": "Find your material in the Content Browser and double-click it",
            "recovery_anchor": "Viewport Center",
        },
    ]


_ANCHOR_COORDS = {
    "Content Browser": {"x": 400.0, "y": 850.0, "confidence": "high"},
    "Main Toolbar":    {"x": 600.0, "y": 30.0,  "confidence": "high"},
    "Material Editor": {"x": 700.0, "y": 400.0, "confidence": "high"},
}
_DEFAULT_COORDS = {"x": 500.0, "y": 500.0, "confidence": "low"}


def find_coordinates_fallback(anchor: str, description: str, screenshot_base64: str) -> dict:
    return _ANCHOR_COORDS.get(anchor, _DEFAULT_COORDS)
