import json

COORDS_FILE = "D:/nodequest/coordinates.json"


def get_coordinates(anchor: str) -> tuple[float, float]:
    try:
        with open(COORDS_FILE) as f:
            data = json.load(f)

        anchor_lower = anchor.lower()

        for key in data:
            if isinstance(data[key], dict) and key.lower() == anchor_lower:
                return float(data[key]["x"]), float(data[key]["y"])

        if any(w in anchor_lower for w in ["browser", "content", "asset"]):
            v = data.get("Content Browser", {"x": 1834, "y": 1154})
            return float(v["x"]), float(v["y"])
        if any(w in anchor_lower for w in ["toolbar", "menu", "tool", "button", "add"]):
            v = data.get("Main Toolbar", {"x": 244, "y": 9})
            return float(v["x"]), float(v["y"])
        if any(w in anchor_lower for w in ["detail", "property", "inspect"]):
            v = data.get("Details Panel", {"x": 1991, "y": 523})
            return float(v["x"]), float(v["y"])
        if any(w in anchor_lower for w in ["outline", "scene", "world", "actor"]):
            v = data.get("Outliner", {"x": 2011, "y": 115})
            return float(v["x"]), float(v["y"])

        v = data.get("Viewport Center", {"x": 1255, "y": 444})
        return float(v["x"]), float(v["y"])

    except Exception as e:
        print(f"[locator] error: {e}")
        return 1255.0, 444.0
