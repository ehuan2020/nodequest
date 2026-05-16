import os, json, re
from google import genai


def get_api_key():
    try:
        with open("D:/nodequest/api_key.txt", "rb") as f:
            raw = f.read()
        for encoding in ("utf-8-sig", "utf-16", "latin-1"):
            try:
                key = raw.decode(encoding).strip()
                break
            except Exception:
                continue
        key = key.encode("ascii", errors="ignore").decode("ascii")
        print(f"[gemini] API key loaded, length: {len(key)}")
        return key
    except Exception as e:
        print(f"[gemini] Key error: {e}")
        return os.environ.get("GOOGLE_API_KEY", "")


_key = get_api_key()
print(f"[gemini] Client init with key length: {len(_key)}")
client = genai.Client(api_key=_key)

MOCK_STEPS = [
    {"step_number": 1, "title": "Right-click in Content Browser", "description": "Right-click on empty space in the Content Browser", "action": "right-click", "anchor": "Content Browser", "relative_position": "center", "recovery_hint": "Open Content Browser from Window menu", "recovery_anchor": "Main Toolbar"},
    {"step_number": 2, "title": "Select Blueprint Class", "description": "Click Blueprint Class from the context menu", "action": "left-click", "anchor": "Content Browser", "relative_position": "context-menu", "recovery_hint": "Right-click empty space first", "recovery_anchor": "Content Browser"},
    {"step_number": 3, "title": "Choose Parent Class", "description": "Click Actor then click Select", "action": "left-click", "anchor": "Viewport Center", "relative_position": "center", "recovery_hint": "A dialog should have appeared", "recovery_anchor": "Viewport Center"},
    {"step_number": 4, "title": "Name the Blueprint", "description": "Type a name and press Enter", "action": "type", "anchor": "Content Browser", "relative_position": "rename", "recovery_hint": "New asset should be waiting to be named", "recovery_anchor": "Content Browser"},
    {"step_number": 5, "title": "Open the Blueprint", "description": "Double-click your new Blueprint to open it", "action": "double-click", "anchor": "Content Browser", "relative_position": "center", "recovery_hint": "Find your Blueprint in Content Browser", "recovery_anchor": "Content Browser"},
]


_MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]


def generate_steps(goal: str, screenshot_base64: str = "") -> list[dict]:
    prompt = f"""You are a UE5 expert. The user wants to: {goal}

Generate exactly 5 steps. Return ONLY a valid JSON array, no markdown, no explanation.
Each item must have: step_number (int), title (str), description (str), action (str), anchor (str — must be one of: Main Toolbar, Content Browser, Details Panel, Outliner, Viewport Center), relative_position (str), recovery_hint (str max 15 words), recovery_anchor (str).
Assume default UE5 layout is open. Do not include steps to open panels that are already visible."""

    for model in _MODELS:
        try:
            print(f"[gemini] Trying {model}...")
            response = client.models.generate_content(model=model, contents=prompt)
            raw = response.text
            print(f"[gemini] {model} responded: {raw[:200]}")
            text = re.sub(r"```json|```", "", raw).strip()
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if not match:
                print(f"[gemini] {model} returned no JSON array, trying next model")
                continue
            steps = json.loads(match.group())
            print(f"[gemini] Success with {model}")
            return steps
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                print(f"[gemini] {model} rate-limited, trying next model")
            else:
                print(f"[gemini] {model} error: {e}, trying next model")

    print("[gemini] All models failed, using mock steps")
    return MOCK_STEPS
