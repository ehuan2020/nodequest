import json
import os
import time

COMMAND_FILE = "D:/nodequest/ue5_command.py"
RESULT_FILE = "D:/nodequest/ue5_result.json"


def send_command(python_code: str, timeout: float = 5.0) -> dict:
    if os.path.exists(RESULT_FILE):
        os.remove(RESULT_FILE)

    with open(COMMAND_FILE, "w") as f:
        f.write(python_code)

    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(RESULT_FILE):
            try:
                with open(RESULT_FILE) as f:
                    return json.load(f)
            except:
                pass
        time.sleep(0.1)

    return {"error": "timeout - UE5 did not respond"}


def get_panel_positions() -> dict:
    code = """
import unreal, json, os
result = {}
try:
    result["status"] = "connected"
    result["ue5_version"] = str(unreal.SystemLibrary.get_engine_version())
except Exception as e:
    result["error"] = str(e)
with open("D:/nodequest/ue5_result.json", "w") as f:
    json.dump(result, f)
"""
    return send_command(code)
